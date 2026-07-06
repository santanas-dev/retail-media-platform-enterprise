"""Delivery foundation (ADR-016, Phase 4.2b)

Revision ID: 008
Revises: 007
Create Date: 2026-07-05

Phase 4.2b: delivery_plans, delivery_manifests, delivery_manifest_surfaces,
delivery_manifest_assets, delivery_attempts.

No RLS — worker-owned infrastructure tables.  Delivery workers need
cross-tenant visibility.  Tables are not exposed through user-facing API.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- delivery_plans ---
    op.create_table(
        "delivery_plans",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("campaign_id", sa.String(36), sa.ForeignKey("campaigns.id"),
                  nullable=False),
        sa.Column("campaign_version_hash", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False,
                  server_default="planned"),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_check_constraint(
        "ck_dp_status", "delivery_plans",
        "status IN ('planned','in_progress','completed','failed')",
    )
    op.create_index("ix_dp_campaign", "delivery_plans", ["campaign_id"])
    op.create_index("ix_dp_status", "delivery_plans", ["status"])

    # --- delivery_manifests ---
    op.create_table(
        "delivery_manifests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("manifest_id", sa.String(128), nullable=False),
        sa.Column("campaign_id", sa.String(36), sa.ForeignKey("campaigns.id"),
                  nullable=False),
        sa.Column("physical_device_id", sa.String(36),
                  sa.ForeignKey("physical_devices.id"), nullable=False),
        sa.Column("content_hash", sa.String(128), nullable=False),
        sa.Column("manifest_version", sa.Integer, nullable=False,
                  server_default="1"),
        sa.Column("status", sa.String(32), nullable=False,
                  server_default="planned"),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_unique_constraint(
        "uq_dm_manifest_id", "delivery_manifests", ["manifest_id"],
    )
    op.create_check_constraint(
        "ck_dm_status", "delivery_manifests",
        "status IN ('planned','generated','delivered','failed','revoked')",
    )
    op.create_index("ix_dm_manifest_id", "delivery_manifests",
                    ["manifest_id"])
    op.create_index("ix_dm_campaign", "delivery_manifests", ["campaign_id"])
    op.create_index("ix_dm_device", "delivery_manifests",
                    ["physical_device_id"])
    op.create_index("ix_dm_status", "delivery_manifests", ["status"])
    op.create_index("ix_dm_generated_at", "delivery_manifests",
                    ["generated_at"])

    # --- delivery_manifest_surfaces ---
    op.create_table(
        "delivery_manifest_surfaces",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("manifest_id", sa.String(36),
                  sa.ForeignKey("delivery_manifests.id"), nullable=False),
        sa.Column("display_surface_id", sa.String(36),
                  sa.ForeignKey("display_surfaces.id"), nullable=False),
        sa.Column("slot_order", sa.Integer, nullable=False,
                  server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_index("ix_dms_manifest", "delivery_manifest_surfaces",
                    ["manifest_id"])
    op.create_index("ix_dms_surface", "delivery_manifest_surfaces",
                    ["display_surface_id"])

    # --- delivery_manifest_assets ---
    op.create_table(
        "delivery_manifest_assets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("manifest_id", sa.String(36),
                  sa.ForeignKey("delivery_manifests.id"), nullable=False),
        sa.Column("creative_asset_id", sa.String(36),
                  sa.ForeignKey("creative_assets.id"), nullable=False),
        sa.Column("sha256_checksum", sa.String(64), nullable=False),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("media_type", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_index("ix_dma_manifest", "delivery_manifest_assets",
                    ["manifest_id"])
    op.create_index("ix_dma_asset", "delivery_manifest_assets",
                    ["creative_asset_id"])

    # --- delivery_attempts ---
    op.create_table(
        "delivery_attempts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("manifest_id", sa.String(128),
                  sa.ForeignKey("delivery_manifests.manifest_id"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False,
                  server_default="pending"),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_check_constraint(
        "ck_da_status", "delivery_attempts",
        "status IN ('pending','delivered','failed')",
    )
    op.create_index("ix_da_manifest", "delivery_attempts", ["manifest_id"])
    op.create_index("ix_da_status", "delivery_attempts", ["status"])

    # NOTE: No RLS on delivery tables.
    # These are worker-owned infrastructure tables.  Delivery workers
    # (delivery planner, manifest generator) need cross-tenant visibility
    # to process any campaign and produce manifests for any device.
    # No user-facing API endpoints expose these tables directly.
    # Per ADR-011 outbox pattern: tenant filtering is a consumer concern,
    # not a DB concern.


def downgrade() -> None:
    op.drop_index("ix_da_status", table_name="delivery_attempts")
    op.drop_index("ix_da_manifest", table_name="delivery_attempts")
    op.drop_table("delivery_attempts")

    op.drop_index("ix_dma_asset", table_name="delivery_manifest_assets")
    op.drop_index("ix_dma_manifest", table_name="delivery_manifest_assets")
    op.drop_table("delivery_manifest_assets")

    op.drop_index("ix_dms_surface", table_name="delivery_manifest_surfaces")
    op.drop_index("ix_dms_manifest", table_name="delivery_manifest_surfaces")
    op.drop_table("delivery_manifest_surfaces")

    op.drop_index("ix_dm_generated_at", table_name="delivery_manifests")
    op.drop_index("ix_dm_status", table_name="delivery_manifests")
    op.drop_index("ix_dm_device", table_name="delivery_manifests")
    op.drop_index("ix_dm_campaign", table_name="delivery_manifests")
    op.drop_index("ix_dm_manifest_id", table_name="delivery_manifests")
    op.drop_table("delivery_manifests")

    op.drop_index("ix_dp_status", table_name="delivery_plans")
    op.drop_index("ix_dp_campaign", table_name="delivery_plans")
    op.drop_table("delivery_plans")
