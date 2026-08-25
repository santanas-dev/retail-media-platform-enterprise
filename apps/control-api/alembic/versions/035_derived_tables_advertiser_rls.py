"""AUTHZ-CROSS-PORTAL-001 — restore the advertiser dimension on campaign-derived RLS.

Revision ID: 035
Revises: 034
Create Date: 2026-08-25

Migration 020 (ADR-018) introduced two-level RLS (retailer + advertiser) but
classified the campaign child tables as ``DERIVED_TABLES`` and gave them a
``RETAILER_ONLY`` policy, dropping the via-campaign advertiser scoping that
migrations 006/010 had established.  The comment in 020 said the scope was
"derived from advertiser scope (via campaign hierarchy)" — the SQL never
derived it.

Effect on the running system: two advertisers under the SAME retailer could
read each other's flights, placements, creatives, approvals and status history
through the ordinary identity list endpoints (``GET /campaign-flights`` etc.),
which are enforced by RLS alone.  ``campaigns`` itself was never affected — it
carries ``advertiser_organization_id`` and kept the two-level policy — so the
leak was invisible in the campaign list.

This migration restores the derivation for the five campaign child tables that
an advertiser role can reach through the identity API:

    admin OR (retailer_id IN retailer_scope
              AND campaign_id IN (campaigns visible to the advertiser scope))

Deliberately unchanged (see AUTHZ-CROSS-PORTAL-001):

* ``delivery_manifests``, ``delivery_manifest_assets``,
  ``delivery_manifest_surfaces``, ``delivery_plans``, ``pop_events_raw``,
  ``pop_ingestion_batches`` — the device plane.  device-gateway authenticates a
  device and sets a retailer scope with NO advertiser scope
  (``apps/device-gateway/main.py``); adding an advertiser predicate would break
  manifest delivery and PoP ingestion.  No advertiser-permission endpoint lists
  these tables, and the per-campaign PoP endpoints already gate on
  ``_require_campaign_visible``.
* ``inventory_bookings`` — read only behind ``inventory.read``, which the
  advertiser role does not hold.
* ``branches``, ``clusters``, ``stores``, ``physical_devices``,
  ``display_surfaces``, ``inventory_rules``, ``inventory_slots`` — retailer
  inventory, not advertiser data; retailer scope is the correct dimension.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "035"
down_revision: Union[str, None] = "034"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ── RLS helper expressions (same shape as migration 020) ─────────────────────

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

# Pre-035 policy: retailer only — this is what leaked.
RETAILER_ONLY = f"({_IS_ADMIN} OR retailer_id = ANY({_SCOPE_RETAILER}))"

# 035: retailer AND the campaign's advertiser org.  Fail-closed on both
# dimensions: an empty scope produces '{}' and ANY('{}') is false.
VIA_CAMPAIGN = f"""({_IS_ADMIN} OR (
    retailer_id = ANY({_SCOPE_RETAILER})
    AND campaign_id IN (
        SELECT c.id FROM campaigns c
        WHERE c.retailer_id = ANY({_SCOPE_RETAILER})
          AND c.advertiser_organization_id = ANY({_SCOPE_ADVERTISER})
    )
))"""

# Campaign child tables reachable by an advertiser role through the identity API.
CAMPAIGN_CHILD_TABLES = [
    "campaign_approvals",
    "campaign_creatives",
    "campaign_flights",
    "campaign_placements",
    "campaign_status_history",
]

_SUFFIX = {"SELECT": "sel", "INSERT": "ins", "UPDATE": "upd", "DELETE": "del"}


def _apply(expression: str) -> None:
    for table in CAMPAIGN_CHILD_TABLES:
        for op_type in ("SELECT", "INSERT", "UPDATE", "DELETE"):
            suffix = _SUFFIX[op_type]
            op.execute(f"DROP POLICY IF EXISTS {table}_rls_{suffix} ON {table}")
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY {table}_rls_sel ON {table}
                FOR SELECT USING ({expression})
        """)
        op.execute(f"""
            CREATE POLICY {table}_rls_ins ON {table}
                FOR INSERT WITH CHECK ({expression})
        """)
        op.execute(f"""
            CREATE POLICY {table}_rls_upd ON {table}
                FOR UPDATE USING ({expression}) WITH CHECK ({expression})
        """)
        op.execute(f"""
            CREATE POLICY {table}_rls_del ON {table}
                FOR DELETE USING ({expression})
        """)


def upgrade() -> None:
    _apply(VIA_CAMPAIGN)


def downgrade() -> None:
    _apply(RETAILER_ONLY)
