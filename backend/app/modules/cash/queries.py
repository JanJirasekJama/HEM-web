"""Read-only query contracts for cash-owned data."""

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.cash.models import CashDiaryEntry


@dataclass(frozen=True)
class CashDiaryStatus:
    cash_start: float | None
    cash_end: float | None
    yesterday_cash_end: float | None
    has_today_entry: bool


def get_cash_diary_status(db: Session, target_date: date, user_id: str) -> CashDiaryStatus:
    today = db.scalar(
        select(CashDiaryEntry).where(
            CashDiaryEntry.entry_date == target_date,
            CashDiaryEntry.user_id == user_id,
        )
    )
    yesterday_cash_end = db.scalar(
        select(CashDiaryEntry.cash_end).where(
            CashDiaryEntry.entry_date == target_date - timedelta(days=1),
            CashDiaryEntry.user_id == user_id,
        )
    )
    return CashDiaryStatus(
        cash_start=None if today is None else today.cash_start,
        cash_end=None if today is None else today.cash_end,
        yesterday_cash_end=yesterday_cash_end,
        has_today_entry=today is not None,
    )
