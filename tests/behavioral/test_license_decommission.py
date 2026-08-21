"""EPIC-L-SEAT-LEDGER-001A3 — Behavioral proof for decommission + exact peak.

Proves under retail_media_app (NOBYPASSRLS), against real PostgreSQL:
- onboard → active device + open seat; decommission → inactive + released_at
  + exactly one device_status_history row.
- Repeat decommission is idempotent (no second transition/history/release).
- cap=1: after release a NEW device enrolls through the A2 choke-point.
- expired/revoked/missing license never blocks decommission.
- active device without an open seat → still decommissioned, seat_released=False
  + anomaly surfaced (reconciliation anomaly, not a 500).
- unauthorized role → 403.
- license ledger/device hidden without the service/admin RLS context.
- two concurrent decommissions of one device serialize on the FOR UPDATE row
  lock: one transition, one history row, released_at set exactly once.
- exact monthly peak computed from real DB intervals incl. half-open boundaries.

Fixtures run via owner role (admin bypass); assertions via the app role.
"""

import asyncio
import os
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine as _cae,
)
from sqlalchemy.pool import NullPool

from packages.domain import licensing_service
from packages.domain.licensing_repository import peak_seats_for_month
from packages.security.config import reset_security_config
from packages.security.jwt import create_access_token
from tests.behavioral.builder import BehBuilder
from tests.behavioral.conftest import _run_sql, USER_IDS

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

AUTH_PROVIDER = "local_advertiser"


def _token(user_id: str) -> str:
    return create_access_token(user_id, AUTH_PROVIDER)


def _auth(token: str):
    return {"Authorization": f"Bearer {token}"}


async def _app_query(stmt: str, *, admin: bool) -> list[dict]:
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


def _q(stmt: str, *, admin: bool = True) -> list[dict]:
    return asyncio.run(_app_query(stmt, admin=admin))


def _setup(sql: str) -> None:
    asyncio.run(_run_sql(sql))


async def _peak_app(license_id: str, year: int, month: int) -> int:
    engine = _cae(_APP_DB_URL, echo=False, poolclass=NullPool)
    try:
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            async with s.begin():
                await licensing_service.set_licensing_admin_context(s)
                return await peak_seats_for_month(
                    s, license_id=license_id, year=year, month=month,
                )
    finally:
        await engine.dispose()


def _peak(license_id: str, year: int, month: int) -> int:
    return asyncio.run(_peak_app(license_id, year, month))


@pytest.fixture
def client(app, db_available, test_users):
    reset_security_config()
    return TestClient(app)


@pytest.fixture
def decommission_setup(db_available, test_users):
    b = BehBuilder("beh-a3")
    rid = b.retailer(code="A3-RET")
    chain = b.store_chain()
    cd = b.channel_device_type()

    # Wipe prior A3 license/device/history rows so each test starts clean.
    _setup("DELETE FROM device_status_history WHERE physical_device_id IN "
           "(SELECT id FROM physical_devices WHERE retailer_id LIKE 'beh-a3%');")
    _setup("DELETE FROM license_seats WHERE id LIKE 'beh-a3%' OR license_id LIKE 'beh-a3%';")
    _setup("DELETE FROM license_grants WHERE id LIKE 'beh-a3%' OR license_id LIKE 'beh-a3%';")

    yield {
        "builder": b,
        "retailer_id": rid,
        "store_id": chain["store_id"],
        "device_type_id": cd["device_type_id"],
    }

    _setup("DELETE FROM device_status_history WHERE physical_device_id IN "
           "(SELECT id FROM physical_devices WHERE retailer_id LIKE 'beh-a3%');")
    _setup("DELETE FROM license_seats WHERE id LIKE 'beh-a3%' OR license_id LIKE 'beh-a3%';")
    _setup("DELETE FROM license_grants WHERE id LIKE 'beh-a3%' OR license_id LIKE 'beh-a3%';")
    _setup("DELETE FROM device_onboarding_codes WHERE retailer_id LIKE 'beh-a3%' OR created_by LIKE 'beh-a3%';")
    _setup("DELETE FROM physical_devices WHERE id LIKE 'beh-a3%' OR retailer_id LIKE 'beh-a3%';")
    b.cleanup()


