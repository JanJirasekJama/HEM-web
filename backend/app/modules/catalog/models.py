"""Catalog SQLAlchemy models are owned by the catalog module."""

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.ids import new_id


class ServiceCategory(Base):
    __tablename__ = "catalog_service_categories"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("svc_cat"))
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    services: Mapped[list["Service"]] = relationship(back_populates="category")


class Service(Base):
    __tablename__ = "catalog_services"
    __table_args__ = (UniqueConstraint("category_id", "name", name="uq_catalog_services_category_name"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("svc"))
    category_id: Mapped[str] = mapped_column(ForeignKey("catalog_service_categories.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    price: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    category: Mapped[ServiceCategory] = relationship(back_populates="services")


class DueTerm(Base):
    __tablename__ = "catalog_due_terms"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("due"))
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    value: Mapped[int] = mapped_column(Integer, nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class InventoryItem(Base):
    __tablename__ = "catalog_inventory_items"
    __table_args__ = (UniqueConstraint("module", "name", name="uq_catalog_inventory_items_module_name"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("inv_item"))
    module: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    category: Mapped[str | None] = mapped_column(String(128))
    price: Mapped[float | None] = mapped_column(Float)
    has_price: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class HotelRoom(Base):
    __tablename__ = "catalog_hotel_rooms"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("room"))
    label: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class HousekeepingMinibarItem(Base):
    __tablename__ = "catalog_housekeeping_minibar_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("hk_minibar"))
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class PhotoTaskType(Base):
    __tablename__ = "catalog_photo_task_types"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("photo_type"))
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class EmailRecipient(Base):
    __tablename__ = "catalog_email_recipients"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("email_rec"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
