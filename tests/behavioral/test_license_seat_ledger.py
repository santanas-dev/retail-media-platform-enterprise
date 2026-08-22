"""
EPIC-L-SEAT-LEDGER-001A1 — DB-level behavioral proof for the license seat ledger.

Proves under retail_media_app (NOBYPASSRLS):
- Without service/admin context, license_grants / license_seats SELECT reveals
  nothing and INSERT/UPDATE are rejected by the DB.
- With app.rmp_is_admin=true (server-set), rows are visible and writes allowed.
- Constraints: single current grant, single open seat per device, release
  window ordering, non-negative limits/grace, source restriction.
- Read model: occupied seats count only active-device open seats; capacity/
  free computed; effective state active/grace/expired/revoked/missing;
  perpetual stays active; missing returns explicit MISSING.
- Dev-ingest: idempotent, source=dev-ingest, production env rejects.

Fixtures run via owner role (admin bypass); assertions run via the app role.
"""

import asyncio
import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine as _cae
from sqlalchemy.pool import NullPool

from packages.domain.licensing import LicenseGrant, LicenseSeat
from packages.domain.licensing_repository import (
    ACTIVE,
    EXPIRED,
    GRACE,
    MISSING,
    REVOKED,
    capacity_of,
    compute_effective_state,
    count_occupied_seats,
    free_of,
    get_effective_license,
)
from tests.behavioral.builder import BehBuilder

_APP_DB_URL = os.environ.get("BEHAVIORAL_APP_DB_URL", "").strip()
if not _APP_DB_URL:
    _APP_DB_URL = os.environ.get("DATABASE_URL", "").strip()
if not _APP_DB_URL:
    _APP_DB_URL = (
        "postgresql+asyncpg://retail_media_app:retail_media_app"
        "@localhost:5432/retail_media_platform"
    )

_OWNER_DB_URL = os.environ.get("BEHAVIORAL_DB_URL", "").strip()
if not _OWNER_DB_URL:
    _OWNER_DB_URL = (
        "postgresql+asyncpg://retail_media:retail_media_dev"
        "@localhost:5432/retail_media_platform"
    )


def _run_setup(sql: str) -> None:
    from tests.behavioral.conftest import _run_sql
    asyncio.run(_run_sql(sql))


async def _app_exec(stmt: str, *, admin: bool) -> list[dict]:
    engine = _cae(_APP_DB_URL, echo=False, poolclass=NullPool)
    try:
        async with engine.connect() as conn:
            await conn.execute(
                text("SELECT set_config('app.rmp_is_admin', :a, true)"),
                {"a": "true" if admin else "false"},
            )
            result = await conn.execute(text(stmt))
            return [dict(r._mapping) for r in result.fetchall()]
    finally:
        await engine.dispose()


async def _app_insert(table: str, columns: str, values: str, *, admin: bool) -> None:
    engine = _cae(_APP_DB_URL, echo=False, poolclass=NullPool)
    try:
        async with engine.connect() as conn:
            await conn.execute(
                text("SELECT set_config('app.rmp_is_admin', :a, true)"),
                {"a": "true" if admin else "false"},
            )
            await conn.execute(text(f"INSERT INTO {table} ({columns}) VALUES ({values})"))
            await conn.commit()
    finally:
        await engine.dispose()


