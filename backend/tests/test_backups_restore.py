from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.catalog.models import HotelRoom


def test_recovery_point_restore_restores_snapshot_data(
    client: TestClient,
    admin_auth: dict[str, str],
    db_session: Session,
) -> None:
    created = client.post("/api/catalog/hotel-rooms", headers=admin_auth, json={"label": "707", "sort_order": 707})
    assert created.status_code == 200
    room = created.json()

    recovery = client.post("/api/backups/recovery-points", headers=admin_auth, json={"description": "Před změnou pokojů"})
    assert recovery.status_code == 200

    changed = client.patch(f"/api/catalog/hotel-rooms/{room['id']}", headers=admin_auth, json={"label": "707 změněno"})
    assert changed.status_code == 200
    extra = client.post("/api/catalog/hotel-rooms", headers=admin_auth, json={"label": "999 navíc"})
    assert extra.status_code == 200

    restored = client.post(f"/api/backups/recovery-points/{recovery.json()['id']}/restore", headers=admin_auth)
    assert restored.status_code == 200
    assert restored.json()["restored"] is True
    assert restored.json()["metadata"]["mode"] == "data-restore"
    assert restored.json()["metadata"]["counts"]["catalog_hotel_rooms"] >= 1

    db_session.expire_all()
    restored_room = db_session.get(HotelRoom, room["id"])
    assert restored_room is not None
    assert restored_room.label == "707"
    assert db_session.get(HotelRoom, extra.json()["id"]) is None


def test_recovery_point_restore_restores_file_storage_snapshot(
    client: TestClient,
    admin_auth: dict[str, str],
    tmp_path: Path,
) -> None:
    storage_root = tmp_path / "files"
    media_dir = storage_root / "media"
    exports_dir = storage_root / "exports"
    media_dir.mkdir(parents=True)
    exports_dir.mkdir(parents=True)
    photo_path = media_dir / "room.jpg"
    export_path = exports_dir / "report.pdf"
    extra_path = media_dir / "later.jpg"
    photo_path.write_bytes(b"original-photo")
    export_path.write_bytes(b"original-pdf")

    recovery = client.post("/api/backups/recovery-points", headers=admin_auth, json={"description": "Před soubory"})
    assert recovery.status_code == 200

    photo_path.write_bytes(b"changed-photo")
    export_path.unlink()
    extra_path.write_bytes(b"later-file")

    restored = client.post(f"/api/backups/recovery-points/{recovery.json()['id']}/restore", headers=admin_auth)
    assert restored.status_code == 200
    assert restored.json()["restored"] is True
    assert restored.json()["metadata"]["file_counts"]["restored"] == 2
    assert restored.json()["metadata"]["file_counts"]["removed"] == 1

    assert photo_path.read_bytes() == b"original-photo"
    assert export_path.read_bytes() == b"original-pdf"
    assert not extra_path.exists()
