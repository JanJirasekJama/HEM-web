"""Reporting SQLAlchemy models are owned by the reporting module."""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.ids import new_id
from app.core.time import utc_now


class ExportRecord(Base):
    __tablename__ = "report_exports"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("export"))
    export_type: Mapped[str] = mapped_column(String(32), nullable=False)
    module: Mapped[str] = mapped_column(String(64), nullable=False)
    period_from: Mapped[date | None] = mapped_column(Date)
    period_to: Mapped[date | None] = mapped_column(Date)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