class _DecomBase:
    @pytest.fixture(autouse=True)
    def _setup(self, client, db_available, decommission_setup):
        reset_security_config()
        self.client = client
        self.b = decommission_setup["builder"]
        self.retailer_id = decommission_setup["retailer_id"]
        self.store_id = decommission_setup["store_id"]
        self.device_type_id = decommission_setup["device_type_id"]
        self.token_admin = _token(USER_IDS["readonly"])  # system_admin
        self.token_adv = _token(USER_IDS["advertiser"])  # no device perms

    def _grant(self, *, max_devices=10, overage=0, grace=0,
               valid_until="NULL", status="current",
               valid_from="NOW() - INTERVAL '1 day'", issued_at="NOW()"):
        gid = self.b._uid("g")
        lid = self.b._uid("lic")
        _setup(f"""
            INSERT INTO license_grants (id, license_id, licensee_id, licensee_name,
                tier, issued_at, valid_from, valid_until, max_devices,
                overage_allowance, grace_days, source, status)
            VALUES ('{gid}', '{lid}', 'a3-op', 'A3 Operator', 'pro',
                {issued_at}, {valid_from}, {valid_until}, {max_devices}, {overage}, {grace},
                'dev-ingest', '{status}');
        """)
        return gid

    def _create_code(self):
        resp = self.client.post(
            "/api/v1/identity/device-codes",
            json={
                "retailer_id": self.retailer_id,
                "store_id": self.store_id,
                "device_type_id": self.device_type_id,
                "ttl_hours": 24,
            },
            headers=_auth(self.token_admin),
        )
        assert resp.status_code == 201, f"code create failed: {resp.text[:200]}"
        return resp.json()["code"]

    def _onboard(self, code, fp):
        return self.client.post(
            "/api/v1/device/onboard",
            json={"device_code": code, "hardware_fingerprint": fp},
        )

    def _decommission(self, device_id, reason="", token=None):
        return self.client.post(
            f"/api/v1/identity/devices/{device_id}/decommission",
            json={"reason": reason},
            headers=_auth(token or self.token_admin),
        )

    def _open_seats(self) -> int:
        rows = _q("SELECT count(*) AS n FROM license_seats WHERE released_at IS NULL")
        return rows[0]["n"]

    def _seat_row(self, device_id):
        return _q(f"SELECT released_at, license_id FROM license_seats WHERE device_id='{device_id}'")

    def _history_count(self, device_id) -> int:
        return _q(f"SELECT count(*) AS n FROM device_status_history WHERE physical_device_id='{device_id}'")[0]["n"]

    def _detail(self, resp):
        return resp.json()["detail"]


@pytest.mark.usefixtures("decommission_setup")
class TestDecommissionLifecycle(_DecomBase):
    """SCOPE E behavioral #1–#4, #6 — transition, idempotency, reuse, anomaly."""

    def test_onboard_then_decommission_releases_seat(self):
        self._grant(max_devices=5)
        code = self._create_code()
        resp = self._onboard(code, "a3-fp-life-000000000000001")
        assert resp.status_code == 200, resp.text[:200]
        device_id = resp.json()["device_id"]
        assert self._open_seats() == 1

        dec = self._decommission(device_id, reason="end of life")
        assert dec.status_code == 200, dec.text[:200]
        data = dec.json()
        assert data["status"] == "inactive"
        assert data["seat_released"] is True
        assert data["released_at"] is not None
        assert data["transitioned"] is True
        assert data["anomaly"] is False

        # Device inactive, seat released, exactly one history row.
        assert _q(f"SELECT status FROM physical_devices WHERE id='{device_id}'")[0]["status"] == "inactive"
        seats = self._seat_row(device_id)
        assert len(seats) == 1 and seats[0]["released_at"] is not None
        assert self._history_count(device_id) == 1

        # changed_by recorded in details_json.
        changed = _q(f"SELECT details_json->>'changed_by' AS cb FROM device_status_history WHERE physical_device_id='{device_id}'")[0]["cb"]
        assert changed == USER_IDS["readonly"]

    def test_repeat_decommission_idempotent(self):
        self._grant(max_devices=5)
        code = self._create_code()
        device_id = self._onboard(code, "a3-fp-idem-00000000000001").json()["device_id"]

        r1 = self._decommission(device_id, reason="first")
        assert r1.status_code == 200
        assert r1.json()["transitioned"] is True
        released_at_1 = r1.json()["released_at"]

        r2 = self._decommission(device_id, reason="second")
        assert r2.status_code == 200
        data2 = r2.json()
        assert data2["transitioned"] is False
        assert data2["seat_released"] is False
        assert data2["released_at"] is None

        # released_at unchanged, still one history row.
        seats = self._seat_row(device_id)
        assert seats[0]["released_at"] is not None
        assert self._history_count(device_id) == 1

    def test_cap1_release_then_new_device_enrolls(self):
        self._grant(max_devices=1, overage=0)  # capacity = 1
        code_a = self._create_code()
        dev_a = self._onboard(code_a, "a3-fp-cap-a-00000000000001").json()["device_id"]
        assert self._open_seats() == 1

        # Second enrollment blocked while seat held.
        code_b = self._create_code()
        resp_b = self._onboard(code_b, "a3-fp-cap-b-00000000000001")
        assert resp_b.status_code == 409
        assert self._detail(resp_b)["code"] == "LICENSE_SEAT_LIMIT"

        # Decommission A → seat freed → B enrolls through the A2 choke-point.
        assert self._decommission(dev_a, reason="reuse").status_code == 200
        assert self._open_seats() == 0

        resp_b2 = self._onboard(code_b, "a3-fp-cap-b-00000000000001")
        assert resp_b2.status_code == 200, resp_b2.text[:200]
        assert self._open_seats() == 1

    def test_active_without_seat_decommission_anomaly(self):
        self._grant(max_devices=5)
        dev = self.b.device(self.store_id, self.device_type_id, self.retailer_id, status="active")
        # No seat inserted → active device with no open seat.

        dec = self._decommission(dev, reason="anomaly")
        assert dec.status_code == 200, dec.text[:200]
        data = dec.json()
        assert data["status"] == "inactive"
        assert data["seat_released"] is False
        assert data["anomaly"] is True
        assert data["transitioned"] is True

        assert _q(f"SELECT status FROM physical_devices WHERE id='{dev}'")[0]["status"] == "inactive"
        assert self._history_count(dev) == 1


