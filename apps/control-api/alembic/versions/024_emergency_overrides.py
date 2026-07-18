"""K1 — Emergency Overrides table.

Revision ID: 024
Revises: 023
Create Date: 2026-07-18

Creates the emergency_overrides table for the global platform emergency
kill-switch.  MVP: global level only (level='global', no target_id).

The table is intentionally NOT under tenant RLS — emergency state is
platform-wide and must be readable by any authenticated service role
(including device-gateway under NOBYPASSRLS).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "024"
down_revision: Union[str, None] = "023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "emergency_overrides",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("level", sa.String(32), nullable=False, server_default="global"),
        sa.Column("target_id", sa.String(36), nullable=True),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("reason", sa.String(512), nullable=False, server_default=""),
        sa.Column("activated_by", sa.String(36), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deactivated_by", sa.String(36), nullable=True),
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deactivated_reason", sa.String(512), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                   server_default=sa.func.now()),
    )
    op.create_index("ix_emergency_overrides_level_active",
                    "emergency_overrides", ["level", "active"])


def downgrade() -> None:
    op.drop_index("ix_emergency_overrides_level_active",
                  table_name="emergency_overrides")
    op.drop_table("emergency_overrides")
