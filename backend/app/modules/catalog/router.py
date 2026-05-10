from typing import Any, TypeVar

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin, require_csrf
from app.core.models import User
from app.modules.catalog.models import (
    DueTerm,
    EmailRecipient,
    HotelRoom,
    HousekeepingMinibarItem,
    InventoryItem,
    PhotoTaskType,
    Service,
    ServiceCategory,
)

router = APIRouter(prefix="/api/catalog", tags=["catalog"])

ModelT = TypeVar("ModelT")


class CatalogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    sort_order: int = 0
    active: bool = True


class NamedCatalogCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    sort_order: int = 0
    active: bool = True


class NamedCatalogUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    sort_order: int | None = None
    active: bool | None = None


class ServiceCategoryRead(CatalogRead):
    pass


class ServiceCategoryCreate(NamedCatalogCreate):
    pass


class ServiceCategoryUpdate(NamedCatalogUpdate):
    pass


class ServiceRead(CatalogRead):
    category_id: str
    type: str
    price: float


class ServiceCreate(BaseModel):
    category_id: str
    name: str = Field(min_length=1, max_length=255)
    type: str = Field(default="ostatni", min_length=1, max_length=64)
    price: float = 0
    sort_order: int = 0
    active: bool = True


class ServiceUpdate(BaseModel):
    category_id: str | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    type: str | None = Field(default=None, min_length=1, max_length=64)
    price: float | None = None
    sort_order: int | None = None
    active: bool | None = None


class DueTermRead(CatalogRead):
    value: int
    unit: str


class DueTermCreate(NamedCatalogCreate):
    value: int
    unit: str = Field(min_length=1, max_length=32)


class DueTermUpdate(NamedCatalogUpdate):
    value: int | None = None
    unit: str | None = Field(default=None, min_length=1, max_length=32)


class InventoryItemRead(CatalogRead):
    module: str
    unit: str
    category: str | None = None
    price: float | None = None
    has_price: bool = False


class InventoryItemCreate(NamedCatalogCreate):
    module: str = Field(min_length=1, max_length=64)
    unit: str = Field(min_length=1, max_length=32)
    category: str | None = Field(default=None, max_length=128)
    price: float | None = None
    has_price: bool = False


class InventoryItemUpdate(NamedCatalogUpdate):
    module: str | None = Field(default=None, min_length=1, max_length=64)
    unit: str | None = Field(default=None, min_length=1, max_length=32)
    category: str | None = Field(default=None, max_length=128)
    price: float | None = None
    has_price: bool | None = None


class HotelRoomRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    label: str
    sort_order: int = 0
    active: bool = True


class HotelRoomCreate(BaseModel):
    label: str = Field(min_length=1, max_length=255)
    sort_order: int = 0
    active: bool = True


class HotelRoomUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=255)
    sort_order: int | None = None
    active: bool | None = None


class EmailRecipientRead(CatalogRead):
    email: str


class EmailRecipientCreate(NamedCatalogCreate):
    email: str = Field(min_length=1, max_length=255)


class EmailRecipientUpdate(NamedCatalogUpdate):
    email: str | None = Field(default=None, min_length=1, max_length=255)


class BootstrapRead(BaseModel):
    service_categories: list[ServiceCategoryRead]
    services: list[ServiceRead]
    due_terms: list[DueTermRead]
    inventory_items: list[InventoryItemRead]
    hotel_rooms: list[HotelRoomRead]
    housekeeping_minibar_items: list[CatalogRead]
    photo_task_types: list[CatalogRead]
    email_recipients: list[EmailRecipientRead]


def _list(db: Session, model: type[ModelT], active_only: bool) -> list[ModelT]:
    statement = select(model)
    if active_only:
        statement = statement.where(model.active.is_(True))  # type: ignore[attr-defined]
    return list(db.scalars(statement.order_by(model.sort_order, model.id)).all())  # type: ignore[attr-defined]


def _get_or_404(db: Session, model: type[ModelT], item_id: str, label: str) -> ModelT:
    item = db.get(model, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} not found")
    return item


def _apply_updates(item: Any, payload: BaseModel) -> None:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)


def _create(db: Session, model: type[ModelT], payload: BaseModel) -> ModelT:
    item = model(**payload.model_dump())  # type: ignore[call-arg]
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def _update(db: Session, item: ModelT, payload: BaseModel) -> ModelT:
    _apply_updates(item, payload)
    db.commit()
    db.refresh(item)
    return item


def _delete(db: Session, item: ModelT) -> dict[str, bool]:
    db.delete(item)
    db.commit()
    return {"ok": True}


