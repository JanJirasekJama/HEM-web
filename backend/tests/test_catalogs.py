from fastapi.testclient import TestClient


def test_service_catalog_preserves_inactive_items_for_history(client: TestClient, admin_auth: dict[str, str]) -> None:
    category = client.post("/api/catalog/service-categories", headers=admin_auth, json={"name": "Wellness", "sort_order": 1})
    assert category.status_code == 200

    service = client.post(
        "/api/catalog/services",
        headers=admin_auth,
        json={"category_id": category.json()["id"], "name": "Vířivka", "type": "wellness", "price": 2000, "active": True},
    )
    assert service.status_code == 200
    service_id = service.json()["id"]

    active = client.get("/api/catalog/services?active_only=true")
    assert [item["name"] for item in active.json()] == ["Vířivka"]

    deactivated = client.patch(f"/api/catalog/services/{service_id}", headers=admin_auth, json={"active": False})
    assert deactivated.status_code == 200

    assert client.get("/api/catalog/services?active_only=true").json() == []
    archived_read = client.get(f"/api/catalog/services/{service_id}")
    assert archived_read.status_code == 200
    assert archived_read.json()["name"] == "Vířivka"
    assert archived_read.json()["active"] is False


def test_due_terms_rooms_photo_types_and_email_recipients(client: TestClient, admin_auth: dict[str, str]) -> None:
    due = client.post(
        "/api/catalog/due-terms",
        headers=admin_auth,
        json={"name": "24 hodin", "value": 24, "unit": "hours", "active": True},
    )
    assert due.status_code == 200
    assert due.json()["unit"] == "hours"

    room = client.post("/api/catalog/hotel-rooms", headers=admin_auth, json={"label": "Afrika - 217", "sort_order": 217})
    assert room.status_code == 200

    photo_type = client.post("/api/catalog/photo-task-types", headers=admin_auth, json={"name": "Vířivka", "sort_order": 8})
    assert photo_type.status_code == 200

    hk_minibar = client.post("/api/catalog/housekeeping-minibar-items", headers=admin_auth, json={"name": "Coca Cola"})
    assert hk_minibar.status_code == 200

    recipient = client.post(
        "/api/catalog/email-recipients",
        headers=admin_auth,
        json={"name": "Recepce", "email": "recepce@example.test", "active": True},
    )
    assert recipient.status_code == 200

    lookup = client.get("/api/catalog/bootstrap")
    assert lookup.status_code == 200
    assert lookup.json()["hotel_rooms"][0]["label"] == "Afrika - 217"
    assert lookup.json()["photo_task_types"][0]["name"] == "Vířivka"
    assert lookup.json()["housekeeping_minibar_items"][0]["name"] == "Coca Cola"
    assert lookup.json()["email_recipients"][0]["email"] == "recepce@example.test"


def test_inventory_item_catalog_separates_priced_inventory_from_housekeeping_checklist(client: TestClient, admin_auth: dict[str, str]) -> None:
    priced = client.post(
        "/api/catalog/inventory-items",
        headers=admin_auth,
        json={"module": "minibar", "name": "Coca Cola", "unit": "ks", "category": "nápoje", "price": 55, "has_price": True},
    )
    assert priced.status_code == 200

    checklist = client.post("/api/catalog/housekeeping-minibar-items", headers=admin_auth, json={"name": "Coca Cola"})
    assert checklist.status_code == 200

    assert priced.json()["id"] != checklist.json()["id"]
    assert priced.json()["price"] == 55
    assert "price" not in checklist.json()

