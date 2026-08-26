"""
COMMERCE-RLS-001 — DB-level RLS behavioral proof for commerce tables.

Proves commerce_orders / commerce_order_lines RLS under NOBYPASSRLS
(app role, no owner bypass):
- ORG_A scope SELECT commerce_orders → sees ORG_A, not ORG_B
- ORG_A scope SELECT commerce_order_lines → sees only own order lines
- INSERT foreign advertiser_organization_id → rejected by DB
- UPDATE foreign order → rejected by DB
- Admin GUC sees/manages all
- Tariff SELECT works under app context (operator-global)

Uses T1 BehBuilder for advertiser orgs, raw SQL for commerce seed.
Admin-bypass is NOT set on the DB session — real RLS applies.
"""

import asyncio
import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine as _cae
from sqlalchemy.pool import NullPool

from tests.behavioral.builder import BehBuilder


# ── Helpers ─────────────────────────────────────────────────────────────

# RM-STAB-001: одна переменная, один helper, обе DSN-формы допустимы.
from tests.behavioral.dsn import sqlalchemy_dsn

_APP_DB_URL = sqlalchemy_dsn()


def _run_setup(sql: str) -> None:
    """Run owner-level setup SQL (rmp_is_admin=true)."""
    from tests.behavioral.conftest import _run_sql
    asyncio.run(_run_sql(sql))


# ── Fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def commerce_setup(db_available):
    """Create two advertiser orgs + one order each, plus tariff + price."""
    b = BehBuilder("beh-crls")

    # Org A
    rid = b.retailer(code="CRLS", legal_name="Commerce RLS Retailer")
    chain = b.store_chain()
    cd = b.channel_device_type()
    dev = b.device(chain["store_id"], cd["device_type_id"], rid)
    surf = b.surface(chain["store_id"], dev, rid)
    org_a = b.advertiser(rid, org_code="CRLS-A")
    org_b = b.advertiser(rid, org_code="CRLS-B")

    # Order A and Order B via raw SQL
    order_a_id = f"{b.prefix}order-{b._n+1:04d}"
    order_b_id = f"{b.prefix}order-{b._n+2:04d}"
    b._n += 2

    _run_setup(f"""
    INSERT INTO commerce_orders (id, advertiser_organization_id, code, status,
        payment_status, tariff_version_id, total_amount, currency)
    VALUES ('{order_a_id}', '{org_a["org_id"]}', 'ORD-CRLS-A', 'draft',
        'not_required', NULL, 0, 'RUB')
    ON CONFLICT (id) DO NOTHING;
    """)
    _run_setup(f"""
    INSERT INTO commerce_orders (id, advertiser_organization_id, code, status,
        payment_status, tariff_version_id, total_amount, currency)
    VALUES ('{order_b_id}', '{org_b["org_id"]}', 'ORD-CRLS-B', 'draft',
        'not_required', NULL, 0, 'RUB')
    ON CONFLICT (id) DO NOTHING;
    """)

    # Order lines (one each)
    line_a1_id = f"{b.prefix}line-a1-{b._n+1:04d}"
    line_b1_id = f"{b.prefix}line-b1-{b._n+2:04d}"
    b._n += 2

    _run_setup(f"""
    INSERT INTO commerce_order_lines (id, order_id, surface_id, date_from,
        date_to, quantity_days, unit_price_amount, line_amount)
    VALUES ('{line_a1_id}', '{order_a_id}', '{surf}',
        '2026-08-01', '2026-08-07', 7, 100.00, 700.00)
    ON CONFLICT (id) DO NOTHING;
    """)
    _run_setup(f"""
    INSERT INTO commerce_order_lines (id, order_id, surface_id, date_from,
        date_to, quantity_days, unit_price_amount, line_amount)
    VALUES ('{line_b1_id}', '{order_b_id}', '{surf}',
        '2026-08-08', '2026-08-14', 7, 150.00, 1050.00)
    ON CONFLICT (id) DO NOTHING;
    """)

    # Tariff version for operator-global proof
    tariff_id = f"{b.prefix}tarf-{b._n+1:04d}"
    b._n += 1
    _run_setup(f"""
    INSERT INTO commerce_tariff_versions (id, code, name, status, valid_from, currency)
    VALUES ('{tariff_id}', 'CRLS-TARIFF', 'CRLS Test Tariff', 'active',
        '2026-01-01', 'RUB')
    ON CONFLICT (code) DO NOTHING;
    """)

    yield {
        "builder": b,
        "org_a": org_a,
        "org_b": org_b,
        "order_a_id": order_a_id,
        "order_b_id": order_b_id,
        "line_a1_id": line_a1_id,
        "line_b1_id": line_b1_id,
        "tariff_id": tariff_id,
        "surf": surf,
    }
    b.cleanup()


