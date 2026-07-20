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
    op.execute("DROP POLICY IF EXISTS advertiser_applications_rls_ins ON advertiser_applications")
    op.execute("""
        CREATE POLICY advertiser_applications_rls_ins ON advertiser_applications
            FOR INSERT
            WITH CHECK (
                app.rmp_is_admin
                OR (
                    app.rmp_scope_retailer_ids IS NOT NULL
                    AND organization_id IN (
                        SELECT ao.id FROM advertiser_organizations ao
                        WHERE ao.retailer_id = ANY(app.rmp_scope_retailer_ids)
                    )
                )
            );
    """)
