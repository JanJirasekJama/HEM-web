from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_csrf
from app.core.models import User
from app.core.time import utc_now
from app.modules.tasks.models import Task, TaskOccurrenceCompletion

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    due_date: date
    priority: str = "Normalni"
    assigned_to_all: bool = False
    assigned_user_id: str | None = None
    recurrence_type: Literal["weekly", "interval"] | None = None
    recurrence_days: list[str] = Field(default_factory=list)
    recurrence_interval_days: int | None = Field(default=None, ge=1)
    interval_days: int | None = Field(default=None, ge=1)
    recurrence_end_date: date | None = None

    @field_validator("recurrence_days")
    @classmethod
    def normalize_weekdays(cls, value: list[str]) -> list[str]:
        days = [day.lower() for day in value]
        unknown = [day for day in days if day not in WEEKDAYS]
        if unknown:
            raise ValueError(f"Unknown recurrence day: {unknown[0]}")
        return days


class TaskCompletionUpdate(BaseModel):
    completed: bool
    occurrence_date: date | None = None


def _task_payload(task: Task, occurrence_date: date | None = None, completed: bool = False) -> dict:
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "due_date": task.due_date.isoformat(),
        "occurrence_date": (occurrence_date or task.due_date).isoformat(),
        "priority": task.priority,
        "assigned_to_all": task.assigned_to_all,
        "assigned_user_id": task.assigned_user_id,
        "recurrence_type": task.recurrence_type,
        "recurrence_days": task.recurrence_days_list(),
        "recurrence_interval_days": task.recurrence_interval_days,
        "recurrence_end_date": task.recurrence_end_date.isoformat() if task.recurrence_end_date else None,
        "completed": completed,
    }


@router.post("", dependencies=[Depends(require_csrf)])
def create_task(payload: TaskCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    interval_days = payload.recurrence_interval_days or payload.interval_days
    if payload.recurrence_type == "weekly" and not payload.recurrence_days:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Weekly recurrence requires recurrence_days")
    if payload.recurrence_type == "interval" and not interval_days:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Interval recurrence requires recurrence_interval_days")
    if payload.recurrence_end_date and payload.recurrence_end_date < payload.due_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="recurrence_end_date cannot be before due_date")

    task = Task(
        title=payload.title,
        description=payload.description,
        due_date=payload.due_date,
        priority=payload.priority,
        assigned_to_all=payload.assigned_to_all,
        assigned_user_id=payload.assigned_user_id,
        recurrence_type=payload.recurrence_type,
        recurrence_days=payload.recurrence_days,
        recurrence_interval_days=interval_days,
        recurrence_end_date=payload.recurrence_end_date,
        created_by_user_id=user.id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return _task_payload(task)


@router.get("/calendar")
def calendar(date: date, db: Session = Depends(get_db)) -> dict:
    candidates = db.scalars(
        select(Task)
        .where(Task.due_date <= date)
        .where((Task.recurrence_end_date.is_(None)) | (Task.recurrence_end_date >= date))
        .order_by(Task.due_date, Task.created_at)
    ).all()
    tasks = [task for task in candidates if _occurs_on(task, date)]
    completion_rows = db.scalars(
        select(TaskOccurrenceCompletion).where(
            TaskOccurrenceCompletion.task_id.in_([task.id for task in tasks]),
            TaskOccurrenceCompletion.occurrence_date == date,
        )
    ).all() if tasks else []
    completed_by_task_id = {row.task_id: row.completed for row in completion_rows}

    items = [_task_payload(task, occurrence_date=date, completed=completed_by_task_id.get(task.id, False)) for task in tasks]
    return {"date": date.isoformat(), "tasks": items, "stats": _stats(items)}


@router.patch("/{task_id}/completion", dependencies=[Depends(require_csrf)])
def update_completion(
    task_id: str,
    payload: TaskCompletionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    occurrence_date = payload.occurrence_date or task.due_date
    if not _occurs_on(task, occurrence_date):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Task does not occur on occurrence_date")

    completion = db.scalar(
        select(TaskOccurrenceCompletion).where(
            TaskOccurrenceCompletion.task_id == task.id,
            TaskOccurrenceCompletion.occurrence_date == occurrence_date,
        )
    )
    if completion is None:
        completion = TaskOccurrenceCompletion(task_id=task.id, occurrence_date=occurrence_date)
        db.add(completion)

    completion.completed = payload.completed
    completion.completed_by_user_id = user.id if payload.completed else None
    completion.completed_at = utc_now() if payload.completed else None
    db.commit()
    db.refresh(task)
    return _task_payload(task, occurrence_date=occurrence_date, completed=payload.completed)


@router.delete("/{task_id}", dependencies=[Depends(require_csrf)])
def delete_task(task_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> dict[str, bool]:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    db.execute(delete(TaskOccurrenceCompletion).where(TaskOccurrenceCompletion.task_id == task.id))
    db.delete(task)
    db.commit()
    return {"ok": True}


def _occurs_on(task: Task, occurrence_date: date) -> bool:
    if occurrence_date < task.due_date:
        return False
    if task.recurrence_end_date and occurrence_date > task.recurrence_end_date:
        return False
    if task.recurrence_type is None:
        return occurrence_date == task.due_date
    if task.recurrence_type == "weekly":
        return WEEKDAYS[occurrence_date.weekday()] in task.recurrence_days_list()
    if task.recurrence_type == "interval":
        interval_days = task.recurrence_interval_days or 1
        return (occurrence_date - task.due_date).days % interval_days == 0
    return False


def _stats(items: list[dict]) -> dict:
    priority: dict[str, int] = {}
    completed = 0
    for item in items:
        priority[item["priority"]] = priority.get(item["priority"], 0) + 1
        if item["completed"]:
            completed += 1
    total = len(items)
    return {"total": total, "open": total - completed, "completed": completed, "priority": priority}
