"""Communication SQLAlchemy models are owned by the communication module."""

from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, DateTime, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.ids import new_id
from app.core.time import utc_now


class DailyMessage(Base):
    __tablename__ = "communication_daily_messages"
    __table_args__ = (UniqueConstraint("message_date", "user_id", name="uq_daily_message_date_user"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("msg"))
    message_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    content_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    content_html: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    comments: Mapped[list["MessageComment"]] = relationship(
        back_populates="message",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class MessageComment(Base):
    __tablename__ = "communication_message_comments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("msg_cmt"))
    message_id: Mapped[str] = mapped_column(ForeignKey("communication_daily_messages.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    color: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    message: Mapped[DailyMessage] = relationship(back_populates="comments")


class MessageEmailIntent(Base):
    __tablename__ = "communication_message_email_intents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("msg_email"))
    message_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    recipients: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    counts: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False)
    response_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
