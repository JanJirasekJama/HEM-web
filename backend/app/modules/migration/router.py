import json
import shutil
from collections import defaultdict
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.database import get_db
from app.core.deps import get_app_settings, require_admin, require_csrf
from app.core.ids import new_id
from app.core.models import MediaFile, Role, User
from app.core.security import hash_password
from app.core.time import utc_now
from app.modules.cash.models import CashDiaryEntry
from app.modules.catalog.models import DueTerm, HotelRoom, HousekeepingMinibarItem, InventoryItem, PhotoTaskType, Service, ServiceCategory
from app.modules.communication.models import DailyMessage
from app.modules.housekeeping.models import AssignmentHistory, AssignmentPhoto, HousekeepingAssignment, LaundryTask, RevisionTask
from app.modules.inventory.models import InventoryEntry, InventoryEntryItem
from app.modules.invoicing.models import Invoice

router = APIRouter(prefix="/api/migration", tags=["migration"])


class HousekeepingMigrationRequest(BaseModel):
    data_path: str
    photos_path: str | None = None


class LegacySuiteMigrationRequest(BaseModel):
    inventory_path: str | None = None
    communication_path: str | None = None
    invoicing_path: str | None = None


@router.post("/housekeeping-json", dependencies=[Depends(require_csrf)])
def migrate_housekeeping_json(
    payload: HousekeepingMigrationRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    _: User = Depends(require_admin),
) -> dict[str, int]:
    data_path = Path(payload.data_path)
    if not data_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Housekeeping data.json not found")
    state = _read_json(data_path, {})
    photos_root = Path(payload.photos_path) if payload.photos_path else data_path.parent / "photos"

    users_imported = _import_housekeeping_users(db, state.get("users", []))
    rooms_imported = _import_rooms(db, state.get("hotelRooms", []))
    minibar_items_imported = _import_housekeeping_minibar_items(db, state.get("minibarItems", []))
    photo_tasks_imported = _import_photo_task_types(db, state.get("photoTasks", []))
    history_imported, photos_imported = _import_housekeeping_history(db, settings, state.get("history", []), photos_root)

    db.commit()
    return {
        "users_imported": users_imported,
        "rooms_imported": rooms_imported,
        "minibar_items_imported": minibar_items_imported,
        "photo_tasks_imported": photo_tasks_imported,
        "history_imported": history_imported,
        "photos_imported": photos_imported,
    }


@router.post("/legacy-suite", dependencies=[Depends(require_csrf)])
def migrate_legacy_suite(
    payload: LegacySuiteMigrationRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    _: User = Depends(require_admin),
) -> dict[str, int]:
    messages_imported = _import_legacy_messages(db, Path(payload.communication_path) if payload.communication_path else None)
    cash_entries_imported = _import_legacy_cash(db, Path(payload.communication_path) if payload.communication_path else None)
    inventory_entries_imported = _import_legacy_inventory(db, Path(payload.inventory_path) if payload.inventory_path else None)
    services_imported, due_terms_imported, invoices_imported = _import_legacy_invoicing(
        db,
        Path(payload.invoicing_path) if payload.invoicing_path else None,
        settings,
    )
    db.commit()
    return {
        "messages_imported": messages_imported,
        "cash_entries_imported": cash_entries_imported,
        "inventory_entries_imported": inventory_entries_imported,
        "services_imported": services_imported,
        "due_terms_imported": due_terms_imported,
        "invoices_imported": invoices_imported,
    }


def _import_housekeeping_users(db: Session, users: list[dict[str, Any]]) -> int:
    imported = 0
    for item in users:
        username = str(item.get("username") or "").strip()
        if not username or db.scalar(select(User).where(User.username == username)) is not None:
            continue
        role_name = _role_name(str(item.get("role") or "pokojska"))
        role = db.scalar(select(Role).where(Role.name == role_name)) or db.scalar(select(Role).where(Role.name == "pokojska"))
        if role is None:
            continue
        db.add(
            User(
                username=username,
                display_name=username,
                role_id=role.id,
                password_hash=hash_password(new_id("imported")),
                active=True,
            )
        )
        imported += 1
    return imported


def _import_rooms(db: Session, rooms: list[Any]) -> int:
    imported = 0
    for index, label in enumerate(rooms):
        label_text = str(label).strip()
        if not label_text or db.scalar(select(HotelRoom).where(HotelRoom.label == label_text)) is not None:
            continue
        db.add(HotelRoom(label=label_text, sort_order=index))
        imported += 1
    return imported


def _import_housekeeping_minibar_items(db: Session, items: list[Any]) -> int:
    imported = 0
    for index, name in enumerate(items):
        name_text = str(name).strip()
        if not name_text or db.scalar(select(HousekeepingMinibarItem).where(HousekeepingMinibarItem.name == name_text)) is not None:
            continue
        db.add(HousekeepingMinibarItem(name=name_text, sort_order=index))
        imported += 1
    return imported


