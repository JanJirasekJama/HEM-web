"""Read-only query contracts for task-owned data."""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.tasks.models import Task, TaskOccurrenceCompletion


@dataclass(frozen=True)
class TaskSummary:
    id: str
    title: str
    priority: str


def list_open_task_summaries(db: Session, target_date: date) -> list[TaskSummary]:
    completed_ids = set(
        db.scalars(
            select(TaskOccurrenceCompletion.task_id).where(
                TaskOccurrenceCompletion.occurrence_date == target_date,
                TaskOccurrenceCompletion.completed.is_(True),
            )
        ).all()
    )
    rows = db.execute(
        select(Task.id, Task.title, Task.priority)
        .where(Task.due_date == target_date)
        .order_by(Task.created_at)
    ).all()
    return [
        TaskSummary(id=row.id, title=row.title, priority=row.priority)
        for row in rows
        if row.id not in completed_ids
    ]
