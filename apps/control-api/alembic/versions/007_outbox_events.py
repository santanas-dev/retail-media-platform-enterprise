"""Transactional outbox foundation (ADR-011)

Revision ID: 007
Revises: 006
Create Date: 2026-07-05

Phase 4.1c: outbox_events table for transactional event delivery.
No business producers yet.  No RLS — relay worker needs cross-tenant visibility.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "outbox_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column("event_version", sa.String(16), nullable=False,
                  server_default="1.0"),
        sa.Column("aggregate_type", sa.String(64), nullable=False),
        sa.Column("aggregate_id", sa.String(36), nullable=False),
        sa.Column("partition_key", sa.String(128), nullable=True),
        sa.Column("payload_json", postgresql.JSONB, nullable=False),
        sa.Column("headers_json", postgresql.JSONB, nullable=False,
                  server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(32), nullable=False,
                  server_default="pending"),
        sa.Column("attempts", sa.Integer, nullable=False,
                  server_default=sa.text("0")),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )

    # Status CHECK constraint
    op.create_check_constraint(
        "ck_outbox_status", "outbox_events",
        "status IN ('pending','publishing','published','failed','dead_letter')",
    )

    # Indexes for relay worker polling and aggregate lookups
    op.create_index(
        "ix_outbox_status_next", "outbox_events",
        ["status", "next_attempt_at"],
        postgresql_where=sa.text(
            "status IN ('pending', 'failed')"
        ),
    )
    op.create_index(
        "ix_outbox_aggregate", "outbox_events",
        ["aggregate_type", "aggregate_id"],
    )
    op.create_index(
        "ix_outbox_created_at", "outbox_events",
        ["created_at"],
    )

    # NOTE: No RLS — outbox_events is internal infrastructure.
    # The relay worker must see all events regardless of tenant.
    # Per ADR-011: events carry aggregate ownership in aggregate_id;
    # tenant filtering is a consumer concern, not a DB concern.


def downgrade() -> None:
    op.drop_index("ix_outbox_created_at", table_name="outbox_events")
    op.drop_index("ix_outbox_aggregate", table_name="outbox_events")
    op.drop_index("ix_outbox_status_next", table_name="outbox_events")
    op.drop_table("outbox_events")
