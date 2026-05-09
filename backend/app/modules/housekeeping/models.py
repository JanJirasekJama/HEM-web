"""Housekeeping SQLAlchemy models are owned by the housekeeping module."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.ids import new_id
from app.core.time import utc_now


class HousekeepingAssignment(Base):
    __tablename__ = "housekeeping_assignments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("hk_asg"))
    room_id: Mapped[str] = mapped_column(ForeignKey("catalog_hotel_rooms.id"), nullable=False, index=True)
    room_label_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    work_type: Mapped[str] = mapped_column(String(128), nullable=False)
    priority: Mapped[str] = mapped_column(String(64), nullable=False)
    reception_note: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(64), default="Prideleno", nullable=False, index=True)
    assigned_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    started_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    finished_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pause_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paused_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AssignmentRequiredPhoto(Base):
    __tablename__ = "housekeeping_assignment_required_photos"
    __table_args__ = (UniqueConstraint("assignment_id", "photo_task_type_id", name="uq_hk_required_photo"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("hk_req_photo"))
    assignment_id: Mapped[str] = mapped_column(ForeignKey("housekeeping_assignments.id", ondelete="CASCADE"), nullable=False, index=True)
    photo_task_type_id: Mapped[str] = mapped_column(ForeignKey("catalog_photo_task_types.id"), nullable=False)
    task_label_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)


class AssignmentPhoto(Base):
    __tablename__ = "housekeeping_assignment_photos"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("hk_photo"))
    assignment_id: Mapped[str] = mapped_column(ForeignKey("housekeeping_assignments.id", ondelete="CASCADE"), nullable=False, index=True)
    media_file_id: Mapped[str] = mapped_column(ForeignKey("media_files.id"), nullable=False)
    photo_task_type_id: Mapped[str | None] = mapped_column(ForeignKey("catalog_photo_task_types.id"))
    task_label: Mapped[str | None] = mapped_column(String(255))
    created_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AssignmentMinibarEntry(Base):
    __tablename__ = "housekeeping_assignment_minibar_entries"
    __table_args__ = (UniqueConstraint("assignment_id", "item_id", name="uq_hk_assignment_minibar_item"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("hk_minibar_row"))
    assignment_id: Mapped[str] = mapped_column(ForeignKey("housekeeping_assignments.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id: Mapped[str] = mapped_column(ForeignKey("catalog_housekeeping_minibar_items.id"), nullable=False)
    item_name_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AssignmentHistory(Base):
    __tablename__ = "housekeeping_assignment_history"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("hk_hist"))
    assignment_id: Mapped[str] = mapped_column(ForeignKey("housekeeping_assignments.id", ondelete="CASCADE"), nullable=False, index=True)
    room_id: Mapped[str] = mapped_column(String(64), nullable=False)
    room_label_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    work_type: Mapped[str] = mapped_column(String(128), nullable=False)
    priority: Mapped[str] = mapped_column(String(64), nullable=False)
    housekeeper_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    housekeeper_username_snapshot: Mapped[str | None] = mapped_column(String(128))
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)


class RevisionTask(Base):
    __tablename__ = "housekeeping_revision_tasks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("hk_rev"))
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="open", nullable=False, index=True)
    created_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    completed_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completion_note: Mapped[str | None] = mapped_column(Text)


class RevisionPhoto(Base):
    __tablename__ = "housekeeping_revision_photos"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("hk_rev_photo"))
    revision_id: Mapped[str] = mapped_column(ForeignKey("housekeeping_revision_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    media_file_id: Mapped[str] = mapped_column(ForeignKey("media_files.id"), nullable=False)
    created_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class LaundryTask(Base):
    __tablename__ = "housekeeping_laundry_tasks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("hk_laundry"))
    status: Mapped[str] = mapped_column(String(32), default="open", nullable=False, index=True)
    created_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    accepted_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    done_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)


class LaundryPhoto(Base):
    __tablename__ = "housekeeping_laundry_photos"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("hk_laundry_photo"))
    laundry_id: Mapped[str] = mapped_column(ForeignKey("housekeeping_laundry_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    media_file_id: Mapped[str] = mapped_column(ForeignKey("media_files.id"), nullable=False)
    created_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
