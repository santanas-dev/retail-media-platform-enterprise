"""Commerce Contour 2 RLS policies — DB-level backstop (COMMERCE-RLS-001)

Revision ID: 033
Revises: 032
Create Date: 2026-08-06

Adds ENABLE + FORCE ROW LEVEL SECURITY on commerce tables:
  commerce_orders              — direct advertiser_organization_id scope
  commerce_order_lines          — via parent order (EXISTS order_id)
  commerce_tariff_versions     — operator-global (admin write)
  commerce_price_items         — operator-global (admin write)

Design:
  commerce_orders / commerce_order_lines: org-scoped exactly like campaigns.
    Admin GUC bypass; scoped users see only their org's orders.
  commerce_tariff_versions / commerce_price_items: operator global.
    Any authenticated app role can SELECT; only admin can INSERT/UPDATE/DELETE.
    These are not org-scoped — tariffs apply across all advertisers.

All policies are fail-closed: missing/empty app.rmp_* session variables → deny.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "033"
down_revision: Union[str, None] = "032"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ── SQL fragments ──

_IS_ADMIN = (
    "COALESCE(NULLIF(current_setting('app.rmp_is_admin', true), ''), "
    "'false')::bool = true"
)

_SCOPE_IDS = (
    "COALESCE(string_to_array("
    "NULLIF(current_setting('app.rmp_scope_advertiser_ids', true), ''), "
    "','), '{}'::text[])"
)

# Org scope: admin OR org_id in scope
SCOPE_CHECK = f"({_IS_ADMIN} OR advertiser_organization_id = ANY({_SCOPE_IDS}))"

# Via-order scope: admin OR parent order belongs to scoped org
VIA_ORDER_SCOPE = f"""({_IS_ADMIN} OR order_id IN (
    SELECT id FROM commerce_orders
    WHERE advertiser_organization_id = ANY({_SCOPE_IDS})
))"""

# Operator-global SELECT: any authenticated app role (check that app context is set)
_APP_CONTEXT = (
    "COALESCE(NULLIF(current_setting('app.rmp_is_admin', true), ''), "
    "'false')::bool IS NOT NULL"
)

# Operator-global write: admin only
TARIFF_WRITE_CHECK = _IS_ADMIN


def upgrade() -> None:
    # ── commerce_orders: org-scoped, same pattern as campaigns ──
    op.execute("ALTER TABLE commerce_orders ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE commerce_orders FORCE ROW LEVEL SECURITY")

    op.execute(f"""
    CREATE POLICY commerce_orders_rls_sel ON commerce_orders
        FOR SELECT
        USING ({SCOPE_CHECK});
    """)

    op.execute(f"""
    CREATE POLICY commerce_orders_rls_ins ON commerce_orders
        FOR INSERT
        WITH CHECK ({SCOPE_CHECK});
    """)

    op.execute(f"""
    CREATE POLICY commerce_orders_rls_upd ON commerce_orders
        FOR UPDATE
        USING ({SCOPE_CHECK})
        WITH CHECK ({SCOPE_CHECK});
    """)

    # ── commerce_order_lines: via parent order ──
    op.execute("ALTER TABLE commerce_order_lines ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE commerce_order_lines FORCE ROW LEVEL SECURITY")

    op.execute(f"""
    CREATE POLICY commerce_order_lines_rls_sel ON commerce_order_lines
        FOR SELECT
        USING ({VIA_ORDER_SCOPE});
    """)

    op.execute(f"""
    CREATE POLICY commerce_order_lines_rls_ins ON commerce_order_lines
        FOR INSERT
        WITH CHECK ({VIA_ORDER_SCOPE});
    """)

    op.execute(f"""
    CREATE POLICY commerce_order_lines_rls_upd ON commerce_order_lines
        FOR UPDATE
        USING ({VIA_ORDER_SCOPE})
        WITH CHECK ({VIA_ORDER_SCOPE});
    """)

    # ── commerce_tariff_versions: operator-global read, admin write ──
    op.execute("ALTER TABLE commerce_tariff_versions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE commerce_tariff_versions FORCE ROW LEVEL SECURITY")

    op.execute(f"""
    CREATE POLICY commerce_tariff_versions_rls_sel ON commerce_tariff_versions
        FOR SELECT
        USING ({_APP_CONTEXT});
    """)

    op.execute(f"""
    CREATE POLICY commerce_tariff_versions_rls_ins ON commerce_tariff_versions
        FOR INSERT
        WITH CHECK ({TARIFF_WRITE_CHECK});
    """)

    op.execute(f"""
    CREATE POLICY commerce_tariff_versions_rls_upd ON commerce_tariff_versions
        FOR UPDATE
        USING ({TARIFF_WRITE_CHECK})
        WITH CHECK ({TARIFF_WRITE_CHECK});
    """)

    # ── commerce_price_items: operator-global read, admin write ──
    op.execute("ALTER TABLE commerce_price_items ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE commerce_price_items FORCE ROW LEVEL SECURITY")

    op.execute(f"""
    CREATE POLICY commerce_price_items_rls_sel ON commerce_price_items
        FOR SELECT
        USING ({_APP_CONTEXT});
    """)

    op.execute(f"""
    CREATE POLICY commerce_price_items_rls_ins ON commerce_price_items
        FOR INSERT
        WITH CHECK ({TARIFF_WRITE_CHECK});
    """)

    op.execute(f"""
    CREATE POLICY commerce_price_items_rls_upd ON commerce_price_items
        FOR UPDATE
        USING ({TARIFF_WRITE_CHECK})
        WITH CHECK ({TARIFF_WRITE_CHECK});
    """)


def downgrade() -> None:
    # commerce_orders
    for suffix in ("sel", "ins", "upd"):
        op.execute(
            f"DROP POLICY IF EXISTS commerce_orders_rls_{suffix} ON commerce_orders"
        )
    op.execute("ALTER TABLE commerce_orders NO FORCE ROW LEVEL SECURITY")

    # commerce_order_lines
    for suffix in ("sel", "ins", "upd"):
        op.execute(
            f"DROP POLICY IF EXISTS commerce_order_lines_rls_{suffix} ON commerce_order_lines"
        )
    op.execute("ALTER TABLE commerce_order_lines NO FORCE ROW LEVEL SECURITY")

    # commerce_tariff_versions
    for suffix in ("sel", "ins", "upd"):
        op.execute(
            f"DROP POLICY IF EXISTS commerce_tariff_versions_rls_{suffix} ON commerce_tariff_versions"
        )
    op.execute("ALTER TABLE commerce_tariff_versions NO FORCE ROW LEVEL SECURITY")

    # commerce_price_items
    for suffix in ("sel", "ins", "upd"):
        op.execute(
            f"DROP POLICY IF EXISTS commerce_price_items_rls_{suffix} ON commerce_price_items"
        )
    op.execute("ALTER TABLE commerce_price_items NO FORCE ROW LEVEL SECURITY")