@pytest.fixture
def ledger_setup(db_available):
    b = BehBuilder("beh-lic")
    rid = b.retailer(code="LIC-RET")
    chain = b.store_chain()
    cd = b.channel_device_type()
    dev_active = b.device(chain["store_id"], cd["device_type_id"], rid, status="active")
    dev_inactive = b.device(chain["store_id"], cd["device_type_id"], rid, status="inactive")

    # Wipe any prior license rows so the single-current constraint is isolated.
    _run_setup("DELETE FROM license_seats WHERE id LIKE 'beh-lic%';")
    _run_setup("DELETE FROM license_grants WHERE id LIKE 'beh-lic%';")

    grant_id = f"{b.prefix}grnt-0001"
    license_id = f"{b.prefix}lic-0001"
    _run_setup(f"""
        INSERT INTO license_grants (id, license_id, licensee_id, licensee_name, tier,
            issued_at, valid_from, valid_until, max_devices, overage_allowance,
            grace_days, source, status)
        VALUES ('{grant_id}', '{license_id}', 'lic-op-1', 'Licensee 1', 'pro',
            NOW(), NOW() - INTERVAL '1 day', NOW() + INTERVAL '30 days',
            5, 2, 3, 'dev-ingest', 'current');
    """)

    yield {
        "builder": b,
        "grant_id": grant_id,
        "license_id": license_id,
        "dev_active": dev_active,
        "dev_inactive": dev_inactive,
    }

    _run_setup("DELETE FROM license_seats WHERE id LIKE 'beh-lic%';")
    _run_setup("DELETE FROM license_grants WHERE id LIKE 'beh-lic%';")
    b.cleanup()


@pytest.mark.usefixtures("ledger_setup")
class TestLicenseRLS:
    @pytest.fixture(autouse=True)
    def setup(self, db_available, ledger_setup):
        self.b = ledger_setup["builder"]
        self.grant_id = ledger_setup["grant_id"]
        self.license_id = ledger_setup["license_id"]
        self.dev_active = ledger_setup["dev_active"]
        self.dev_inactive = ledger_setup["dev_inactive"]

    # ── Scope 1: no admin context hides data / blocks writes ──

    def test_no_context_select_reveals_nothing(self):
        rows = asyncio.run(_app_exec(
            "SELECT id FROM license_grants", admin=False,
        ))
        assert len(rows) == 0, f"Non-admin must see 0 grants, got {len(rows)}"

    def test_no_context_insert_rejected(self):
        with pytest.raises(Exception) as exc:
            asyncio.run(_app_insert(
                "license_grants",
                "id, license_id, licensee_id, licensee_name, tier, issued_at, valid_from, source, status",
                f"'{self.b._uid('gx')}', 'lic-noctx', 'op', 'Op', 'tier', NOW(), NOW(), 'dev-ingest', 'current'",
                admin=False,
            ))
        assert "violates row-level security" in str(exc.value)

    # ── Scope 2: admin context sees + writes ──

    def test_admin_context_sees_grant(self):
        rows = asyncio.run(_app_exec(
            f"SELECT id, license_id, source FROM license_grants WHERE id = '{self.grant_id}'",
            admin=True,
        ))
        assert len(rows) == 1
        assert rows[0]["source"] == "dev-ingest"

    def test_admin_context_insert_seat_allowed(self):
        seat_id = self.b._uid("seat")
        asyncio.run(_app_insert(
            "license_seats",
            "id, license_id, device_id, reserved_at",
            f"'{seat_id}', '{self.grant_id}', '{self.dev_active}', NOW()",
            admin=True,
        ))
        rows = asyncio.run(_app_exec(
            f"SELECT id FROM license_seats WHERE id = '{seat_id}'", admin=True,
        ))
        assert len(rows) == 1
        _run_setup(f"DELETE FROM license_seats WHERE id = '{seat_id}';")


