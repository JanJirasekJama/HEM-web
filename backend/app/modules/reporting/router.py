import csv
from collections import Counter, defaultdict
from datetime import date
from io import StringIO
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_app_settings, require_permission, require_csrf
from app.core.models import Setting, User
from app.core.time import utc_now
from app.modules.inventory.queries import list_inventory_monthly_items
from app.modules.invoicing.queries import list_invoice_report_rows
from app.modules.reporting.models import ExportRecord

router = APIRouter(prefix="/api/reports", tags=["reporting"])


class ExportCreate(BaseModel):
    module: str
    export_type: str
    period_from: date | None = None
    period_to: date | None = None


@router.get("/invoices/statistics")
def invoice_statistics(date_from: date, date_to: date, db: Session = Depends(get_db), _: User = Depends(require_permission("reports:read"))) -> dict[str, Any]:
    invoices = _invoice_rows(db, date_from, date_to)
    prices = [float(row.price or 0) for row in invoices]
    statuses = Counter(str(row.payment_status) for row in invoices)
    services = Counter(str(row.service_name) for row in invoices)
    turnover: dict[str, float] = defaultdict(float)
    for row in invoices:
        turnover[str(row.service_name)] += float(row.price or 0)

    return {
        "invoice_count": len(invoices),
        "paid_count": statuses.get("paid", 0),
        "unpaid_count": statuses.get("unpaid", 0) + statuses.get("overdue", 0),
        "pending_count": statuses.get("pending", 0),
        "total_amount": sum(prices),
        "average_invoice": round(sum(prices) / len(prices), 2) if prices else 0,
        "most_common_service": services.most_common(1)[0][0] if services else None,
        "highest_turnover_service": max(turnover, key=turnover.get) if turnover else None,
        "by_service": dict(turnover),
    }


@router.get("/invoices/tax")
def invoice_tax_report(date_from: date, date_to: date, db: Session = Depends(get_db), _: User = Depends(require_permission("reports:read"))) -> dict[str, Any]:
    invoices = _invoice_rows(db, date_from, date_to)
    vat_rate = _tax_rate(db)
    gross = sum(float(row.price or 0) for row in invoices)
    net = round(gross / (1 + vat_rate / 100), 2) if vat_rate else gross
    vat = round(gross - net, 2)
    by_service: dict[str, dict[str, float]] = defaultdict(lambda: {"gross": 0.0, "net": 0.0, "vat": 0.0})
    for row in invoices:
        service_gross = float(row.price or 0)
        service_net = round(service_gross / (1 + vat_rate / 100), 2) if vat_rate else service_gross
        item = by_service[str(row.service_name)]
        item["gross"] += service_gross
        item["net"] += service_net
        item["vat"] += round(service_gross - service_net, 2)

    return {
        "gross_revenue": gross,
        "vat_rate": vat_rate,
        "vat": vat,
        "net_revenue": net,
        "by_service": dict(by_service),
    }


@router.get("/inventory/monthly")
def inventory_monthly(module: str, month: str, db: Session = Depends(get_db), _: User = Depends(require_permission("reports:read"))) -> dict[str, Any]:
    start, end = _month_bounds(month)
    rows = list_inventory_monthly_items(db, module, start, end)
    totals: dict[str, dict[str, float]] = defaultdict(lambda: {"quantity": 0.0, "total_price": 0.0})
    custom_total_price = 0.0
    for row in rows:
        total_price = float(row.quantity or 0) * float(row.unit_price or 0)
        if row.is_custom:
            custom_total_price += total_price
            continue
        totals[str(row.item_name)]["quantity"] += float(row.quantity or 0)
        totals[str(row.item_name)]["total_price"] += total_price
    return {"module": module, "month": month, "totals": dict(totals), "custom_total_price": custom_total_price}


@router.post("/exports", dependencies=[Depends(require_csrf)])
def create_export(
    payload: ExportCreate,
    db: Session = Depends(get_db),
    settings=Depends(get_app_settings),
    user: User = Depends(require_permission("exports:create")),
) -> dict[str, Any]:
    record = ExportRecord(
        export_type=payload.export_type,
        module=payload.module,
        period_from=payload.period_from,
        period_to=payload.period_to,
        file_path="",
        created_by=user.id,
    )
    db.add(record)
    db.flush()

    relative_path = Path("exports") / f"{record.id}.{payload.export_type}"
    absolute_path = settings.file_storage_root / relative_path
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    absolute_path.write_text(_export_content(payload), encoding="utf-8")

    record.file_path = relative_path.as_posix()
    db.commit()
    db.refresh(record)
    return {
        "id": record.id,
        "export_type": record.export_type,
        "module": record.module,
        "period_from": record.period_from,
        "period_to": record.period_to,
        "file_path": record.file_path,
        "created_at": record.created_at,
    }


def _invoice_rows(db: Session, date_from: date, date_to: date):
    return list_invoice_report_rows(db, date_from, date_to)


def _tax_rate(db: Session) -> float:
    setting = db.get(Setting, "app")
    if setting is None:
        return 21
    return float((setting.value_json or {}).get("finance", {}).get("tax_rate", 21))


def _month_bounds(month: str) -> tuple[date, date]:
    try:
        year_text, month_text = month.split("-", 1)
        year = int(year_text)
        month_number = int(month_text)
        start = date(year, month_number, 1)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Month must use YYYY-MM format") from exc
    if month_number == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month_number + 1, 1)
    return start, date.fromordinal(end.toordinal() - 1)


def _export_content(payload: ExportCreate) -> str:
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["module", "export_type", "period_from", "period_to", "created_at"])
    writer.writerow([payload.module, payload.export_type, payload.period_from, payload.period_to, utc_now().isoformat()])
    return output.getvalue()
