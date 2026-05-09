"""Inventory SQLAlchemy models are owned by the inventory module."""

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.ids import new_id
from app.core.time import utc_now


class InventoryEntry(Base):
    __tablename__ = "inventory_entries"
    __table_args__ = (UniqueConstraint("entry_date", "module", name="uq_inventory_entries_date_module"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("inventry"))
    entry_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    module: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    note: Mapped[str | None] = mapped_column(Text)
    created_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    updated_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    items: Mapped[list["InventoryEntryItem"]] = relationship(
        back_populates="entry",
        cascade="all, delete-orphan",
        order_by="InventoryEntryItem.position",
    )


class InventoryEntryItem(Base):
    __tablename__ = "inventory_entry_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("inventry_item"))
    entry_id: Mapped[str] = mapped_column(ForeignKey("inventory_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id: Mapped[str | None] = mapped_column(String(64), index=True)
    item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(32))
    custom_description: Mapped[str | None] = mapped_column(String(255))
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    position: Mapped[int] = mapped_column(default=0, nullable=False)

    entry: Mapped[InventoryEntry] = relationship(back_populates="items")

    @property
    def total_price(self) -> float:
        return self.quantity * self.unit_price
