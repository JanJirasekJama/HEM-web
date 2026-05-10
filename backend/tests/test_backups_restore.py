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