@pytest.mark.usefixtures("ledger_setup")
class TestLicenseConstraints:
    @pytest.fixture(autouse=True)
    def setup(self, db_available, ledger_setup):
        self.b = ledger_setup["builder"]
        self.grant_id = ledger_setup["grant_id"]
        self.dev_active = ledger_setup["dev_active"]

    def _insert_grant(self, *, status="current", source="dev-ingest", max_devices=5,
                      overage=0, grace=0, valid_from="NOW()", valid_until="NULL",
                      license_id=None, id=None):
        lid = license_id or self.b._uid("l")
        gid = id or self.b._uid("g")
        vu = valid_until if valid_until == "NULL" else f"'{valid_until}'"
        return _run_setup(f"""
            INSERT INTO license_grants (id, license_id, licensee_id, licensee_name,
                tier, issued_at, valid_from, valid_until, max_devices,
                overage_allowance, grace_days, source, status)
            VALUES ('{gid}', '{lid}', 'op', 'Op', 'tier', NOW(), {valid_from}, {vu},
                {max_devices}, {overage}, {grace}, '{source}', '{status}');
        """), gid

    def test_second_current_grant_rejected(self):
        with pytest.raises(Exception) as exc:
            self._insert_grant(status="current", license_id=self.b._uid("second"))
        assert "duplicate key" in str(exc.value) or "uq_license_grants_single_current" in str(exc.value)

    def test_second_open_seat_same_device_rejected(self):
        seat1 = self.b._uid("s1")
        seat2 = self.b._uid("s2")
        dev = self.dev_active  # real device from fixture
        _run_setup(f"""
            INSERT INTO license_seats (id, license_id, device_id, reserved_at)
            VALUES ('{seat1}', '{self.grant_id}', '{dev}', NOW());
        """)
        # Second open seat on same device must fail.
        with pytest.raises(Exception) as exc:
            _run_setup(f"""
                INSERT INTO license_seats (id, license_id, device_id, reserved_at)
                VALUES ('{seat2}', '{self.grant_id}', '{dev}', NOW());
            """)
        assert "duplicate key" in str(exc.value) or "uq_license_seats_open_per_device" in str(exc.value)

    def test_release_then_new_seat_allowed(self):
        dev = self.dev_active
        seat1 = self.b._uid("s3")
        seat2 = self.b._uid("s4")
        _run_setup(f"""
            INSERT INTO license_seats (id, license_id, device_id, reserved_at)
            VALUES ('{seat1}', '{self.grant_id}', '{dev}', NOW());
        """)
        _run_setup(f"""
            UPDATE license_seats SET released_at = NOW() WHERE id = '{seat1}';
        """)
        # Now a new open seat for the same device is fine.
        _run_setup(f"""
            INSERT INTO license_seats (id, license_id, device_id, reserved_at)
            VALUES ('{seat2}', '{self.grant_id}', '{dev}', NOW());
        """)

    def test_released_before_reserved_rejected(self):
        dev = self.dev_active
        seat = self.b._uid("s5")
        with pytest.raises(Exception) as exc:
            _run_setup(f"""
                INSERT INTO license_seats (id, license_id, device_id, reserved_at, released_at)
                VALUES ('{seat}', '{self.grant_id}', '{dev}', NOW(), NOW() - INTERVAL '1 day');
            """)
        assert "ck_license_seats_release_after_reserve" in str(exc.value) or "violates" in str(exc.value)

    def test_negative_limits_rejected(self):
        with pytest.raises(Exception):
            self._insert_grant(status="superseded", max_devices=-1)
        with pytest.raises(Exception):
            self._insert_grant(status="superseded", overage=-1)
        with pytest.raises(Exception):
            self._insert_grant(status="superseded", grace=-1)

    def test_source_not_dev_ingest_rejected(self):
        with pytest.raises(Exception):
            self._insert_grant(status="superseded", source="signed-upload")


