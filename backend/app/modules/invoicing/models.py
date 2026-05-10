"""Invoicing SQLAlchemy models are owned by the invoicing module."""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.ids import new_id
from app.core.time import utc_now


class InvoiceCounter(Base):
    __tablename__ = "invoice_counters"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("invoice_counter"))
    year: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)
    next_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (UniqueConstraint("invoice_number", name="uq_invoices_invoice_number"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("invoice"))
    invoice_number: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    variable_symbol: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_email: Mapped[str | None] = mapped_column(String(255))
    customer_phone: Mapped[str | None] = mapped_column(String(64))
    service_id: Mapped[str | None] = mapped_column(String(64), index=True)
    service_name: Mapped[str] = mapped_column(String(255), nullable=False)
    custom_service_name: Mapped[str | None] = mapped_column(String(255))
    event_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    due_term_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    due_term_name: Mapped[str] = mapped_column(String(255), nullable=False)
    due_term_value: Mapped[int] = mapped_column(Integer, nullable=False)
    due_term_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    base_price: Mapped[float] = mapped_column(Float, nullable=False)
    increase_percent: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    pdf_path: Mapped[str] = mapped_column(String(512), nullable=False)
    payment_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class InvoiceEmailIntent(Base):
    __tablename__ = "invoice_email_intents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("invoice_email"))
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    recipient: Mapped[str] = mapped_column(String(255), nullable=False)
    sender: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    attachment_path: Mapped[str] = mapped_column(Text, nullable=False)
    smtp_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False)
    response_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
