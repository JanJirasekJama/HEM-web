from fastapi.testclient import TestClient


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "app": "hem"}


def test_login_uses_cookie_session_and_returns_current_user(client: TestClient) -> None:
    login = client.post("/api/auth/login", json={"username": "admin", "password": "061004"})

    assert login.status_code == 200
    body = login.json()
    assert body["ok"] is True
    assert body["user"]["username"] == "admin"
    assert body["csrf_token"]

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["username"] == "admin"


def test_mutations_require_csrf(client: TestClient) -> None:
    login = client.post("/api/auth/login", json={"username": "admin", "password": "061004"})
    assert login.status_code == 200

    response = client.post(
        "/api/users",
        json={"username": "recepce", "password": "recepce1", "role_name": "recepcni"},
    )

    assert response.status_code == 403


def test_admin_can_manage_users_but_protected_admin_and_self_delete_are_blocked(client: TestClient, admin_auth: dict[str, str]) -> None:
    created = client.post(
        "/api/users",
        headers=admin_auth,
        json={"username": "recepce", "password": "recepce1", "role_name": "recepcni", "display_name": "Recepce"},
    )
    assert created.status_code == 200
    user_id = created.json()["id"]

    listed = client.get("/api/users")
    assert listed.status_code == 200
    assert {user["username"] for user in listed.json()} >= {"admin", "recepce"}

    protected_admin_id = next(user["id"] for user in listed.json() if user["username"] == "admin")
    protected_delete = client.delete(f"/api/users/{protected_admin_id}", headers=admin_auth)
    assert protected_delete.status_code == 400

    deleted = client.delete(f"/api/users/{user_id}", headers=admin_auth)
    assert deleted.status_code == 200


def test_settings_are_json_documents(client: TestClient, admin_auth: dict[str, str]) -> None:
    current = client.get("/api/settings/app")
    assert current.status_code == 200
    assert current.json()["value"]["finance"]["currency"] == "CZK"

    updated_payload = current.json()["value"]
    updated_payload["ui"]["theme"] = "dark"
    updated = client.put("/api/settings/app", headers=admin_auth, json={"value": updated_payload})

    assert updated.status_code == 200
    assert updated.json()["value"]["ui"]["theme"] == "dark"


def test_notifications_are_persisted_and_published_to_queue(client: TestClient, admin_auth: dict[str, str]) -> None:
    user = client.get("/api/auth/me").json()
    created = client.post(
        "/api/notifications",
        headers=admin_auth,
        json={
            "user_id": user["id"],
            "event_type": "message.comment_created",
            "severity": "info",
            "title": "Nový komentář",
            "body": "Recepce přidala komentář.",
        },
    )
    assert created.status_code == 200

    notifications = client.get("/api/notifications")
    assert notifications.status_code == 200
    assert notifications.json()[0]["title"] == "Nový komentář"

    drained = client.get("/api/notifications/queue/drain")
    assert drained.status_code == 200
    assert drained.json()[0]["type"] == "notification.created"

    read = client.patch(f"/api/notifications/{created.json()['id']}/read", headers=admin_auth)
    assert read.status_code == 200
    assert read.json()["read_at"] is not None