@pytest.mark.usefixtures("decommission_setup")
class TestDecommissionSoftEnforcement(_DecomBase):
    """SCOPE C + behavioral #5, #7, #8 — softness, authorization, RLS."""

    def test_expired_revoked_license_does_not_block_decommission(self):
        gid = self._grant(max_devices=5)
        code = self._create_code()
        device_id = self._onboard(code, "a3-fp-soft-00000000000001").json()["device_id"]

        # Revoke the license — decommission must still succeed.
        _setup(f"UPDATE license_grants SET status='revoked' WHERE id='{gid}';")
        dec = self._decommission(device_id, reason="soft-revoked")
        assert dec.status_code == 200, dec.text[:200]
        assert dec.json()["seat_released"] is True

    def test_missing_license_does_not_block_decommission(self):
        # No grant at all — decommission is device lifecycle, not enrollment.
        dev = self.b.device(self.store_id, self.device_type_id, self.retailer_id, status="active")
        dec = self._decommission(dev, reason="soft-missing")
        assert dec.status_code == 200, dec.text[:200]
        assert dec.json()["status"] == "inactive"

    def test_unauthorized_role_403(self):
        self._grant(max_devices=5)
        code = self._create_code()
        device_id = self._onboard(code, "a3-fp-auth-00000000000001").json()["device_id"]

        resp = self._decommission(device_id, reason="nope", token=self.token_adv)
        assert resp.status_code == 403, resp.text[:200]
        # Device still active — nothing changed.
        assert _q(f"SELECT status FROM physical_devices WHERE id='{device_id}'")[0]["status"] == "active"

    def test_ledger_hidden_without_admin_context(self):
        gid = self._grant(max_devices=5)
        dev = self.b.device(self.store_id, self.device_type_id, self.retailer_id, status="active")
        _setup(f"INSERT INTO license_seats (id, license_id, device_id, reserved_at) "
               f"VALUES ('{self.b._uid('seat')}', '{gid}', '{dev}', NOW());")

        # Without admin context the app role sees no seats.
        assert _q("SELECT id FROM license_seats", admin=False) == []
        # With admin context the seat is visible.
        rows = _q(f"SELECT id FROM license_seats WHERE device_id='{dev}'", admin=True)
        assert len(rows) == 1


