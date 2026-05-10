"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-10 00:00:00
"""

from typing import Sequence

from alembic import op

from app.core.database import Base
import app.models  # noqa: F401

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    Base.metadata.create_all(op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(op.get_bind())

