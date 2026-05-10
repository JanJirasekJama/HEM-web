from datetime import UTC, date, datetime, time
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.models import User
from app.core.time import utc_now
from app.modules.cash.queries import get_cash_diary_status
from app.modules.communication.queries import count_daily_messages
from app.modules.housekeeping.queries import get_housekeeping_dashboard_status
from app.modules.invoicing.queries import count_due_or_overdue_invoices
from app.modules.tasks.queries import list_open_task_summaries

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
    return count_daily_messages(db, target_date)


def _open_tasks_today(db: Session, target_date: date) -> int:
    return len(list_open_task_summaries(db, target_date))


def _open_task_list(db: Session, target_date: date) -> list[dict[str, Any]]:
    return [
        {"id": task.id, "title": task.title, "priority": task.priority}
        for task in list_open_task_summaries(db, target_date)
    ]


def _cash_status(db: Session, target_date: date, user_id: str, now: datetime) -> dict[str, Any]:
    status = get_cash_diary_status(db, target_date, user_id)
    missing_morning = not status.has_today_entry or status.cash_start is None
    missing_evening = now.timetz().replace(tzinfo=None) >= time(20, 0) and (
        not status.has_today_entry or status.cash_end is None
    )
    return {
        "missing_morning_cash": missing_morning,
        "missing_evening_cash": missing_evening,
        "cash_start": status.cash_start,
        "cash_end": status.cash_end,
        "yesterday_cash_end": status.yesterday_cash_end,
    }


def _invoice_status(db: Session, now: datetime) -> dict[str, Any]:
    return {"due_or_overdue": count_due_or_overdue_invoices(db, now)}


def _housekeeping_status(db: Session) -> dict[str, int]:
    return get_housekeeping_dashboard_status(db)


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
