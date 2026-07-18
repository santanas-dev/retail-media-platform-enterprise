"""EDGE-002-FU-v4 — Device RLS bootstrap: physical_devices SELECT by app.rmp_device_id.

Revision ID: 023
Revises: 022
Create Date: 2026-07-17

Adds `id = current_setting('app.rmp_device_id')` to the SELECT RLS policy
on physical_devices so the app role can look up a single device row by its
own ID before the retailer scope is known.  This breaks the chicken-and-egg
problem: the device-gateway needs the device's retailer_id to set the RLS
scope, but the app role couldn't read the device row without a scope.

INSERT / UPDATE / DELETE policies are unchanged — the device_id bootstrap
only applies to SELECT.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "023"
down_revision: Union[str, None] = "022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Re-use the same RLS helper expressions as migration 020.
_IS_ADMIN = (
    "COALESCE(NULLIF(current_setting('app.rmp_is_admin', true), ''), "
    "'false')::bool = true"
)

_SCOPE_RETAILER = (
    "COALESCE(string_to_array("
    "NULLIF(current_setting('app.rmp_scope_retailer_ids', true), ''), "
    "','), '{}'::text[])"
)

RETAILER_ONLY = (
    f"({_IS_ADMIN} OR retailer_id = ANY({_SCOPE_RETAILER}))"
)

# New: device bootstrap — allow SELECT when id matches app.rmp_device_id.
# This lets the device-gateway resolve the device's retailer_id using only
# its own device JWT (sub=device_id), without needing a pre-existing scope.
DEVICE_BOOTSTRAP_SELECT = (
    f"({_IS_ADMIN}"
    f" OR id = NULLIF(current_setting('app.rmp_device_id', true), '')::varchar"
    f" OR retailer_id = ANY({_SCOPE_RETAILER}))"
)

TABLE = "physical_devices"


def upgrade() -> None:
    # Drop existing policies for SELECT so we can recreate with bootstrap.
    for suffix in ("sel",):
        op.execute(f"DROP POLICY IF EXISTS {TABLE}_rls_{suffix} ON {TABLE}")

    # Recreate SELECT policy with device bootstrap.
    op.execute(f"""
        CREATE POLICY {TABLE}_rls_sel ON {TABLE}
            FOR SELECT
            USING ({DEVICE_BOOTSTRAP_SELECT});
    """)

    # INSERT / UPDATE / DELETE policies are unchanged — they already
    # require retailer scope (no device bootstrap needed for writes).


def downgrade() -> None:
    # Restore the original SELECT policy (no device bootstrap).
    op.execute(f"DROP POLICY IF EXISTS {TABLE}_rls_sel ON {TABLE}")

    op.execute(f"""
        CREATE POLICY {TABLE}_rls_sel ON {TABLE}
            FOR SELECT
            USING ({RETAILER_ONLY});
    """)