@pytest.mark.usefixtures("commerce_setup")
class TestCommerceRLS:
    """Commerce order/order_line RLS under NOBYPASSRLS."""

    @pytest.fixture(autouse=True)
    def setup(self, db_available, commerce_setup):
        self.org_a = commerce_setup["org_a"]
        self.org_b = commerce_setup["org_b"]
        self.order_a_id = commerce_setup["order_a_id"]
        self.order_b_id = commerce_setup["order_b_id"]
        self.line_a1_id = commerce_setup["line_a1_id"]
        self.line_b1_id = commerce_setup["line_b1_id"]
        self.tariff_id = commerce_setup["tariff_id"]
        self.surf = commerce_setup["surf"]
        self.b = commerce_setup["builder"]

    # ── Scope A: orders ────────────────────────────────────────────

    def test_org_a_scope_sees_org_a_order_only(self):
        """ORG_A scope SELECT commerce_orders → sees ORG_A, not ORG_B."""
        rows = asyncio.run(_execute_with_scope(
            "SELECT id, code FROM commerce_orders ORDER BY code",
            advertiser_ids=self.org_a["org_id"],
        ))
        codes = {r["code"] for r in rows}
        assert "ORD-CRLS-A" in codes, f"ORG_A scope must see its own order: {codes}"
        assert "ORD-CRLS-B" not in codes, f"ORG_A scope must NOT see ORG_B order: {codes}"

    def test_org_b_scope_sees_org_b_order_only(self):
        """ORG_B scope SELECT commerce_orders → sees ORG_B, not ORG_A."""
        rows = asyncio.run(_execute_with_scope(
            "SELECT id, code FROM commerce_orders ORDER BY code",
            advertiser_ids=self.org_b["org_id"],
        ))
        codes = {r["code"] for r in rows}
        assert "ORD-CRLS-B" in codes, f"ORG_B scope must see its own order: {codes}"
        assert "ORD-CRLS-A" not in codes, f"ORG_B scope must NOT see ORG_A order: {codes}"

    def test_empty_scope_sees_nothing(self):
        """Empty scope → RLS denies all for non-admin."""
        rows = asyncio.run(_execute_with_scope(
            "SELECT id, code FROM commerce_orders",
            advertiser_ids="",
        ))
        assert len(rows) == 0, f"Empty scope must return 0 rows: got {len(rows)}"

    # ── Scope B: order lines via parent order ────────────────────

    def test_org_a_scope_sees_own_order_lines(self):
        """ORG_A scope SELECT commerce_order_lines → sees only ORG_A lines."""
        rows = asyncio.run(_execute_with_scope(
            "SELECT id, order_id FROM commerce_order_lines ORDER BY id",
            advertiser_ids=self.org_a["org_id"],
        ))
        order_ids = {r["order_id"] for r in rows}
        assert self.order_a_id in order_ids, f"Must see ORG_A order lines: {order_ids}"
        assert self.order_b_id not in order_ids, \
            f"Must NOT see ORG_B order lines: {order_ids}"

    # ── Scope C: INSERT foreign rejected ──────────────────────────

    def test_insert_foreign_org_rejected(self):
        """ORG_A scope INSERT order with advertiser_organization_id=ORG_B → rejected."""
        new_id = self.b._uid("frgn")
        # Attempt INSERT with ORG_A scope but ORG_B's org_id — RLS must block.
        # RLS raises an error (not silent), so we catch it.
        with pytest.raises(Exception) as exc_info:
            asyncio.run(_attempt_insert(
                table="commerce_orders",
                columns="id, advertiser_organization_id, code, status, payment_status",
                values=f"'{new_id}', '{self.org_b['org_id']}', 'ORD-FRGN', 'draft', 'not_required'",
                advertiser_ids=self.org_a["org_id"],
            ))
        assert "violates row-level security" in str(exc_info.value), \
            f"Expected RLS violation, got: {exc_info.value}"

    # ── Scope D: UPDATE foreign rejected ──────────────────────────

    def test_update_foreign_order_rejected(self):
        """ORG_A scope UPDATE on ORG_B's order → rejected (0 rows affected)."""
        rows_before = asyncio.run(_attempt_update(
            table="commerce_orders",
            set_clause="status = 'booked'",
            where_id=self.order_b_id,
            advertiser_ids=self.org_a["org_id"],
        ))
        # 0 rows affected = RLS blocked
        assert rows_before == 0, \
            f"Foreign UPDATE must affect 0 rows (RLS blocked), got {rows_before}"

        # Verify status unchanged (using ORG_B scope, which can see its own)
        rows = asyncio.run(_execute_with_scope(
            f"SELECT status FROM commerce_orders WHERE id = '{self.order_b_id}'",
            advertiser_ids=self.org_b["org_id"],
        ))
        assert rows[0]["status"] == "draft", \
            f"Foreign UPDATE must not change status: {rows[0]['status']}"

    # ── Scope E: Admin GUC ────────────────────────────────────────

    def test_admin_sees_all_orders(self):
        """Admin GUC sees both ORG_A and ORG_B orders."""
        rows = asyncio.run(_execute_with_scope(
            "SELECT id, code FROM commerce_orders ORDER BY code",
            admin=True,
        ))
        codes = {r["code"] for r in rows}
        assert "ORD-CRLS-A" in codes
        assert "ORD-CRLS-B" in codes

    # ── Scope F: Tariff operator-global ───────────────────────────

    def test_app_context_can_read_tariffs(self):
        """Any app context (non-admin, no org scope) can SELECT tariffs."""
        rows = asyncio.run(_execute_with_scope(
            f"SELECT id, code FROM commerce_tariff_versions WHERE code = 'CRLS-TARIFF'",
            admin=False,
            advertiser_ids="",
        ))
        assert len(rows) == 1, f"App context must read tariffs: got {len(rows)}"
        assert rows[0]["code"] == "CRLS-TARIFF"

    def test_non_admin_cannot_insert_tariff(self):
        """Non-admin cannot INSERT into commerce_tariff_versions."""
        new_id = self.b._uid("tins")
        with pytest.raises(Exception) as exc_info:
            asyncio.run(_attempt_insert(
                table="commerce_tariff_versions",
                columns="id, code, name, status, valid_from, currency",
                values=f"'{new_id}', 'CRLS-INS', 'Test Insert', 'draft', '2026-01-01', 'RUB'",
                admin=False,
                advertiser_ids="",
            ))
        assert "violates row-level security" in str(exc_info.value), \
            f"Expected RLS violation, got: {exc_info.value}"