def _import_photo_task_types(db: Session, items: list[Any]) -> int:
    imported = 0
    for index, name in enumerate(items):
        name_text = str(name).strip()
        if not name_text or db.scalar(select(PhotoTaskType).where(PhotoTaskType.name == name_text)) is not None:
            continue
        db.add(PhotoTaskType(name=name_text, sort_order=index))
        imported += 1
    return imported


def _import_housekeeping_history(db: Session, settings: Settings, rows: list[dict[str, Any]], photos_root: Path) -> tuple[int, int]:
    history_imported = 0
    photos_imported = 0
    fallback_room = _ensure_room(db, "Legacy")
    for row in rows:
        room = _ensure_room(db, str(row.get("room") or row.get("roomLabel") or "Legacy"))
        housekeeper = _user_by_username(db, str(row.get("housekeeperName") or row.get("completedByName") or ""))
        finished_at = _parse_datetime(row.get("finishedAt") or row.get("completedAt") or row.get("savedAt")) or utc_now()
        assignment = HousekeepingAssignment(
            room_id=room.id if room else fallback_room.id,
            room_label_snapshot=room.label if room else fallback_room.label,
            work_type=str(row.get("workType") or row.get("type") or "legacy"),
            priority=str(row.get("priority") or "Normalni"),
            status=str(row.get("status") or "Hotovo"),
            started_by_id=housekeeper.id if housekeeper else None,
            finished_by_id=housekeeper.id if housekeeper else None,
            finished_at=finished_at,
        )
        db.add(assignment)
        db.flush()
        db.add(
            AssignmentHistory(
                assignment_id=assignment.id,
                room_id=assignment.room_id,
                room_label_snapshot=assignment.room_label_snapshot,
                work_type=assignment.work_type,
                priority=assignment.priority,
                housekeeper_id=housekeeper.id if housekeeper else None,
                housekeeper_username_snapshot=housekeeper.username if housekeeper else row.get("housekeeperName"),
                finished_at=finished_at,
                duration_seconds=None,
            )
        )
        history_imported += 1
        for photo in row.get("photos", []) or []:
            media = _import_legacy_photo(db, settings, photos_root, str(photo.get("src") or photo.get("fullSrc") or ""))
            if media is None:
                continue
            db.add(AssignmentPhoto(assignment_id=assignment.id, media_file_id=media.id, task_label=str(photo.get("task") or "Legacy")))
            photos_imported += 1
    return history_imported, photos_imported


def _import_legacy_messages(db: Session, communication_path: Path | None) -> int:
    if communication_path is None:
        return 0
    rows = _read_json(communication_path / "messages.json", [])
    grouped: dict[tuple[date, str], list[str]] = defaultdict(list)
    for row in rows:
        if "timestamp" in row:
            dt = _parse_datetime(row.get("timestamp"))
            if dt is None:
                continue
            grouped[(dt.date(), str(row.get("user") or "admin"))].append(str(row.get("message") or ""))
        else:
            msg_date = _parse_date(row.get("date") or row.get("message_date"))
            if msg_date is None:
                continue
            grouped[(msg_date, str(row.get("user") or "admin"))].append(str(row.get("content") or row.get("message") or ""))
    imported = 0
    for (message_date, username), messages in grouped.items():
        user = _user_by_username(db, username) or _user_by_username(db, "admin")
        if user is None:
            continue
        content = "\n".join(f"- {message}" for message in messages if message)
        existing = db.scalar(select(DailyMessage).where(DailyMessage.message_date == message_date, DailyMessage.user_id == user.id))
        if existing is None:
            db.add(DailyMessage(message_date=message_date, user_id=user.id, content_text=content))
            imported += 1
        else:
            existing.content_text = content
            existing.updated_at = utc_now()
    return imported


def _import_legacy_cash(db: Session, communication_path: Path | None) -> int:
    if communication_path is None:
        return 0
    rows = _read_json(communication_path / "cash_diary.json", [])
    imported = 0
    for row in rows:
        entry_date = _parse_date(row.get("date") or row.get("entry_date"))
        user = _user_by_username(db, str(row.get("user") or "admin")) or _user_by_username(db, "admin")
        if entry_date is None or user is None:
            continue
        cash_start = _float_or_none(row.get("cash_start"))
        cash_end = _float_or_none(row.get("cash_end"))
        existing = db.scalar(select(CashDiaryEntry).where(CashDiaryEntry.entry_date == entry_date, CashDiaryEntry.user_id == user.id))
        if existing is not None:
            continue
        db.add(
            CashDiaryEntry(
                entry_date=entry_date,
                user_id=user.id,
                shift_type=str(row.get("shift_type") or row.get("shift") or "Celodenní"),
                cash_start=cash_start,
                cash_end=cash_end,
                difference=(cash_end - cash_start) if cash_start is not None and cash_end is not None else None,
                notes=row.get("notes") or row.get("note"),
            )
        )
        imported += 1
    return imported


