"""Read-only query contracts for invoicing-owned data."""

from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.modules.invoicing.models import Invoice


@dataclass(frozen=True)
class InvoiceReportRow:
    service_name: str
    payment_status: str
    price: float


def count_due_or_overdue_invoices(db: Session, now: datetime) -> int:
    return int(
        db.scalar(
            select(func.count()).select_from(Invoice).where(
                Invoice.payment_status.in_(["pending", "unpaid", "overdue"]),
                Invoice.due_at <= now,
            )
        )
        or 0
    )


def list_invoice_report_rows(db: Session, date_from: date, date_to: date) -> list[InvoiceReportRow]:
    start = datetime.combine(date_from, datetime.min.time(), tzinfo=UTC)
    end = datetime.combine(date_to, datetime.max.time(), tzinfo=UTC)
    rows = db.execute(
        select(Invoice.service_name, Invoice.payment_status, Invoice.price).where(
            and_(Invoice.event_at >= start, Invoice.event_at <= end)
        )
    ).all()
    return [
        InvoiceReportRow(service_name=row.service_name, payment_status=row.payment_status, price=row.price)
        for row in rows
    ]
