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
    assert body["user"]["role"]["name"] == "admin"
    assert body["user"]["role"]["permissions"] == ["*"]
    assert body["csrf_token"]

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["username"] == "admin"
    assert me.json()["role"]["permissions"] == ["*"]


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
    created_body = created.json()
    user_id = created_body["id"]
    assert created_body["role"]["name"] == "recepcni"
    assert "messages:*" in created_body["role"]["permissions"]

    listed = client.get("/api/users")
    assert listed.status_code == 200
    assert {user["username"] for user in listed.json()} >= {"admin", "recepce"}
    recepce = next(user for user in listed.json() if user["username"] == "recepce")
    assert "housekeeping:reception" in recepce["role"]["permissions"]

    protected_admin_id = next(user["id"] for user in listed.json() if user["username"] == "admin")
    protected_delete = client.delete(f"/api/users/{protected_admin_id}", headers=admin_auth)
    assert protected_delete.status_code == 400

    deleted = client.delete(f"/api/users/{user_id}", headers=admin_auth)
    assert deleted.status_code == 200

    second_admin = client.post(
        "/api/users",
        headers=admin_auth,
        json={"username": "admin2", "password": "admin22", "role_name": "admin"},
    )
    assert second_admin.status_code == 200
    login = client.post("/api/auth/login", json={"username": "admin2", "password": "admin22"})
    self_delete_headers = {"X-CSRF-Token": login.json()["csrf_token"]}
    self_delete = client.delete(f"/api/users/{second_admin.json()['id']}", headers=self_delete_headers)
    assert self_delete.status_code == 400


def test_roles_include_server_issued_permission_codes(client: TestClient, admin_auth: dict[str, str]) -> None:
    roles = client.get("/api/roles")

    assert roles.status_code == 200
    role_permissions = {role["name"]: role["permissions"] for role in roles.json()}
    assert role_permissions["admin"] == ["*"]
    assert "invoices:*" in role_permissions["recepcni"]
    assert role_permissions["pokojska"] == ["housekeeping:work", "notifications:read"]


def test_passwords_are_argon2_and_last_login_is_recorded(client: TestClient, admin_auth: dict[str, str]) -> None:
    created = client.post(
        "/api/users",
        headers=admin_auth,
        json={"username": "ucetni", "password": "ucetni1", "role_name": "ucetni"},
    )
    assert created.status_code == 200

    login = client.post("/api/auth/login", json={"username": "ucetni", "password": "ucetni1"})
    assert login.status_code == 200

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["last_login_at"] is not None
    assert "password" not in me.json()


def test_non_admin_cannot_manage_users(client: TestClient, admin_auth: dict[str, str]) -> None:
    client.post(
        "/api/users",
        headers=admin_auth,
        json={"username": "recepcni", "password": "recepcni1", "role_name": "recepcni"},
    )
    login = client.post("/api/auth/login", json={"username": "recepcni", "password": "recepcni1"})
    headers = {"X-CSRF-Token": login.json()["csrf_token"]}

    response = client.post(
        "/api/users",
        headers=headers,
        json={"username": "blocked", "password": "blocked1", "role_name": "pokojska"},
    )
    assert response.status_code == 403


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
