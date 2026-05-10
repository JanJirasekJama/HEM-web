import json
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Date, DateTime, Table, delete, insert, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.database import Base, get_db
from app.core.deps import get_app_settings, require_admin, require_csrf, require_role
from app.core.models import User
from app.core.time import utc_now
from app.modules.backups.models import BackupRecord, RecoveryPoint, RestoreRecord

router = APIRouter(prefix="/api/backups", tags=["backups"])

SNAPSHOT_FORMAT = "hem-db-snapshot-v1"
VOLATILE_TABLES = {"sessions"}
RESTORE_METADATA_TABLES = {"backup_records", "recovery_points", "restore_records"}
BACKUP_STORAGE_DIR = Path("backups")
FILES_ARCHIVE_PREFIX = "files/"


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


def _snapshot_tables() -> list[Table]:
    return [table for table in Base.metadata.sorted_tables if table.name not in VOLATILE_TABLES]


def _restore_tables(snapshot: dict[str, Any]) -> list[Table]:
    available = snapshot.get("tables", {})
    return [
        table
        for table in Base.metadata.sorted_tables
        if table.name in available and table.name not in VOLATILE_TABLES and table.name not in RESTORE_METADATA_TABLES
    ]


def _json_value(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _db_value(column: Any, value: Any) -> Any:
    if value is None:
        return None
    if isinstance(column.type, DateTime):
        return datetime.fromisoformat(value)
    if isinstance(column.type, Date):
        return date.fromisoformat(value)
    return value


def _dump_database(db: Session) -> dict[str, Any]:
    tables: dict[str, Any] = {}
    for table in _snapshot_tables():
        ordering = list(table.primary_key.columns) or list(table.columns)
        rows = db.execute(select(table).order_by(*ordering)).mappings().all()
        tables[table.name] = {
            "columns": [column.name for column in table.columns],
            "rows": [{column.name: _json_value(row[column.name]) for column in table.columns} for row in rows],
        }
    return {"format": SNAPSHOT_FORMAT, "tables": tables}


def _load_snapshot(path: Path) -> dict[str, Any]:
    try:
        snapshot = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Recovery snapshot is unreadable") from exc
    if snapshot.get("format") != SNAPSHOT_FORMAT or not isinstance(snapshot.get("tables"), dict):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Recovery snapshot has unsupported format")
    return snapshot


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _iter_storage_files(storage_root: Path, excluded_paths: set[Path] | None = None) -> list[tuple[Path, Path]]:
    excluded_paths = {path.resolve() for path in excluded_paths or set()}
    if not storage_root.exists():
        return []

    files: list[tuple[Path, Path]] = []
    for path in sorted(storage_root.rglob("*")):
        if not path.is_file():
            continue
        resolved = path.resolve()
        if resolved in excluded_paths:
            continue
        relative_path = path.relative_to(storage_root)
        if relative_path.parts and relative_path.parts[0] == BACKUP_STORAGE_DIR.name:
            continue
        files.append((relative_path, path))
    return files


def _write_files_to_archive(
    archive: zipfile.ZipFile,
    storage_root: Path,
    excluded_paths: set[Path] | None = None,
) -> dict[str, int]:
    count = 0
    size_bytes = 0
    for relative_path, path in _iter_storage_files(storage_root, excluded_paths):
        archive.write(path, f"{FILES_ARCHIVE_PREFIX}{relative_path.as_posix()}")
        count += 1
        size_bytes += path.stat().st_size
    return {"count": count, "bytes": size_bytes}


def _create_file_snapshot(snapshot_path: Path, storage_root: Path) -> dict[str, int | str]:
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(snapshot_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        stats = _write_files_to_archive(archive, storage_root, {snapshot_path})
        archive.writestr(
            "manifest.json",
            json.dumps({"format": "hem-file-snapshot-v1", "files": stats}, ensure_ascii=False, indent=2),
        )
    return {"path": str(snapshot_path.relative_to(storage_root)), **stats}


def _restore_file_snapshot(snapshot_path: Path, storage_root: Path) -> dict[str, int]:
    if not snapshot_path.exists():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Recovery file snapshot is missing")

    storage_root.mkdir(parents=True, exist_ok=True)
    restored_paths: set[Path] = set()
    restored_count = 0
    restored_bytes = 0

    try:
        with zipfile.ZipFile(snapshot_path) as archive:
            for info in archive.infolist():
                if info.is_dir() or not info.filename.startswith(FILES_ARCHIVE_PREFIX):
                    continue
                relative_name = info.filename[len(FILES_ARCHIVE_PREFIX) :]
                relative_path = Path(relative_name)
                if relative_path.is_absolute() or ".." in relative_path.parts:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Recovery file snapshot has unsafe paths",
                    )

                target_path = storage_root / relative_path
                if not _is_relative_to(target_path.resolve(), storage_root.resolve()):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Recovery file snapshot has unsafe paths",
                    )
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_bytes(archive.read(info))
                restored_paths.add(relative_path)
                restored_count += 1
                restored_bytes += info.file_size
    except zipfile.BadZipFile as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Recovery file snapshot is unreadable") from exc

    removed_count = 0
    for relative_path, path in reversed(_iter_storage_files(storage_root)):
        if relative_path not in restored_paths:
            path.unlink()
            removed_count += 1

    for directory in sorted((path for path in storage_root.rglob("*") if path.is_dir()), reverse=True):
        if directory == storage_root or _is_relative_to(directory, storage_root / BACKUP_STORAGE_DIR):
            continue
        try:
            directory.rmdir()
        except OSError:
            pass

    return {"restored": restored_count, "bytes": restored_bytes, "removed": removed_count}


