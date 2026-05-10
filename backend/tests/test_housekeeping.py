from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image


def valid_png() -> bytes:
    output = BytesIO()
    Image.new("RGB", (1, 1), color=(255, 255, 255)).save(output, format="PNG")
    return output.getvalue()


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


def _housekeeper_auth(client: TestClient, admin_auth: dict[str, str]) -> dict[str, str]:
    return _user_auth(client, admin_auth, "pokojska", "pokojska")


def test_assignment_workflow_requires_photos_creates_history_and_unique_minibar_entries(client: TestClient, admin_auth: dict[str, str]) -> None:
    admin_auth = _login_auth(client, "admin", "061004")
    room = client.post("/api/catalog/hotel-rooms", headers=admin_auth, json={"label": "101"}).json()
    photo_type = client.post("/api/catalog/photo-task-types", headers=admin_auth, json={"name": "Postel"}).json()
    minibar_item = client.post("/api/catalog/housekeeping-minibar-items", headers=admin_auth, json={"name": "Voda"}).json()
    housekeeper_auth = _housekeeper_auth(client, admin_auth)

    created = client.post(
        "/api/housekeeping/assignments",
        headers=admin_auth,
        json={
            "room_ids": [room["id"]],
            "work_type": "Prijezd",
            "priority": "Vysoka",
            "reception_note": "VIP",
            "required_photo_type_ids": [photo_type["id"]],
        },
    )
    assert created.status_code == 200
    assignment = created.json()[0]

    started = client.patch(f"/api/housekeeping/assignments/{assignment['id']}/start", headers=housekeeper_auth)
    assert started.status_code == 200
    assert started.json()["status"] == "Uklizi se"

    client.patch(f"/api/housekeeping/assignments/{assignment['id']}/pause", headers=housekeeper_auth)
    resumed = client.patch(f"/api/housekeeping/assignments/{assignment['id']}/resume", headers=housekeeper_auth)
    assert resumed.status_code == 200

    minibar = client.post(
        f"/api/housekeeping/assignments/{assignment['id']}/minibar",
        headers=housekeeper_auth,
        json={"item_id": minibar_item["id"], "quantity": 1},
    )
    assert minibar.status_code == 200
    duplicate_minibar = client.post(
        f"/api/housekeeping/assignments/{assignment['id']}/minibar",
        headers=housekeeper_auth,
        json={"item_id": minibar_item["id"], "quantity": 1},
    )
    assert duplicate_minibar.status_code == 409

    blocked_finish = client.patch(f"/api/housekeeping/assignments/{assignment['id']}/finish", headers=housekeeper_auth)
    assert blocked_finish.status_code == 400

    invalid_upload = client.post(
        f"/api/housekeeping/assignments/{assignment['id']}/photos",
        headers=housekeeper_auth,
        data={"task_label": "Postel", "photo_task_type_id": photo_type["id"]},
        files={"file": ("postel.jpg", b"fake-image", "image/jpeg")},
    )
    assert invalid_upload.status_code in {400, 415}

    uploaded = client.post(
        f"/api/housekeeping/assignments/{assignment['id']}/photos",
        headers=housekeeper_auth,
        data={"task_label": "Postel", "photo_task_type_id": photo_type["id"]},
        files={"file": ("postel.png", valid_png(), "image/png")},
    )
    assert uploaded.status_code == 200

    finished = client.patch(f"/api/housekeeping/assignments/{assignment['id']}/finish", headers=housekeeper_auth)
    assert finished.status_code == 200
    assert finished.json()["status"] == "Hotovo"

    history = client.get("/api/housekeeping/history?month=2026-05", headers=admin_auth)
    assert history.status_code == 200
    assert history.json()[0]["room_label_snapshot"] == "101"


def test_revision_laundry_and_monthly_work_report(client: TestClient, admin_auth: dict[str, str]) -> None:
    admin_auth = _login_auth(client, "admin", "061004")
    housekeeper_auth = _housekeeper_auth(client, admin_auth)

    revision = client.post(
        "/api/housekeeping/revisions",
        headers=admin_auth,
        json={"location": "2. patro", "text": "Vyleštit okna"},
    )
    assert revision.status_code == 200
    completed_revision = client.patch(
        f"/api/housekeeping/revisions/{revision.json()['id']}/complete",
        headers=housekeeper_auth,
        data={"note": "Hotovo"},
        files={"files": ("okno.png", valid_png(), "image/png")},
    )
    assert completed_revision.status_code == 200
    assert completed_revision.json()["status"] == "done"

    laundry = client.post("/api/housekeeping/laundry", headers=admin_auth)
    assert laundry.status_code == 200
    client.patch(f"/api/housekeeping/laundry/{laundry.json()['id']}/accept", headers=housekeeper_auth)
    blocked = client.patch(f"/api/housekeeping/laundry/{laundry.json()['id']}/done", headers=housekeeper_auth)
    assert blocked.status_code == 400

    uploaded = client.post(
        f"/api/housekeeping/laundry/{laundry.json()['id']}/photos",
        headers=housekeeper_auth,
        files={"file": ("pradlo.png", valid_png(), "image/png")},
    )
    assert uploaded.status_code == 200

    done = client.patch(f"/api/housekeeping/laundry/{laundry.json()['id']}/done", headers=housekeeper_auth)
    assert done.status_code == 200
    assert done.json()["status"] == "done"

    report = client.get("/api/housekeeping/reports/monthly-work?month=2026-05", headers=admin_auth)
    assert report.status_code == 200
    assert report.json()["housekeepers"]["pokojska"]["laundry_count"] == 1


