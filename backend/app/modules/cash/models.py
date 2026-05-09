from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, DateTime, Float, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.ids import new_id
from app.core.time import utc_now


class CashShiftLog(Base):
    __tablename__ = "cash_shift_logs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("cashshift"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    shift_type: Mapped[str] = mapped_column(String(64), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cash_start: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class CashDiaryEntry(Base):
    __tablename__ = "cash_diary_entries"
    __table_args__ = (UniqueConstraint("entry_date", "user_id", name="uq_cash_diary_date_user"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("cashdiary"))
    entry_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    shift_type: Mapped[str] = mapped_column(String(64), nullable=False)
    cash_start: Mapped[float | None] = mapped_column(Float)
    cash_end: Mapped[float | None] = mapped_column(Float)
    difference: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    history: Mapped[list["CashDiaryHistory"]] = relationship(
        back_populates="entry",
        cascade="all, delete-orphan",
        order_by="CashDiaryHistory.created_at",
    )


class CashDiaryHistory(Base):
    __tablename__ = "cash_diary_history"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("cashhist"))
    diary_entry_id: Mapped[str] = mapped_column(ForeignKey("cash_diary_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    changed_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    entry: Mapped[CashDiaryEntry] = relationship(back_populates="history")
