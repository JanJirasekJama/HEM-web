from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.database import get_db
from app.core.deps import (
    create_session_for_user,
    get_app_settings,
    get_current_session,
    get_current_user,
    require_admin,
    require_csrf,
)
from app.core.models import Notification, Role, SessionToken, Setting, User
from app.core.schemas import (
    LoginRequest,
    LoginResponse,
    NotificationCreate,
    NotificationRead,
    SettingsRead,
    SettingsUpdate,
    UserCreate,
    UserRead,
)
from app.core.security import hash_password, verify_password
from app.core.time import utc_now
from app.shared.notifications import NotificationQueue, create_notification

router = APIRouter(prefix="/api", tags=["core"])
_notification_queues: dict[str, NotificationQueue] = {}


def get_notification_queue(settings: Settings = Depends(get_app_settings)) -> NotificationQueue:
    return queue_from_app_settings(settings)


def queue_from_app_settings(settings: Settings) -> NotificationQueue:
    if settings.redis_url not in _notification_queues:
        from app.shared.notifications import queue_from_url

        _notification_queues[settings.redis_url] = queue_from_url(settings.redis_url)
    return _notification_queues[settings.redis_url]


@router.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db), settings: Settings = Depends(get_app_settings)) -> LoginResponse:
    user = db.scalar(select(User).where(User.username == payload.username, User.active.is_(True)))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    ok, needs_rehash = verify_password(payload.password, user.password_hash)
    if not ok:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if needs_rehash:
        user.password_hash = hash_password(payload.password)
    user.last_login_at = utc_now()
    session = create_session_for_user(db, response, settings, user)
    db.refresh(user)
    return LoginResponse(ok=True, user=UserRead.model_validate(user), csrf_token=session.csrf_token)


@router.post("/auth/logout", dependencies=[Depends(require_csrf)])
def logout(response: Response, session: SessionToken = Depends(get_current_session), db: Session = Depends(get_db), settings: Settings = Depends(get_app_settings)) -> dict[str, bool]:
    db.delete(session)
    db.commit()
    response.delete_cookie(settings.session_cookie_name)
    return {"ok": True}


@router.get("/auth/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.get("/roles")
def list_roles(db: Session = Depends(get_db), _: User = Depends(require_admin)) -> list[dict[str, str]]:
    return [{"id": role.id, "name": role.name} for role in db.scalars(select(Role).order_by(Role.name)).all()]


@router.get("/users", response_model=list[UserRead])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_admin)) -> list[User]:
    return list(db.scalars(select(User).order_by(User.username)).all())


@router.post("/users", response_model=UserRead, dependencies=[Depends(require_csrf)])
def create_user(payload: UserCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> User:
    role = db.scalar(select(Role).where(Role.name == payload.role_name))
    if role is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown role")
    if db.scalar(select(User).where(User.username == payload.username)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")
    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
        role_id=role.id,
        comment_color=payload.comment_color,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}", dependencies=[Depends(require_csrf)])
def delete_user(user_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_admin)) -> dict[str, bool]:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.cannot_delete:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Protected user cannot be deleted")
    if user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete current user")
    db.delete(user)
    db.commit()
    return {"ok": True}


@router.get("/settings/{key}", response_model=SettingsRead)
def read_settings(key: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> SettingsRead:
    setting = db.get(Setting, key)
    if setting is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Settings not found")
    return SettingsRead(key=setting.key, value=setting.value_json)


@router.put("/settings/{key}", response_model=SettingsRead, dependencies=[Depends(require_csrf)])
def update_settings(key: str, payload: SettingsUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> SettingsRead:
    setting = db.get(Setting, key)
    if setting is None:
        setting = Setting(key=key, value_json=payload.value)
        db.add(setting)
    else:
        setting.value_json = payload.value
        setting.updated_at = utc_now()
    db.commit()
    return SettingsRead(key=setting.key, value=setting.value_json)


@router.get("/notifications", response_model=list[NotificationRead])
def list_notifications(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[Notification]:
    return list(db.scalars(select(Notification).where(Notification.user_id == user.id).order_by(Notification.created_at.desc())).all())


@router.post("/notifications", response_model=NotificationRead, dependencies=[Depends(require_csrf)])
def post_notification(
    payload: NotificationCreate,
    db: Session = Depends(get_db),
    queue: NotificationQueue = Depends(get_notification_queue),
    _: User = Depends(require_admin),
) -> Notification:
    return create_notification(db, queue, payload)


@router.patch("/notifications/{notification_id}/read", response_model=NotificationRead, dependencies=[Depends(require_csrf)])
def mark_notification_read(notification_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Notification:
    notification = db.get(Notification, notification_id)
    if notification is None or notification.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    notification.read_at = utc_now()
    db.commit()
    db.refresh(notification)
    return notification


@router.get("/notifications/queue/drain")
def drain_notification_queue(queue: NotificationQueue = Depends(get_notification_queue), _: User = Depends(require_admin)) -> list[dict]:
    return queue.drain()
