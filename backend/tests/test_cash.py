from fastapi.testclient import TestClient


def test_cash_diary_calculates_difference_and_detects_shift_from_log(client: TestClient, admin_auth: dict[str, str]) -> None:
    me = client.get("/api/auth/me").json()
    shift = client.post(
        "/api/cash/shift-log",
        headers=admin_auth,
        json={"user_id": me["id"], "shift_type": "Ranní", "start_time": "2026-05-09T06:00:00Z", "cash_start": 1000},
    )
    assert shift.status_code == 200

    diary = client.post(
        "/api/cash/diary",
        headers=admin_auth,
        json={"entry_date": "2026-05-09", "user_id": me["id"], "cash_start": 1000, "cash_end": 1450, "notes": "OK"},
    )
    assert diary.status_code == 200
    assert diary.json()["shift_type"] == "Ranní"
    assert diary.json()["difference"] == 450

    history = client.get("/api/cash/diary?date_from=2026-05-01&date_to=2026-05-31")
    assert history.status_code == 200
    assert history.json()[0]["cash_end"] == 1450


def test_cash_status_warns_about_missing_morning_and_evening_cash(client: TestClient, admin_auth: dict[str, str]) -> None:
    me = client.get("/api/auth/me").json()

    missing_morning = client.get(f"/api/cash/status?date=2026-05-09&user_id={me['id']}&at=2026-05-09T08:00:00Z")
    assert missing_morning.status_code == 200
    assert missing_morning.json()["missing_morning_cash"] is True

    client.post(
        "/api/cash/diary",
        headers=admin_auth,
        json={"entry_date": "2026-05-09", "user_id": me["id"], "cash_start": 1000},
    )
    missing_evening = client.get(f"/api/cash/status?date=2026-05-09&user_id={me['id']}&at=2026-05-09T21:00:00Z")
    assert missing_evening.status_code == 200
    assert missing_evening.json()["missing_evening_cash"] is True

    exported = client.get("/api/cash/diary/export.csv?date_from=2026-05-01&date_to=2026-05-31")
    assert exported.status_code == 200
    assert "cash_start" in exported.text

