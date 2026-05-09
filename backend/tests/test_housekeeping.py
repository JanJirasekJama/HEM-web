from fastapi.testclient import TestClient


def _housekeeper_auth(client: TestClient, admin_auth: dict[str, str]) -> dict[str, str]:
    created = client.post(
        "/api/users",
        headers=admin_auth,
        json={"username": "pokojska", "password": "pokojska1", "role_name": "pokojska", "display_name": "Pokojská"},
    )
    assert created.status_code == 200
    login = client.post("/api/auth/login", json={"username": "pokojska", "password": "pokojska1"})
    assert login.status_code == 200
    return {"X-CSRF-Token": login.json()["csrf_token"]}


def test_assignment_workflow_requires_photos_creates_history_and_unique_minibar_entries(client: TestClient, admin_auth: dict[str, str]) -> None:
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

    uploaded = client.post(
        f"/api/housekeeping/assignments/{assignment['id']}/photos",
        headers=housekeeper_auth,
        data={"task_label": "Postel", "photo_task_type_id": photo_type["id"]},
        files={"file": ("postel.jpg", b"fake-image", "image/jpeg")},
    )
    assert uploaded.status_code == 200

    finished = client.patch(f"/api/housekeeping/assignments/{assignment['id']}/finish", headers=housekeeper_auth)
    assert finished.status_code == 200
    assert finished.json()["status"] == "Hotovo"

    history = client.get("/api/housekeeping/history?month=2026-05")
    assert history.status_code == 200
    assert history.json()[0]["room_label_snapshot"] == "101"


def test_revision_laundry_and_monthly_work_report(client: TestClient, admin_auth: dict[str, str]) -> None:
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
        files={"files": ("okno.jpg", b"fake-image", "image/jpeg")},
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
        files={"file": ("pradlo.jpg", b"fake-image", "image/jpeg")},
    )
    assert uploaded.status_code == 200

    done = client.patch(f"/api/housekeeping/laundry/{laundry.json()['id']}/done", headers=housekeeper_auth)
    assert done.status_code == 200
    assert done.json()["status"] == "done"

    report = client.get("/api/housekeeping/reports/monthly-work?month=2026-05")
    assert report.status_code == 200
    assert report.json()["housekeepers"]["pokojska"]["laundry_count"] == 1

