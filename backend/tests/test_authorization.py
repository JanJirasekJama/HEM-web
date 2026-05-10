from fastapi.testclient import TestClient


def _create_user(client: TestClient, admin_auth: dict[str, str], username: str, role_name: str) -> dict:
    response = client.post(
        "/api/users",
        headers=admin_auth,
        json={"username": username, "password": f"{username}123", "role_name": role_name},
    )
    assert response.status_code == 200
    return response.json()


def _login(client: TestClient, username: str) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": f"{username}123"})
    assert response.status_code == 200
    return {"X-CSRF-Token": response.json()["csrf_token"]}


def test_tasks_calendar_requires_authenticated_task_permission(client: TestClient) -> None:
    response = client.get("/api/tasks/calendar?date=2026-05-10")
    assert response.status_code == 401

    admin_login = client.post("/api/auth/login", json={"username": "admin", "password": "061004"})
    assert admin_login.status_code == 200
    admin_auth = {"X-CSRF-Token": admin_login.json()["csrf_token"]}
    _create_user(client, admin_auth, "recepce", "recepcni")
    _login(client, "recepce")

    allowed = client.get("/api/tasks/calendar?date=2026-05-10")
    assert allowed.status_code == 200


def test_reception_cannot_access_accounting_reports_or_exports(client: TestClient, admin_auth: dict[str, str]) -> None:
    _create_user(client, admin_auth, "recepce", "recepcni")
    headers = _login(client, "recepce")

    statistics = client.get("/api/reports/invoices/statistics?date_from=2026-05-01&date_to=2026-05-31")
    assert statistics.status_code == 403

    export = client.post(
        "/api/reports/exports",
        headers=headers,
        json={"module": "invoicing", "export_type": "csv", "period_from": "2026-05-01", "period_to": "2026-05-31"},
    )
    assert export.status_code == 403


def test_housekeeper_cannot_access_cash_or_inventory(client: TestClient, admin_auth: dict[str, str]) -> None:
    housekeeper = _create_user(client, admin_auth, "pokojska", "pokojska")
    _login(client, "pokojska")

    cash = client.get(f"/api/cash/status?date=2026-05-10&user_id={housekeeper['id']}")
    assert cash.status_code == 403

    inventory = client.get("/api/inventory/archive")
    assert inventory.status_code == 403


def test_accountant_has_reports_exports_and_admin_has_sensitive_access(client: TestClient, admin_auth: dict[str, str]) -> None:
    _create_user(client, admin_auth, "ucetni", "ucetni")
    accounting_headers = _login(client, "ucetni")

    report = client.get("/api/reports/invoices/tax?date_from=2026-05-01&date_to=2026-05-31")
    assert report.status_code == 200

    export = client.post(
        "/api/reports/exports",
        headers=accounting_headers,
        json={"module": "invoicing", "export_type": "csv", "period_from": "2026-05-01", "period_to": "2026-05-31"},
    )
    assert export.status_code == 200

    admin_login = client.post("/api/auth/login", json={"username": "admin", "password": "061004"})
    assert admin_login.status_code == 200
    backups = client.get("/api/backups")
    assert backups.status_code == 200
