"""RLS pilot — advertiser_organizations + advertiser_user_memberships

Revision ID: 004
Revises: 003
Create Date: 2026-07-04

Phase 3.5b: Fail-closed PostgreSQL RLS on advertiser tenant tables.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ---------------------------------------------------------------------------
# Policy SQL — fail-closed: unset session variables = deny-all
# ---------------------------------------------------------------------------

POLICY_ADVERTISER_SELECT = """
CREATE POLICY advertiser_rls_sel ON advertiser_organizations
    FOR SELECT
    USING (
        COALESCE(
            NULLIF(current_setting('app.rmp_is_admin', true), ''),
            'false'
        )::bool = true
        OR id = ANY(
            COALESCE(
                string_to_array(
                    NULLIF(
                        current_setting('app.rmp_scope_advertiser_ids', true),
                        ''
                    ),
                    ','
                ),
                '{}'::text[]
            )
        )
    )
"""

POLICY_MEMBERSHIP_SELECT = """
CREATE POLICY membership_rls_sel ON advertiser_user_memberships
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
                '{}'::text[]
            )
        )
    )
"""


def upgrade() -> None:
    # Advertiser organizations
    op.execute("ALTER TABLE advertiser_organizations ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE advertiser_organizations FORCE ROW LEVEL SECURITY")
    op.execute(POLICY_ADVERTISER_SELECT)

    # Advertiser user memberships
    op.execute("ALTER TABLE advertiser_user_memberships ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE advertiser_user_memberships FORCE ROW LEVEL SECURITY")
    op.execute(POLICY_MEMBERSHIP_SELECT)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS advertiser_rls_sel ON advertiser_organizations")
    op.execute("ALTER TABLE advertiser_organizations DISABLE ROW LEVEL SECURITY")

    op.execute("DROP POLICY IF EXISTS membership_rls_sel ON advertiser_user_memberships")
    op.execute("ALTER TABLE advertiser_user_memberships DISABLE ROW LEVEL SECURITY")
