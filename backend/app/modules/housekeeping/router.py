from calendar import monthrange
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.database import get_db
from app.core.deps import get_app_settings, get_current_user
from app.core.models import SessionToken, User
from app.core.router import get_notification_queue
from app.core.schemas import NotificationCreate
from app.core.time import utc_now
from app.modules.catalog.models import HotelRoom, HousekeepingMinibarItem, PhotoTaskType
from app.modules.housekeeping.models import (
    AssignmentHistory,
    AssignmentMinibarEntry,
    AssignmentPhoto,
    AssignmentRequiredPhoto,
    HousekeepingAssignment,
    LaundryPhoto,
    LaundryTask,
    RevisionPhoto,
    RevisionTask,
)
from app.shared.files import save_upload
from app.shared.notifications import NotificationQueue, create_notification

router = APIRouter(prefix="/api/housekeeping", tags=["housekeeping"])


class AssignmentCreate(BaseModel):
    room_ids: list[str] = Field(min_length=1)
    work_type: str = Field(min_length=1, max_length=128)
    priority: str = Field(min_length=1, max_length=64)
    reception_note: str | None = None
    required_photo_type_ids: list[str] = Field(default_factory=list)


class MinibarCreate(BaseModel):
    item_id: str
    quantity: int = Field(gt=0)


class RevisionCreate(BaseModel):
    location: str = Field(min_length=1, max_length=255)
    text: str = Field(min_length=1)


def _csrf_user(x_csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"), db: Session = Depends(get_db)) -> User:
    if not x_csrf_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token")
    session = db.scalar(select(SessionToken).where(SessionToken.csrf_token == x_csrf_token))
    if session is None or _same_timezone(session.expires_at) < utc_now():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token")
    if session.user is None or not session.user.active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user")
    return session.user


def _csrf_admin(user: User = Depends(_csrf_user)) -> User:
    if user.role.name != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return user


@router.post("/assignments")
def create_assignments(
    payload: AssignmentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(_csrf_admin),
) -> list[dict]:
    required_types = _photo_types(db, payload.required_photo_type_ids)
    assignments: list[HousekeepingAssignment] = []
    for room_id in payload.room_ids:
        room = db.get(HotelRoom, room_id)
        if room is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown room")
        assignment = HousekeepingAssignment(
            room_id=room.id,
            room_label_snapshot=room.label,
            work_type=payload.work_type,
            priority=payload.priority,
            reception_note=payload.reception_note,
            assigned_by_id=user.id,
        )
        db.add(assignment)
        db.flush()
        for photo_type in required_types:
            db.add(
                AssignmentRequiredPhoto(
                    assignment_id=assignment.id,
                    photo_task_type_id=photo_type.id,
                    task_label_snapshot=photo_type.name,
                )
            )
        assignments.append(assignment)
    db.commit()
    for assignment in assignments:
        db.refresh(assignment)
    return [_assignment_dict(assignment) for assignment in assignments]


@router.patch("/assignments/{assignment_id}/start")
def start_assignment(assignment_id: str, db: Session = Depends(get_db), user: User = Depends(_csrf_user)) -> dict:
    assignment = _assignment(db, assignment_id)
    if assignment.status not in {"Prideleno", "Pozastaveno"}:
        return _assignment_dict(assignment)
    now = utc_now()
    assignment.status = "Uklizi se"
    assignment.started_at = assignment.started_at or now
    assignment.started_by_id = assignment.started_by_id or user.id
    assignment.pause_started_at = None
    db.commit()
    db.refresh(assignment)
    return _assignment_dict(assignment)


@router.patch("/assignments/{assignment_id}/pause")
def pause_assignment(assignment_id: str, db: Session = Depends(get_db), _: User = Depends(_csrf_user)) -> dict:
    assignment = _assignment(db, assignment_id)
    if assignment.status != "Uklizi se":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assignment is not in progress")
    assignment.status = "Pozastaveno"
    assignment.pause_started_at = utc_now()
    db.commit()
    db.refresh(assignment)
    return _assignment_dict(assignment)


@router.patch("/assignments/{assignment_id}/resume")
def resume_assignment(assignment_id: str, db: Session = Depends(get_db), _: User = Depends(_csrf_user)) -> dict:
    assignment = _assignment(db, assignment_id)
    if assignment.status != "Pozastaveno":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assignment is not paused")
    if assignment.pause_started_at is not None:
        assignment.paused_seconds += max(0, int((utc_now() - _same_timezone(assignment.pause_started_at)).total_seconds()))
    assignment.status = "Uklizi se"
    assignment.pause_started_at = None
    db.commit()
    db.refresh(assignment)
    return _assignment_dict(assignment)


@router.patch("/assignments/{assignment_id}/finish")
def finish_assignment(
    assignment_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(_csrf_user),
    queue: NotificationQueue = Depends(get_notification_queue),
) -> dict:
    assignment = _assignment(db, assignment_id)
    missing = _missing_required_photo_labels(db, assignment.id)
    if missing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"missing_required_photos": missing})
    now = utc_now()
    assignment.status = "Hotovo"
    assignment.finished_at = now
    assignment.finished_by_id = user.id
    if assignment.pause_started_at is not None:
        assignment.paused_seconds += max(0, int((now - _same_timezone(assignment.pause_started_at)).total_seconds()))
        assignment.pause_started_at = None
    if db.scalar(select(AssignmentHistory).where(AssignmentHistory.assignment_id == assignment.id)) is None:
        duration_seconds = None
        if assignment.started_at is not None:
            duration_seconds = max(0, int((now - _same_timezone(assignment.started_at)).total_seconds()) - assignment.paused_seconds)
        db.add(
            AssignmentHistory(
                assignment_id=assignment.id,
                room_id=assignment.room_id,
                room_label_snapshot=assignment.room_label_snapshot,
                work_type=assignment.work_type,
                priority=assignment.priority,
                housekeeper_id=user.id,
                housekeeper_username_snapshot=user.username,
                finished_at=now,
                duration_seconds=duration_seconds,
            )
        )
    db.commit()
    db.refresh(assignment)
    _notify(db, queue, user, "housekeeping.assignment.finished", "Pokoj dokončen", assignment.room_label_snapshot, "housekeeping_assignment", assignment.id)
    return _assignment_dict(assignment)


