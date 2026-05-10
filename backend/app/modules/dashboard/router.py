from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import Base, get_db
from app.core.deps import get_current_user
from app.core.models import User
from app.core.time import utc_now

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
def dashboard(date: date | None = None, current_time: datetime | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict[str, Any]:
    target_date = date or utc_now().date()
    now = _aware(current_time or utc_now())
    return {
        "current_user": {"id": user.id, "username": user.username, "display_name": user.display_name, "role": user.role.name},
        "messages_today": _messages_today(db, target_date),
        "open_tasks_today": _open_tasks_today(db, target_date),
        "open_task_list": _open_task_list(db, target_date),
        "cash": _cash_status(db, target_date, user.id, now),
        "invoices": _invoice_status(db, now),
        "housekeeping": _housekeeping_status(db),
    }


def _messages_today(db: Session, target_date: date) -> int:
    messages = Base.metadata.tables["communication_daily_messages"]
    return int(db.scalar(select(func.count()).select_from(messages).where(messages.c.message_date == target_date)) or 0)


def _open_tasks_today(db: Session, target_date: date) -> int:
    tasks = Base.metadata.tables["tasks"]
    completions = Base.metadata.tables["task_occurrence_completions"]
    task_ids = [row.id for row in db.execute(select(tasks.c.id).where(tasks.c.due_date == target_date)).all()]
    completed_ids = {
        row.task_id
        for row in db.execute(
            select(completions.c.task_id).where(
                completions.c.occurrence_date == target_date,
                completions.c.completed.is_(True),
            )
        ).all()
    }
    return len([task_id for task_id in task_ids if task_id not in completed_ids])


def _open_task_list(db: Session, target_date: date) -> list[dict[str, Any]]:
    tasks = Base.metadata.tables["tasks"]
    completions = Base.metadata.tables["task_occurrence_completions"]
    completed_ids = {
        row.task_id
        for row in db.execute(
            select(completions.c.task_id).where(completions.c.occurrence_date == target_date, completions.c.completed.is_(True))
        ).all()
    }
    rows = db.execute(select(tasks.c.id, tasks.c.title, tasks.c.priority).where(tasks.c.due_date == target_date).order_by(tasks.c.created_at)).all()
    return [{"id": row.id, "title": row.title, "priority": row.priority} for row in rows if row.id not in completed_ids]


def _cash_status(db: Session, target_date: date, user_id: str, now: datetime) -> dict[str, Any]:
    diary = Base.metadata.tables["cash_diary_entries"]
    today = db.execute(select(diary).where(diary.c.entry_date == target_date, diary.c.user_id == user_id)).first()
    yesterday = db.execute(select(diary.c.cash_end).where(diary.c.entry_date == target_date - timedelta(days=1), diary.c.user_id == user_id)).first()
    missing_morning = today is None or today.cash_start is None
    missing_evening = now.timetz().replace(tzinfo=None) >= time(20, 0) and (today is None or today.cash_end is None)
    return {
        "missing_morning_cash": missing_morning,
        "missing_evening_cash": missing_evening,
        "cash_start": None if today is None else today.cash_start,
        "cash_end": None if today is None else today.cash_end,
        "yesterday_cash_end": None if yesterday is None else yesterday.cash_end,
    }


def _invoice_status(db: Session, now: datetime) -> dict[str, Any]:
    invoices = Base.metadata.tables["invoices"]
    due_or_overdue = int(
        db.scalar(
            select(func.count()).select_from(invoices).where(
                invoices.c.payment_status.in_(["pending", "unpaid", "overdue"]),
                invoices.c.due_at <= now,
            )
        )
        or 0
    )
    return {"due_or_overdue": due_or_overdue}


def _housekeeping_status(db: Session) -> dict[str, int]:
    assignments = Base.metadata.tables["housekeeping_assignments"]
    laundry = Base.metadata.tables["housekeeping_laundry_tasks"]
    revisions = Base.metadata.tables["housekeeping_revision_tasks"]
    rows = db.execute(select(assignments.c.status, func.count()).group_by(assignments.c.status)).all()
    by_status = {str(status): int(count) for status, count in rows}
    return {
        "waiting": sum(by_status.get(status, 0) for status in ["Prideleno", "Ceka", "waiting"]),
        "cleaning": sum(by_status.get(status, 0) for status in ["Uklizi se", "cleaning"]),
        "done": sum(by_status.get(status, 0) for status in ["Hotovo", "done"]),
        "laundry_active": int(db.scalar(select(func.count()).select_from(laundry).where(laundry.c.status.in_(["open", "accepted"]))) or 0),
        "open_revisions": int(db.scalar(select(func.count()).select_from(revisions).where(revisions.c.status == "open")) or 0),
    }


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
