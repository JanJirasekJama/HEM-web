import csv
from datetime import UTC, datetime, timedelta
from io import StringIO
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from app.core.database import get_db
from app.core.deps import get_app_settings, get_current_user, has_permission, require_csrf
from app.core.models import Setting, User
from app.core.time import utc_now
from app.modules.catalog.models import DueTerm, Service
from app.modules.invoicing.models import Invoice, InvoiceCounter, InvoiceEmailIntent

INVOICE_PERMISSION = "invoices:*"
EVENT_FORMATS = ("%d.%m.%Y %H:%M", "%d.%m.%Y")
ALLOWED_DUE_UNITS = {"hodiny", "dny"}
DEFAULT_CANCEL_TEXT = "Storno podmínky se řídí aktuálními obchodními podmínkami provozovny."
PDF_FONT_NAME = "HEMDejaVu"
PDF_FONT_REGISTERED = False


def require_invoicing_permission(user: User = Depends(get_current_user)) -> User:
    if not has_permission(user, INVOICE_PERMISSION):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invoicing permission required")
    return user


router = APIRouter(prefix="/api/invoices", tags=["invoicing"], dependencies=[Depends(require_invoicing_permission)])


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


class InvoiceEmailRead(BaseModel):
    intent_id: str
    invoice_id: str
    recipient: str
    sender: str
    subject: str
    status: str


@router.post("", response_model=InvoiceRead, dependencies=[Depends(require_csrf)])
def create_invoice(
    payload: InvoiceCreate,
    db: Session = Depends(get_db),
    settings=Depends(get_app_settings),
) -> Invoice:
    service_name, base_price = _resolve_service(db, payload)
    due_term = _require_due_term(db, payload.due_term_id)
    event_at = _parse_event_at(payload.event_at)
    due_at = _calculate_due_at(event_at, due_term)
    invoice_number = _next_invoice_number(db, event_at.year)
    price = _apply_increase(base_price, payload.increase_percent)

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
        pdf_path=_invoice_pdf_path(invoice_number),
        payment_status="pending",
    )
    _write_pdf(settings.file_storage_root, invoice, _invoice_settings(db))
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


@router.get("/archive", response_model=list[InvoiceRead])
def list_archive(db: Session = Depends(get_db)) -> list[Invoice]:
    return list(db.scalars(select(Invoice).order_by(Invoice.created_at.desc(), Invoice.invoice_number.desc())).all())


@router.post("/archive/refresh-statuses", response_model=StatusRefreshRead, dependencies=[Depends(require_csrf)])
def refresh_statuses(payload: StatusRefreshRequest, db: Session = Depends(get_db)) -> StatusRefreshRead:
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
def export_archive_csv(db: Session = Depends(get_db)) -> Response:
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


@router.get("/{invoice_id}/pdf")
def download_pdf(invoice_id: str, db: Session = Depends(get_db), settings=Depends(get_app_settings)) -> FileResponse:
    invoice = _require_invoice(db, invoice_id)
    absolute_path = _absolute_pdf_path(settings.file_storage_root, invoice.pdf_path)
    if not absolute_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice PDF not found")
    return FileResponse(
        absolute_path,
        media_type="application/pdf",
        filename=f"{invoice.invoice_number}.pdf",
    )


@router.patch("/{invoice_id}/mark-paid", response_model=InvoiceRead, dependencies=[Depends(require_csrf)])
def mark_paid(invoice_id: str, db: Session = Depends(get_db)) -> Invoice:
    invoice = _require_invoice(db, invoice_id)
    invoice.payment_status = "paid"
    invoice.updated_at = utc_now()
    db.commit()
    db.refresh(invoice)
    return invoice


@router.patch("/{invoice_id}/mark-unpaid", response_model=InvoiceRead, dependencies=[Depends(require_csrf)])
def mark_unpaid(invoice_id: str, db: Session = Depends(get_db)) -> Invoice:
    invoice = _require_invoice(db, invoice_id)
    invoice.payment_status = "pending"
    invoice.updated_at = utc_now()
    db.commit()
    db.refresh(invoice)
    return invoice


@router.post("/{invoice_id}/send-email", response_model=InvoiceEmailRead, dependencies=[Depends(require_csrf)])
def queue_invoice_email(
    invoice_id: str,
    db: Session = Depends(get_db),
    settings=Depends(get_app_settings),
    user: User = Depends(get_current_user),
) -> InvoiceEmailRead:
    invoice = _require_invoice(db, invoice_id)
    email_settings = _validated_email_settings(db, invoice)
    absolute_path = _absolute_pdf_path(settings.file_storage_root, invoice.pdf_path)
    if not absolute_path.exists():
        _write_pdf(settings.file_storage_root, invoice, _invoice_settings(db))

    subject = _format_template(
        str(email_settings.get("invoice_subject_template") or "Faktura {invoice_number}"),
        _invoice_template_values(invoice),
    )
    body_text = _format_template(
        str(email_settings.get("invoice_body_template") or "Dobrý den, v příloze posíláme zálohovou fakturu."),
        _invoice_template_values(invoice),
    )
    intent = InvoiceEmailIntent(
        invoice_id=invoice.id,
        user_id=user.id,
        recipient=str(invoice.customer_email),
        sender=str(email_settings["sender"]),
        subject=subject,
        body_text=body_text,
        attachment_path=invoice.pdf_path,
        smtp_json={
            "server": email_settings["server"],
            "port": email_settings["port"],
            "username": email_settings["username"],
            "password_secret_ref": email_settings.get("password_secret_ref"),
            "has_password": bool(email_settings.get("password")),
        },
        status="queued",
        response_json={"queued": True, "delivery": "persisted_intent"},
    )
    db.add(intent)
    db.commit()
    db.refresh(intent)
    return InvoiceEmailRead(
        intent_id=intent.id,
        invoice_id=invoice.id,
        recipient=intent.recipient,
        sender=intent.sender,
        subject=intent.subject,
        status=intent.status,
    )