@pytest.mark.usefixtures("decommission_setup")
class TestDecommissionConcurrencyAndPeak(_DecomBase):
    """SCOPE E behavioral #9, #10 — concurrency + exact peak."""

    def test_concurrent_decommission_single_transition(self):
        gid = self._grant(max_devices=10)
        dev_id = self.b.device(self.store_id, self.device_type_id, self.retailer_id, status="active")
        _setup(f"INSERT INTO license_seats (id, license_id, device_id, reserved_at) "
               f"VALUES ('{self.b._uid('seat')}', '{gid}', '{dev_id}', NOW());")

        now = datetime.now(timezone.utc)
        changed_by = USER_IDS["readonly"]

        async def _run():
            a_lock_acquired = asyncio.Event()
            a_release = asyncio.Event()
            b_started = asyncio.Event()
            outcome = {}

            async def tx_a():
                engine = _cae(_APP_DB_URL, echo=False, poolclass=NullPool)
                try:
                    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
                    async with factory() as s:
                        async with s.begin():
                            res = await licensing_service.decommission_device(
                                s, device_id=dev_id, changed_by=changed_by,
                                reason="conc-a", now=now,
                            )
                            a_lock_acquired.set()
                            await a_release.wait()  # hold the device row lock
                            outcome["a"] = res
                finally:
                    await engine.dispose()

            async def tx_b():
                await a_lock_acquired.wait()
                engine = _cae(_APP_DB_URL, echo=False, poolclass=NullPool)
                try:
                    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
                    async with factory() as s:
                        async with s.begin():
                            b_started.set()
                            return await licensing_service.decommission_device(
                                s, device_id=dev_id, changed_by=changed_by,
                                reason="conc-b", now=now,
                            )
                finally:
                    await engine.dispose()

            a_task = asyncio.create_task(tx_a())
            await a_lock_acquired.wait()
            b_task = asyncio.create_task(tx_b())
            await b_started.wait()

            done, _pending = await asyncio.wait({b_task}, timeout=1.0)
            assert not done, "B must block on the device FOR UPDATE row lock"

            a_release.set()
            await a_task
            result_b = await b_task
            return outcome["a"], result_b

        res_a, res_b = asyncio.run(_run())
        assert res_a is not None and res_b is not None
        assert res_a.transitioned is True and res_a.seat_released is True
        assert res_b.transitioned is False and res_b.seat_released is False

        assert self._history_count(dev_id) == 1
        assert _q(f"SELECT count(*) AS n FROM license_seats WHERE device_id='{dev_id}' AND released_at IS NOT NULL")[0]["n"] == 1

    def test_exact_peak_real_intervals_and_boundaries(self):
        gid = self._grant(max_devices=10)
        year, month = 2026, 8
        d1 = self.b.device(self.store_id, self.device_type_id, self.retailer_id, status="active")
        d2 = self.b.device(self.store_id, self.device_type_id, self.retailer_id, status="active")
        d3 = self.b.device(self.store_id, self.device_type_id, self.retailer_id, status="active")
        d4 = self.b.device(self.store_id, self.device_type_id, self.retailer_id, status="active")

        # Three overlapping Aug intervals → peak 3. A fourth interval ends
        # exactly at month_start (excluded) → does not add to the peak.
        _setup(f"""
            INSERT INTO license_seats (id, license_id, device_id, reserved_at, released_at) VALUES
            ('{self.b._uid('pk')}', '{gid}', '{d1}', '2026-08-01T00:00:00Z', '2026-08-10T00:00:00Z'),
            ('{self.b._uid('pk')}', '{gid}', '{d2}', '2026-08-02T00:00:00Z', '2026-08-11T00:00:00Z'),
            ('{self.b._uid('pk')}', '{gid}', '{d3}', '2026-08-03T00:00:00Z', '2026-08-12T00:00:00Z'),
            ('{self.b._uid('pk')}', '{gid}', '{d4}', '2026-07-20T00:00:00Z', '2026-08-01T00:00:00Z');
        """)
        assert _peak(gid, year, month) == 3

    def test_exact_peak_open_interval_and_next_month_reserve(self):
        gid = self._grant(max_devices=10)
        year, month = 2026, 8
        d1 = self.b.device(self.store_id, self.device_type_id, self.retailer_id, status="active")
        d2 = self.b.device(self.store_id, self.device_type_id, self.retailer_id, status="active")

        # One open interval (released_at NULL) + one interval reserved exactly
        # at next_month_start (excluded) → peak stays 1.
        _setup(f"""
            INSERT INTO license_seats (id, license_id, device_id, reserved_at, released_at) VALUES
            ('{self.b._uid('pk')}', '{gid}', '{d1}', '2026-08-10T00:00:00Z', NULL),
            ('{self.b._uid('pk')}', '{gid}', '{d2}', '2026-09-01T00:00:00Z', '2026-09-10T00:00:00Z');
        """)
        assert _peak(gid, year, month) == 1

    def test_exact_peak_release_reserve_same_instant_no_false_peak(self):
        gid = self._grant(max_devices=10)
        year, month = 2026, 8
        d1 = self.b.device(self.store_id, self.device_type_id, self.retailer_id, status="active")
        d2 = self.b.device(self.store_id, self.device_type_id, self.retailer_id, status="active")

        # Seat A released at T, seat B reserved at the same T — the seat passes
        # hands, so the peak must be 1, not 2.
        _setup(f"""
            INSERT INTO license_seats (id, license_id, device_id, reserved_at, released_at) VALUES
            ('{self.b._uid('pk')}', '{gid}', '{d1}', '2026-08-01T00:00:00Z', '2026-08-15T12:00:00Z'),
            ('{self.b._uid('pk')}', '{gid}', '{d2}', '2026-08-15T12:00:00Z', '2026-08-20T00:00:00Z');
        """)
        assert _peak(gid, year, month) == 1

    def test_exact_peak_empty_month(self):
        gid = self._grant(max_devices=10)
        assert _peak(gid, 2026, 8) == 0
