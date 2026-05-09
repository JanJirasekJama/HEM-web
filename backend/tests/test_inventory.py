from fastapi.testclient import TestClient


def _inventory_item(client: TestClient, admin_auth: dict[str, str], module: str, name: str, price: float | None = None) -> str:
    response = client.post(
        "/api/catalog/inventory-items",
        headers=admin_auth,
        json={"module": module, "name": name, "unit": "ks", "category": "test", "price": price, "has_price": price is not None},
    )
    assert response.status_code == 200
    return response.json()["id"]


def test_daily_inventory_entry_can_be_loaded_updated_archived_and_deleted(client: TestClient, admin_auth: dict[str, str]) -> None:
    water_id = _inventory_item(client, admin_auth, "minibar", "Bonaqua", 45)

    created = client.post(
        "/api/inventory/entries",
        headers=admin_auth,
        json={
            "entry_date": "2026-05-09",
            "module": "minibar",
            "note": "Doplněno patro 2",
            "items": [{"item_id": water_id, "quantity": 3, "unit_price": 45}],
        },
    )
    assert created.status_code == 200
    entry_id = created.json()["id"]

    loaded = client.get("/api/inventory/entries/by-date?entry_date=2026-05-09&module=minibar")
    assert loaded.status_code == 200
    assert loaded.json()["items"][0]["quantity"] == 3

    updated = client.put(
        f"/api/inventory/entries/{entry_id}",
        headers=admin_auth,
        json={"note": "Opraveno", "items": [{"item_id": water_id, "quantity": 5, "unit_price": 45}]},
    )
    assert updated.status_code == 200
    assert updated.json()["items"][0]["quantity"] == 5

    archive = client.get("/api/inventory/archive?module=minibar&text=opraveno")
    assert archive.status_code == 200
    assert archive.json()[0]["id"] == entry_id

    deleted = client.delete(f"/api/inventory/archive/{entry_id}", headers=admin_auth)
    assert deleted.status_code == 200
    assert client.get("/api/inventory/archive?module=minibar").json() == []


def test_monthly_inventory_report_sums_quantities_and_lobby_money(client: TestClient, admin_auth: dict[str, str]) -> None:
    coffee_id = _inventory_item(client, admin_auth, "lobby", "Káva", 55)
    client.post(
        "/api/inventory/entries",
        headers=admin_auth,
        json={
            "entry_date": "2026-05-01",
            "module": "lobby",
            "items": [
                {"item_id": coffee_id, "quantity": 2, "unit_price": 55},
                {"custom_description": "Deštník na přání", "quantity": 1, "unit_price": 120, "is_custom": True},
            ],
        },
    )
    client.post(
        "/api/inventory/entries",
        headers=admin_auth,
        json={"entry_date": "2026-05-15", "module": "lobby", "items": [{"item_id": coffee_id, "quantity": 1, "unit_price": 55}]},
    )

    report = client.get("/api/inventory/reports/monthly?module=lobby&month=2026-05")
    assert report.status_code == 200
    assert report.json()["totals"]["Káva"]["quantity"] == 3
    assert report.json()["totals"]["Káva"]["total_price"] == 165
    assert report.json()["custom_total_price"] == 120

