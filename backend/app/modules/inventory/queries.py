"""Read-only query contracts for inventory-owned data."""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.inventory.models import InventoryEntry, InventoryEntryItem


@dataclass(frozen=True)
class InventoryMonthlyItem:
    item_name: str
    quantity: float
    unit_price: float
    is_custom: bool


def list_inventory_monthly_items(db: Session, module: str, start: date, end: date) -> list[InventoryMonthlyItem]:
    rows = db.execute(
        select(
            InventoryEntryItem.item_name,
            InventoryEntryItem.quantity,
            InventoryEntryItem.unit_price,
            InventoryEntryItem.is_custom,
        )
        .join(InventoryEntry, InventoryEntry.id == InventoryEntryItem.entry_id)
        .where(
            InventoryEntry.module == module,
            InventoryEntry.entry_date >= start,
            InventoryEntry.entry_date <= end,
        )
    ).all()
    return [
        InventoryMonthlyItem(
            item_name=row.item_name,
            quantity=row.quantity,
            unit_price=row.unit_price,
            is_custom=row.is_custom,
        )
        for row in rows
    ]