@router.delete("/{invoice_id}", dependencies=[Depends(require_csrf)])
def delete_invoice(invoice_id: str, db: Session = Depends(get_db), settings=Depends(get_app_settings)) -> dict[str, bool]:
    invoice = _require_invoice(db, invoice_id)
    absolute_path = _absolute_pdf_path(settings.file_storage_root, invoice.pdf_path)
    db.execute(delete(InvoiceEmailIntent).where(InvoiceEmailIntent.invoice_id == invoice.id))
    db.delete(invoice)
    db.commit()
    if absolute_path.exists():
        absolute_path.unlink()
    return {"deleted": True}


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
        if not service.active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Service is inactive")
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
    if not due_term.active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Due term is inactive")
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


def _invoice_pdf_path(invoice_number: str) -> str:
    return (Path("invoices") / f"{invoice_number}.pdf").as_posix()


def _write_pdf(storage_root: Path, invoice: Invoice, invoice_settings: dict[str, Any]) -> str:
    relative_path = Path(invoice.pdf_path)
    absolute_path = storage_root / relative_path
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    font_name = _pdf_font_name()
    pdf = canvas.Canvas(str(absolute_path), pagesize=A4)
    width, height = A4
    y = height - 24 * mm

    def text(line: str, x: float = 22 * mm, size: int = 10, leading: float = 6 * mm, bold: bool = False) -> None:
        nonlocal y
        pdf.setFont(font_name, size)
        if bold:
            pdf.setFillColor(colors.HexColor("#111827"))
        else:
            pdf.setFillColor(colors.HexColor("#374151"))
        pdf.drawString(x, y, _clean_pdf_text(line))
        y -= leading

    pdf.setTitle(f"Faktura {invoice.invoice_number}")
    pdf.setAuthor(str(invoice_settings.get("supplier_name") or "HEM"))
    pdf.setFillColor(colors.HexColor("#111827"))
    pdf.setFont(font_name, 20)
    pdf.drawString(22 * mm, y, _clean_pdf_text(f"Zálohová faktura {invoice.invoice_number}"))
    y -= 12 * mm

    text("Dodavatel", bold=True)
    for line in _compact_lines(
        invoice_settings.get("supplier_name"),
        invoice_settings.get("supplier_address"),
        _label_value("IČ", invoice_settings.get("company_id")),
        _label_value("DIČ", invoice_settings.get("company_vat")),
    ):
        text(line)

    y -= 3 * mm
    text("Provozovna", bold=True)
    for line in _compact_lines(invoice_settings.get("branch_name"), invoice_settings.get("branch_address")):
        text(line)

    y -= 3 * mm
    text("Odběratel a kontakt", bold=True)
    for line in _compact_lines(
        invoice.customer_name,
        _label_value("E-mail", invoice.customer_email),
        _label_value("Telefon", invoice.customer_phone),
    ):
        text(line)

    y -= 3 * mm
    text("Služba a termín", bold=True)
    for line in _compact_lines(
        _label_value("Služba", invoice.service_name),
        _label_value("Termín", _format_datetime(invoice.event_at)),
        _label_value("Splatnost", _format_datetime(invoice.due_at)),
        _label_value("Poznámka", invoice.note),
    ):
        text(line)

    y -= 3 * mm
    text("Cena a platební údaje", bold=True)
    for line in _compact_lines(
        _label_value("Cena", _format_money(invoice.price, invoice_settings.get("currency"))),
        _label_value("Variabilní symbol", invoice.variable_symbol),
        _label_value("Číslo účtu", invoice_settings.get("bank_account")),
        _label_value("IBAN", invoice_settings.get("iban")),
    ):
        text(line)

    y -= 5 * mm
    text("Storno podmínky", bold=True)
    for line in _wrap_text(str(invoice_settings.get("cancel_text") or DEFAULT_CANCEL_TEXT), 92):
        text(line, size=9, leading=5 * mm)

    pdf.setStrokeColor(colors.HexColor("#e5e7eb"))
    pdf.line(22 * mm, 18 * mm, width - 22 * mm, 18 * mm)
    pdf.setFont(font_name, 8)
    pdf.setFillColor(colors.HexColor("#6b7280"))
    pdf.drawString(22 * mm, 12 * mm, _clean_pdf_text(f"Vystaveno {utc_now().strftime('%d.%m.%Y %H:%M')}"))
    pdf.save()
    return relative_path.as_posix()