def _ensure_category_exists(db: Session, category_id: str) -> None:
    if db.get(ServiceCategory, category_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown service category")


@router.get("/bootstrap", response_model=BootstrapRead)
def bootstrap_catalog(active_only: bool = True, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> BootstrapRead:
    return BootstrapRead(
        service_categories=_list(db, ServiceCategory, active_only),
        services=_list(db, Service, active_only),
        due_terms=_list(db, DueTerm, active_only),
        inventory_items=_list(db, InventoryItem, active_only),
        hotel_rooms=_list(db, HotelRoom, active_only),
        housekeeping_minibar_items=_list(db, HousekeepingMinibarItem, active_only),
        photo_task_types=_list(db, PhotoTaskType, active_only),
        email_recipients=_list(db, EmailRecipient, active_only),
    )


@router.get("/service-categories", response_model=list[ServiceCategoryRead])
def list_service_categories(active_only: bool = True, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[ServiceCategory]:
    return _list(db, ServiceCategory, active_only)


@router.post("/service-categories", response_model=ServiceCategoryRead, dependencies=[Depends(require_csrf)])
def create_service_category(payload: ServiceCategoryCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> ServiceCategory:
    return _create(db, ServiceCategory, payload)


@router.get("/service-categories/{item_id}", response_model=ServiceCategoryRead)
def read_service_category(item_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> ServiceCategory:
    return _get_or_404(db, ServiceCategory, item_id, "Service category")


@router.patch("/service-categories/{item_id}", response_model=ServiceCategoryRead, dependencies=[Depends(require_csrf)])
def update_service_category(item_id: str, payload: ServiceCategoryUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> ServiceCategory:
    return _update(db, _get_or_404(db, ServiceCategory, item_id, "Service category"), payload)


@router.delete("/service-categories/{item_id}", dependencies=[Depends(require_csrf)])
def delete_service_category(item_id: str, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> dict[str, bool]:
    return _delete(db, _get_or_404(db, ServiceCategory, item_id, "Service category"))


@router.get("/services", response_model=list[ServiceRead])
def list_services(active_only: bool = True, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[Service]:
    return _list(db, Service, active_only)


@router.post("/services", response_model=ServiceRead, dependencies=[Depends(require_csrf)])
def create_service(payload: ServiceCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> Service:
    _ensure_category_exists(db, payload.category_id)
    return _create(db, Service, payload)


@router.get("/services/{item_id}", response_model=ServiceRead)
def read_service(item_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> Service:
    return _get_or_404(db, Service, item_id, "Service")


@router.patch("/services/{item_id}", response_model=ServiceRead, dependencies=[Depends(require_csrf)])
def update_service(item_id: str, payload: ServiceUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> Service:
    if payload.category_id is not None:
        _ensure_category_exists(db, payload.category_id)
    return _update(db, _get_or_404(db, Service, item_id, "Service"), payload)


@router.delete("/services/{item_id}", dependencies=[Depends(require_csrf)])
def delete_service(item_id: str, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> dict[str, bool]:
    return _delete(db, _get_or_404(db, Service, item_id, "Service"))


@router.get("/due-terms", response_model=list[DueTermRead])
def list_due_terms(active_only: bool = True, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[DueTerm]:
    return _list(db, DueTerm, active_only)


@router.post("/due-terms", response_model=DueTermRead, dependencies=[Depends(require_csrf)])
def create_due_term(payload: DueTermCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> DueTerm:
    return _create(db, DueTerm, payload)


@router.get("/due-terms/{item_id}", response_model=DueTermRead)
def read_due_term(item_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> DueTerm:
    return _get_or_404(db, DueTerm, item_id, "Due term")


@router.patch("/due-terms/{item_id}", response_model=DueTermRead, dependencies=[Depends(require_csrf)])
def update_due_term(item_id: str, payload: DueTermUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> DueTerm:
    return _update(db, _get_or_404(db, DueTerm, item_id, "Due term"), payload)


@router.delete("/due-terms/{item_id}", dependencies=[Depends(require_csrf)])
def delete_due_term(item_id: str, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> dict[str, bool]:
    return _delete(db, _get_or_404(db, DueTerm, item_id, "Due term"))


@router.get("/inventory-items", response_model=list[InventoryItemRead])
def list_inventory_items(active_only: bool = True, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[InventoryItem]:
    return _list(db, InventoryItem, active_only)


@router.post("/inventory-items", response_model=InventoryItemRead, dependencies=[Depends(require_csrf)])
def create_inventory_item(payload: InventoryItemCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> InventoryItem:
    return _create(db, InventoryItem, payload)


@router.get("/inventory-items/{item_id}", response_model=InventoryItemRead)
def read_inventory_item(item_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> InventoryItem:
    return _get_or_404(db, InventoryItem, item_id, "Inventory item")


@router.patch("/inventory-items/{item_id}", response_model=InventoryItemRead, dependencies=[Depends(require_csrf)])
def update_inventory_item(item_id: str, payload: InventoryItemUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> InventoryItem:
    return _update(db, _get_or_404(db, InventoryItem, item_id, "Inventory item"), payload)


@router.delete("/inventory-items/{item_id}", dependencies=[Depends(require_csrf)])
def delete_inventory_item(item_id: str, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> dict[str, bool]:
    return _delete(db, _get_or_404(db, InventoryItem, item_id, "Inventory item"))


@router.get("/hotel-rooms", response_model=list[HotelRoomRead])
def list_hotel_rooms(active_only: bool = True, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[HotelRoom]:
    return _list(db, HotelRoom, active_only)


@router.post("/hotel-rooms", response_model=HotelRoomRead, dependencies=[Depends(require_csrf)])
def create_hotel_room(payload: HotelRoomCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> HotelRoom:
    return _create(db, HotelRoom, payload)


@router.get("/hotel-rooms/{item_id}", response_model=HotelRoomRead)
def read_hotel_room(item_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> HotelRoom:
    return _get_or_404(db, HotelRoom, item_id, "Hotel room")


@router.patch("/hotel-rooms/{item_id}", response_model=HotelRoomRead, dependencies=[Depends(require_csrf)])
def update_hotel_room(item_id: str, payload: HotelRoomUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> HotelRoom:
    return _update(db, _get_or_404(db, HotelRoom, item_id, "Hotel room"), payload)


@router.delete("/hotel-rooms/{item_id}", dependencies=[Depends(require_csrf)])
def delete_hotel_room(item_id: str, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> dict[str, bool]:
    return _delete(db, _get_or_404(db, HotelRoom, item_id, "Hotel room"))


@router.get("/housekeeping-minibar-items", response_model=list[CatalogRead])
def list_housekeeping_minibar_items(active_only: bool = True, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[HousekeepingMinibarItem]:
    return _list(db, HousekeepingMinibarItem, active_only)


@router.post("/housekeeping-minibar-items", response_model=CatalogRead, dependencies=[Depends(require_csrf)])
def create_housekeeping_minibar_item(payload: NamedCatalogCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> HousekeepingMinibarItem:
    return _create(db, HousekeepingMinibarItem, payload)


@router.get("/housekeeping-minibar-items/{item_id}", response_model=CatalogRead)
def read_housekeeping_minibar_item(item_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> HousekeepingMinibarItem:
    return _get_or_404(db, HousekeepingMinibarItem, item_id, "Housekeeping minibar item")


@router.patch("/housekeeping-minibar-items/{item_id}", response_model=CatalogRead, dependencies=[Depends(require_csrf)])
def update_housekeeping_minibar_item(item_id: str, payload: NamedCatalogUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> HousekeepingMinibarItem:
    return _update(db, _get_or_404(db, HousekeepingMinibarItem, item_id, "Housekeeping minibar item"), payload)


@router.delete("/housekeeping-minibar-items/{item_id}", dependencies=[Depends(require_csrf)])
def delete_housekeeping_minibar_item(item_id: str, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> dict[str, bool]:
    return _delete(db, _get_or_404(db, HousekeepingMinibarItem, item_id, "Housekeeping minibar item"))


@router.get("/photo-task-types", response_model=list[CatalogRead])
def list_photo_task_types(active_only: bool = True, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[PhotoTaskType]:
    return _list(db, PhotoTaskType, active_only)


@router.post("/photo-task-types", response_model=CatalogRead, dependencies=[Depends(require_csrf)])
def create_photo_task_type(payload: NamedCatalogCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> PhotoTaskType:
    return _create(db, PhotoTaskType, payload)


@router.get("/photo-task-types/{item_id}", response_model=CatalogRead)
def read_photo_task_type(item_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> PhotoTaskType:
    return _get_or_404(db, PhotoTaskType, item_id, "Photo task type")


@router.patch("/photo-task-types/{item_id}", response_model=CatalogRead, dependencies=[Depends(require_csrf)])
def update_photo_task_type(item_id: str, payload: NamedCatalogUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> PhotoTaskType:
    return _update(db, _get_or_404(db, PhotoTaskType, item_id, "Photo task type"), payload)


@router.delete("/photo-task-types/{item_id}", dependencies=[Depends(require_csrf)])
def delete_photo_task_type(item_id: str, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> dict[str, bool]:
    return _delete(db, _get_or_404(db, PhotoTaskType, item_id, "Photo task type"))


@router.get("/email-recipients", response_model=list[EmailRecipientRead])
def list_email_recipients(active_only: bool = True, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[EmailRecipient]:
    return _list(db, EmailRecipient, active_only)


@router.post("/email-recipients", response_model=EmailRecipientRead, dependencies=[Depends(require_csrf)])
def create_email_recipient(payload: EmailRecipientCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> EmailRecipient:
    return _create(db, EmailRecipient, payload)


@router.get("/email-recipients/{item_id}", response_model=EmailRecipientRead)
def read_email_recipient(item_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> EmailRecipient:
    return _get_or_404(db, EmailRecipient, item_id, "Email recipient")


@router.patch("/email-recipients/{item_id}", response_model=EmailRecipientRead, dependencies=[Depends(require_csrf)])
def update_email_recipient(item_id: str, payload: EmailRecipientUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> EmailRecipient:
    return _update(db, _get_or_404(db, EmailRecipient, item_id, "Email recipient"), payload)


@router.delete("/email-recipients/{item_id}", dependencies=[Depends(require_csrf)])
def delete_email_recipient(item_id: str, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> dict[str, bool]:
    return _delete(db, _get_or_404(db, EmailRecipient, item_id, "Email recipient"))
