"""Campaign briefs RLS policies — tenant boundary (BP-004 follow-up)

Revision ID: 019
Revises: 018
Create Date: 2026-07-17

Adds ENABLE + FORCE ROW LEVEL SECURITY on campaign_briefs,
plus SELECT / INSERT / UPDATE RLS policies matching the
existing campaign-domain pattern (migration 010).

All policies are fail-closed: missing/empty app.rmp_*
session variables → deny.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "019"
down_revision: Union[str, None] = "018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_IS_ADMIN = (
    "COALESCE(NULLIF(current_setting('app.rmp_is_admin', true), ''), "
    "'false')::bool = true"
)

_SCOPE_IDS = (
    "COALESCE(string_to_array("
    "NULLIF(current_setting('app.rmp_scope_advertiser_ids', true), ''), "
    "','), '{}'::text[])"
)

SCOPE_CHECK = f"({_IS_ADMIN} OR advertiser_organization_id = ANY({_SCOPE_IDS}))"


def upgrade() -> None:
    op.execute("ALTER TABLE campaign_briefs ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE campaign_briefs FORCE ROW LEVEL SECURITY")

    op.execute(f"""
    CREATE POLICY campaign_briefs_rls_sel ON campaign_briefs
        FOR SELECT
        USING ({SCOPE_CHECK});
    """)

    op.execute(f"""
    CREATE POLICY campaign_briefs_rls_ins ON campaign_briefs
        FOR INSERT
        WITH CHECK ({SCOPE_CHECK});
    """)

    op.execute(f"""
    CREATE POLICY campaign_briefs_rls_upd ON campaign_briefs
        FOR UPDATE
        USING ({SCOPE_CHECK})
        WITH CHECK ({SCOPE_CHECK});
    """)


def downgrade() -> None:
    for suffix in ("sel", "ins", "upd"):
        op.execute(f"DROP POLICY IF EXISTS campaign_briefs_rls_{suffix} ON campaign_briefs")
    op.execute("ALTER TABLE campaign_briefs NO FORCE ROW LEVEL SECURITY")