def _import_legacy_inventory(db: Session, inventory_path: Path | None) -> int:
    if inventory_path is None:
        return 0
    imported = 0
    for module in ["wellness", "minibar", "lobby"]:
        items = _read_json(inventory_path / f"{module}_items.json", [])
        item_map: dict[str, InventoryItem] = {}
        for index, row in enumerate(items):
            legacy_id = str(row.get("id") or index + 1)
            item = _ensure_inventory_item(db, module, row, index)
            item_map[legacy_id] = item
        data = _read_json(inventory_path / f"{module}_data.json", {})
        for raw_date, raw_payload in data.items():
            entry_date = _parse_date(raw_date)
            if entry_date is None:
                continue
            if db.scalar(select(InventoryEntry).where(InventoryEntry.entry_date == entry_date, InventoryEntry.module == module)) is not None:
                continue
            payload = raw_payload if isinstance(raw_payload, dict) else {}
            entry = InventoryEntry(entry_date=entry_date, module=module, note=payload.get("note"))
            db.add(entry)
            db.flush()
            position = 0
            for legacy_id, value in payload.items():
                if legacy_id == "note" or legacy_id == "custom":
                    continue
                item = item_map.get(str(legacy_id))
                if item is None:
                    continue
                quantity = _quantity(value)
                if quantity <= 0:
                    continue
                unit_price = item.price if item.price is not None else 0
                db.add(
                    InventoryEntryItem(
                        entry_id=entry.id,
                        item_id=item.id,
                        item_name=item.name,
                        unit=item.unit,
                        quantity=quantity,
                        unit_price=unit_price,
                        is_custom=False,
                        position=position,
                    )
                )
                position += 1
            imported += 1
    return imported


def _import_legacy_invoicing(db: Session, invoicing_path: Path | None, settings: Settings) -> tuple[int, int, int]:
    if invoicing_path is None:
        return 0, 0, 0
    services_imported = _import_legacy_services(db, _read_json(invoicing_path / "services.json", {}))
    due_terms_imported = _import_legacy_due_terms(db, _read_json(invoicing_path / "splatnosti.json", []))
    invoices_imported = _import_legacy_invoice_archive(db, _read_json(invoicing_path / "archiv_data.json", []), settings)
    return services_imported, due_terms_imported, invoices_imported


def _import_legacy_services(db: Session, data: dict[str, list[dict[str, Any]]]) -> int:
    imported = 0
    for sort_order, (category_name, services) in enumerate(data.items()):
        category = _ensure_service_category(db, category_name, sort_order)
        for service_order, row in enumerate(services):
            name = str(row.get("nazev") or row.get("name") or "").strip()
            if not name or db.scalar(select(Service).where(Service.category_id == category.id, Service.name == name)) is not None:
                continue
            db.add(
                Service(
                    category_id=category.id,
                    name=name,
                    type=str(row.get("typ") or row.get("type") or "ostatni"),
                    price=float(row.get("cena") or row.get("price") or 0),
                    active=bool(row.get("aktivni", row.get("active", True))),
                    sort_order=service_order,
                )
            )
            imported += 1
    return imported


def _import_legacy_due_terms(db: Session, rows: list[dict[str, Any]]) -> int:
    imported = 0
    for index, row in enumerate(rows):
        name = str(row.get("nazev") or row.get("name") or "").strip()
        if not name or db.scalar(select(DueTerm).where(DueTerm.name == name)) is not None:
            continue
        db.add(
            DueTerm(
                name=name,
                value=int(row.get("hodiny") or row.get("value") or 0),
                unit=str(row.get("jednotka") or row.get("unit") or "hodiny"),
                active=bool(row.get("aktivni", row.get("active", True))),
                sort_order=index,
            )
        )
        imported += 1
    return imported


