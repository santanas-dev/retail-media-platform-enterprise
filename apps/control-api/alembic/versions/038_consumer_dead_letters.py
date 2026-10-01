"""RM-STAB-020 — dead-letter table for the orchestrator campaign consumer.

Revision ID: 038
Revises: 037
Create Date: 2026-10-01

Finding P1-6.b (RF-10): the JetStream consumer redelivered a failing message
forever (``max_deliver=-1``, fixed 5 s nak).  The consumer now stops after the
last allowed delivery and keeps the message here for the operator, who can
replay it into the outbox (``python -m packages.services.consumer_dead_letters``).

Additive only.  The table is worker-owned and holds no tenant-scoped data, so
it is FORCE RLS with an admin-only policy: rows are visible and writable only
under the worker admin context (``app.rmp_is_admin``), never to a portal
request.  Downgrade removes this new table and its policies — nothing else.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "038"
down_revision: Union[str, None] = "037"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "consumer_dead_letters"

_IS_ADMIN = (
    "COALESCE(NULLIF(current_setting('app.rmp_is_admin', true), ''), "
    "'false')::bool = true"
)


def upgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_id", sa.String(64), nullable=False),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column("aggregate_type", sa.String(64), nullable=True),
        sa.Column("aggregate_id", sa.String(36), nullable=True),
        sa.Column("envelope_json", postgresql.JSONB, nullable=False),
        sa.Column("deliveries", sa.Integer, nullable=False),
        sa.Column("stream_sequence", sa.BigInteger, nullable=True),
        sa.Column("last_error", sa.Text, nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="dead"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("replayed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replay_outbox_event_id", sa.String(36), nullable=True),
        sa.CheckConstraint("status IN ('dead','replayed')", name="ck_consumer_dead_letters_status"),
    )
    op.create_index("ix_consumer_dead_letters_status_created", TABLE, ["status", "created_at"])
    op.create_index("ix_consumer_dead_letters_event_id", TABLE, ["event_id"])

    op.execute(f"ALTER TABLE {TABLE} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {TABLE} FORCE ROW LEVEL SECURITY")
    op.execute(f"CREATE POLICY {TABLE}_admin_sel ON {TABLE} FOR SELECT USING ({_IS_ADMIN})")
    op.execute(f"CREATE POLICY {TABLE}_admin_ins ON {TABLE} FOR INSERT WITH CHECK ({_IS_ADMIN})")
    op.execute(
        f"CREATE POLICY {TABLE}_admin_upd ON {TABLE} FOR UPDATE "
        f"USING ({_IS_ADMIN}) WITH CHECK ({_IS_ADMIN})"
    )
    # Operator purge of handled rows; also admin-only.
    op.execute(f"CREATE POLICY {TABLE}_admin_del ON {TABLE} FOR DELETE USING ({_IS_ADMIN})")


def downgrade() -> None:
    for suffix in ("sel", "ins", "upd", "del"):
        op.execute(f"DROP POLICY IF EXISTS {TABLE}_admin_{suffix} ON {TABLE}")
    op.drop_index("ix_consumer_dead_letters_event_id", table_name=TABLE)
    op.drop_index("ix_consumer_dead_letters_status_created", table_name=TABLE)
    op.drop_table(TABLE)
