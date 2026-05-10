from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    permissions: list[str] = Field(default_factory=list)

    @field_validator("permissions", mode="before")
    @classmethod
    def permissions_to_codes(cls, value: Any) -> list[str]:
        if value is None:
            return []
        return sorted(permission if isinstance(permission, str) else permission.code for permission in value)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    display_name: str | None
    role_id: str
    role: RoleRead | None = None
    comment_color: str | None
    cannot_delete: bool
    created_at: datetime
    last_login_at: datetime | None
    active: bool


class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=128)
    password: str = Field(min_length=6)
    display_name: str | None = None
    role_name: str
    comment_color: str | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    ok: bool
    user: UserRead
    csrf_token: str


class SettingsRead(BaseModel):
    key: str
    value: dict[str, Any]


class SettingsUpdate(BaseModel):
    value: dict[str, Any]


class NotificationCreate(BaseModel):
    user_id: str
    event_type: str
    severity: str = "info"
    title: str
    body: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    action_url: str | None = None


class NotificationRead(NotificationCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    delivered_at: datetime | None
    read_at: datetime | None


class EmailRecipientCreate(BaseModel):
    name: str
    email: EmailStr
    active: bool = True
