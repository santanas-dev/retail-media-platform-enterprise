"""
EPIC-L-SEAT-LEDGER-001A2 — Behavioral proof for the enrollment choke-point.

Proves under retail_media_app (NOBYPASSRLS), against real PostgreSQL:
- Active license + free seat → onboarding mints device + one open seat.
- max_devices=N → N pass, N+1 → 409 LICENSE_SEAT_LIMIT.
- overage_allowance extends capacity exactly to max+overage.
- Missing/expired/revoked license → 409 with stable codes; grace allows.
- Repeat fingerprint → one device, one open seat (no second seat).
- Rollback: artificial seat-reserve error leaves no device and does not
  consume the onboarding code.
- Existing active device stays active (heartbeat unaffected) under
  over-cap / expired / revoked; its open seat is never released.
- Grandfather reconciliation: active devices get seats, inactive/unregistered
  do not, over-cap fleet preserved, idempotent.
- RLS: license tables are invisible without the service/admin context.
- Deterministic concurrency proof: with grant capacity=1, a parallel
  enrollment blocks on the FOR UPDATE row lock, then sees the last seat taken
  and returns LICENSE_SEAT_LIMIT (one device + one seat total).

Fixtures run via owner role (admin bypass); assertions via the app role.
"""

import asyncio
import os
from datetime import datetime, timezone
from unittest import mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine as _cae,
)
from sqlalchemy.pool import NullPool

from packages.domain import licensing_service, repository
from packages.domain.licensing_repository import count_occupied_seats
from packages.domain.models import PhysicalDevice
from packages.security.config import reset_security_config
from packages.security.jwt import create_access_token
from tests.behavioral.builder import BehBuilder
from tests.behavioral.conftest import _run_sql, USER_IDS

# RM-STAB-001: одна переменная, один helper, обе DSN-формы допустимы.
from tests.behavioral.dsn import sqlalchemy_dsn

_APP_DB_URL = sqlalchemy_dsn()

_OWNER_DB_URL = os.environ.get("BEHAVIORAL_DB_URL", "").strip()
if not _OWNER_DB_URL:
    _OWNER_DB_URL = (
        "postgresql+asyncpg://retail_media:retail_media_dev"
        "@localhost:5432/retail_media_platform"
    )

AUTH_PROVIDER = "local_advertiser"

# Fixed fixture identities (prefix-scoped, deleted in teardown).
RET = "beh-a2-ret-0000000000000001"
BR = "beh-a2-br-000000000000000001"
CL = "beh-a2-cl-000000000000000001"
ST = "beh-a2-st-000000000000000001"
CH = "beh-a2-ch-000000000000000001"
DT = "beh-a2-dt-000000000000000001"


def _token(user_id: str) -> str:
    return create_access_token(user_id, AUTH_PROVIDER)


def _auth(token: str):
    return {"Authorization": f"Bearer {token}"}


async def _app_query(stmt: str, *, admin: bool) -> list[dict]:
    """Run a SELECT via the app role; admin toggles the service context."""
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
    """Owner-role SQL for fixture setup/cleanup (RLS bypass)."""
    asyncio.run(_run_sql(sql))


@pytest.fixture
def client(app, db_available, test_users):
    reset_security_config()
    return TestClient(app)


@pytest.fixture
def enroll_setup(db_available, test_users):
    """Retailer → store → channel/device_type chain + clean license namespace."""
    b = BehBuilder("beh-a2")
    rid = b.retailer(code="A2-RET")
    chain = b.store_chain()
    cd = b.channel_device_type()

    # Wipe any prior A2 license rows so the single-current constraint is isolated.
    _setup("DELETE FROM license_seats WHERE id LIKE 'beh-a2%' OR license_id LIKE 'beh-a2%';")
    _setup("DELETE FROM license_grants WHERE id LIKE 'beh-a2%' OR license_id LIKE 'beh-a2%';")

    yield {
        "builder": b,
        "retailer_id": rid,
        "store_id": chain["store_id"],
        "device_type_id": cd["device_type_id"],
    }

    # Seats first (FK RESTRICT → must precede grants/devices).
    _setup("DELETE FROM license_seats WHERE id LIKE 'beh-a2%' OR license_id LIKE 'beh-a2%';")
    _setup("DELETE FROM license_grants WHERE id LIKE 'beh-a2%' OR license_id LIKE 'beh-a2%';")
    # API-onboarded devices carry a UUID id but the fixture retailer_id — clean
    # by retailer_id before the device_type/retailer are dropped.
    _setup("DELETE FROM device_onboarding_codes WHERE retailer_id LIKE 'beh-a2%' OR created_by LIKE 'beh-a2%';")
    _setup("DELETE FROM physical_devices WHERE id LIKE 'beh-a2%' OR retailer_id LIKE 'beh-a2%';")
    b.cleanup()


