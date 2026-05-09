from fastapi.testclient import TestClient


def test_one_time_task_calendar_completion_and_stats(client: TestClient, admin_auth: dict[str, str]) -> None:
    task = client.post(
        "/api/tasks",
        headers=admin_auth,
        json={"title": "Zkontrolovat minibar", "due_date": "2026-05-09", "priority": "Vysoka", "assigned_to_all": True},
    )
    assert task.status_code == 200

    calendar = client.get("/api/tasks/calendar?date=2026-05-09")
    assert calendar.status_code == 200
    assert calendar.json()["tasks"][0]["title"] == "Zkontrolovat minibar"
    assert calendar.json()["stats"]["total"] == 1
    assert calendar.json()["stats"]["open"] == 1

    done = client.patch(f"/api/tasks/{task.json()['id']}/completion", headers=admin_auth, json={"completed": True})
    assert done.status_code == 200

    stats = client.get("/api/tasks/calendar?date=2026-05-09").json()["stats"]
    assert stats["completed"] == 1
    assert stats["priority"]["Vysoka"] == 1


def test_recurring_task_tracks_completion_by_occurrence_and_delete_removes_series(client: TestClient, admin_auth: dict[str, str]) -> None:
    task = client.post(
        "/api/tasks",
        headers=admin_auth,
        json={
            "title": "Týdenní kontrola vířivky",
            "due_date": "2026-05-04",
            "priority": "Normalni",
            "recurrence_type": "weekly",
            "recurrence_days": ["monday", "wednesday"],
            "recurrence_end_date": "2026-05-31",
        },
    )
    assert task.status_code == 200
    task_id = task.json()["id"]

    monday = client.get("/api/tasks/calendar?date=2026-05-11").json()
    tuesday = client.get("/api/tasks/calendar?date=2026-05-12").json()
    assert [item["id"] for item in monday["tasks"]] == [task_id]
    assert tuesday["tasks"] == []

    completed = client.patch(
        f"/api/tasks/{task_id}/completion",
        headers=admin_auth,
        json={"completed": True, "occurrence_date": "2026-05-11"},
    )
    assert completed.status_code == 200

    assert client.get("/api/tasks/calendar?date=2026-05-11").json()["tasks"][0]["completed"] is True
    assert client.get("/api/tasks/calendar?date=2026-05-18").json()["tasks"][0]["completed"] is False

    deleted = client.delete(f"/api/tasks/{task_id}", headers=admin_auth)
    assert deleted.status_code == 200
    assert client.get("/api/tasks/calendar?date=2026-05-18").json()["tasks"] == []

