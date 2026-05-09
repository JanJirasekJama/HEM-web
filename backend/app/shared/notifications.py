import json
from collections import deque
from collections.abc import Iterable
from typing import Any

from redis import Redis
from sqlalchemy.orm import Session

from app.core.models import Notification
from app.core.schemas import NotificationCreate
from app.core.time import utc_now


class NotificationQueue:
    def publish(self, event: dict[str, Any]) -> None:
        raise NotImplementedError

    def drain(self) -> list[dict[str, Any]]:
        raise NotImplementedError


class RedisNotificationQueue(NotificationQueue):
    def __init__(self, redis_url: str, list_name: str = "hem:notifications", channel: str = "hem:events") -> None:
        self._redis = Redis.from_url(redis_url, decode_responses=True)
        self._list_name = list_name
        self._channel = channel

    def publish(self, event: dict[str, Any]) -> None:
        payload = json.dumps(event, default=str, ensure_ascii=False)
        self._redis.rpush(self._list_name, payload)
        self._redis.publish(self._channel, payload)

    def drain(self) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        while True:
            payload = self._redis.lpop(self._list_name)
            if payload is None:
                break
            events.append(json.loads(payload))
        return events


class MemoryNotificationQueue(NotificationQueue):
    def __init__(self) -> None:
        self.events: deque[dict[str, Any]] = deque()

    def publish(self, event: dict[str, Any]) -> None:
        self.events.append(event)

    def drain(self) -> list[dict[str, Any]]:
        events = list(self.events)
        self.events.clear()
        return events


def queue_from_url(redis_url: str) -> NotificationQueue:
    if redis_url.startswith("memory://"):
        return MemoryNotificationQueue()
    return RedisNotificationQueue(redis_url)


def create_notification(db: Session, queue: NotificationQueue, payload: NotificationCreate) -> Notification:
    notification = Notification(**payload.model_dump())
    db.add(notification)
    db.commit()
    db.refresh(notification)
    queue.publish(
        {
            "type": "notification.created",
            "notification_id": notification.id,
            "user_id": notification.user_id,
            "event_type": notification.event_type,
            "severity": notification.severity,
            "title": notification.title,
            "created_at": notification.created_at.isoformat(),
        }
    )
    return notification


def mark_delivered(db: Session, notifications: Iterable[Notification]) -> None:
    now = utc_now()
    changed = False
    for notification in notifications:
        if notification.delivered_at is None:
            notification.delivered_at = now
            changed = True
    if changed:
        db.commit()