# ── Raw exec helpers (app role) ────────────────────────────────────────


async def _execute_with_scope(
    stmt: str,
    *,
    admin: bool = False,
    advertiser_ids: str | None = None,
) -> list[dict]:
    """Run a SELECT via app role with RLS scope set in the same transaction."""
    engine = _cae(_APP_DB_URL, echo=False, poolclass=NullPool)
    try:
        async with engine.connect() as conn:
            # set_config is_local=true — lives for the current transaction only.
            # Do NOT commit between set_config and the query.
            await conn.execute(
                text("SELECT set_config('app.rmp_is_admin', :admin, true)"),
                {"admin": "true" if admin else "false"},
            )
            if advertiser_ids:
                await conn.execute(
                    text(
                        "SELECT set_config('app.rmp_scope_advertiser_ids', :ids, true)"
                    ),
                    {"ids": advertiser_ids},
                )
            else:
                await conn.execute(
                    text("SELECT set_config('app.rmp_scope_advertiser_ids', '', true)"),
                )
            result = await conn.execute(text(stmt))
            rows = result.fetchall()
            return [dict(row._mapping) for row in rows]
    finally:
        await engine.dispose()


async def _attempt_insert(
    table: str,
    columns: str,
    values: str,
    *,
    admin: bool = False,
    advertiser_ids: str | None = None,
) -> None:
    """Attempt INSERT via app role with scope set. RLS violation raises."""
    engine = _cae(_APP_DB_URL, echo=False, poolclass=NullPool)
    try:
        async with engine.connect() as conn:
            await conn.execute(
                text("SELECT set_config('app.rmp_is_admin', :admin, true)"),
                {"admin": "true" if admin else "false"},
            )
            if advertiser_ids:
                await conn.execute(
                    text(
                        "SELECT set_config('app.rmp_scope_advertiser_ids', :ids, true)"
                    ),
                    {"ids": advertiser_ids},
                )
            else:
                await conn.execute(
                    text("SELECT set_config('app.rmp_scope_advertiser_ids', '', true)"),
                )
            # No commit — keep scope alive for the INSERT
            await conn.execute(text(
                f"INSERT INTO {table} ({columns}) VALUES ({values})"
            ))
            await conn.commit()
    finally:
        await engine.dispose()


async def _attempt_update(
    table: str,
    set_clause: str,
    where_id: str,
    *,
    admin: bool = False,
    advertiser_ids: str | None = None,
) -> int:
    """Attempt UPDATE via app role with scope set. Returns rowcount."""
    engine = _cae(_APP_DB_URL, echo=False, poolclass=NullPool)
    try:
        async with engine.connect() as conn:
            await conn.execute(
                text("SELECT set_config('app.rmp_is_admin', :admin, true)"),
                {"admin": "true" if admin else "false"},
            )
            if advertiser_ids:
                await conn.execute(
                    text(
                        "SELECT set_config('app.rmp_scope_advertiser_ids', :ids, true)"
                    ),
                    {"ids": advertiser_ids},
                )
            # No commit — keep scope alive
            result = await conn.execute(text(
                f"UPDATE {table} SET {set_clause} WHERE id = '{where_id}'"
            ))
            await conn.commit()
            return result.rowcount
    finally:
        await engine.dispose()
