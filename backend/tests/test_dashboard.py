from fastapi.testclient import TestClient


def _login_auth(client: TestClient, username: str, password: str) -> dict[str, str]:
    login = client.post("/api/auth/login", json={"username": username, "password": password})
    assert login.status_code == 200
    session = login.cookies.get("hem_session")
    assert session
    return {"X-CSRF-Token": login.json()["csrf_token"], "Cookie": f"hem_session={session}"}


def _user_auth(client: TestClient, admin_auth: dict[str, str], username: str, role_name: str) -> dict[str, str]:
    created = client.post(
        "/api/users",
        headers=admin_auth,
        json={"username": username, "password": f"{username}1", "role_name": role_name, "display_name": username},
    )
    assert created.status_code == 200
    return _login_auth(client, username, f"{username}1")


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
    due = client.post("/api/catalog/due-terms", headers=admin_auth, json={"name": "okamžitě", "value": 0, "unit": "hodiny"}).json()
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


def test_dashboard_returns_safe_defaults_for_role_without_sensitive_permissions(client: TestClient, admin_auth: dict[str, str]) -> None:
    admin_auth = _login_auth(client, "admin", "061004")
    client.post("/api/messages/daily", headers=admin_auth, json={"message_date": "2026-05-09", "content_text": "Denní vzkaz"})
    client.post("/api/tasks", headers=admin_auth, json={"title": "Doplnit lobby", "due_date": "2026-05-09", "priority": "Normalni"})
    room = client.post("/api/catalog/hotel-rooms", headers=admin_auth, json={"label": "201"}).json()
    client.post("/api/housekeeping/assignments", headers=admin_auth, json={"room_ids": [room["id"]], "work_type": "Odjezd", "priority": "Normalni"})
    category = client.post("/api/catalog/service-categories", headers=admin_auth, json={"name": "Wellness"}).json()
    service = client.post("/api/catalog/services", headers=admin_auth, json={"category_id": category["id"], "name": "Sauna", "price": 1500}).json()
    due = client.post("/api/catalog/due-terms", headers=admin_auth, json={"name": "okamžitě", "value": 0, "unit": "hodiny"}).json()
    client.post("/api/invoices", headers=admin_auth, json={"customer_name": "Host", "service_id": service["id"], "event_at": "09.05.2026", "due_term_id": due["id"]})

    housekeeper_auth = _user_auth(client, admin_auth, "pokojska", "pokojska")
    housekeeper_dashboard = client.get("/api/dashboard?date=2026-05-09&current_time=2026-05-09T21:00:00Z", headers=housekeeper_auth)
    assert housekeeper_dashboard.status_code == 200
    housekeeper_body = housekeeper_dashboard.json()
    assert housekeeper_body["messages_today"] == 0
    assert housekeeper_body["open_tasks_today"] == 0
    assert housekeeper_body["open_task_list"] == []
    assert housekeeper_body["cash"]["missing_evening_cash"] is False
    assert housekeeper_body["invoices"]["due_or_overdue"] == 0
    assert housekeeper_body["housekeeping"]["waiting"] == 1

    accountant_auth = _user_auth(client, admin_auth, "ucetni", "ucetni")
    accountant_dashboard = client.get("/api/dashboard?date=2026-05-09&current_time=2026-05-09T21:00:00Z", headers=accountant_auth)
    assert accountant_dashboard.status_code == 200
    accountant_body = accountant_dashboard.json()
    assert accountant_body["messages_today"] == 0
    assert accountant_body["open_tasks_today"] == 0
    assert accountant_body["cash"]["cash_start"] is None
    assert accountant_body["invoices"]["due_or_overdue"] >= 1
    assert accountant_body["housekeeping"]["waiting"] == 0
