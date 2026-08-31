"""RM-TECH-210 — RLS bootstrap for device self-onboarding (no JWT).

Revision ID: 037
Revises: 036
Create Date: 2026-08-31

Defect RLS-CONTEXT-DEVICE-001 (PROJECT_STATE): ``POST /device/onboard`` carries no
JWT — the one-time code IS the authorisation — so the app role (NOSUPERUSER,
NOBYPASSRLS) runs it without any RLS context and the 022 policies deny every
row: the device gets ``403 INVALID_CODE`` in production. The behavioral suite
hid it behind an admin elevation allowlist (RM-STAB-002).

Fix (additive, mirrors migration 023's ``app.rmp_device_id`` bootstrap):

* ``device_onboarding_codes`` SELECT/UPDATE additionally match the single row
  whose ``code`` equals ``app.rmp_device_code`` — the secret the caller already
  presents. INSERT policy is unchanged (admin or retailer scope).
* ``physical_devices`` SELECT additionally matches the row whose
  ``hardware_fingerprint`` equals ``app.rmp_device_fingerprint`` — the value the
  caller already presents — so the global fingerprint-conflict check keeps
  working without exposing other retailers' devices.

After the code row is read, the route derives the retailer scope from the code
(``app.rmp_scope_retailer_ids``); device INSERT and code binding then pass the
unchanged retailer policies. No admin bypass is ever set on the public route.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "037"
down_revision: Union[str, None] = "036"
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
RETAILER_RLS = f"({_IS_ADMIN} OR retailer_id = ANY({_SCOPE_RETAILER}))"
CODE_BOOTSTRAP = "code = NULLIF(current_setting('app.rmp_device_code', true), '')::varchar"
CODES_SEL_UPD = f"({RETAILER_RLS} OR {CODE_BOOTSTRAP})"

DEVICE_BOOTSTRAP_SELECT = (
    f"({_IS_ADMIN}"
    f" OR id = NULLIF(current_setting('app.rmp_device_id', true), '')::varchar"
    f" OR retailer_id = ANY({_SCOPE_RETAILER}))"
)
FINGERPRINT_BOOTSTRAP = (
    "hardware_fingerprint = NULLIF(current_setting('app.rmp_device_fingerprint', true), '')::varchar"
)
DEVICES_SEL = f"({DEVICE_BOOTSTRAP_SELECT} OR {FINGERPRINT_BOOTSTRAP})"


def upgrade() -> None:
    op.execute("DROP POLICY IF EXISTS device_onboarding_codes_sel ON device_onboarding_codes")
    op.execute("DROP POLICY IF EXISTS device_onboarding_codes_upd ON device_onboarding_codes")
    op.execute(f"CREATE POLICY device_onboarding_codes_sel ON device_onboarding_codes FOR SELECT USING ({CODES_SEL_UPD})")
    op.execute(f"CREATE POLICY device_onboarding_codes_upd ON device_onboarding_codes FOR UPDATE USING ({CODES_SEL_UPD})")

    op.execute("DROP POLICY IF EXISTS physical_devices_rls_sel ON physical_devices")
    op.execute(f"CREATE POLICY physical_devices_rls_sel ON physical_devices FOR SELECT USING ({DEVICES_SEL})")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS device_onboarding_codes_sel ON device_onboarding_codes")
    op.execute("DROP POLICY IF EXISTS device_onboarding_codes_upd ON device_onboarding_codes")
    op.execute(f"CREATE POLICY device_onboarding_codes_sel ON device_onboarding_codes FOR SELECT USING ({RETAILER_RLS})")
    op.execute(f"CREATE POLICY device_onboarding_codes_upd ON device_onboarding_codes FOR UPDATE USING ({RETAILER_RLS})")

    op.execute("DROP POLICY IF EXISTS physical_devices_rls_sel ON physical_devices")
    op.execute(f"CREATE POLICY physical_devices_rls_sel ON physical_devices FOR SELECT USING ({DEVICE_BOOTSTRAP_SELECT})")
