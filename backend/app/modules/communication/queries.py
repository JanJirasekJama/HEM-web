"""Read-only query contracts for communication-owned data."""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.communication.models import DailyMessage


def count_daily_messages(db: Session, target_date: date) -> int:
    return int(db.scalar(select(func.count()).select_from(DailyMessage).where(DailyMessage.message_date == target_date)) or 0)