def _absolute_pdf_path(storage_root: Path, pdf_path: str) -> Path:
    absolute_path = (storage_root / pdf_path).resolve()
    storage_root = storage_root.resolve()
    if storage_root not in absolute_path.parents:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid invoice PDF path")
    return absolute_path


def _invoice_settings(db: Session) -> dict[str, Any]:
    app_settings = _setting_value(db, "app")
    company = dict(app_settings.get("company") or {})
    finance = dict(app_settings.get("finance") or {})
    invoicing = dict(app_settings.get("invoicing") or {})
    payment = dict(app_settings.get("payment") or {})
    return {
        "supplier_name": company.get("name"),
        "supplier_address": company.get("address"),
        "company_id": company.get("company_id"),
        "company_vat": company.get("company_vat"),
        "branch_name": company.get("branch_name") or company.get("name"),
        "branch_address": company.get("branch_address") or company.get("address"),
        "currency": finance.get("currency") or "CZK",
        "bank_account": invoicing.get("bank_account") or payment.get("bank_account") or finance.get("bank_account"),
        "iban": invoicing.get("iban") or payment.get("iban") or finance.get("iban"),
        "cancel_text": invoicing.get("cancel_text") or finance.get("cancel_text"),
    }


def _validated_email_settings(db: Session, invoice: Invoice) -> dict[str, Any]:
    email_settings = _email_settings(db)
    normalized = {
        "server": email_settings.get("server") or email_settings.get("smtp_server"),
        "port": email_settings.get("port") or email_settings.get("smtp_port"),
        "username": email_settings.get("username"),
        "password_secret_ref": email_settings.get("password_secret_ref"),
        "password": email_settings.get("password"),
        "sender": email_settings.get("sender"),
        "invoice_subject_template": email_settings.get("invoice_subject_template"),
        "invoice_body_template": email_settings.get("invoice_body_template"),
    }
    missing = [key for key in ("server", "port", "username", "sender") if not normalized.get(key)]
    if not normalized.get("password_secret_ref") and not normalized.get("password"):
        missing.append("password_secret_ref or password")
    if not invoice.customer_email:
        missing.append("customer_email")
    if missing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Missing email settings: {', '.join(missing)}")
    try:
        normalized["port"] = int(normalized["port"])
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SMTP port must be a number") from exc
    if normalized["port"] <= 0 or normalized["port"] > 65535:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SMTP port must be between 1 and 65535")
    if "@" not in str(invoice.customer_email) or "@" not in str(normalized["sender"]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email address")
    return normalized


def _email_settings(db: Session) -> dict[str, Any]:
    direct = _setting_value(db, "email")
    if direct:
        return direct
    return dict((_setting_value(db, "app").get("email") or {}))


def _setting_value(db: Session, key: str) -> dict[str, Any]:
    setting = db.get(Setting, key)
    if setting is None:
        return {}
    return dict(setting.value_json or {})


def _format_template(template: str, values: dict[str, Any]) -> str:
    try:
        return template.format(**values)
    except KeyError:
        return template


def _invoice_template_values(invoice: Invoice) -> dict[str, Any]:
    return {
        "invoice_number": invoice.invoice_number,
        "variable_symbol": invoice.variable_symbol,
        "customer_name": invoice.customer_name,
        "service_name": invoice.service_name,
        "price": invoice.price,
        "event_at": _format_datetime(invoice.event_at),
        "due_at": _format_datetime(invoice.due_at),
    }


def _pdf_font_name() -> str:
    global PDF_FONT_REGISTERED
    if PDF_FONT_REGISTERED:
        return PDF_FONT_NAME
    for font_path in (
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/dejavu/DejaVuSans.ttf"),
    ):
        if font_path.exists():
            pdfmetrics.registerFont(TTFont(PDF_FONT_NAME, str(font_path)))
            PDF_FONT_REGISTERED = True
            return PDF_FONT_NAME
    return "Helvetica"


def _compact_lines(*values: object) -> list[str]:
    return [str(value) for value in values if value not in (None, "")]


def _label_value(label: str, value: object) -> str | None:
    if value in (None, ""):
        return None
    return f"{label}: {value}"


def _format_datetime(value: datetime) -> str:
    return _as_aware_utc(value).strftime("%d.%m.%Y %H:%M")


def _format_money(value: float, currency: object) -> str:
    return f"{value:,.2f} {currency or 'CZK'}".replace(",", " ")


def _wrap_text(value: str, limit: int) -> list[str]:
    words = value.split()
    lines: list[str] = []
    current = ""
    for word in words:
        next_line = f"{current} {word}".strip()
        if len(next_line) > limit and current:
            lines.append(current)
            current = word
        else:
            current = next_line
    if current:
        lines.append(current)
    return lines or [""]


def _clean_pdf_text(value: str) -> str:
    return value.replace("\r", " ").replace("\n", " ")


def _require_invoice(db: Session, invoice_id: str) -> Invoice:
    invoice = db.get(Invoice, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return invoice


def _as_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
