import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.database import Base, get_db
from app.core.deps import get_app_settings, get_current_user, require_admin, require_csrf
from app.core.models import User
from app.core.time import utc_now
from app.modules.backups.models import BackupRecord, RecoveryPoint, RestoreRecord

router = APIRouter(prefix="/api/backups", tags=["backups"])


class ManualBackupCreate(BaseModel):
    note: str | None = None


class BackupRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    backup_type: str
    file_path: str
    note: str | None
    size_bytes: int | None
    status: str
    created_by: str | None
    created_at: datetime
    retained_until: datetime | None
    metadata_json: dict[str, Any] | None


class RecoveryPointCreate(BaseModel):
    description: str | None = None


class RecoveryPointRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    description: str | None
    data_snapshot_path: str
    created_by: str | None
    created_at: datetime
    restored_at: datetime | None
    restore_metadata_json: dict[str, Any] | None


class RestoreRead(BaseModel):
    restored: bool
    recovery_point_id: str
    restored_at: datetime
    metadata: dict[str, Any]


@router.get("", response_model=list[BackupRead])
def list_backups(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[BackupRecord]:
    return list(
        db.scalars(
            select(BackupRecord)
            .where(BackupRecord.deleted_at.is_(None))
            .order_by(BackupRecord.created_at.desc(), BackupRecord.id.desc())
        ).all()
    )


@router.post("/manual", response_model=BackupRead, dependencies=[Depends(require_csrf)])
def create_manual_backup(
    payload: ManualBackupCreate,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    user: User = Depends(require_admin),
) -> BackupRecord:
    created_at = utc_now()
    record = BackupRecord(
        backup_type="manual",
        note=payload.note,
        file_path="",
        status="running",
        created_by=user.id,
        created_at=created_at,
        metadata_json={"format": "zip", "contents": ["manifest.json"]},
    )
    db.add(record)
    db.flush()

    relative_path = Path("backups") / "manual" / f"{record.id}.zip"
    absolute_path = settings.file_storage_root / relative_path
    absolute_path.parent.mkdir(parents=True, exist_ok=True)

    manifest = {
        "id": record.id,
        "backup_type": record.backup_type,
        "note": record.note,
        "created_by": record.created_by,
        "created_at": created_at.isoformat(),
        "database_tables": sorted(Base.metadata.tables),
    }
    with zipfile.ZipFile(absolute_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))

    record.file_path = str(relative_path)
    record.size_bytes = absolute_path.stat().st_size
    record.status = "completed"
    db.commit()
    db.refresh(record)
    return record


@router.delete("/{backup_id}", dependencies=[Depends(require_csrf)])
def delete_backup(
    backup_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    _: User = Depends(require_admin),
) -> dict[str, bool]:
    backup = db.get(BackupRecord, backup_id)
    if backup is None or backup.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup not found")
    now = utc_now()
    if backup.retained_until is not None and backup.retained_until > now:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Backup is still retained")

    path = settings.file_storage_root / backup.file_path
    if path.exists():
        path.unlink()
    backup.deleted_at = now
    db.commit()
    return {"ok": True}


@router.post("/recovery-points", response_model=RecoveryPointRead, dependencies=[Depends(require_csrf)])
def create_recovery_point(
    payload: RecoveryPointCreate,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    user: User = Depends(require_admin),
) -> RecoveryPoint:
    created_at = utc_now()
    point = RecoveryPoint(
        description=payload.description,
        data_snapshot_path="",
        created_by=user.id,
        created_at=created_at,
    )
    db.add(point)
    db.flush()

    relative_path = Path("backups") / "recovery-points" / f"{point.id}.json"
    absolute_path = settings.file_storage_root / relative_path
    absolute_path.parent.mkdir(parents=True, exist_ok=True)

    snapshot = {
        "id": point.id,
        "description": point.description,
        "created_by": point.created_by,
        "created_at": created_at.isoformat(),
        "database_tables": sorted(Base.metadata.tables),
    }
    absolute_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

    point.data_snapshot_path = str(relative_path)
    db.commit()
    db.refresh(point)
    return point


@router.post("/recovery-points/{recovery_point_id}/restore", response_model=RestoreRead, dependencies=[Depends(require_csrf)])
def restore_recovery_point(
    recovery_point_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    user: User = Depends(require_admin),
) -> RestoreRead:
    point = db.get(RecoveryPoint, recovery_point_id)
    if point is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recovery point not found")

    snapshot_path = settings.file_storage_root / point.data_snapshot_path
    if not snapshot_path.exists():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Recovery snapshot is missing")

    metadata = {
        "snapshot_path": point.data_snapshot_path,
        "description": point.description,
        "mode": "metadata-only",
    }
    restored_at = utc_now()
    restore = RestoreRecord(
        recovery_point_id=point.id,
        restored_by=user.id,
        restored_at=restored_at,
        metadata_json=metadata,
    )
    point.restored_at = restored_at
    point.restore_metadata_json = metadata
    db.add(restore)
    db.commit()

    return RestoreRead(restored=True, recovery_point_id=point.id, restored_at=restored_at, metadata=metadata)
