from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.ids import new_id
from app.core.time import utc_now


class BackupRecord(Base):
    __tablename__ = "backup_records"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("backup"))
    backup_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="completed", nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    retained_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)


class RecoveryPoint(Base):
    __tablename__ = "recovery_points"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("recovery"))
    description: Mapped[str | None] = mapped_column(Text)
    data_snapshot_path: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    restored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    restore_metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)


class RestoreRecord(Base):
    __tablename__ = "restore_records"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("restore"))
    recovery_point_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    restored_by: Mapped[str | None] = mapped_column(String(64))
    restored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
