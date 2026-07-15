"""Add composite index for delivery_manifests latest lookup (S-068)

Revision ID: 014
Revises: 013
Create Date: 2026-07-15

Improves performance of get_latest_manifest_metadata / get_latest_manifest_for_device
which query with (physical_device_id, status, generated_at DESC).
"""

from typing import Sequence, Union

from alembic import op

revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_delivery_manifests_device_status_generated",
        "delivery_manifests",
        ["physical_device_id", "status", "generated_at"],
        postgresql_using="btree",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_delivery_manifests_device_status_generated",
        table_name="delivery_manifests",
    )
