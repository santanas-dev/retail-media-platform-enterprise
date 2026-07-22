"""028: Allow public INSERT on advertiser_applications (no RLS on write).

The public endpoint POST /api/v1/public/advertiser-applications has no auth context,
so the existing RLS ins policy (TWO_LEVEL) blocks non-admin inserts.
This migration replaces the ins policy with a permissive one.
SELECT/UPDATE/DELETE remain RLS-protected.
"""

from alembic import op

revision = "028"
down_revision = "027"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("DROP POLICY IF EXISTS advertiser_applications_rls_ins ON advertiser_applications")
    op.execute("""
        CREATE POLICY advertiser_applications_rls_ins ON advertiser_applications
            FOR INSERT
            WITH CHECK (true);
    """)


def downgrade():
    # Restore the TWO_LEVEL insert policy from migration 020 (APP_ORG_TWO_LEVEL variant).
    # Uses current_setting() — bare app.rmp_* references are NOT valid SQL.
    _IS_ADMIN = (
        "COALESCE(NULLIF(current_setting('app.rmp_is_admin', true), ''), "
        "'false')::bool = true"
    )
    _SCOPE_RETAILER = (
        "COALESCE(string_to_array("
        "NULLIF(current_setting('app.rmp_scope_retailer_ids', true), ''), "
        "','), '{}'::text[])"
    )
    _SCOPE_ADVERTISER = (
        "COALESCE(string_to_array("
        "NULLIF(current_setting('app.rmp_scope_advertiser_ids', true), ''), "
        "','), '{}'::text[])"
    )
    TWO_LEVEL = (
        f"({_IS_ADMIN} OR (retailer_id = ANY({_SCOPE_RETAILER})"
        f" AND organization_id = ANY({_SCOPE_ADVERTISER})))"
    )

    op.execute("DROP POLICY IF EXISTS advertiser_applications_rls_ins ON advertiser_applications")
    op.execute(f"""
        CREATE POLICY advertiser_applications_rls_ins ON advertiser_applications
            FOR INSERT
            WITH CHECK ({TWO_LEVEL});
    """)
