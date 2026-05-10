from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.deps import require_permission, require_csrf
from app.core.models import Setting, User
from app.core.time import utc_now
from app.modules.catalog.models import EmailRecipient
from app.modules.communication.models import DailyMessage, MessageComment, MessageEmailIntent

router = APIRouter(prefix="/api/messages", tags=["communication"])


class MessageCreate(BaseModel):
    message_date: date
    content_text: str = ""
    content_html: str | None = None


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    message_date: date
    user_id: str
    content_text: str
    content_html: str | None = None
    created_at: Any
    updated_at: Any


class CommentCreate(BaseModel):
    content_text: str = Field(min_length=1)
    color: str | None = Field(default=None, max_length=32)


class CommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    message_id: str
    user_id: str
    content_text: str
    color: str | None = None
    created_at: Any


class CopyToTodayRequest(BaseModel):
    today: date | None = None


class SendMessageEmailRequest(BaseModel):
    message_date: date
    counts: dict[str, int] = Field(default_factory=dict)


class SendMessageEmailResponse(BaseModel):
    intent_id: str
    queued_recipients: list[str]
    subject: str
    status: str


@router.post("/daily", response_model=MessageRead, dependencies=[Depends(require_csrf)])
def upsert_daily_message(payload: MessageCreate, db: Session = Depends(get_db), user: User = Depends(require_permission("messages:write"))) -> DailyMessage:
    message = db.scalar(
        select(DailyMessage).where(
            DailyMessage.message_date == payload.message_date,
            DailyMessage.user_id == user.id,
        )
    )
    now = utc_now()
    if message is None:
        message = DailyMessage(
            message_date=payload.message_date,
            user_id=user.id,
            content_text=payload.content_text,
            content_html=payload.content_html,
        )
        db.add(message)
    else:
        message.content_text = payload.content_text
        message.content_html = payload.content_html
        message.updated_at = now
    db.commit()
    db.refresh(message)
    return message


@router.get("/history", response_model=list[MessageRead])
def search_history(
    date_from: date | None = None,
    date_to: date | None = None,
    text: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("messages:read")),
) -> list[DailyMessage]:
    statement = select(DailyMessage)
    if date_from is not None:
        statement = statement.where(DailyMessage.message_date >= date_from)
    if date_to is not None:
        statement = statement.where(DailyMessage.message_date <= date_to)
    if text:
        like_text = f"%{text}%"
        statement = statement.where(or_(DailyMessage.content_text.ilike(like_text), DailyMessage.content_html.ilike(like_text)))
    return list(db.scalars(statement.order_by(DailyMessage.message_date.desc(), DailyMessage.updated_at.desc())).all())


@router.post("/{message_id}/comments", response_model=CommentRead, dependencies=[Depends(require_csrf)])
def create_comment(
    message_id: str,
    payload: CommentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("messages:write")),
) -> MessageComment:
    message = db.get(DailyMessage, message_id)
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    comment = MessageComment(
        message_id=message.id,
        user_id=user.id,
        content_text=payload.content_text,
        color=payload.color or user.comment_color,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


@router.post("/{message_id}/copy-to-today", response_model=MessageRead, dependencies=[Depends(require_csrf)])
def copy_to_today(
    message_id: str,
    payload: CopyToTodayRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("messages:write")),
) -> DailyMessage:
    source = db.get(DailyMessage, message_id)
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    target_date = payload.today or date.today()
    target = db.scalar(select(DailyMessage).where(DailyMessage.message_date == target_date, DailyMessage.user_id == user.id))
    if target is None:
        target = DailyMessage(
            message_date=target_date,
            user_id=user.id,
            content_text=source.content_text,
            content_html=source.content_html,
        )
        db.add(target)
    else:
        target.content_text = source.content_text
        target.content_html = source.content_html
        target.updated_at = utc_now()
    db.commit()
    db.refresh(target)
    return target


@router.get("/{message_id}/export.txt")
def export_message_txt(message_id: str, db: Session = Depends(get_db), _: User = Depends(require_permission("messages:export"))) -> Response:
    message = db.scalar(select(DailyMessage).options(selectinload(DailyMessage.comments)).where(DailyMessage.id == message_id))
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    lines = [
        f"Vzkazy recepce - {message.message_date.isoformat()}",
        "",
        message.content_text,
    ]
    if message.comments:
        lines.extend(["", "Komentare:"])
        for comment in sorted(message.comments, key=lambda item: item.created_at):
            lines.append(f"- {comment.content_text}")
    return Response(content="\n".join(lines), media_type="text/plain; charset=utf-8")


@router.post("/send-email", response_model=SendMessageEmailResponse, dependencies=[Depends(require_csrf)])
def queue_message_email(
    payload: SendMessageEmailRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("messages:send")),
) -> SendMessageEmailResponse:
    recipients = list(
        db.scalars(
            select(EmailRecipient)
            .where(EmailRecipient.active.is_(True))
            .order_by(EmailRecipient.sort_order, EmailRecipient.id)
        ).all()
    )
    queued_recipients = [recipient.email for recipient in recipients]

    email_settings = _email_settings(db)
    subject_template = str(email_settings.get("message_subject_template") or "Vzkazy z recepce - {date}")
    body_template = str(email_settings.get("message_body_template") or "{messages}")
    messages = _messages_for_date(db, payload.message_date)
    template_values = {
        "date": payload.message_date.isoformat(),
        "messages": messages,
        **{key: value for key, value in payload.counts.items()},
    }
    subject = _format_template(subject_template, template_values)
    body_text = _format_template(body_template, template_values)

    intent = MessageEmailIntent(
        message_date=payload.message_date,
        user_id=user.id,
        subject=subject,
        body_text=body_text,
        recipients=queued_recipients,
        counts=payload.counts,
        status="queued",
        response_json={"queued": True, "delivery": "persisted_intent"},
    )
    db.add(intent)
    db.commit()
    db.refresh(intent)

    return SendMessageEmailResponse(intent_id=intent.id, queued_recipients=queued_recipients, subject=subject, status=intent.status)


def _email_settings(db: Session) -> dict[str, Any]:
    setting = db.get(Setting, "email")
    if setting is None:
        return {}
    return dict(setting.value_json or {})


def _messages_for_date(db: Session, message_date: date) -> str:
    messages = db.scalars(select(DailyMessage).where(DailyMessage.message_date == message_date).order_by(DailyMessage.created_at)).all()
    return "\n\n".join(message.content_text for message in messages if message.content_text)


def _format_template(template: str, values: dict[str, Any]) -> str:
    try:
        return template.format(**values)
    except KeyError:
        return template
