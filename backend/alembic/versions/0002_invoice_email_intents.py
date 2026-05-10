"""invoice email intents

Revision ID: 0002_invoice_email_intents
Revises: 0001_initial_schema
Create Date: 2026-05-10 00:00:00
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0002_invoice_email_intents"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _invoice_email_intents_table() -> sa.Table:
    metadata = sa.MetaData()
    sa.Table("invoices", metadata, sa.Column("id", sa.String(length=64), primary_key=True))
    sa.Table("users", metadata, sa.Column("id", sa.String(length=64), primary_key=True))

    return sa.Table(
        "invoice_email_intents",
        metadata,
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column(
            "invoice_id",
            sa.String(length=64),
            sa.ForeignKey("invoices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.String(length=64),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("recipient", sa.String(length=255), nullable=False),
        sa.Column("sender", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("body_text", sa.Text(), nullable=False),
        sa.Column("attachment_path", sa.Text(), nullable=False),
        sa.Column("smtp_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("response_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def upgrade() -> None:
    bind = op.get_bind()
    table = _invoice_email_intents_table()

    table.create(bind, checkfirst=True)
    sa.Index("ix_invoice_email_intents_invoice_id", table.c.invoice_id).create(bind, checkfirst=True)
    sa.Index("ix_invoice_email_intents_user_id", table.c.user_id).create(bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    table = _invoice_email_intents_table()

    sa.Index("ix_invoice_email_intents_user_id", table.c.user_id).drop(bind, checkfirst=True)
    sa.Index("ix_invoice_email_intents_invoice_id", table.c.invoice_id).drop(bind, checkfirst=True)
    table.drop(bind, checkfirst=True)
