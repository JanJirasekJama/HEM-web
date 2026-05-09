from datetime import timedelta

from fastapi import Cookie, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.database import get_db
from app.core.models import SessionToken, User
from app.core.security import new_csrf_token, new_session_token
from app.core.time import utc_now


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


def create_session_for_user(db: Session, response: Response, settings: Settings, user: User) -> SessionToken:
    session = SessionToken(
        id=new_session_token(),
        user_id=user.id,
        csrf_token=new_csrf_token(),
        expires_at=utc_now() + timedelta(seconds=settings.session_ttl_seconds),
    )
    db.add(session)
    db.commit()
    response.set_cookie(
        settings.session_cookie_name,
        session.id,
        httponly=True,
        samesite="lax",
        secure=settings.app_env == "production",
        max_age=settings.session_ttl_seconds,
    )
    return session


def get_current_session(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    session_cookie: str | None = Cookie(default=None, alias="hem_session"),
) -> SessionToken:
    cookie_value = request.cookies.get(settings.session_cookie_name) or session_cookie
    if not cookie_value:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    session = db.get(SessionToken, cookie_value)
    if session is None or _is_expired(session.expires_at):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")
    return session


def require_csrf(
    request: Request,
    session: SessionToken = Depends(get_current_session),
    csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> None:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    if not csrf_token or csrf_token != session.csrf_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token")


def get_current_user(session: SessionToken = Depends(get_current_session)) -> User:
    if session.user is None or not session.user.active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user")
    return session.user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role.name != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return user


def has_permission(user: User, permission_code: str) -> bool:
    if user.role.name == "admin":
        return True
    return any(permission.code == permission_code or permission.code == "*" for permission in user.role.permissions)


def delete_expired_sessions(db: Session) -> None:
    expired = [session for session in db.scalars(select(SessionToken)).all() if _is_expired(session.expires_at)]
    for session in expired:
        db.delete(session)
    if expired:
        db.commit()


def _is_expired(expires_at) -> bool:
    now = utc_now()
    if getattr(expires_at, "tzinfo", None) is None:
        now = now.replace(tzinfo=None)
    return expires_at < now
