"""Campaign write RLS policies — INSERT/UPDATE/DELETE (S-008)

Revision ID: 010
Revises: 009
Create Date: 2026-07-08

S-008: Add FOR INSERT / FOR UPDATE / FOR DELETE policies with
WITH CHECK on all 7 campaign-domain tables that previously had
SELECT-only RLS.  All policies are fail-closed: missing/empty
app.rmp_* session variables → deny.

Policy patterns:

  Direct (advertiser_organization_id column):
    campaigns, creative_assets

  Via campaign (campaign_id FK → campaigns):
    campaign_flights, campaign_placements, campaign_creatives,
    campaign_approvals, campaign_status_history
"""

from typing import Sequence, Union

from alembic import op

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ---------------------------------------------------------------------------
# SQL fragments — fail-closed: missing/empty session vars → deny
# ---------------------------------------------------------------------------

_IS_ADMIN = (
    "COALESCE(NULLIF(current_setting('app.rmp_is_admin', true), ''), "
    "'false')::bool = true"
)

_SCOPE_IDS = (
    "COALESCE(string_to_array("
    "NULLIF(current_setting('app.rmp_scope_advertiser_ids', true), ''), "
    "','), '{}'::text[])"
)

# Scope check: admin OR org_id in scope
SCOPE_CHECK = f"({_IS_ADMIN} OR advertiser_organization_id = ANY({_SCOPE_IDS}))"

# Via-campaign scope: admin OR campaign belongs to scoped org
VIA_CAMPAIGN_SCOPE = f"""({_IS_ADMIN} OR campaign_id IN (
    SELECT id FROM campaigns
    WHERE advertiser_organization_id = ANY({_SCOPE_IDS})
))"""

# ---------------------------------------------------------------------------
# Policy templates
# ---------------------------------------------------------------------------


def _direct_policies(table: str) -> str:
    """INSERT + UPDATE + DELETE policies for tables with
    advertiser_organization_id column (campaigns, creative_assets)."""
    return f"""
CREATE POLICY {table}_rls_ins ON {table}
    FOR INSERT
    WITH CHECK ({SCOPE_CHECK});

CREATE POLICY {table}_rls_upd ON {table}
    FOR UPDATE
    USING ({SCOPE_CHECK})
    WITH CHECK ({SCOPE_CHECK});

CREATE POLICY {table}_rls_del ON {table}
    FOR DELETE
    USING ({SCOPE_CHECK});
"""


def _via_campaign_policies(table: str) -> str:
    """INSERT + UPDATE + DELETE policies for tables linked via
    campaign_id FK (flights, placements, creatives, approvals,
    status_history)."""
    return f"""
CREATE POLICY {table}_rls_ins ON {table}
    FOR INSERT
    WITH CHECK ({VIA_CAMPAIGN_SCOPE});

CREATE POLICY {table}_rls_upd ON {table}
    FOR UPDATE
    USING ({VIA_CAMPAIGN_SCOPE})
    WITH CHECK ({VIA_CAMPAIGN_SCOPE});

CREATE POLICY {table}_rls_del ON {table}
    FOR DELETE
    USING ({VIA_CAMPAIGN_SCOPE});
"""


# ---------------------------------------------------------------------------
# Tables grouped by policy type
# ---------------------------------------------------------------------------

DIRECT_TABLES = [
    "campaigns",
    "creative_assets",
]

VIA_CAMPAIGN_TABLES = [
    "campaign_flights",
    "campaign_placements",
    "campaign_creatives",
    "campaign_approvals",
    "campaign_status_history",
]


# ---------------------------------------------------------------------------
# Migration
# ---------------------------------------------------------------------------


def upgrade() -> None:
    for table in DIRECT_TABLES:
        op.execute(_direct_policies(table))

    for table in VIA_CAMPAIGN_TABLES:
        op.execute(_via_campaign_policies(table))


def downgrade() -> None:
    all_tables = DIRECT_TABLES + VIA_CAMPAIGN_TABLES
    for table in all_tables:
        for suffix in ("ins", "upd", "del"):
            op.execute(f"DROP POLICY IF EXISTS {table}_rls_{suffix} ON {table}")
