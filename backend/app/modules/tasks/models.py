from datetime import date, datetime
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.ids import new_id
from app.core.time import utc_now


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("task"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(64), default="Normalni", nullable=False)
    assigned_to_all: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    assigned_user_id: Mapped[str | None] = mapped_column(String(64), index=True)
    recurrence_type: Mapped[str | None] = mapped_column(String(32), index=True)
    recurrence_days: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    recurrence_interval_days: Mapped[int | None] = mapped_column(Integer)
    recurrence_end_date: Mapped[date | None] = mapped_column(Date, index=True)
    created_by_user_id: Mapped[str | None] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    completions: Mapped[list["TaskOccurrenceCompletion"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def recurrence_days_list(self) -> list[str]:
        if isinstance(self.recurrence_days, list):
            return [str(day).lower() for day in self.recurrence_days]
        return []


class TaskOccurrenceCompletion(Base):
    __tablename__ = "task_occurrence_completions"
    __table_args__ = (UniqueConstraint("task_id", "occurrence_date", name="uq_task_occurrence_completion"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("task_done"))
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    occurrence_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    completed_by_user_id: Mapped[str | None] = mapped_column(String(64), index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    task: Mapped[Task] = relationship(back_populates="completions")
