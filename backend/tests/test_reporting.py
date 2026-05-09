from fastapi.testclient import TestClient


def test_invoice_statistics_tax_report_and_exports(client: TestClient, admin_auth: dict[str, str]) -> None:
    category = client.post("/api/catalog/service-categories", headers=admin_auth, json={"name": "Ubytování"}).json()
    service = client.post(
        "/api/catalog/services",
        headers=admin_auth,
        json={"category_id": category["id"], "name": "Apartmá", "type": "ubytovani", "price": 3500},
    ).json()
    due = client.post("/api/catalog/due-terms", headers=admin_auth, json={"name": "1 den", "value": 1, "unit": "dny"}).json()
    client.post(
        "/api/invoices",
        headers=admin_auth,
        json={"customer_name": "Host A", "service_id": service["id"], "event_at": "09.05.2026", "due_term_id": due["id"]},
    )
    invoice_b = client.post(
        "/api/invoices",
        headers=admin_auth,
        json={"customer_name": "Host B", "service_id": service["id"], "event_at": "10.05.2026", "due_term_id": due["id"]},
    ).json()
    client.patch(f"/api/invoices/{invoice_b['id']}/mark-paid", headers=admin_auth)

    stats = client.get("/api/reports/invoices/statistics?date_from=2026-05-01&date_to=2026-05-31")
    assert stats.status_code == 200
    assert stats.json()["invoice_count"] == 2
    assert stats.json()["paid_count"] == 1
    assert stats.json()["total_amount"] == 7000
    assert stats.json()["most_common_service"] == "Apartmá"

    tax = client.get("/api/reports/invoices/tax?date_from=2026-05-01&date_to=2026-05-31")
    assert tax.status_code == 200
    assert tax.json()["gross_revenue"] == 7000
    assert tax.json()["vat_rate"] == 21
    assert tax.json()["by_service"]["Apartmá"]["gross"] == 7000

    export = client.post(
        "/api/reports/exports",
        headers=admin_auth,
        json={"module": "invoicing", "export_type": "csv", "period_from": "2026-05-01", "period_to": "2026-05-31"},
    )
    assert export.status_code == 200
    assert export.json()["file_path"]


def test_reporting_reads_inventory_monthly_totals(client: TestClient, admin_auth: dict[str, str]) -> None:
    item = client.post(
        "/api/catalog/inventory-items",
        headers=admin_auth,
        json={"module": "wellness", "name": "Čaj", "unit": "ks", "category": "nápoje"},
    ).json()
    client.post(
        "/api/inventory/entries",
        headers=admin_auth,
        json={"entry_date": "2026-05-09", "module": "wellness", "items": [{"item_id": item["id"], "quantity": 4}]},
    )

    report = client.get("/api/reports/inventory/monthly?module=wellness&month=2026-05")
    assert report.status_code == 200
    assert report.json()["totals"]["Čaj"]["quantity"] == 4
