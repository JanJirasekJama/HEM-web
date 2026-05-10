import csv
from datetime import UTC, date, datetime, time
from io import StringIO
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_permission, require_csrf
from app.core.models import User
from app.core.time import utc_now
from app.modules.cash.models import CashDiaryEntry, CashDiaryHistory, CashShiftLog

router = APIRouter(prefix="/api/cash", tags=["cash"])


class ShiftLogCreate(BaseModel):
    user_id: str
    shift_type: str = Field(min_length=1, max_length=64)
    start_time: datetime
    end_time: datetime | None = None
    cash_start: float | None = None


class ShiftLogRead(ShiftLogCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime


class DiaryUpsert(BaseModel):
    entry_date: date
    user_id: str
    shift_type: str | None = Field(default=None, max_length=64)
    cash_start: float | None = None
    cash_end: float | None = None
    notes: str | None = None


class DiaryRead(DiaryUpsert):
    model_config = ConfigDict(from_attributes=True)

    id: str
    shift_type: str
    difference: float | None
    created_at: datetime
    updated_at: datetime


class DiaryHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    diary_entry_id: str
    action: str
    changed_by_id: str | None
    snapshot_json: dict[str, Any]
    created_at: datetime


class CashStatusRead(BaseModel):
    date: date
    user_id: str
    missing_morning_cash: bool
    missing_evening_cash: bool


@router.post("/shift-log", response_model=ShiftLogRead, dependencies=[Depends(require_csrf)])
def create_shift_log(payload: ShiftLogCreate, db: Session = Depends(get_db), _: User = Depends(require_permission("cash:write"))) -> CashShiftLog:
    _require_user(db, payload.user_id)
    shift = CashShiftLog(**payload.model_dump())
    db.add(shift)
    db.commit()
    db.refresh(shift)
    return shift


@router.get("/shift-log", response_model=list[ShiftLogRead])
def list_shift_logs(
    date_from: date | None = None,
    date_to: date | None = None,
    user_id: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("cash:read")),
) -> list[CashShiftLog]:
    stmt = select(CashShiftLog)
    if user_id:
        stmt = stmt.where(CashShiftLog.user_id == user_id)
    if date_from:
        stmt = stmt.where(CashShiftLog.start_time >= datetime.combine(date_from, time.min, tzinfo=UTC))
    if date_to:
        stmt = stmt.where(CashShiftLog.start_time <= datetime.combine(date_to, time.max, tzinfo=UTC))
    return list(db.scalars(stmt.order_by(CashShiftLog.start_time)).all())


@router.post("/diary", response_model=DiaryRead, dependencies=[Depends(require_csrf)])
def upsert_diary(payload: DiaryUpsert, db: Session = Depends(get_db), user: User = Depends(require_permission("cash:write"))) -> CashDiaryEntry:
    _require_user(db, payload.user_id)
    entry = db.scalar(select(CashDiaryEntry).where(CashDiaryEntry.entry_date == payload.entry_date, CashDiaryEntry.user_id == payload.user_id))
    action = "updated" if entry else "created"
    if entry is None:
        entry = CashDiaryEntry(entry_date=payload.entry_date, user_id=payload.user_id, shift_type="")
        db.add(entry)

    entry.shift_type = payload.shift_type or _detect_shift_type(db, payload.entry_date, payload.user_id, entry.id if action == "updated" else None)
    entry.cash_start = payload.cash_start
    entry.cash_end = payload.cash_end
    entry.difference = _calculate_difference(payload.cash_start, payload.cash_end)
    entry.notes = payload.notes
    entry.updated_at = utc_now()
    db.flush()
    _add_history(db, entry, action, user.id)
    db.commit()
    db.refresh(entry)
    return entry


@router.get("/diary/export.csv")
def export_diary_csv(
    date_from: date | None = None,
    date_to: date | None = None,
    user_id: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("cash:export")),
) -> Response:
    rows = _query_diary(db, date_from, date_to, user_id)
    output = StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["id", "entry_date", "user_id", "shift_type", "cash_start", "cash_end", "difference", "notes", "created_at", "updated_at"],
    )
    writer.writeheader()
    for entry in rows:
        writer.writerow(_entry_snapshot(entry))
    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="cash-diary.csv"'},
    )


@router.get("/diary", response_model=list[DiaryRead])
def list_diary(
    date_from: date | None = None,
    date_to: date | None = None,
    user_id: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("cash:read")),
) -> list[CashDiaryEntry]:
    return _query_diary(db, date_from, date_to, user_id)


@router.get("/diary/{entry_id}", response_model=DiaryRead)
def read_diary(entry_id: str, db: Session = Depends(get_db), _: User = Depends(require_permission("cash:read"))) -> CashDiaryEntry:
    return _require_diary(db, entry_id)


