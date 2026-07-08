"""Advertiser-domain write RLS policies — INSERT/UPDATE/DELETE (S-008 follow-up)

Revision ID: 011
Revises: 010
Create Date: 2026-07-08

S-008 extended: advertiser_organizations + advertiser_user_memberships
have FORCE RLS with only SELECT policies.  Under NOBYPASSRLS every
INSERT/UPDATE/DELETE is blocked.  This migration adds admin-only
write policies — the app never does direct INSERT on these tables
at runtime (seeds run as owner, behavioral fixtures use admin bypass),
but the policies must exist so that admin-bypassed test helpers can
write setup/teardown data.

Policy pattern: COALESCE(NULLIF(app.rmp_is_admin, ''), 'false')::bool = true
"""

from typing import Sequence, Union

from alembic import op

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_IS_ADMIN = (
    "COALESCE(NULLIF(current_setting('app.rmp_is_admin', true), ''), "
    "'false')::bool = true"
)

_DIRECT_TABLES = [
    "advertiser_organizations",
    "advertiser_user_memberships",
    "advertiser_brands",
    "advertiser_contracts",
    "advertiser_contacts",
]


def upgrade() -> None:
    for table in _DIRECT_TABLES:
        op.execute(f"""
CREATE POLICY {table}_rls_ins ON {table}
    FOR INSERT
    WITH CHECK ({_IS_ADMIN});

CREATE POLICY {table}_rls_upd ON {table}
    FOR UPDATE
    USING ({_IS_ADMIN})
    WITH CHECK ({_IS_ADMIN});

CREATE POLICY {table}_rls_del ON {table}
    FOR DELETE
    USING ({_IS_ADMIN});
""")


def downgrade() -> None:
    for table in _DIRECT_TABLES:
        for suffix in ("ins", "upd", "del"):
            op.execute(f"DROP POLICY IF EXISTS {table}_rls_{suffix} ON {table}")
