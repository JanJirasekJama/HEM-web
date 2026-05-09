import json
from pathlib import Path

from fastapi.testclient import TestClient


def test_manual_backup_recovery_point_and_restore_metadata(client: TestClient, admin_auth: dict[str, str]) -> None:
    backup = client.post("/api/backups/manual", headers=admin_auth, json={"note": "Před migrací"})
    assert backup.status_code == 200
    assert backup.json()["file_path"].endswith(".zip")
    assert backup.json()["backup_type"] == "manual"

    listed = client.get("/api/backups")
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == backup.json()["id"]

    recovery = client.post("/api/backups/recovery-points", headers=admin_auth, json={"description": "Bezpečný bod"})
    assert recovery.status_code == 200
    assert recovery.json()["data_snapshot_path"]

    restored = client.post(f"/api/backups/recovery-points/{recovery.json()['id']}/restore", headers=admin_auth)
    assert restored.status_code == 200
    assert restored.json()["restored"] is True


def test_housekeeping_json_migration_preserves_rooms_users_history_and_photo_refs(
    client: TestClient,
    admin_auth: dict[str, str],
    tmp_path: Path,
) -> None:
    photos = tmp_path / "photos"
    photos.mkdir()
    (photos / "legacy.jpg").write_bytes(b"fake-image")
    data_path = tmp_path / "data.json"
    data_path.write_text(
        json.dumps(
            {
                "users": [{"id": "legacy-housekeeper", "username": "pokojska", "passwordHash": "legacy", "role": "housekeeping"}],
                "hotelRooms": ["101", "VIP"],
                "minibarItems": ["Voda"],
                "photoTasks": ["Postel"],
                "history": [
                    {
                        "type": "cleaning",
                        "room": "101",
                        "housekeeperName": "pokojska",
                        "finishedAt": "2026-05-09T08:00:00Z",
                        "photos": [{"src": "/api/photos/legacy.jpg", "task": "Postel"}],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    migrated = client.post(
        "/api/migration/housekeeping-json",
        headers=admin_auth,
        json={"data_path": str(data_path), "photos_path": str(photos)},
    )
    assert migrated.status_code == 200
    assert migrated.json()["rooms_imported"] == 2
    assert migrated.json()["history_imported"] == 1
    assert migrated.json()["photos_imported"] == 1

    rooms = client.get("/api/catalog/hotel-rooms").json()
    assert {room["label"] for room in rooms} >= {"101", "VIP"}