@router.put("/diary/{entry_id}", response_model=DiaryRead, dependencies=[Depends(require_csrf)])
def update_diary(entry_id: str, payload: DiaryUpsert, db: Session = Depends(get_db), user: User = Depends(require_permission("cash:write"))) -> CashDiaryEntry:
    _require_user(db, payload.user_id)
    entry = _require_diary(db, entry_id)
    duplicate = db.scalar(
        select(CashDiaryEntry).where(
            CashDiaryEntry.id != entry_id,
            CashDiaryEntry.entry_date == payload.entry_date,
            CashDiaryEntry.user_id == payload.user_id,
        )
    )
    if duplicate is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cash diary entry already exists for this date and user")

    entry.entry_date = payload.entry_date
    entry.user_id = payload.user_id
    entry.shift_type = payload.shift_type or _detect_shift_type(db, payload.entry_date, payload.user_id, entry.id)
    entry.cash_start = payload.cash_start
    entry.cash_end = payload.cash_end
    entry.difference = _calculate_difference(payload.cash_start, payload.cash_end)
    entry.notes = payload.notes
    entry.updated_at = utc_now()
    _add_history(db, entry, "updated", user.id)
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/diary/{entry_id}", dependencies=[Depends(require_csrf)])
def delete_diary(entry_id: str, db: Session = Depends(get_db), user: User = Depends(require_permission("cash:write"))) -> dict[str, bool]:
    entry = _require_diary(db, entry_id)
    _add_history(db, entry, "deleted", user.id)
    db.delete(entry)
    db.commit()
    return {"ok": True}


@router.get("/diary/{entry_id}/history", response_model=list[DiaryHistoryRead])
def diary_history(entry_id: str, db: Session = Depends(get_db), _: User = Depends(require_permission("cash:read"))) -> list[CashDiaryHistory]:
    _require_diary(db, entry_id)
    return list(db.scalars(select(CashDiaryHistory).where(CashDiaryHistory.diary_entry_id == entry_id).order_by(CashDiaryHistory.created_at)).all())


@router.get("/status", response_model=CashStatusRead)
def cash_status(
    date: date,
    user_id: str,
    at: datetime | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("cash:read")),
) -> CashStatusRead:
    _require_user(db, user_id)
    entry = db.scalar(select(CashDiaryEntry).where(CashDiaryEntry.entry_date == date, CashDiaryEntry.user_id == user_id))
    check_time = at or utc_now()
    missing_morning = entry is None or entry.cash_start is None
    missing_evening = _is_after_evening_deadline(check_time) and (entry is None or entry.cash_end is None)
    return CashStatusRead(date=date, user_id=user_id, missing_morning_cash=missing_morning, missing_evening_cash=missing_evening)


def _query_diary(db: Session, date_from: date | None, date_to: date | None, user_id: str | None) -> list[CashDiaryEntry]:
    stmt = select(CashDiaryEntry)
    if date_from:
        stmt = stmt.where(CashDiaryEntry.entry_date >= date_from)
    if date_to:
        stmt = stmt.where(CashDiaryEntry.entry_date <= date_to)
    if user_id:
        stmt = stmt.where(CashDiaryEntry.user_id == user_id)
    return list(db.scalars(stmt.order_by(CashDiaryEntry.entry_date, CashDiaryEntry.created_at)).all())


def _require_user(db: Session, user_id: str) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def _require_diary(db: Session, entry_id: str) -> CashDiaryEntry:
    entry = db.get(CashDiaryEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cash diary entry not found")
    return entry


def _detect_shift_type(db: Session, entry_date: date, user_id: str, current_entry_id: str | None = None) -> str:
    start = datetime.combine(entry_date, time.min, tzinfo=UTC)
    end = datetime.combine(entry_date, time.max, tzinfo=UTC)
    shift = db.scalar(
        select(CashShiftLog)
        .where(CashShiftLog.user_id == user_id, CashShiftLog.start_time >= start, CashShiftLog.start_time <= end)
        .order_by(CashShiftLog.start_time)
        .limit(1)
    )
    if shift is not None:
        return shift.shift_type

    stmt = select(CashDiaryEntry).where(CashDiaryEntry.entry_date == entry_date, CashDiaryEntry.user_id == user_id)
    if current_entry_id is not None:
        stmt = stmt.where(CashDiaryEntry.id != current_entry_id)
    existing_count = len(db.scalars(stmt).all())
    return "Ranní" if existing_count == 0 else "Večerní"


def _calculate_difference(cash_start: float | None, cash_end: float | None) -> float | None:
    if cash_start is None or cash_end is None:
        return None
    return cash_end - cash_start


def _add_history(db: Session, entry: CashDiaryEntry, action: str, changed_by_id: str | None) -> None:
    db.add(
        CashDiaryHistory(
            diary_entry_id=entry.id,
            action=action,
            changed_by_id=changed_by_id,
            snapshot_json=_entry_snapshot(entry),
        )
    )


def _entry_snapshot(entry: CashDiaryEntry) -> dict[str, Any]:
    return {
        "id": entry.id,
        "entry_date": entry.entry_date.isoformat(),
        "user_id": entry.user_id,
        "shift_type": entry.shift_type,
        "cash_start": entry.cash_start,
        "cash_end": entry.cash_end,
        "difference": entry.difference,
        "notes": entry.notes,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
        "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
    }


def _is_after_evening_deadline(value: datetime) -> bool:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.timetz().replace(tzinfo=None) >= time(20, 0)
