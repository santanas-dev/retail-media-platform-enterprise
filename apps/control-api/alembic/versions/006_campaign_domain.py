"""Campaign domain foundation — 7 tables + RLS (ADR-015)

Revision ID: 006
Revises: 005
Create Date: 2026-07-05

Phase 4.1b: Campaign domain tables with RLS per ADR-015.
No mutations, no outbox producers yet.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ---------------------------------------------------------------------------
# RLS SELECT policies — fail-closed
# ---------------------------------------------------------------------------

# Tables with direct advertiser_organization_id
RLS_DIRECT = """
CREATE POLICY {table}_rls_sel ON {table}
    FOR SELECT
    USING (
        COALESCE(
            NULLIF(current_setting('app.rmp_is_admin', true), ''),
            'false'
        )::bool = true
        OR advertiser_organization_id = ANY(
            COALESCE(
                string_to_array(
                    NULLIF(
                        current_setting('app.rmp_scope_advertiser_ids', true),
                        ''
                    ),
                    ','
                ),
                '{{}}'::text[]
            )
        )
    )
"""

# Tables joined via campaign_id → campaigns.advertiser_organization_id
RLS_VIA_CAMPAIGN = """
CREATE POLICY {table}_rls_sel ON {table}
    FOR SELECT
    USING (
        COALESCE(
            NULLIF(current_setting('app.rmp_is_admin', true), ''),
            'false'
        )::bool = true
        OR campaign_id IN (
            SELECT id FROM campaigns
            WHERE advertiser_organization_id = ANY(
                COALESCE(
                    string_to_array(
                        NULLIF(
                            current_setting('app.rmp_scope_advertiser_ids', true),
                            ''
                        ),
                        ','
                    ),
                    '{{}}'::text[]
                )
            )
        )
    )