@router.post("/assignments/{assignment_id}/photos")
def upload_assignment_photo(
    assignment_id: str,
    task_label: str | None = Form(default=None),
    photo_task_type_id: str | None = Form(default=None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    user: User = Depends(_csrf_user),
) -> dict:
    _assignment(db, assignment_id)
    if photo_task_type_id is not None and db.get(PhotoTaskType, photo_task_type_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown photo task type")
    media = save_upload(db, settings, "housekeeping", file, user.id)
    photo = AssignmentPhoto(
        assignment_id=assignment_id,
        media_file_id=media.id,
        photo_task_type_id=photo_task_type_id,
        task_label=task_label,
        created_by_id=user.id,
    )
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return {"id": photo.id, "assignment_id": assignment_id, "media_file_id": media.id, "public_url": media.public_url}


@router.post("/assignments/{assignment_id}/minibar")
def add_minibar_entry(assignment_id: str, payload: MinibarCreate, db: Session = Depends(get_db), user: User = Depends(_csrf_user)) -> dict:
    _assignment(db, assignment_id)
    item = db.get(HousekeepingMinibarItem, payload.item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown minibar item")
    existing = db.scalar(
        select(AssignmentMinibarEntry).where(
            AssignmentMinibarEntry.assignment_id == assignment_id,
            AssignmentMinibarEntry.item_id == payload.item_id,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Minibar item already checked")
    entry = AssignmentMinibarEntry(
        assignment_id=assignment_id,
        item_id=item.id,
        item_name_snapshot=item.name,
        quantity=payload.quantity,
        created_by_id=user.id,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {"id": entry.id, "item_id": entry.item_id, "item_name_snapshot": entry.item_name_snapshot, "quantity": entry.quantity}


@router.get("/history")
def list_history(month: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[dict]:
    start, end = _month_window(month)
    rows = db.scalars(select(AssignmentHistory).where(AssignmentHistory.finished_at >= start, AssignmentHistory.finished_at < end).order_by(AssignmentHistory.finished_at.desc())).all()
    return [
        {
            "id": row.id,
            "assignment_id": row.assignment_id,
            "room_label_snapshot": row.room_label_snapshot,
            "work_type": row.work_type,
            "priority": row.priority,
            "housekeeper_username_snapshot": row.housekeeper_username_snapshot,
            "finished_at": row.finished_at,
            "duration_seconds": row.duration_seconds,
        }
        for row in rows
    ]


@router.post("/revisions")
def create_revision(payload: RevisionCreate, db: Session = Depends(get_db), user: User = Depends(_csrf_admin)) -> dict:
    revision = RevisionTask(location=payload.location, text=payload.text, created_by_id=user.id)
    db.add(revision)
    db.commit()
    db.refresh(revision)
    return _revision_dict(revision)


@router.patch("/revisions/{revision_id}/complete")
def complete_revision(
    revision_id: str,
    note: str | None = Form(default=None),
    files: list[UploadFile] | None = File(default=None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    user: User = Depends(_csrf_user),
    queue: NotificationQueue = Depends(get_notification_queue),
) -> dict:
    revision = _revision(db, revision_id)
    for upload in files or []:
        media = save_upload(db, settings, "housekeeping", upload, user.id)
        db.add(RevisionPhoto(revision_id=revision.id, media_file_id=media.id, created_by_id=user.id))
    revision.status = "done"
    revision.completed_by_id = user.id
    revision.completed_at = utc_now()
    revision.completion_note = note
    db.commit()
    db.refresh(revision)
    _notify(db, queue, user, "housekeeping.revision.completed", "Revize dokončena", revision.location, "housekeeping_revision", revision.id)
    return _revision_dict(revision)


@router.post("/laundry")
def create_laundry(db: Session = Depends(get_db), user: User = Depends(_csrf_admin)) -> dict:
    laundry = LaundryTask(created_by_id=user.id)
    db.add(laundry)
    db.commit()
    db.refresh(laundry)
    return _laundry_dict(laundry)


@router.patch("/laundry/{laundry_id}/accept")
def accept_laundry(laundry_id: str, db: Session = Depends(get_db), user: User = Depends(_csrf_user)) -> dict:
    laundry = _laundry(db, laundry_id)
    laundry.status = "accepted"
    laundry.accepted_by_id = user.id
    laundry.accepted_at = utc_now()
    db.commit()
    db.refresh(laundry)
    return _laundry_dict(laundry)


@router.post("/laundry/{laundry_id}/photos")
def upload_laundry_photo(
    laundry_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    user: User = Depends(_csrf_user),
) -> dict:
    _laundry(db, laundry_id)
    media = save_upload(db, settings, "housekeeping", file, user.id)
    photo = LaundryPhoto(laundry_id=laundry_id, media_file_id=media.id, created_by_id=user.id)
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return {"id": photo.id, "laundry_id": laundry_id, "media_file_id": media.id, "public_url": media.public_url}


@router.patch("/laundry/{laundry_id}/done")
def finish_laundry(
    laundry_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(_csrf_user),
    queue: NotificationQueue = Depends(get_notification_queue),
) -> dict:
    laundry = _laundry(db, laundry_id)
    has_photo = db.scalar(select(LaundryPhoto.id).where(LaundryPhoto.laundry_id == laundry_id).limit(1))
    if has_photo is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Laundry photo is required")
    laundry.status = "done"
    laundry.done_by_id = user.id
    laundry.done_at = utc_now()
    db.commit()
    db.refresh(laundry)
    _notify(db, queue, user, "housekeeping.laundry.done", "Prádlo dokončeno", None, "housekeeping_laundry", laundry.id)
    return _laundry_dict(laundry)


@router.get("/reports/monthly-work")
def monthly_work_report(month: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> dict:
    start, end = _month_window(month)
    housekeepers: dict[str, dict[str, int]] = {}

    assignment_rows = db.execute(
        select(User.username, func.count(AssignmentHistory.id))
        .join(User, User.id == AssignmentHistory.housekeeper_id)
        .where(AssignmentHistory.finished_at >= start, AssignmentHistory.finished_at < end)
        .group_by(User.username)
    ).all()
    for username, count in assignment_rows:
        housekeepers.setdefault(username, _empty_report())["assignment_count"] = count

    revision_rows = db.execute(
        select(User.username, func.count(RevisionTask.id))
        .join(User, User.id == RevisionTask.completed_by_id)
        .where(RevisionTask.completed_at >= start, RevisionTask.completed_at < end)
        .group_by(User.username)
    ).all()
    for username, count in revision_rows:
        housekeepers.setdefault(username, _empty_report())["revision_count"] = count

    laundry_rows = db.execute(
        select(User.username, func.count(LaundryTask.id))
        .join(User, User.id == LaundryTask.done_by_id)
        .where(LaundryTask.done_at >= start, LaundryTask.done_at < end)
        .group_by(User.username)
    ).all()
    for username, count in laundry_rows:
        housekeepers.setdefault(username, _empty_report())["laundry_count"] = count

    return {"month": month, "housekeepers": housekeepers}


def _assignment(db: Session, assignment_id: str) -> HousekeepingAssignment:
    assignment = db.get(HousekeepingAssignment, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    return assignment


def _revision(db: Session, revision_id: str) -> RevisionTask:
    revision = db.get(RevisionTask, revision_id)
    if revision is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Revision not found")
    return revision


def _laundry(db: Session, laundry_id: str) -> LaundryTask:
    laundry = db.get(LaundryTask, laundry_id)
    if laundry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Laundry task not found")
    return laundry


def _photo_types(db: Session, photo_type_ids: list[str]) -> list[PhotoTaskType]:
    photo_types: list[PhotoTaskType] = []
    for photo_type_id in photo_type_ids:
        photo_type = db.get(PhotoTaskType, photo_type_id)
        if photo_type is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown photo task type")
        photo_types.append(photo_type)
    return photo_types


def _missing_required_photo_labels(db: Session, assignment_id: str) -> list[str]:
    required = db.scalars(select(AssignmentRequiredPhoto).where(AssignmentRequiredPhoto.assignment_id == assignment_id)).all()
    missing: list[str] = []
    for required_photo in required:
        uploaded = db.scalar(
            select(AssignmentPhoto.id)
            .where(
                AssignmentPhoto.assignment_id == assignment_id,
                AssignmentPhoto.photo_task_type_id == required_photo.photo_task_type_id,
            )
            .limit(1)
        )
        if uploaded is None:
            missing.append(required_photo.task_label_snapshot)
    return missing


def _assignment_dict(assignment: HousekeepingAssignment) -> dict:
    return {
        "id": assignment.id,
        "room_id": assignment.room_id,
        "room_label_snapshot": assignment.room_label_snapshot,
        "work_type": assignment.work_type,
        "priority": assignment.priority,
        "reception_note": assignment.reception_note,
        "status": assignment.status,
        "paused_seconds": assignment.paused_seconds,
        "created_at": assignment.created_at,
        "started_at": assignment.started_at,
        "finished_at": assignment.finished_at,
    }


def _revision_dict(revision: RevisionTask) -> dict:
    return {
        "id": revision.id,
        "location": revision.location,
        "text": revision.text,
        "status": revision.status,
        "completion_note": revision.completion_note,
        "created_at": revision.created_at,
        "completed_at": revision.completed_at,
    }


def _laundry_dict(laundry: LaundryTask) -> dict:
    return {
        "id": laundry.id,
        "status": laundry.status,
        "created_at": laundry.created_at,
        "accepted_at": laundry.accepted_at,
        "done_at": laundry.done_at,
    }


def _month_window(month: str) -> tuple[datetime, datetime]:
    try:
        year_text, month_text = month.split("-", 1)
        year = int(year_text)
        month_number = int(month_text)
        monthrange(year, month_number)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Month must use YYYY-MM format") from None
    start = datetime(year, month_number, 1, tzinfo=UTC)
    if month_number == 12:
        end = datetime(year + 1, 1, 1, tzinfo=UTC)
    else:
        end = datetime(year, month_number + 1, 1, tzinfo=UTC)
    return start, end


def _notify(db: Session, queue: NotificationQueue, user: User, event_type: str, title: str, body: str | None, entity_type: str, entity_id: str) -> None:
    create_notification(
        db,
        queue,
        NotificationCreate(
            user_id=user.id,
            event_type=event_type,
            title=title,
            body=body,
            entity_type=entity_type,
            entity_id=entity_id,
        ),
    )


def _same_timezone(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _empty_report() -> dict[str, int]:
    return {"assignment_count": 0, "revision_count": 0, "laundry_count": 0}
