"""EDGE-001 — Device onboarding codes.

Revision ID: 021
Revises: 020
Create Date: 2026-07-17

Adds device_onboarding_codes table for one-time device registration.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "021"
down_revision: Union[str, None] = "020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "device_onboarding_codes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("code", sa.String(128), nullable=False, unique=True, index=True),
        sa.Column("retailer_id", sa.String(36), sa.ForeignKey("retailers.id"), nullable=False, index=True),
        sa.Column("store_id", sa.String(36), sa.ForeignKey("stores.id"), nullable=True),
        sa.Column("device_type_id", sa.String(36), sa.ForeignKey("device_types.id"), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="active",
                  comment="active | used | expired | revoked"),
        sa.Column("hardware_fingerprint_bound", sa.String(255), nullable=True),
        sa.Column("physical_device_id", sa.String(36), sa.ForeignKey("physical_devices.id"), nullable=True),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("device_onboarding_codes")
