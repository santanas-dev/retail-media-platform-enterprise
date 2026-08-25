"""CAMPAIGN-PERMISSION-SPLIT-001 — separate advertiser brief writes from operator campaign management.

Revision ID: 036
Revises: 035
Create Date: 2026-08-25

``campaigns.manage`` was granted to the ``advertiser`` role because the brief
flow (create draft / edit draft / submit) happened to sit behind the same
permission as operator campaign management.  The consequence was that an
advertiser passed the permission gate on 17 operator endpoints — campaign
create and edit, the whole lifecycle (activate / pause / complete / archive /
request-approval), flights, placements, creative attachment and creative-asset
upload — while ``self.campaign_create`` is a blocked feature in the registry.

This migration splits the two:

* new permission ``campaign_briefs.manage`` — the three brief writes only;
* ``advertiser`` gains it and LOSES ``campaigns.manage``;
* ``system_admin`` gains it too (it holds every permission);
* ``security_admin`` and ``system_admin`` keep ``campaigns.manage`` untouched.

Changing the seed alone would not be enough: seeding is additive
(``ON CONFLICT (role_id, permission_id) DO NOTHING``) and runs on every
db-migrate, so an installation that already carries the grant keeps it. Hence
the DELETE below. The matching seed rows were removed in the same change, so
the next seed run does not hand the permission back.

Idempotent by construction: inserts are ON CONFLICT DO NOTHING and the delete
is a no-op once applied, so re-running upgrade is safe.

Downgrade restores the pre-split state, which **re-widens the advertiser role**
back to operator campaign management. That is a deliberate, documented
widening — it exists so the revision is reversible, not because the old state
is safe.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "036"
down_revision: Union[str, None] = "035"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BRIEF_PERM_ID = "00000000-0000-0000-0000-000000000125"
BRIEF_PERM_CODE = "campaign_briefs.manage"
BRIEF_PERM_NAME = "Подача и правка брифов рекламодателем"

ADVERTISER_ROLE = "advertiser"
ADMIN_ROLE = "system_admin"

RP_SYSTEM_ADMIN_BRIEF = "00000000-0000-0000-0000-000000000266"
RP_ADVERTISER_BRIEF = "00000000-0000-0000-0000-000000000267"
RP_ADVERTISER_CAMPAIGNS_MANAGE = "00000000-0000-0000-0000-000000000254"


def _insert_permission() -> None:
    op.execute(f"""
        INSERT INTO permissions (id, code, name)
        VALUES ('{BRIEF_PERM_ID}', '{BRIEF_PERM_CODE}', '{BRIEF_PERM_NAME}')
        ON CONFLICT (code) DO NOTHING
    """)


def _grant(assignment_id: str, role_code: str, permission_code: str) -> None:
    """Grant by code lookup so the row is correct even if ids differ."""
    op.execute(f"""
        INSERT INTO role_permissions (id, role_id, permission_id)
        SELECT '{assignment_id}', r.id, p.id
        FROM roles r, permissions p
        WHERE r.code = '{role_code}' AND p.code = '{permission_code}'
        ON CONFLICT (role_id, permission_id) DO NOTHING
    """)


def _revoke(role_code: str, permission_code: str) -> None:
    op.execute(f"""
        DELETE FROM role_permissions rp
        USING roles r, permissions p
        WHERE rp.role_id = r.id AND rp.permission_id = p.id
          AND r.code = '{role_code}' AND p.code = '{permission_code}'
    """)


def upgrade() -> None:
    _insert_permission()
    _grant(RP_ADVERTISER_BRIEF, ADVERTISER_ROLE, BRIEF_PERM_CODE)
    _grant(RP_SYSTEM_ADMIN_BRIEF, ADMIN_ROLE, BRIEF_PERM_CODE)
    # The point of the revision: the advertiser role stops passing the
    # operator campaign gate. security_admin / system_admin are untouched.
    _revoke(ADVERTISER_ROLE, "campaigns.manage")


def downgrade() -> None:
    # WIDENS the advertiser role back to operator campaign management.
    _grant(RP_ADVERTISER_CAMPAIGNS_MANAGE, ADVERTISER_ROLE, "campaigns.manage")
    _revoke(ADVERTISER_ROLE, BRIEF_PERM_CODE)
    _revoke(ADMIN_ROLE, BRIEF_PERM_CODE)
    op.execute(f"DELETE FROM permissions WHERE code = '{BRIEF_PERM_CODE}'")
