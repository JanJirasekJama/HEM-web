import json
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient


def test_manual_backup_recovery_point_and_restore_metadata(
    client: TestClient,
    admin_auth: dict[str, str],
    tmp_path: Path,
) -> None:
    storage_root = tmp_path / "files"
    (storage_root / "media").mkdir(parents=True)
    (storage_root / "media" / "photo.jpg").write_bytes(b"photo-bytes")

    backup = client.post("/api/backups/manual", headers=admin_auth, json={"note": "Před migrací"})
    assert backup.status_code == 200
    backup_data = backup.json()
    assert backup_data["file_path"].endswith(".zip")
    assert backup_data["backup_type"] == "manual"

    with zipfile.ZipFile(tmp_path / "files" / backup_data["file_path"]) as archive:
        names = set(archive.namelist())
        assert {"manifest.json", "database.json", "files/media/photo.jpg"} <= names
        assert f"files/{backup_data['file_path']}" not in names
        manifest = json.loads(archive.read("manifest.json"))
        database = json.loads(archive.read("database.json"))
    assert manifest["files"] == {"count": 1, "bytes": len(b"photo-bytes")}
    assert database["format"] == "hem-db-snapshot-v1"
    assert "users" in database["tables"]
    assert "sessions" not in database["tables"]

    listed = client.get("/api/backups")
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == backup_data["id"]

    recovery = client.post("/api/backups/recovery-points", headers=admin_auth, json={"description": "Bezpečný bod"})
    assert recovery.status_code == 200
    assert recovery.json()["data_snapshot_path"]

    restored = client.post(f"/api/backups/recovery-points/{recovery.json()['id']}/restore", headers=admin_auth)
    assert restored.status_code == 200
    assert restored.json()["restored"] is True
    assert restored.json()["metadata"]["mode"] == "data-restore"


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


def test_legacy_suite_migration_imports_messages_inventory_cash_and_invoice_archives(
    client: TestClient,
    admin_auth: dict[str, str],
    tmp_path: Path,
) -> None:
    inventory_dir = tmp_path / "HEM_InventoryManager"
    communication_dir = tmp_path / "HEM_Komunikace"
    invoicing_dir = tmp_path / "HEM_ZalohoveFaktury"
    inventory_dir.mkdir()
    communication_dir.mkdir()
    invoicing_dir.mkdir()

    (inventory_dir / "wellness_items.json").write_text(
        json.dumps([{"id": 1, "name": "Čaj", "unit": "ks", "active": True, "category": "nápoje"}]),
        encoding="utf-8",
    )
    (inventory_dir / "wellness_data.json").write_text(
        json.dumps({"2026-05-09": {"1": 2, "note": "starý wellness odpis"}}),
        encoding="utf-8",
    )
    (communication_dir / "messages.json").write_text(
        json.dumps([{"timestamp": "2026-05-09 08:30:00", "user": "admin", "message": "Starý recepční vzkaz"}]),
        encoding="utf-8",
    )
    (communication_dir / "cash_diary.json").write_text(
        json.dumps([{"date": "09.05.2026", "user": "admin", "cash_start": 1000, "cash_end": 1250, "notes": "starý deník"}]),
        encoding="utf-8",
    )
    (invoicing_dir / "services.json").write_text(
        json.dumps({"Wellness": [{"nazev": "Vířivka", "cena": 2000, "aktivni": True, "typ": "wellness"}]}),
        encoding="utf-8",
    )
    (invoicing_dir / "splatnosti.json").write_text(
        json.dumps([{"nazev": "24 hodin", "hodiny": 24, "jednotka": "hodiny", "aktivni": True}]),
        encoding="utf-8",
    )
    (invoicing_dir / "archiv_data.json").write_text(
        json.dumps(
            [
                {
                    "cislo_faktury": "260001",
                    "jmeno": "Host Migrace",
                    "termin": "09.05.2026 18:00",
                    "datum_vytvoreni": "09.05.2026 09:00:00",
                    "stav": 2,
                    "splatnost": "24 hodin",
                    "due_date": "10.05.2026 09:00",
                    "cena": 2000,
                    "sluzba": "Vířivka",
                    "email": "host@example.test",
                    "telefon": "+420123456789",
                    "vydal": "admin",
                }
            ]
        ),
        encoding="utf-8",
    )

    migrated = client.post(
        "/api/migration/legacy-suite",
        headers=admin_auth,
        json={
            "inventory_path": str(inventory_dir),
            "communication_path": str(communication_dir),
            "invoicing_path": str(invoicing_dir),
        },
    )
    assert migrated.status_code == 200
    assert migrated.json()["messages_imported"] == 1
    assert migrated.json()["inventory_entries_imported"] == 1
    assert migrated.json()["cash_entries_imported"] == 1
    assert migrated.json()["invoices_imported"] == 1

    assert client.get("/api/messages/history?text=starý").json()[0]["content_text"] == "- Starý recepční vzkaz"
    assert client.get("/api/inventory/reports/monthly?module=wellness&month=2026-05").json()["totals"]["Čaj"]["quantity"] == 2
    assert client.get("/api/cash/diary?date_from=2026-05-01&date_to=2026-05-31").json()[0]["difference"] == 250
    assert client.get("/api/invoices/archive").json()[0]["invoice_number"] == "260001"