def _import_legacy_invoice_archive(db: Session, rows: list[dict[str, Any]], settings: Settings) -> int:
    imported = 0
    for row in rows:
        invoice_number = str(row.get("cislo_faktury") or "").strip()
        if not invoice_number or db.scalar(select(Invoice).where(Invoice.invoice_number == invoice_number)) is not None:
            continue
        service_name = str(row.get("sluzba") or "Legacy")
        due_term_name = str(row.get("splatnost") or "")
        due_term = db.scalar(select(DueTerm).where(DueTerm.name == due_term_name))
        issued_at = _parse_datetime(row.get("datum_vytvoreni")) or utc_now()
        event_at = _parse_datetime(row.get("termin")) or issued_at
        due_at = _parse_datetime(row.get("due_date")) or event_at
        pdf_path = _legacy_invoice_pdf(settings, invoice_number)
        db.add(
            Invoice(
                invoice_number=invoice_number,
                variable_symbol=invoice_number,
                customer_name=str(row.get("jmeno") or "Legacy"),
                customer_email=row.get("email"),
                customer_phone=row.get("telefon"),
                service_id=None,
                service_name=service_name,
                custom_service_name=None,
                event_at=event_at,
                due_at=due_at,
                due_term_id=due_term.id if due_term else "legacy",
                due_term_name=due_term_name,
                due_term_value=due_term.value if due_term else 0,
                due_term_unit=due_term.unit if due_term else "hodiny",
                base_price=float(row.get("cena") or 0),
                increase_percent=0,
                price=float(row.get("cena") or 0),
                note=row.get("poznamka"),
                pdf_path=pdf_path,
                payment_status=_payment_status(row.get("stav")),
                created_at=issued_at,
                updated_at=issued_at,
            )
        )
        imported += 1
    return imported


def _ensure_inventory_item(db: Session, module: str, row: dict[str, Any], sort_order: int) -> InventoryItem:
    name = str(row.get("name") or row.get("nazev") or f"Legacy {sort_order + 1}").strip()
    existing = db.scalar(select(InventoryItem).where(InventoryItem.module == module, InventoryItem.name == name))
    if existing is not None:
        return existing
    item = InventoryItem(
        module=module,
        name=name,
        unit=str(row.get("unit") or "ks"),
        category=row.get("category"),
        price=_float_or_none(row.get("price") or row.get("default_price")),
        has_price=bool(row.get("has_price", row.get("price") is not None or row.get("default_price") is not None)),
        active=bool(row.get("active", True)),
        sort_order=sort_order,
    )
    db.add(item)
    db.flush()
    return item


def _ensure_service_category(db: Session, name: str, sort_order: int = 0) -> ServiceCategory:
    existing = db.scalar(select(ServiceCategory).where(ServiceCategory.name == name))
    if existing is not None:
        return existing
    category = ServiceCategory(name=name, sort_order=sort_order)
    db.add(category)
    db.flush()
    return category


def _ensure_room(db: Session, label: str) -> HotelRoom:
    label = label.strip() or "Legacy"
    room = db.scalar(select(HotelRoom).where(HotelRoom.label == label))
    if room is not None:
        return room
    room = HotelRoom(label=label)
    db.add(room)
    db.flush()
    return room


def _import_legacy_photo(db: Session, settings: Settings, photos_root: Path, src: str) -> MediaFile | None:
    filename = Path(src).name
    if not filename:
        return None
    source = photos_root / filename
    relative_path = Path("photos") / "legacy" / filename
    absolute_path = settings.file_storage_root / relative_path
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    size = None
    if source.exists():
        shutil.copy2(source, absolute_path)
        size = absolute_path.stat().st_size
    else:
        absolute_path.write_bytes(b"")
        size = 0
    media = MediaFile(
        module="housekeeping",
        original_name=filename,
        storage_path=relative_path.as_posix(),
        public_url=f"/api/files/{relative_path.as_posix()}",
        mime_type=_mime_from_suffix(filename),
        size_bytes=size,
    )
    db.add(media)
    db.flush()
    return media


def _legacy_invoice_pdf(settings: Settings, invoice_number: str) -> str:
    relative = Path("invoices") / f"{invoice_number}.pdf"
    absolute = settings.file_storage_root / relative
    absolute.parent.mkdir(parents=True, exist_ok=True)
    if not absolute.exists():
        absolute.write_bytes(b"%PDF-1.4\n% legacy imported invoice\n%%EOF\n")
    return relative.as_posix()


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_date(value: Any) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    dt = _parse_datetime(value)
    return dt.date() if dt else None


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return _aware(value)
    text = str(value).strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S", "%d.%m.%Y %H:%M:%S", "%d.%m.%Y %H:%M", "%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    try:
        return _aware(datetime.fromisoformat(text.replace("Z", "+00:00")))
    except ValueError:
        return None


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _quantity(value: Any) -> float:
    if isinstance(value, dict):
        return float(value.get("qty") or value.get("quantity") or 0)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0


def _float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _payment_status(value: Any) -> str:
    if value in {1, "1", "paid", "uhrazeno"}:
        return "paid"
    if value in {0, "0", "overdue", "neuhrazeno"}:
        return "overdue"
    return "pending"


def _role_name(legacy_role: str) -> str:
    return {"housekeeping": "pokojska", "reception": "recepcni", "accounting": "ucetni"}.get(legacy_role, legacy_role)


def _user_by_username(db: Session, username: str) -> User | None:
    if not username:
        return None
    return db.scalar(select(User).where(User.username == username))


def _mime_from_suffix(filename: str) -> str | None:
    suffix = Path(filename).suffix.lower()
    return {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(suffix)
