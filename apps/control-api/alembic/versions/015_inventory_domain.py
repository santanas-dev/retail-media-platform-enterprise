"""Inventory domain foundation — slots, bookings, rules (S-077)

Revision ID: 015
Revises: 014
Create Date: 2026-07-16

Adds the three core inventory-domain tables:

  inventory_slots       — atomic unit: one hour of one display surface
  inventory_bookings    — links campaign placements to reserved/committed slots
  inventory_rules       — scoped business rules (max_sov, blackout, etc.)

RLS is DEFERRED for this MVP (S-076 §2.1, §11 D5):
  All three tables are admin-only.  No advertiser-organization FK exists,
  so no tenant-scoped RLS policy is meaningful at this stage.  If/when
  advertiser-facing inventory is added later, an advertiser_organization_id
  column should be added and RLS policies applied then.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- inventory_slots ---
    op.create_table(
        "inventory_slots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "display_surface_id", sa.String(36),
            sa.ForeignKey("display_surfaces.id"), nullable=False,
        ),
        sa.Column("slot_date", sa.Date(), nullable=False),
        sa.Column("slot_hour", sa.Integer(), nullable=False),
        sa.Column("total_capacity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("booked_capacity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reserved_capacity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("internal_blocked_capacity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("emergency_blocked_capacity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(32), nullable=False, server_default="'available'"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_inventory_slots_display_surface_id", "inventory_slots",
        ["display_surface_id"],
    )
    op.create_unique_constraint(
        "uq_inventory_slot_surface_date_hour", "inventory_slots",
        ["display_surface_id", "slot_date", "slot_hour"],
    )
    op.create_index(
        "ix_inventory_slots_surface_date", "inventory_slots",
        ["display_surface_id", "slot_date"],
    )
    op.create_index(
        "ix_inventory_slots_status_date", "inventory_slots",
        ["status", "slot_date"],
    )

    # --- inventory_bookings ---
    op.create_table(
        "inventory_bookings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "campaign_id", sa.String(36),
            sa.ForeignKey("campaigns.id"), nullable=True,
        ),
        sa.Column(
            "campaign_placement_id", sa.String(36),
            sa.ForeignKey("campaign_placements.id"), nullable=True,
        ),
        sa.Column(
            "inventory_slot_id", sa.String(36),
            sa.ForeignKey("inventory_slots.id"), nullable=False,
        ),
        sa.Column("capacity_units", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="'reserved'"),
        sa.Column("reserved_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("release_reason", sa.String(512), nullable=False, server_default="''"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_inventory_bookings_campaign_id", "inventory_bookings",
        ["campaign_id"],
    )
    op.create_index(
        "ix_inventory_bookings_campaign_placement_id", "inventory_bookings",
        ["campaign_placement_id"],
    )
    op.create_index(
        "ix_inventory_bookings_inventory_slot_id", "inventory_bookings",
        ["inventory_slot_id"],
    )
    op.create_unique_constraint(
        "uq_inventory_booking_placement_slot", "inventory_bookings",
        ["campaign_placement_id", "inventory_slot_id"],
    )
    op.create_index(
        "ix_inventory_bookings_slot_status", "inventory_bookings",
        ["inventory_slot_id", "status"],
    )
    op.create_index(
        "ix_inventory_bookings_status_until", "inventory_bookings",
        ["status", "reserved_until"],
    )

    # --- inventory_rules ---
    op.create_table(
        "inventory_rules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("scope_type", sa.String(32), nullable=False, server_default="'global'"),
        sa.Column("scope_id", sa.String(36), nullable=True),
        sa.Column("rule_type", sa.String(64), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("value_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_inventory_rules_scope", "inventory_rules",
        ["scope_type", "scope_id"],
    )
    op.create_index(
        "ix_inventory_rules_type_active", "inventory_rules",
        ["rule_type", "is_active"],
    )


def downgrade() -> None:
    op.drop_table("inventory_bookings")
    op.drop_table("inventory_slots")
    op.drop_table("inventory_rules")
