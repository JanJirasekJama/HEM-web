import csv
from datetime import UTC, datetime, timedelta
from io import StringIO
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_app_settings, get_current_user, require_csrf
from app.core.models import User
from app.core.time import utc_now
from app.modules.catalog.models import DueTerm, Service
from app.modules.invoicing.models import Invoice, InvoiceCounter

router = APIRouter(prefix="/api/invoices", tags=["invoicing"])

EVENT_FORMATS = ("%d.%m.%Y %H:%M", "%d.%m.%Y")
ALLOWED_DUE_UNITS = {"hodiny", "dny"}


class InvoiceCreate(BaseModel):
    customer_name: str = Field(min_length=1, max_length=255)
    customer_email: str | None = Field(default=None, max_length=255)
    customer_phone: str | None = Field(default=None, max_length=64)
    service_id: str | None = None
    custom_service_name: str | None = Field(default=None, max_length=255)
    event_at: str
    due_term_id: str
    price: float | None = None
    increase_percent: float = 0
    note: str | None = None

    @field_validator("event_at")
    @classmethod
    def validate_event_at(cls, value: str) -> str:
        _parse_event_at(value)
        return value

    @model_validator(mode="after")
    def validate_service_choice(self) -> "InvoiceCreate":
        if bool(self.service_id) == bool(self.custom_service_name):
            raise ValueError("Provide exactly one of service_id or custom_service_name")
        if self.custom_service_name and self.price is None:
            raise ValueError("Custom service requires price")
        return self


class StatusRefreshRequest(BaseModel):
    current_time: datetime | None = None


class StatusRefreshRead(BaseModel):
    updated: int


class InvoiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    invoice_number: str
    variable_symbol: str
    customer_name: str
    customer_email: str | None = None
    customer_phone: str | None = None
    service_id: str | None = None
    service_name: str
    custom_service_name: str | None = None
    event_at: datetime
    due_at: datetime
    due_term_id: str
    due_term_name: str
    due_term_value: int
    due_term_unit: str
    base_price: float
    increase_percent: float
    price: float
    note: str | None = None
    pdf_path: str
    payment_status: str
    created_at: datetime
    updated_at: datetime


