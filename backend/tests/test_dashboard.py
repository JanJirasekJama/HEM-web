from fastapi.testclient import TestClient


def test_dashboard_aggregates_user_tasks_cash_invoices_and_housekeeping(client: TestClient, admin_auth: dict[str, str]) -> None:
    me = client.get("/api/auth/me").json()
    client.post("/api/messages/daily", headers=admin_auth, json={"message_date": "2026-05-09", "content_text": "Denní vzkaz"})
    client.post("/api/tasks", headers=admin_auth, json={"title": "Doplnit lobby", "due_date": "2026-05-09", "priority": "Normalni"})
    client.post("/api/cash/diary", headers=admin_auth, json={"entry_date": "2026-05-08", "user_id": me["id"], "cash_start": 1000, "cash_end": 1200})
    client.post("/api/cash/diary", headers=admin_auth, json={"entry_date": "2026-05-09", "user_id": me["id"], "cash_start": 1200})
    room = client.post("/api/catalog/hotel-rooms", headers=admin_auth, json={"label": "101"}).json()
    client.post("/api/housekeeping/assignments", headers=admin_auth, json={"room_ids": [room["id"]], "work_type": "Odjezd", "priority": "Normalni"})

    category = client.post("/api/catalog/service-categories", headers=admin_auth, json={"name": "Wellness"}).json()
    service = client.post("/api/catalog/services", headers=admin_auth, json={"category_id": category["id"], "name": "Sauna", "price": 1500}).json()
    due = client.post("/api/catalog/due-terms", headers=admin_auth, json={"name": "okamžitě", "value": 0, "unit": "hours"}).json()
    client.post("/api/invoices", headers=admin_auth, json={"customer_name": "Host", "service_id": service["id"], "event_at": "09.05.2026", "due_term_id": due["id"]})

    dashboard = client.get("/api/dashboard?date=2026-05-09&current_time=2026-05-09T21:00:00Z")
    assert dashboard.status_code == 200
    body = dashboard.json()
    assert body["current_user"]["username"] == "admin"
    assert body["messages_today"] == 1
    assert body["open_tasks_today"] == 1
    assert body["cash"]["yesterday_cash_end"] == 1200
    assert body["cash"]["missing_evening_cash"] is True
    assert body["housekeeping"]["waiting"] == 1
    assert body["invoices"]["due_or_overdue"] >= 1