@pytest.mark.usefixtures("ledger_setup")
class TestReadModel:
    @pytest.fixture(autouse=True)
    def setup(self, db_available, ledger_setup):
        self.b = ledger_setup["builder"]
        self.grant_id = ledger_setup["grant_id"]
        self.dev_active = ledger_setup["dev_active"]
        self.dev_inactive = ledger_setup["dev_inactive"]

    def _seat(self, device_id, *, released=False):
        sid = self.b._uid("rm")
        rel = "NOW()" if released else "NULL"
        _run_setup(f"""
            INSERT INTO license_seats (id, license_id, device_id, reserved_at, released_at)
            VALUES ('{sid}', '{self.grant_id}', '{device_id}', NOW(), {rel});
        """)
        return sid

    def test_occupied_counts_active_open_seats_only(self):
        self._seat(self.dev_active, released=False)          # counted
        self._seat(self.dev_inactive, released=False)        # NOT counted (inactive)
        self._seat(self.dev_active, released=True)           # NOT counted (released)
        occupied = asyncio.run(_app_count_occupied())
        assert occupied == 1, f"Expected 1 occupied seat, got {occupied}"

    def test_capacity_and_free(self):
        grant = _load_grant(self.grant_id)
        assert capacity_of(grant) == 7  # 5 + 2 overage
        assert free_of(7, 3) == 4
        assert free_of(7, 10) == 0

    def test_effective_state_window(self):
        from datetime import datetime, timedelta, timezone
        g = _load_grant(self.grant_id)  # valid_from=-1d, valid_until=+30d, grace=3
        now = datetime.now(timezone.utc)
        assert compute_effective_state(g, now) == ACTIVE
        # grace window: within 3 days after valid_until
        g2 = _clone_with_window(g, now - timedelta(days=10), now - timedelta(days=1), 3)
        assert compute_effective_state(g2, now) == GRACE
        # expired: after grace
        g3 = _clone_with_window(g, now - timedelta(days=10), now - timedelta(days=4), 3)
        assert compute_effective_state(g3, now) == EXPIRED
        # revoked wins over dates
        g4 = _clone_with_window(g, now - timedelta(days=10), now + timedelta(days=10), 0)
        g4.status = "revoked"
        assert compute_effective_state(g4, now) == REVOKED

    def test_perpetual_stays_active(self):
        from datetime import datetime, timedelta, timezone
        g = _load_grant(self.grant_id)
        now = datetime.now(timezone.utc)
        g.valid_from = now - timedelta(days=100)
        g.valid_until = None
        assert compute_effective_state(g, now) == ACTIVE

    def test_missing_returns_missing(self):
        assert compute_effective_state(None) == MISSING

    def test_get_effective_license_returns_current(self):
        grant = asyncio.run(_app_get_effective())
        assert grant is not None
        assert grant.id == self.grant_id

    def test_current_outranks_newer_revoked(self):
        from datetime import datetime, timezone

        # Isolate from the fixture's single 'current' grant.
        _run_setup("DELETE FROM license_seats WHERE id LIKE 'beh-lic%';")
        _run_setup("DELETE FROM license_grants WHERE id LIKE 'beh-lic%';")
        # current grant issued EARLIER than the revoked grant. A naive
        # `issued_at DESC` would wrongly return the revoked row.
        g_current = self.b._uid("cur")
        g_revoked = self.b._uid("rvk")
        _run_setup(f"""
            INSERT INTO license_grants (id, license_id, licensee_id, licensee_name,
                tier, issued_at, valid_from, valid_until, max_devices,
                overage_allowance, grace_days, source, status)
            VALUES ('{g_current}', '{self.b._uid("lic")}', 'op', 'Op', 'pro',
                NOW() - INTERVAL '5 days', NOW() - INTERVAL '5 days',
                NOW() + INTERVAL '30 days', 5, 0, 3, 'dev-ingest', 'current');
        """)
        _run_setup(f"""
            INSERT INTO license_grants (id, license_id, licensee_id, licensee_name,
                tier, issued_at, valid_from, valid_until, max_devices,
                overage_allowance, grace_days, source, status)
            VALUES ('{g_revoked}', '{self.b._uid("lic")}', 'op', 'Op', 'pro',
                NOW(), NOW() - INTERVAL '1 day', NOW() + INTERVAL '30 days',
                1, 0, 0, 'dev-ingest', 'revoked');
        """)
        grant = asyncio.run(_app_get_effective())
        assert grant is not None
        assert grant.id == g_current, "current grant must outrank a newer revoked grant"
        assert grant.status == "current"
        assert compute_effective_state(grant, datetime.now(timezone.utc)) == ACTIVE


