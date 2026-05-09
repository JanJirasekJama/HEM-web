from fastapi.testclient import TestClient


def _service_and_due(client: TestClient, admin_auth: dict[str, str]) -> tuple[str, str]:
    category = client.post("/api/catalog/service-categories", headers=admin_auth, json={"name": "Wellness"}).json()
    service = client.post(
        "/api/catalog/services",
        headers=admin_auth,
        json={"category_id": category["id"], "name": "Vířivka", "type": "wellness", "price": 2000, "active": True},
    ).json()
    due = client.post("/api/catalog/due-terms", headers=admin_auth, json={"name": "24 hodin", "value": 24, "unit": "hodiny"}).json()
    return service["id"], due["id"]


def test_invoice_validates_term_price_generates_number_pdf_and_archive(client: TestClient, admin_auth: dict[str, str]) -> None:
    service_id, due_id = _service_and_due(client, admin_auth)

    invalid_term = client.post(
        "/api/invoices",
        headers=admin_auth,
        json={
            "customer_name": "Host",
            "service_id": service_id,
            "event_at": "2026/05/09",
            "due_term_id": due_id,
            "price": 2000,
        },
    )
    assert invalid_term.status_code in {400, 422}

    custom_without_price = client.post(
        "/api/invoices",
        headers=admin_auth,
        json={"customer_name": "Host", "custom_service_name": "Balíček", "event_at": "09.05.2026", "due_term_id": due_id},
    )
    assert custom_without_price.status_code in {400, 422}

    created = client.post(
        "/api/invoices",
        headers=admin_auth,
        json={
            "customer_name": "Jan Novak",
            "customer_email": "jan@example.test",
            "customer_phone": "+420123456789",
            "service_id": service_id,
            "event_at": "09.05.2026 18:30",
            "due_term_id": due_id,
            "increase_percent": 10,
            "note": "Test",
        },
    )
    assert created.status_code == 200
    body = created.json()
    assert body["invoice_number"]
    assert body["variable_symbol"] == body["invoice_number"]
    assert body["price"] == 2200
    assert body["pdf_path"].endswith(".pdf")

    archive = client.get("/api/invoices/archive")
    assert archive.status_code == 200
    assert archive.json()[0]["customer_name"] == "Jan Novak"


def test_invoice_payment_states_manual_toggles_and_csv_export(client: TestClient, admin_auth: dict[str, str]) -> None:
    service_id, due_id = _service_and_due(client, admin_auth)
    invoice = client.post(
        "/api/invoices",
        headers=admin_auth,
        json={"customer_name": "Host", "service_id": service_id, "event_at": "09.05.2026", "due_term_id": due_id},
    ).json()

    paid = client.patch(f"/api/invoices/{invoice['id']}/mark-paid", headers=admin_auth)
    assert paid.status_code == 200
    assert paid.json()["payment_status"] == "paid"

    unpaid = client.patch(f"/api/invoices/{invoice['id']}/mark-unpaid", headers=admin_auth)
    assert unpaid.status_code == 200
    assert unpaid.json()["payment_status"] in {"pending", "unpaid"}

    refreshed = client.post("/api/invoices/archive/refresh-statuses", headers=admin_auth, json={"current_time": "2026-06-01T10:00:00Z"})
    assert refreshed.status_code == 200
    assert refreshed.json()["updated"] >= 1

    exported = client.get("/api/invoices/archive/export.csv")
    assert exported.status_code == 200
    assert "invoice_number" in exported.text
