from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.deps import get_current_user, require_csrf
from app.core.models import User
from app.core.time import utc_now
from app.modules.catalog.models import InventoryItem
from app.modules.inventory.models import InventoryEntry, InventoryEntryItem

router = APIRouter(prefix="/api/inventory", tags=["inventory"])

ALLOWED_MODULES = {"wellness", "minibar", "lobby"}


class EntryItemCreate(BaseModel):
    item_id: str | None = None
    custom_description: str | None = Field(default=None, max_length=255)
    quantity: float
    unit_price: float | None = None
    is_custom: bool = False


class EntryCreate(BaseModel):
    entry_date: date
    module: str = Field(min_length=1, max_length=64)
    note: str | None = None
    items: list[EntryItemCreate] = Field(default_factory=list)


class EntryUpdate(BaseModel):
    entry_date: date | None = None
    module: str | None = Field(default=None, min_length=1, max_length=64)
    note: str | None = None
    items: list[EntryItemCreate] | None = None


class EntryItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    item_id: str | None
    item_name: str
    unit: str | None
    custom_description: str | None
    quantity: float
    unit_price: float
    total_price: float
    is_custom: bool
    position: int


class EntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    entry_date: date
    module: str
    note: str | None
    items: list[EntryItemRead]


class MonthlyReport(BaseModel):
    module: str
    month: str
    totals: dict[str, dict[str, float]]
    custom_total_price: float


@router.post("/entries", response_model=EntryRead, dependencies=[Depends(require_csrf)])
def create_entry(payload: EntryCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> InventoryEntry:
    _validate_module(payload.module)
    existing = _find_entry(db, payload.entry_date, payload.module)
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Inventory entry already exists for this date and module")

    entry = InventoryEntry(
        entry_date=payload.entry_date,
        module=payload.module,
        note=payload.note,
        created_by_id=user.id,
        updated_by_id=user.id,
        updated_at=utc_now(),
    )
    db.add(entry)
    _replace_items(db, entry, payload.module, payload.items)
    db.commit()
    return _load_entry(db, entry.id)


@router.get("/entries/by-date", response_model=EntryRead)
def read_entry_by_date(entry_date: date, module: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> InventoryEntry:
    _validate_module(module)
    entry = _find_entry(db, entry_date, module)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory entry not found")
    return _load_entry(db, entry.id)


@router.put("/entries/{entry_id}", response_model=EntryRead, dependencies=[Depends(require_csrf)])
def update_entry(entry_id: str, payload: EntryUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> InventoryEntry:
    entry = _require_entry(db, entry_id)
    new_module = payload.module or entry.module
    new_date = payload.entry_date or entry.entry_date
    _validate_module(new_module)
    duplicate = _find_entry(db, new_date, new_module, exclude_id=entry_id)
    if duplicate is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Inventory entry already exists for this date and module")

    entry.entry_date = new_date
    entry.module = new_module
    if "note" in payload.model_fields_set:
        entry.note = payload.note
    if payload.items is not None:
        _replace_items(db, entry, new_module, payload.items)
    entry.updated_by_id = user.id
    entry.updated_at = utc_now()
    db.commit()
    return _load_entry(db, entry.id)


@router.get("/archive", response_model=list[EntryRead])
def list_archive(
    module: str | None = None,
    text: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[InventoryEntry]:
    if module is not None:
        _validate_module(module)
    stmt = select(InventoryEntry).options(selectinload(InventoryEntry.items))
    if module is not None:
        stmt = stmt.where(InventoryEntry.module == module)
    if date_from is not None:
        stmt = stmt.where(InventoryEntry.entry_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(InventoryEntry.entry_date <= date_to)
    if text:
        needle = f"%{text.lower()}%"
        stmt = stmt.join(InventoryEntry.items, isouter=True).where(
            or_(
                InventoryEntry.note.ilike(needle),
                InventoryEntryItem.item_name.ilike(needle),
                InventoryEntryItem.custom_description.ilike(needle),
            )
        )
    stmt = stmt.order_by(InventoryEntry.entry_date.desc(), InventoryEntry.created_at.desc())
    return list(db.scalars(stmt).unique().all())


@router.delete("/archive/{entry_id}", dependencies=[Depends(require_csrf)])
def delete_archive_entry(entry_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> dict[str, bool]:
    entry = _require_entry(db, entry_id)
    db.delete(entry)
    db.commit()
    return {"ok": True}


@router.get("/reports/monthly", response_model=MonthlyReport)
def monthly_report(module: str, month: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> MonthlyReport:
    _validate_module(module)
    start, end = _month_bounds(month)
    rows = db.scalars(
        select(InventoryEntry)
        .options(selectinload(InventoryEntry.items))
        .where(InventoryEntry.module == module, InventoryEntry.entry_date >= start, InventoryEntry.entry_date <= end)
        .order_by(InventoryEntry.entry_date)
    ).all()

    totals: dict[str, dict[str, float]] = {}
    custom_total_price = 0.0
    for entry in rows:
        for item in entry.items:
            total_price = item.quantity * item.unit_price
            if item.is_custom:
                custom_total_price += total_price
                continue
            aggregate = totals.setdefault(item.item_name, {"quantity": 0.0, "total_price": 0.0})
            aggregate["quantity"] += item.quantity
            aggregate["total_price"] += total_price
    return MonthlyReport(module=module, month=month, totals=totals, custom_total_price=custom_total_price)


def _validate_module(module: str) -> None:
    if module not in ALLOWED_MODULES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown inventory module")


def _find_entry(db: Session, entry_date: date, module: str, exclude_id: str | None = None) -> InventoryEntry | None:
    stmt = select(InventoryEntry).where(InventoryEntry.entry_date == entry_date, InventoryEntry.module == module)
    if exclude_id is not None:
        stmt = stmt.where(InventoryEntry.id != exclude_id)
    return db.scalar(stmt)


def _require_entry(db: Session, entry_id: str) -> InventoryEntry:
    entry = db.get(InventoryEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory entry not found")
    return entry


def _load_entry(db: Session, entry_id: str) -> InventoryEntry:
    entry = db.scalar(select(InventoryEntry).options(selectinload(InventoryEntry.items)).where(InventoryEntry.id == entry_id))
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory entry not found")
    return entry


def _replace_items(db: Session, entry: InventoryEntry, module: str, payload_items: list[EntryItemCreate]) -> None:
    entry.items.clear()
    db.flush()
    for position, payload in enumerate(payload_items):
        entry.items.append(_build_item_row(db, module, payload, position))


def _build_item_row(db: Session, module: str, payload: EntryItemCreate, position: int) -> InventoryEntryItem:
    if payload.quantity < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quantity cannot be negative")
    if payload.is_custom:
        if module != "lobby":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Custom rows are only supported for lobby inventory")
        if not payload.custom_description:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Custom description is required")
        return InventoryEntryItem(
            item_name=payload.custom_description,
            custom_description=payload.custom_description,
            quantity=payload.quantity,
            unit_price=payload.unit_price or 0,
            is_custom=True,
            position=position,
        )

    if payload.item_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Item id is required")
    catalog_item = db.get(InventoryItem, payload.item_id)
    if catalog_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory catalog item not found")
    if catalog_item.module != module:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Catalog item does not belong to this inventory module")
    unit_price = payload.unit_price
    if unit_price is None:
        unit_price = catalog_item.price if catalog_item.price is not None else 0
    return InventoryEntryItem(
        item_id=catalog_item.id,
        item_name=catalog_item.name,
        unit=catalog_item.unit,
        quantity=payload.quantity,
        unit_price=unit_price,
        is_custom=False,
        position=position,
    )


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