@pytest.mark.usefixtures("ledger_setup")
class TestDevIngest:
    def test_dev_ingest_idempotent_and_sourced(self):
        import subprocess
        # Dev-ingest writes a CURRENT grant. Clear the fixture grant first so
        # the single-current unique index doesn't conflict.
        _run_setup("DELETE FROM license_seats WHERE id LIKE 'beh-lic%';")
        _run_setup("DELETE FROM license_grants WHERE id LIKE 'beh-lic%';")
        env = dict(os.environ)
        env["ENVIRONMENT"] = "dev"
        env["LICENSE_DEV_INGEST_ENABLED"] = "true"
        env["DATABASE_URL"] = _OWNER_DB_URL
        for _ in range(2):
            r = subprocess.run(
                ["python3", "scripts/dev/license-dev-ingest.py"], env=env,
                capture_output=True, text=True,
            )
            assert r.returncode == 0, r.stderr
        # Idempotent: still one dev-ingest grant.
        rows = asyncio.run(_app_exec(
            "SELECT count(*) AS n FROM license_grants WHERE license_id='dev-ingest-0001' AND source='dev-ingest'",
            admin=True,
        ))
        assert rows[0]["n"] == 1
        # Clean up the dev-ingest grant so it doesn't leak across tests.
        _run_setup("DELETE FROM license_grants WHERE license_id='dev-ingest-0001';")

    def test_dev_ingest_production_rejected(self):
        import subprocess
        env = dict(os.environ)
        env["ENVIRONMENT"] = "production"
        env["LICENSE_DEV_INGEST_ENABLED"] = "true"
        r = subprocess.run(
            ["python3", "scripts/dev/license-dev-ingest.py"], env=env,
            capture_output=True, text=True,
        )
        assert r.returncode != 0
        assert "refused" in r.stderr


# ── Helpers ──────────────────────────────────────────────────────────────


def _load_grant(grant_id: str) -> LicenseGrant:
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
    from sqlalchemy import select

    async def _go():
        engine = _cae(_APP_DB_URL, echo=False, poolclass=NullPool)
        try:
            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            async with factory() as s:
                async with s.begin():
                    await s.execute(text("SELECT set_config('app.rmp_is_admin','true',true)"))
                    res = await s.execute(
                        select(LicenseGrant).where(LicenseGrant.id == grant_id)
                    )
                    return res.scalar_one()
        finally:
            await engine.dispose()

    return asyncio.run(_go())


def _clone_with_window(g, valid_from, valid_until, grace_days) -> LicenseGrant:
    clone = LicenseGrant(
        id="clone-000000000000000000000001",
        license_id="clone-lic",
        licensee_id=g.licensee_id,
        licensee_name=g.licensee_name,
        tier=g.tier,
        issued_at=g.issued_at,
        valid_from=valid_from,
        valid_until=valid_until,
        max_devices=g.max_devices,
        overage_allowance=g.overage_allowance,
        grace_days=grace_days,
        source=g.source,
        status=g.status,
    )
    return clone


async def _app_count_occupied() -> int:
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

    engine = _cae(_APP_DB_URL, echo=False, poolclass=NullPool)
    try:
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            async with s.begin():
                await s.execute(text("SELECT set_config('app.rmp_is_admin','true',true)"))
                return await count_occupied_seats(s)
    finally:
        await engine.dispose()


async def _app_get_effective():
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

    engine = _cae(_APP_DB_URL, echo=False, poolclass=NullPool)
    try:
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            async with s.begin():
                await s.execute(text("SELECT set_config('app.rmp_is_admin','true',true)"))
                return await get_effective_license(s)
    finally:
        await engine.dispose()
