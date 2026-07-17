"""EDGE-001 hardening — RLS on device_onboarding_codes.

Revision ID: 022
Revises: 021
Create Date: 2026-07-17

Adds ENABLE/FORCE ROW LEVEL SECURITY + SELECT/INSERT policies.
Admin bypass via app.rmp_is_admin.
Tenant filtering via app.rmp_scope_retailer_ids.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "022"
down_revision: Union[str, None] = "021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_IS_ADMIN = (
    "COALESCE(NULLIF(current_setting('app.rmp_is_admin', true), ''), "
    "'false')::bool = true"
)

_SCOPE_RETAILER = (
    "COALESCE(string_to_array("
    "NULLIF(current_setting('app.rmp_scope_retailer_ids', true), ''), "
    "','), '{}'::text[])"
)

# Admin bypass OR retailer_id IN scope_retailer_ids
RETAILER_RLS = f"({_IS_ADMIN} OR retailer_id = ANY({_SCOPE_RETAILER}))"


def upgrade() -> None:
    op.execute("ALTER TABLE device_onboarding_codes ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE device_onboarding_codes FORCE ROW LEVEL SECURITY")

    op.execute(f"""
        CREATE POLICY device_onboarding_codes_sel
        ON device_onboarding_codes FOR SELECT
        USING ({RETAILER_RLS})
    """)

    op.execute(f"""
        CREATE POLICY device_onboarding_codes_ins
        ON device_onboarding_codes FOR INSERT
        WITH CHECK ({RETAILER_RLS})
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS device_onboarding_codes_sel ON device_onboarding_codes")
    op.execute("DROP POLICY IF EXISTS device_onboarding_codes_ins ON device_onboarding_codes")
    op.execute("ALTER TABLE device_onboarding_codes NO FORCE ROW LEVEL SECURITY")