def _restore_snapshot_data(db: Session, snapshot: dict[str, Any]) -> dict[str, int]:
    tables = _restore_tables(snapshot)
    counts: dict[str, int] = {}

    for volatile_table_name in VOLATILE_TABLES:
        volatile_table = Base.metadata.tables.get(volatile_table_name)
        if volatile_table is not None:
            db.execute(delete(volatile_table))
    for table in reversed(tables):
        db.execute(delete(table))

    for table in tables:
        table_snapshot = snapshot["tables"][table.name]
        columns = {column.name: column for column in table.columns}
        rows = [
            {column_name: _db_value(columns[column_name], value) for column_name, value in row.items() if column_name in columns}
            for row in table_snapshot.get("rows", [])
        ]
        if rows:
            db.execute(insert(table), rows)
        counts[table.name] = len(rows)

    return counts


@router.get("", response_model=list[BackupRead])
def list_backups(db: Session = Depends(get_db), _: User = Depends(require_role("admin"))) -> list[BackupRecord]:
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
        metadata_json={"format": "zip", "contents": ["manifest.json", "database.json", "files/"]},
    )
    db.add(record)
    db.flush()

    relative_path = Path("backups") / "manual" / f"{record.id}.zip"
    absolute_path = settings.file_storage_root / relative_path
    absolute_path.parent.mkdir(parents=True, exist_ok=True)

    database = _dump_database(db)
    with zipfile.ZipFile(absolute_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        file_stats = _write_files_to_archive(archive, settings.file_storage_root, {absolute_path})
        manifest = {
            "id": record.id,
            "backup_type": record.backup_type,
            "note": record.note,
            "created_by": record.created_by,
            "created_at": created_at.isoformat(),
            "snapshot_format": SNAPSHOT_FORMAT,
            "database_tables": sorted(database["tables"]),
            "excluded_tables": sorted(VOLATILE_TABLES),
            "files": file_stats,
        }
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        archive.writestr("database.json", json.dumps(database, ensure_ascii=False, indent=2))

    record.file_path = str(relative_path)
    record.size_bytes = absolute_path.stat().st_size
    record.status = "completed"
    record.metadata_json = {
        "format": "zip",
        "contents": ["manifest.json", "database.json", "files/"],
        "files": file_stats,
    }
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
    file_snapshot_relative_path = Path("backups") / "recovery-points" / f"{point.id}.files.zip"
    absolute_path = settings.file_storage_root / relative_path
    file_snapshot_path = settings.file_storage_root / file_snapshot_relative_path
    absolute_path.parent.mkdir(parents=True, exist_ok=True)

    file_snapshot = _create_file_snapshot(file_snapshot_path, settings.file_storage_root)
    snapshot = _dump_database(db)
    snapshot.update(
        {
            "id": point.id,
            "description": point.description,
            "created_by": point.created_by,
            "created_at": created_at.isoformat(),
            "database_tables": sorted(snapshot["tables"]),
            "excluded_tables": sorted(VOLATILE_TABLES),
            "file_snapshot": file_snapshot,
        }
    )
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

    snapshot = _load_snapshot(snapshot_path)
    try:
        counts = _restore_snapshot_data(db, snapshot)
        file_snapshot = snapshot.get("file_snapshot")
        file_counts = None
        if isinstance(file_snapshot, dict) and isinstance(file_snapshot.get("path"), str):
            file_counts = _restore_file_snapshot(settings.file_storage_root / file_snapshot["path"], settings.file_storage_root)
    except Exception:
        db.rollback()
        raise

    metadata = {
        "snapshot_path": point.data_snapshot_path,
        "description": point.description,
        "mode": "data-restore",
        "counts": counts,
        "file_counts": file_counts,
        "skipped_tables": sorted(RESTORE_METADATA_TABLES | VOLATILE_TABLES),
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