"""


def upgrade() -> None:
    # --- campaigns ---
    op.create_table(
        "campaigns",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("advertiser_organization_id", sa.String(36),
                  sa.ForeignKey("advertiser_organizations.id"), nullable=False),
        sa.Column("advertiser_brand_id", sa.String(36),
                  sa.ForeignKey("advertiser_brands.id"), nullable=True),
        sa.Column("advertiser_contract_id", sa.String(36),
                  sa.ForeignKey("advertiser_contracts.id"), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("priority", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("budget_limit_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("budget_limit_currency", sa.String(3), nullable=False, server_default="RUB"),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="Europe/Moscow"),
        sa.Column("created_by", sa.String(36),
                  sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_index("ix_campaigns_org_id", "campaigns", ["advertiser_organization_id"])
    op.create_index("ix_campaigns_code", "campaigns", ["code"])
    op.create_unique_constraint("uq_campaign_code_per_org", "campaigns",
                                ["advertiser_organization_id", "code"])
    op.execute("ALTER TABLE campaigns ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE campaigns FORCE ROW LEVEL SECURITY")
    op.execute(RLS_DIRECT.format(table="campaigns"))

    # --- campaign_flights ---
    op.create_table(
        "campaign_flights",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("campaign_id", sa.String(36),
                  sa.ForeignKey("campaigns.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dayparting_json", postgresql.JSONB, nullable=True),
        sa.Column("days_of_week", postgresql.ARRAY(sa.Integer), nullable=True),
        sa.Column("priority", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_index("ix_campaign_flights_cid", "campaign_flights", ["campaign_id"])
    op.execute("ALTER TABLE campaign_flights ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE campaign_flights FORCE ROW LEVEL SECURITY")
    op.execute(RLS_VIA_CAMPAIGN.format(table="campaign_flights"))

    # --- campaign_placements ---
    op.create_table(
        "campaign_placements",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("campaign_id", sa.String(36),
                  sa.ForeignKey("campaigns.id"), nullable=False),
        sa.Column("display_surface_id", sa.String(36),
                  sa.ForeignKey("display_surfaces.id"), nullable=True),
        sa.Column("store_id", sa.String(36),
                  sa.ForeignKey("stores.id"), nullable=True),
        sa.Column("cluster_id", sa.String(36),
                  sa.ForeignKey("clusters.id"), nullable=True),
        sa.Column("branch_id", sa.String(36),
                  sa.ForeignKey("branches.id"), nullable=True),
        sa.Column("share_of_voice_pct", sa.Integer, nullable=False,
                  server_default=sa.text("100")),
        sa.Column("max_impressions", sa.Integer, nullable=True),
        sa.Column("impressions_delivered", sa.Integer, nullable=False,
                  server_default=sa.text("0")),
        sa.Column("status", sa.String(32), nullable=False,
                  server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_index("ix_cp_campaign_id", "campaign_placements", ["campaign_id"])
    op.create_check_constraint(
        "ck_cp_at_least_one_target", "campaign_placements",
        "display_surface_id IS NOT NULL OR store_id IS NOT NULL "
        "OR cluster_id IS NOT NULL OR branch_id IS NOT NULL",
    )
    op.execute("ALTER TABLE campaign_placements ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE campaign_placements FORCE ROW LEVEL SECURITY")
    op.execute(RLS_VIA_CAMPAIGN.format(table="campaign_placements"))

    # --- creative_assets ---
    op.create_table(
        "creative_assets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("advertiser_organization_id", sa.String(36),
                  sa.ForeignKey("advertiser_organizations.id"), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("media_type", sa.String(32), nullable=False),
        sa.Column("storage_bucket", sa.String(128), nullable=False),
        sa.Column("storage_key", sa.String(512), nullable=False),
        sa.Column("sha256_checksum", sa.String(64), nullable=False),
        sa.Column("file_size_bytes", sa.Integer, nullable=False),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("resolution_w", sa.Integer, nullable=True),
        sa.Column("resolution_h", sa.Integer, nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="ready"),
        sa.Column("moderation_status", sa.String(32), nullable=False,
                  server_default="approved"),
        sa.Column("moderation_notes", sa.Text, nullable=True),
        sa.Column("created_by", sa.String(36),
                  sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_index("ix_ca_org_id", "creative_assets", ["advertiser_organization_id"])
    op.create_index("ix_ca_code", "creative_assets", ["code"])
    op.create_unique_constraint("uq_creative_asset_code_per_org", "creative_assets",
                                ["advertiser_organization_id", "code"])
    op.execute("ALTER TABLE creative_assets ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE creative_assets FORCE ROW LEVEL SECURITY")
    op.execute(RLS_DIRECT.format(table="creative_assets"))

    # --- campaign_creatives ---
    op.create_table(
        "campaign_creatives",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("campaign_id", sa.String(36),
                  sa.ForeignKey("campaigns.id"), nullable=False),
        sa.Column("creative_asset_id", sa.String(36),
                  sa.ForeignKey("creative_assets.id"), nullable=False),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("duration_override_ms", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_index("ix_cc_campaign_id", "campaign_creatives", ["campaign_id"])
    op.create_unique_constraint("uq_campaign_creative", "campaign_creatives",
                                ["campaign_id", "creative_asset_id"])
    op.execute("ALTER TABLE campaign_creatives ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE campaign_creatives FORCE ROW LEVEL SECURITY")
    op.execute(RLS_VIA_CAMPAIGN.format(table="campaign_creatives"))

    # --- campaign_approvals ---
    op.create_table(
        "campaign_approvals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("campaign_id", sa.String(36),
                  sa.ForeignKey("campaigns.id"), nullable=False),
        sa.Column("requested_by", sa.String(36),
                  sa.ForeignKey("users.id"), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_by", sa.String(36),
                  sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision", sa.String(32), nullable=True),
        sa.Column("rejection_reason", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_index("ix_cappr_campaign_id", "campaign_approvals", ["campaign_id"])
    op.execute("ALTER TABLE campaign_approvals ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE campaign_approvals FORCE ROW LEVEL SECURITY")
    op.execute(RLS_VIA_CAMPAIGN.format(table="campaign_approvals"))

    # --- campaign_status_history ---
    op.create_table(
        "campaign_status_history",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("campaign_id", sa.String(36),
                  sa.ForeignKey("campaigns.id"), nullable=False),
        sa.Column("old_status", sa.String(32), nullable=True),
        sa.Column("new_status", sa.String(32), nullable=False),
        sa.Column("changed_by", sa.String(36),
                  sa.ForeignKey("users.id"), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("reason", sa.Text, nullable=True),
    )
    op.create_index("ix_csh_campaign_id", "campaign_status_history", ["campaign_id"])
    op.execute("ALTER TABLE campaign_status_history ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE campaign_status_history FORCE ROW LEVEL SECURITY")
    op.execute(RLS_VIA_CAMPAIGN.format(table="campaign_status_history"))


def downgrade() -> None:
    via_campaign = [
        "campaign_status_history",
        "campaign_approvals",
        "campaign_creatives",
        "campaign_placements",
        "campaign_flights",
    ]
    for table in via_campaign:
        op.execute(f"DROP POLICY IF EXISTS {table}_rls_sel ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
        op.drop_table(table)

    # Tables with direct advertiser_organization_id RLS
    for table in ("creative_assets", "campaigns"):
        op.execute(f"DROP POLICY IF EXISTS {table}_rls_sel ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
        op.drop_table(table)