def test_housekeeping_mutations_require_cookie_bound_csrf(client: TestClient, admin_auth: dict[str, str]) -> None:
    admin_auth = _login_auth(client, "admin", "061004")
    room = client.post("/api/catalog/hotel-rooms", headers=admin_auth, json={"label": "102"}).json()
    csrf_only = {"X-CSRF-Token": admin_auth["X-CSRF-Token"]}

    client.cookies.clear()
    response = client.post(
        "/api/housekeeping/assignments",
        headers=csrf_only,
        json={"room_ids": [room["id"]], "work_type": "Odjezd", "priority": "Normalni"},
    )

    assert response.status_code == 401


def test_housekeeping_reception_and_work_permissions(client: TestClient, admin_auth: dict[str, str]) -> None:
    admin_auth = _login_auth(client, "admin", "061004")
    room = client.post("/api/catalog/hotel-rooms", headers=admin_auth, json={"label": "103"}).json()
    housekeeper_auth = _housekeeper_auth(client, admin_auth)
    reception_auth = _user_auth(client, admin_auth, "recepce", "recepcni")
    accountant_auth = _user_auth(client, admin_auth, "ucetni", "ucetni")

    reception_created = client.post(
        "/api/housekeeping/assignments",
        headers=reception_auth,
        json={"room_ids": [room["id"]], "work_type": "Prijezd", "priority": "Normalni"},
    )
    assert reception_created.status_code == 200
    assignment = reception_created.json()[0]

    admin_created = client.post(
        "/api/housekeeping/revisions",
        headers=admin_auth,
        json={"location": "Sklad", "text": "Zkontrolovat zásoby"},
    )
    assert admin_created.status_code == 200

    housekeeper_created = client.post(
        "/api/housekeeping/assignments",
        headers=housekeeper_auth,
        json={"room_ids": [room["id"]], "work_type": "Prijezd", "priority": "Normalni"},
    )
    assert housekeeper_created.status_code == 403

    accountant_created = client.post(
        "/api/housekeeping/assignments",
        headers=accountant_auth,
        json={"room_ids": [room["id"]], "work_type": "Prijezd", "priority": "Normalni"},
    )
    assert accountant_created.status_code == 403

    started = client.patch(f"/api/housekeeping/assignments/{assignment['id']}/start", headers=housekeeper_auth)
    assert started.status_code == 200

    reception_started = client.patch(f"/api/housekeeping/assignments/{assignment['id']}/pause", headers=reception_auth)
    assert reception_started.status_code == 403

    accountant_started = client.patch(f"/api/housekeeping/assignments/{assignment['id']}/pause", headers=accountant_auth)
    assert accountant_started.status_code == 403


def test_housekeeping_history_and_monthly_report_require_specific_read_permissions(client: TestClient, admin_auth: dict[str, str]) -> None:
    admin_auth = _login_auth(client, "admin", "061004")
    housekeeper_auth = _housekeeper_auth(client, admin_auth)
    reception_auth = _user_auth(client, admin_auth, "recepce", "recepcni")
    accountant_auth = _user_auth(client, admin_auth, "ucetni", "ucetni")

    housekeeper_history = client.get("/api/housekeeping/history?month=2026-05", headers=housekeeper_auth)
    assert housekeeper_history.status_code == 403

    reception_history = client.get("/api/housekeeping/history?month=2026-05", headers=reception_auth)
    assert reception_history.status_code == 200

    housekeeper_report = client.get("/api/housekeeping/reports/monthly-work?month=2026-05", headers=housekeeper_auth)
    assert housekeeper_report.status_code == 403

    accountant_report = client.get("/api/housekeeping/reports/monthly-work?month=2026-05", headers=accountant_auth)
    assert accountant_report.status_code == 200