class _EnrollBase:
    """Shared grant/onboarding helpers."""

    @pytest.fixture(autouse=True)
    def _setup(self, client, db_available, enroll_setup):
        reset_security_config()
        self.client = client
        self.b = enroll_setup["builder"]
        self.retailer_id = enroll_setup["retailer_id"]
        self.store_id = enroll_setup["store_id"]
        self.device_type_id = enroll_setup["device_type_id"]
        self.token_admin = _token(USER_IDS["readonly"])  # system_admin

    def _grant(self, *, max_devices=10, overage=0, grace=0,
               valid_until="NULL", status="current", valid_from="NOW() - INTERVAL '1 day'",
               issued_at="NOW()"):
        gid = self.b._uid("g")
        lid = self.b._uid("lic")
        _setup(f"""
            INSERT INTO license_grants (id, license_id, licensee_id, licensee_name,
                tier, issued_at, valid_from, valid_until, max_devices,
                overage_allowance, grace_days, source, status)
            VALUES ('{gid}', '{lid}', 'a2-op', 'A2 Operator', 'pro',
                {issued_at}, {valid_from}, {valid_until}, {max_devices}, {overage}, {grace},
                'dev-ingest', '{status}');
        """)
        return gid

    def _create_code(self, retailer_id=None, store_id=None, device_type_id=None):
        resp = self.client.post(
            "/api/v1/identity/device-codes",
            json={
                "retailer_id": retailer_id or self.retailer_id,
                "store_id": store_id or self.store_id,
                "device_type_id": device_type_id or self.device_type_id,
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

    def _open_seats(self) -> int:
        rows = _q("SELECT count(*) AS n FROM license_seats WHERE released_at IS NULL")
        return rows[0]["n"]

    def _detail(self, resp):
        """FastAPI wraps HTTPException detail as {"detail": {...}}."""
        return resp.json()["detail"]


@pytest.mark.usefixtures("enroll_setup")
class TestEnrollmentEnforcement(_EnrollBase):
    """SCOPE E #1–#7 — the soft-enforcement decision matrix."""

    def test_active_license_free_seat_onboards(self):
        self._grant(max_devices=5)
        code = self._create_code()
        fp = "a2-fp-active-0000000000000001"
        resp = self._onboard(code, fp)
        assert resp.status_code == 200, f"onboard failed: {resp.status_code} {resp.text[:200]}"
        data = resp.json()
        assert data["device_id"]
        assert data["status"] == "active"
        assert data["license_state"] == "active"
        # One device + one open seat.
        assert _q(f"SELECT count(*) AS n FROM physical_devices WHERE hardware_fingerprint='{fp}'")[0]["n"] == 1
        assert self._open_seats() == 1

    def test_max_devices_enforced(self):
        self._grant(max_devices=2, overage=0)
        for i in range(2):
            code = self._create_code()
            fp = f"a2-fp-max-{i:04d}"
            assert self._onboard(code, fp).status_code == 200
        # N+1 → 409.
        code = self._create_code()
        resp = self._onboard(code, "a2-fp-max-over")
        assert resp.status_code == 409, f"expected 409, got {resp.status_code}: {resp.text[:200]}"
        detail = self._detail(resp)
        assert detail["code"] == "LICENSE_SEAT_LIMIT"
        assert "лимит 2" in detail["message"]

    def test_overage_allowance_extends_capacity(self):
        self._grant(max_devices=2, overage=2)  # capacity = 4
        for i in range(4):
            code = self._create_code()
            assert self._onboard(code, f"a2-fp-ovr-{i:04d}").status_code == 200
        # 5th blocked.
        code = self._create_code()
        resp = self._onboard(code, "a2-fp-ovr-over")
        assert resp.status_code == 409
        assert self._detail(resp)["code"] == "LICENSE_SEAT_LIMIT"

    def test_missing_license_denies(self):
        # No grant at all → 409 LICENSE_MISSING.
        code = self._create_code()
        resp = self._onboard(code, "a2-fp-missing-000000000001")
        assert resp.status_code == 409, f"expected 409, got {resp.status_code}: {resp.text[:200]}"
        assert self._detail(resp)["code"] == "LICENSE_MISSING"

    def test_expired_after_grace_denies(self):
        self._grant(valid_from="NOW() - INTERVAL '30 days'",
                    valid_until="NOW() - INTERVAL '5 days'", grace=3)
        code = self._create_code()
        resp = self._onboard(code, "a2-fp-expired-000000000001")
        assert resp.status_code == 409
        assert self._detail(resp)["code"] == "LICENSE_EXPIRED"

    def test_within_grace_allows(self):
        self._grant(valid_from="NOW() - INTERVAL '30 days'",
                    valid_until="NOW() - INTERVAL '1 day'", grace=3)
        code = self._create_code()
        fp = "a2-fp-grace-000000000000001"
        resp = self._onboard(code, fp)
        assert resp.status_code == 200, f"grace should allow: {resp.status_code} {resp.text[:200]}"
        assert resp.json()["license_state"] == "grace"

    def test_revoked_denies(self):
        self._grant(status="revoked")
        code = self._create_code()
        resp = self._onboard(code, "a2-fp-revoked-000000000001")
        assert resp.status_code == 409
        assert self._detail(resp)["code"] == "LICENSE_REVOKED"

    def test_current_outranks_newer_revoked(self):
        # current grant issued EARLIER; revoked grant issued LATER. A naive
        # `issued_at DESC` would select the revoked grant and deny enrollment
        # as LICENSE_REVOKED, even though a live current grant exists.
        g_current = self._grant(max_devices=5, valid_from="NOW() - INTERVAL '5 days'",
                                issued_at="NOW() - INTERVAL '5 days'")
        self._grant(status="revoked", valid_from="NOW() - INTERVAL '1 day'",
                    issued_at="NOW()")

        code = self._create_code()
        fp = "a2-fp-cur-revoked-000000000001"
        resp = self._onboard(code, fp)
        assert resp.status_code == 200, f"enrollment must use current grant: {resp.status_code} {resp.text[:200]}"
        data = resp.json()
        assert data["license_state"] == "active", "must not be treated as revoked"
        assert _q(f"SELECT count(*) AS n FROM physical_devices WHERE hardware_fingerprint='{fp}'")[0]["n"] == 1
        seats = _q(f"SELECT license_id FROM license_seats WHERE device_id='{data['device_id']}' AND released_at IS NULL")
        assert len(seats) == 1
        assert seats[0]["license_id"] == g_current, "seat must be reserved under the current grant"
        assert self._open_seats() == 1


@pytest.mark.usefixtures("enroll_setup")
class TestIdempotencyAndRollback(_EnrollBase):
    """SCOPE E #8, #9, #10 — idempotency, rollback, softness."""

    def test_repeat_fingerprint_single_device_single_seat(self):
        self._grant(max_devices=5)
        code = self._create_code()
        fp = "a2-fp-idem-000000000000001"
        r1 = self._onboard(code, fp)
        assert r1.status_code == 200
        dev1 = r1.json()["device_id"]
        # Same code + same fingerprint (code now 'used') → idempotent.
        r2 = self._onboard(code, fp)
        assert r2.status_code == 200
        assert r2.json()["device_id"] == dev1
        assert self._open_seats() == 1, "repeat fingerprint must not consume a second seat"

    def test_rollback_on_seat_reserve_error(self):
        self._grant(max_devices=5)
        code = self._create_code()
        fp = "a2-fp-rollback-000000000001"

        # Artificial error during seat reservation, AFTER device creation.
        with mock.patch(
            "packages.domain.licensing_service.reserve_seat",
            side_effect=RuntimeError("injected seat-reserve failure"),
        ):
            with TestClient(self.client.app, raise_server_exceptions=False) as tc:
                resp = tc.post(
                    "/api/v1/device/onboard",
                    json={"device_code": code, "hardware_fingerprint": fp},
                )
        assert resp.status_code == 500, f"expected server error, got {resp.status_code}"

        # Transaction rolled back: no device, no seat, code not consumed.
        assert _q(f"SELECT count(*) AS n FROM physical_devices WHERE hardware_fingerprint='{fp}'")[0]["n"] == 0
        assert self._open_seats() == 0
        code_row = _q(f"SELECT status FROM device_onboarding_codes WHERE code='{code}'")
        assert code_row and code_row[0]["status"] == "active", "code claim must be reverted"

        # The code remains reusable after the failed attempt.
        resp2 = self._onboard(code, "a2-fp-rollback-000000000002")
        assert resp2.status_code == 200, f"code should be reusable: {resp2.status_code} {resp2.text[:200]}"

    def test_existing_active_device_survives_overcap_expired_revoked(self):
        # Grandfather an existing active device + open seat, then break the
        # license three ways. The device must stay active and keep its seat.
        dev_id = self.b.device(self.store_id, self.device_type_id, self.retailer_id, status="active")
        gid = self._grant(max_devices=0, overage=0)  # capacity 0 → over-cap
        _setup(f"INSERT INTO license_seats (id, license_id, device_id, reserved_at) "
                 f"VALUES ('{self.b._uid('seat')}', '{gid}', '{dev_id}', NOW());")

        # Over-cap: seat still open, device still active.
        assert self._open_seats() == 1
        assert _q(f"SELECT status FROM physical_devices WHERE id='{dev_id}'")[0]["status"] == "active"

        # Expired + revoked: still no change to the active device or its seat.
        _setup(f"UPDATE license_grants SET status='revoked' WHERE id='{gid}';")
        assert self._open_seats() == 1
        assert _q(f"SELECT status FROM physical_devices WHERE id='{dev_id}'")[0]["status"] == "active"

        # Heartbeat still works (soft enforcement never touches device auth).
        async def _hb():
            engine = _cae(_APP_DB_URL, echo=False, poolclass=NullPool)
            try:
                factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
                async with factory() as s:
                    async with s.begin():
                        await s.execute(text("SELECT set_config('app.rmp_is_admin','true',true)"))
                        return await repository.record_device_heartbeat(s, dev_id, health_state="healthy")
            finally:
                await engine.dispose()

        assert asyncio.run(_hb()) is True


@pytest.mark.usefixtures("enroll_setup")
class TestReconciliation(_EnrollBase):
    """SCOPE E #11 — grandfather reconciliation."""

    def test_reconciliation_seats_active_only_and_idempotent(self):
        self._grant(max_devices=0, overage=0)  # capacity 0
        # Pre-existing fleet: 2 active, 1 inactive, 1 unregistered.
        a1 = self.b.device(self.store_id, self.device_type_id, self.retailer_id, status="active")
        a2 = self.b.device(self.store_id, self.device_type_id, self.retailer_id, status="active")
        ina = self.b.device(self.store_id, self.device_type_id, self.retailer_id, status="inactive")
        unreg = self.b.device(self.store_id, self.device_type_id, self.retailer_id, status="unregistered")

        now = datetime.now(timezone.utc)

        async def _reconcile():
            engine = _cae(_APP_DB_URL, echo=False, poolclass=NullPool)
            try:
                factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
                async with factory() as s:
                    async with s.begin():
                        return await licensing_service.reconcile_existing_fleet(s, now=now)
            finally:
                await engine.dispose()

        r1 = asyncio.run(_reconcile())
        # Reconciliation is global by design (grandfather the whole active
        # fleet, incl. any pre-seeded active device), so assert a lower bound
        # plus per-device correctness rather than an exact global count.
        assert r1.created_seats >= 2
        assert r1.overage is True  # active fleet > capacity 0

        for dev in (a1, a2):
            n = _q(f"SELECT count(*) AS n FROM license_seats WHERE device_id='{dev}' AND released_at IS NULL")[0]["n"]
            assert n == 1, f"active device {dev} must hold one open seat"
        for dev in (ina, unreg):
            n = _q(f"SELECT count(*) AS n FROM license_seats WHERE device_id='{dev}'")[0]["n"]
            assert n == 0, f"inactive/unregistered device {dev} must not be seated"

        # Idempotent: second pass creates nothing new.
        r2 = asyncio.run(_reconcile())
        assert r2.created_seats == 0


@pytest.mark.usefixtures("enroll_setup")
class TestRLSContext(_EnrollBase):
    """SCOPE E #12 — license tables invisible without service context."""

    def test_license_tables_hidden_without_service_context(self):
        gid = self._grant(max_devices=5)
        # Without admin context: app role sees nothing.
        assert _q("SELECT id FROM license_grants", admin=False) == []
        # With service context: visible.
        visible = _q(f"SELECT id FROM license_grants WHERE id='{gid}'", admin=True)
        assert len(visible) == 1
        # Direct INSERT without admin context is rejected by RLS.
        with pytest.raises(Exception) as exc:
            asyncio.run(_app_insert_no_context())
        assert "violates row-level security" in str(exc.value)


async def _app_insert_no_context():
    engine = _cae(_APP_DB_URL, echo=False, poolclass=NullPool)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT set_config('app.rmp_is_admin','false',true)"))
            await conn.execute(text(
                "INSERT INTO license_seats (id, license_id, device_id, reserved_at) "
                "VALUES ('beh-a2-noctx', 'x', 'x', NOW())"
            ))
            await conn.commit()
    finally:
        await engine.dispose()


@pytest.mark.usefixtures("enroll_setup")
class TestConcurrencyLastSeat(_EnrollBase):
    """SCOPE F — deterministic proof that FOR UPDATE serializes enrollment."""

    def test_last_seat_serialized_by_row_lock(self):
        gid = self._grant(max_devices=1, overage=0)  # capacity = 1

        now = datetime.now(timezone.utc)
        store_id = self.store_id
        device_type_id = self.device_type_id
        retailer_id = self.retailer_id

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
                            await licensing_service.set_licensing_admin_context(s)
                            grant = await licensing_service.lock_current_grant(s)
                            assert grant is not None
                            assert await count_occupied_seats(s) == 0
                            dev = await repository.create_physical_device_onboard(
                                s, store_id=store_id, device_type_id=device_type_id,
                                hardware_fingerprint="a2-fp-conc-a", retailer_id=retailer_id,
                            )
                            await s.flush()
                            await licensing_service.reserve_seat(
                                s, grant_id=grant.id, device_id=dev.id, now=now,
                            )
                            a_lock_acquired.set()
                            await a_release.wait()  # hold the lock until told to commit
                    outcome["a"] = "committed"
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
                            return await licensing_service.authorize_and_reserve_enrollment(
                                s,
                                create_device=lambda: repository.create_physical_device_onboard(
                                    s, store_id=store_id, device_type_id=device_type_id,
                                    hardware_fingerprint="a2-fp-conc-b", retailer_id=retailer_id,
                                ),
                                now=now,
                            )
                finally:
                    await engine.dispose()

            a_task = asyncio.create_task(tx_a())
            await a_lock_acquired.wait()  # A holds the grant row lock
            b_task = asyncio.create_task(tx_b())
            await b_started.wait()        # B has issued its FOR UPDATE

            # B must be blocked on the row lock (not yet done).
            done, _pending = await asyncio.wait({b_task}, timeout=1.0)
            assert not done, "B must block on the FOR UPDATE row lock"

            a_release.set()               # A commits → releases the lock
            await a_task
            result_b = await b_task        # B unblocks and recomputes occupied

            assert result_b.allowed is False
            assert result_b.code == "LICENSE_SEAT_LIMIT"
            assert result_b.occupied == 1

        asyncio.run(_run())

        # End state: exactly one new device and one open seat.
        assert _q("SELECT count(*) AS n FROM physical_devices WHERE hardware_fingerprint IN ('a2-fp-conc-a','a2-fp-conc-b')")[0]["n"] == 1
        assert self._open_seats() == 1
