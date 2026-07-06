"""PoP persistence schema (ADR-017, Phase 4.3b)

Revision ID: 009
Revises: 008
Create Date: 2026-07-07

Phase 4.3b: pop_events_raw, pop_dedup_index, pop_ingestion_batches.

No RLS — device-owned events ingested by internal service.
Reporting APIs enforce their own RLS via JOINs to campaign/placement
visibility rules (ADR-017 §5).

campaign_id and manifest_id have NO FK constraints — quarantine events
arrive before the manifest record reaches the backend (manifest generation
is asynchronous).  Cross-entity consistency checks happen at the
application layer (ADR-017 §4.2).

No UPDATE after acceptance except campaign_verified transition.
Quarantined events may transition to accepted or expired.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- pop_events_raw ---
    op.create_table(
        "pop_events_raw",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_id", sa.String(36), nullable=False),
        sa.Column("schema_version", sa.String(8), nullable=False),
        sa.Column("device_id", sa.String(36),
                  sa.ForeignKey("physical_devices.id"), nullable=False),
        sa.Column("manifest_id", sa.String(128), nullable=True),
        sa.Column("campaign_id", sa.String(36), nullable=True),
        sa.Column("campaign_verified", sa.Boolean, nullable=False,
                  server_default="false"),
        sa.Column("creative_asset_id", sa.String(36),
                  sa.ForeignKey("creative_assets.id"), nullable=False),
        sa.Column("surface_id", sa.String(36), nullable=False),
        sa.Column("rendered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_recorded_at", sa.DateTime(timezone=True),
                  nullable=False),
        sa.Column("duration_ms", sa.Integer, nullable=False),
        sa.Column("playback_result", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("quarantine_reason", sa.String(128), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("batch_id", sa.String(36), nullable=True),
    )
    # Unique index on event_id for dedup
    op.create_unique_constraint(
        "uq_pop_event_id", "pop_events_raw", ["event_id"],
    )
    op.create_index("ix_pop_event_id", "pop_events_raw", ["event_id"])
    op.create_index("ix_pop_device_id", "pop_events_raw", ["device_id"])
    op.create_index("ix_pop_campaign_id", "pop_events_raw", ["campaign_id"])
    op.create_index("ix_pop_manifest_id", "pop_events_raw", ["manifest_id"])
    op.create_index("ix_pop_status", "pop_events_raw", ["status"])
    op.create_index("ix_pop_batch_id", "pop_events_raw", ["batch_id"])
    op.create_index("ix_pop_received_at", "pop_events_raw", ["received_at"])
    # playback_result must be 'success' or 'fallback' or 'interrupted' or 'failed'
    op.create_check_constraint(
        "ck_pop_playback_result", "pop_events_raw",
        "playback_result IN ('success','fallback','interrupted','failed')",
    )
    # duration_ms: 1ms to 24h (86,400,000 ms)
    op.create_check_constraint(
        "ck_pop_duration", "pop_events_raw",
        "duration_ms >= 1 AND duration_ms <= 86400000",
    )
    # status must be one of accepted, quarantined, rejected
    op.create_check_constraint(
        "ck_pop_status", "pop_events_raw",
        "status IN ('accepted','quarantined','rejected')",
    )

    # --- pop_dedup_index ---
    op.create_table(
        "pop_dedup_index",
        sa.Column("event_id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )

    # --- pop_ingestion_batches ---
    op.create_table(
        "pop_ingestion_batches",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("device_id", sa.String(36),
                  sa.ForeignKey("physical_devices.id"), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("event_count", sa.Integer, nullable=False,
                  server_default="0"),
        sa.Column("accepted_count", sa.Integer, nullable=False,
                  server_default="0"),
        sa.Column("rejected_count", sa.Integer, nullable=False,
                  server_default="0"),
        sa.Column("quarantined_count", sa.Integer, nullable=False,
                  server_default="0"),
    )
    op.create_index("ix_pib_device", "pop_ingestion_batches", ["device_id"])
    op.create_index("ix_pib_received", "pop_ingestion_batches", ["received_at"])

    # NOTE: No RLS on PoP tables.
    # Events are device-owned and ingested by an internal service (device
    # gateway / PoP ingestor).  Reporting APIs enforce their own RLS via
    # JOINs to campaign/placement visibility rules (ADR-017 §5).
    #
    # No FK on campaign_id — quarantine events may reference campaigns
    # that do not exist in the DB yet (manifest not yet generated).
    # Cross-entity consistency is enforced at the application layer
    # (ADR-017 §4.2).
    #
    # No FK on manifest_id — same rationale.  Quarantine events arrive
    # before the manifest record reaches the backend.  The manifest_id
    # string is stored for later resolution; consistency checks happen
    # when the manifest appears (ADR-017 §4).


def downgrade() -> None:
    op.drop_index("ix_pib_received", table_name="pop_ingestion_batches")
    op.drop_index("ix_pib_device", table_name="pop_ingestion_batches")
    op.drop_table("pop_ingestion_batches")

    op.drop_table("pop_dedup_index")

    op.drop_index("ix_pop_received_at", table_name="pop_events_raw")
    op.drop_index("ix_pop_batch_id", table_name="pop_events_raw")
    op.drop_index("ix_pop_status", table_name="pop_events_raw")
    op.drop_index("ix_pop_manifest_id", table_name="pop_events_raw")
    op.drop_index("ix_pop_campaign_id", table_name="pop_events_raw")
    op.drop_index("ix_pop_device_id", table_name="pop_events_raw")
    op.drop_index("ix_pop_event_id", table_name="pop_events_raw")
    op.drop_table("pop_events_raw")
