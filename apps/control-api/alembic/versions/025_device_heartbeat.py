"""EDGE-004 — Device Heartbeat columns on physical_devices.

Revision ID: 025
Revises: 024
Create Date: 2026-07-19

Adds:
- last_heartbeat_at: last successful heartbeat timestamp
- health_state: device health status string (healthy/degraded/unhealthy)
- runtime_version: player/sidecar runtime version string
- player_version: player application version/build string
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "025"
down_revision: Union[str, None] = "024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "physical_devices",
        sa.Column(
            "last_heartbeat_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "physical_devices",
        sa.Column(
            "health_state",
            sa.String(32),
            nullable=False,
            server_default="unknown",
            comment="Device health: unknown/healthy/degraded/unhealthy",
        ),
    )
    op.add_column(
        "physical_devices",
        sa.Column(
            "runtime_version",
            sa.String(64),
            nullable=False,
            server_default="",
            comment="Player/sidecar runtime version reported by device",
        ),
    )
    op.add_column(
        "physical_devices",
        sa.Column(
            "player_version",
            sa.String(128),
            nullable=False,
            server_default="",
            comment="Player application version/build reported by device",
        ),
    )


def downgrade() -> None:
    op.drop_column("physical_devices", "player_version")
    op.drop_column("physical_devices", "runtime_version")
    op.drop_column("physical_devices", "health_state")
    op.drop_column("physical_devices", "last_heartbeat_at")
