import hashlib
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.ids import new_id
from app.core.models import MediaFile


ALLOWED_IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


def save_upload(
    db: Session,
    settings: Settings,
    module: str,
    upload: UploadFile,
    created_by: str | None,
    allowed_types: set[str] | None = None,
) -> MediaFile:
    allowed = allowed_types or set(ALLOWED_IMAGE_TYPES)
    if upload.content_type not in allowed:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Unsupported file type")

    content = upload.file.read()
    if len(content) > settings.upload_max_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large")

    digest = hashlib.sha256(content).hexdigest()
    suffix = ALLOWED_IMAGE_TYPES.get(upload.content_type or "", Path(upload.filename or "").suffix.lower() or ".bin")
    relative_path = Path(module) / f"{digest}{suffix}"
    absolute_path = settings.file_storage_root / relative_path
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    absolute_path.write_bytes(content)

    media = MediaFile(
        module=module,
        original_name=upload.filename,
        storage_path=str(relative_path),
        public_url=f"/api/files/{module}/{digest}{suffix}",
        mime_type=upload.content_type,
        sha256=digest,
        size_bytes=len(content),
        created_by=created_by,
    )
    db.add(media)
    db.commit()
    db.refresh(media)
    return media

