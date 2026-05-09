from fastapi.testclient import TestClient


def test_daily_message_is_unique_per_date_and_user_with_history_search(client: TestClient, admin_auth: dict[str, str]) -> None:
    first = client.post(
        "/api/messages/daily",
        headers=admin_auth,
        json={"message_date": "2026-05-09", "content_text": "Příjezdy 4", "content_html": "<p>Příjezdy 4</p>"},
    )
    assert first.status_code == 200

    second = client.post(
        "/api/messages/daily",
        headers=admin_auth,
        json={"message_date": "2026-05-09", "content_text": "Příjezdy 5", "content_html": "<p>Příjezdy 5</p>"},
    )
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["content_text"] == "Příjezdy 5"

    history = client.get("/api/messages/history?date_from=2026-05-01&date_to=2026-05-31&text=příjezdy")
    assert history.status_code == 200
    assert len(history.json()) == 1


def test_message_comments_export_copy_and_email_queue(client: TestClient, admin_auth: dict[str, str]) -> None:
    message = client.post(
        "/api/messages/daily",
        headers=admin_auth,
        json={"message_date": "2026-05-08", "content_text": "Wellness večer"},
    ).json()

    comment = client.post(
        f"/api/messages/{message['id']}/comments",
        headers=admin_auth,
        json={"content_text": "Zavolat hostovi", "color": "#008000"},
    )
    assert comment.status_code == 200
    assert comment.json()["color"] == "#008000"

    copied = client.post(f"/api/messages/{message['id']}/copy-to-today", headers=admin_auth, json={"today": "2026-05-09"})
    assert copied.status_code == 200
    assert copied.json()["message_date"] == "2026-05-09"

    exported = client.get(f"/api/messages/{message['id']}/export.txt")
    assert exported.status_code == 200
    assert "Wellness večer" in exported.text

    client.post("/api/catalog/email-recipients", headers=admin_auth, json={"name": "Recepce", "email": "recepce@example.test", "active": True})
    sent = client.post(
        "/api/messages/send-email",
        headers=admin_auth,
        json={"message_date": "2026-05-09", "counts": {"arrivals": 1, "departures": 2, "stayovers": 3, "wellnesses": 4}},
    )
    assert sent.status_code == 200
    assert sent.json()["queued_recipients"] == ["recepce@example.test"]