@router.post("", response_model=InvoiceRead, dependencies=[Depends(require_csrf)])
def create_invoice(
    payload: InvoiceCreate,
    db: Session = Depends(get_db),
    settings=Depends(get_app_settings),
    _: User = Depends(get_current_user),
) -> Invoice:
    service_name, base_price = _resolve_service(db, payload)
    due_term = _require_due_term(db, payload.due_term_id)
    event_at = _parse_event_at(payload.event_at)
    due_at = _calculate_due_at(event_at, due_term)
    invoice_number = _next_invoice_number(db, event_at.year)
    price = _apply_increase(base_price, payload.increase_percent)
    relative_pdf_path = _write_pdf(settings.file_storage_root, invoice_number, payload.customer_name, service_name, price)

    invoice = Invoice(
        invoice_number=invoice_number,
        variable_symbol=invoice_number,
        customer_name=payload.customer_name,
        customer_email=payload.customer_email,
        customer_phone=payload.customer_phone,
        service_id=payload.service_id,
        service_name=service_name,
        custom_service_name=payload.custom_service_name,
        event_at=event_at,
        due_at=due_at,
        due_term_id=due_term.id,
        due_term_name=due_term.name,
        due_term_value=due_term.value,
        due_term_unit=due_term.unit,
        base_price=base_price,
        increase_percent=payload.increase_percent,
        price=price,
        note=payload.note,
        pdf_path=relative_pdf_path,
        payment_status="pending",
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


@router.get("/archive", response_model=list[InvoiceRead])
def list_archive(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[Invoice]:
    return list(db.scalars(select(Invoice).order_by(Invoice.created_at.desc(), Invoice.invoice_number.desc())).all())


@router.post("/archive/refresh-statuses", response_model=StatusRefreshRead, dependencies=[Depends(require_csrf)])
def refresh_statuses(payload: StatusRefreshRequest, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> StatusRefreshRead:
    current_time = _as_aware_utc(payload.current_time or utc_now())
    updated = 0
    invoices = db.scalars(select(Invoice).where(Invoice.payment_status.in_(["pending", "unpaid"]))).all()
    for invoice in invoices:
        if _as_aware_utc(invoice.due_at) < current_time and invoice.payment_status != "overdue":
            invoice.payment_status = "overdue"
            invoice.updated_at = utc_now()
            updated += 1
    if updated:
        db.commit()
    return StatusRefreshRead(updated=updated)


@router.get("/archive/export.csv")
def export_archive_csv(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> Response:
    rows = list(db.scalars(select(Invoice).order_by(Invoice.created_at, Invoice.invoice_number)).all())
    output = StringIO()
    fieldnames = [
        "id",
        "invoice_number",
        "variable_symbol",
        "customer_name",
        "service_name",
        "event_at",
        "due_at",
        "price",
        "payment_status",
        "pdf_path",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for invoice in rows:
        writer.writerow({field: getattr(invoice, field) for field in fieldnames})
    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="invoices.csv"'},
    )


@router.patch("/{invoice_id}/mark-paid", response_model=InvoiceRead, dependencies=[Depends(require_csrf)])
def mark_paid(invoice_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> Invoice:
    invoice = _require_invoice(db, invoice_id)
    invoice.payment_status = "paid"
    invoice.updated_at = utc_now()
    db.commit()
    db.refresh(invoice)
    return invoice


@router.patch("/{invoice_id}/mark-unpaid", response_model=InvoiceRead, dependencies=[Depends(require_csrf)])
def mark_unpaid(invoice_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> Invoice:
    invoice = _require_invoice(db, invoice_id)
    invoice.payment_status = "pending"
    invoice.updated_at = utc_now()
    db.commit()
    db.refresh(invoice)
    return invoice


def _parse_event_at(value: str) -> datetime:
    for fmt in EVENT_FORMATS:
        try:
            parsed = datetime.strptime(value, fmt)
        except ValueError:
            continue
        return parsed.replace(tzinfo=UTC)
    raise ValueError("Term must use DD.MM.RRRR or DD.MM.RRRR HH:MM")


def _resolve_service(db: Session, payload: InvoiceCreate) -> tuple[str, float]:
    if payload.service_id:
        service = db.get(Service, payload.service_id)
        if service is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown service")
        price = service.price if payload.price is None else payload.price
        _validate_price(price)
        return service.name, price

    if payload.custom_service_name is None or payload.price is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Custom service requires price")
    _validate_price(payload.price)
    return payload.custom_service_name, payload.price


def _validate_price(price: float) -> None:
    if price < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Price must not be negative")


def _require_due_term(db: Session, due_term_id: str) -> DueTerm:
    due_term = db.get(DueTerm, due_term_id)
    if due_term is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown due term")
    if due_term.unit not in ALLOWED_DUE_UNITS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Due term unit must be hodiny or dny")
    if due_term.value < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Due term value must not be negative")
    return due_term


def _calculate_due_at(event_at: datetime, due_term: DueTerm) -> datetime:
    if due_term.unit == "hodiny":
        return event_at + timedelta(hours=due_term.value)
    return event_at + timedelta(days=due_term.value)


def _apply_increase(base_price: float, increase_percent: float) -> float:
    _validate_price(base_price)
    price = base_price * (1 + increase_percent / 100)
    return round(price, 2)


def _next_invoice_number(db: Session, year: int) -> str:
    counter = db.scalar(select(InvoiceCounter).where(InvoiceCounter.year == year))
    if counter is None:
        counter = InvoiceCounter(year=year, next_number=1)
        db.add(counter)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            counter = db.scalar(select(InvoiceCounter).where(InvoiceCounter.year == year))
            if counter is None:
                raise
    number = counter.next_number
    counter.next_number += 1
    counter.updated_at = utc_now()
    db.flush()
    return f"{year}{number:04d}"


def _write_pdf(storage_root: Path, invoice_number: str, customer_name: str, service_name: str, price: float) -> str:
    relative_path = Path("invoices") / f"{invoice_number}.pdf"
    absolute_path = storage_root / relative_path
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    content = (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Count 1 /Kids [3 0 R] >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /Contents 4 0 R >> endobj\n"
        b"4 0 obj << /Length 64 >> stream\n"
        + f"Invoice {invoice_number} {customer_name} {service_name} {price}".encode("utf-8", errors="ignore")
        + b"\nendstream endobj\n%%EOF\n"
    )
    absolute_path.write_bytes(content)
    return relative_path.as_posix()


def _require_invoice(db: Session, invoice_id: str) -> Invoice:
    invoice = db.get(Invoice, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return invoice


def _as_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
