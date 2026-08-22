"""EPIC-L-SEAT-LEDGER-001A4 — Behavioral proof for the license report + reconciliation.

Proves under retail_media_app (NOBYPASSRLS), against real PostgreSQL:
- Report: occupied/free/capacity/peak, over-cap, effective states, days_remaining,
  seat list fields (device/status/heartbeat/store, no secrets).
- RLS: license tables hidden without service/admin context; report endpoint
  returns data only with the RLS context (tamper-sensitive).
- API: 403 unauthorized, 422 invalid month.
- Reconciliation: clean / active-without-seat / inactive-with-seat /
  non-current-grant drift, dry-run no-change, apply idempotent.

Fixtures run via owner role (admin bypass); assertions via the app role.
"""

import asyncio
import os
from datetime import datetime, timedelta, timezone

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


def _current_ym() -> tuple[int, int]:
    now = datetime.now(timezone.utc)
    return now.year, now.month


@pytest.fixture
def client(app, db_available, test_users):
    reset_security_config()
    return TestClient(app)


@pytest.fixture
def report_setup(db_available, test_users):
    b = BehBuilder("beh-a4")
    rid = b.retailer(code="A4-RET")
    chain = b.store_chain()
    cd = b.channel_device_type()

    _setup("DELETE FROM device_status_history WHERE physical_device_id IN "
           "(SELECT id FROM physical_devices WHERE retailer_id LIKE 'beh-a4%');")
    _setup("DELETE FROM license_seats WHERE id LIKE 'beh-a4%' OR license_id LIKE 'beh-a4%';")
    _setup("DELETE FROM license_grants WHERE id LIKE 'beh-a4%' OR license_id LIKE 'beh-a4%';")

    yield {
        "builder": b,
        "retailer_id": rid,
        "store_id": chain["store_id"],
        "device_type_id": cd["device_type_id"],
    }

    _setup("DELETE FROM device_status_history WHERE physical_device_id IN "
           "(SELECT id FROM physical_devices WHERE retailer_id LIKE 'beh-a4%');")
    _setup("DELETE FROM license_seats WHERE id LIKE 'beh-a4%' OR license_id LIKE 'beh-a4%';")
    _setup("DELETE FROM license_grants WHERE id LIKE 'beh-a4%' OR license_id LIKE 'beh-a4%';")
    _setup("DELETE FROM device_onboarding_codes WHERE retailer_id LIKE 'beh-a4%' OR created_by LIKE 'beh-a4%';")
    _setup("DELETE FROM physical_devices WHERE id LIKE 'beh-a4%' OR retailer_id LIKE 'beh-a4%';")
    b.cleanup()


class _ReportBase:
    @pytest.fixture(autouse=True)
    def _setup(self, client, db_available, report_setup):
        reset_security_config()
        self.client = client
        self.b = report_setup["builder"]
        self.retailer_id = report_setup["retailer_id"]
        self.store_id = report_setup["store_id"]
        self.device_type_id = report_setup["device_type_id"]
        self.token_admin = _token(USER_IDS["readonly"])  # system_admin
        self.token_adv = _token(USER_IDS["advertiser"])  # no license.read

    def _grant(self, *, max_devices=10, overage=0, grace=0,
               valid_until="NULL", status="current",
               valid_from="NOW() - INTERVAL '1 day'", issued_at="NOW()") -> str:
        gid = self.b._uid("g")
        lid = self.b._uid("lic")
        _setup(f"""
            INSERT INTO license_grants (id, license_id, licensee_id, licensee_name,
                tier, issued_at, valid_from, valid_until, max_devices,
                overage_allowance, grace_days, source, status)
            VALUES ('{gid}', '{lid}', 'a4-op', 'A4 Operator', 'pro',
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
        assert resp.status_code == 201, resp.text[:200]
        return resp.json()["code"]

    def _onboard(self, code, fp):
        return self.client.post(
            "/api/v1/device/onboard",
            json={"device_code": code, "hardware_fingerprint": fp},
        )

    def _report(self, year=None, month=None, token=None):
        y, m = (year, month) if (year is not None and month is not None) else _current_ym()
        return self.client.get(
            f"/api/v1/identity/licenses/report?year={y}&month={m}",
            headers=_auth(token or self.token_admin),
        )

    def _seat(self, device_id, gid, *, released_at="NULL"):
        _setup(f"""
            INSERT INTO license_seats (id, license_id, device_id, reserved_at, released_at)
            VALUES ('{self.b._uid('seat')}', '{gid}', '{device_id}', NOW(), {released_at});
        """)

    def _detail(self, resp):
        return resp.json()["detail"]


def _reconcile() -> licensing_service.ReconciliationReport:
    async def _run():
        engine = _cae(_APP_DB_URL, echo=False, poolclass=NullPool)
        try:
            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            async with factory() as s:
                async with s.begin():
                    return await licensing_service.get_reconciliation_report(
                        s, now=datetime.now(timezone.utc),
                    )
        finally:
            await engine.dispose()

    return asyncio.run(_run())


def _apply_reconcile() -> licensing_service.ReconciliationResult:
    async def _run():
        engine = _cae(_APP_DB_URL, echo=False, poolclass=NullPool)
        try:
            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            async with factory() as s:
                async with s.begin():
                    return await licensing_service.reconcile_existing_fleet(
                        s, now=datetime.now(timezone.utc),
                    )
        finally:
            await engine.dispose()

    return asyncio.run(_run())


@pytest.mark.usefixtures("report_setup")
class TestLicenseReport(_ReportBase):
    """SCOPE F #1–#5, #7 — report content."""

    def test_report_active_license_counts(self):
        gid = self._grant(max_devices=5)
        for i in range(2):
            code = self._create_code()
            assert self._onboard(code, f"a4-fp-cnt-{i:04d}").status_code == 200

        year, month = _current_ym()
        resp = self._report(year, month)
        assert resp.status_code == 200, resp.text[:200]
        data = resp.json()
        assert data["license"]["effective_state"] == "active"
        assert data["license"]["capacity"] == 5
        assert data["usage"]["occupied"] == 2
        assert data["usage"]["free"] == 3
        assert data["usage"]["peak"] == 2
        assert data["usage"]["year"] == year and data["usage"]["month"] == month
        assert data["license"]["over_capacity_by"] == 0

    def test_report_over_capacity(self):
        gid = self._grant(max_devices=1, overage=0)  # capacity = 1
        # Grandfather 3 active devices with open seats (over cap).
        for i in range(3):
            dev = self.b.device(self.store_id, self.device_type_id, self.retailer_id, status="active")
            self._seat(dev, gid)

        year, month = _current_ym()
        resp = self._report(year, month)
        assert resp.status_code == 200
        data = resp.json()
        assert data["usage"]["occupied"] == 3
        assert data["usage"]["free"] == 0
        assert data["license"]["over_capacity_by"] == 2

    def test_report_effective_states(self):
        # missing — no grant
        resp = self._report(*_current_ym())
        assert resp.json()["license"]["effective_state"] == "missing"
        assert resp.json()["usage"]["occupied"] == 0

        # revoked
        self._grant(status="revoked")
        assert self._report(*_current_ym()).json()["license"]["effective_state"] == "revoked"

        # expired
        _setup("DELETE FROM license_grants WHERE license_id LIKE 'beh-a4%';")
        self._grant(valid_from="NOW() - INTERVAL '30 days'",
                    valid_until="NOW() - INTERVAL '5 days'", grace=3)
        assert self._report(*_current_ym()).json()["license"]["effective_state"] == "expired"

        # grace
        _setup("DELETE FROM license_grants WHERE license_id LIKE 'beh-a4%';")
        self._grant(valid_from="NOW() - INTERVAL '30 days'",
                    valid_until="NOW() - INTERVAL '1 day'", grace=30)
        assert self._report(*_current_ym()).json()["license"]["effective_state"] == "grace"

        # perpetual (active, no valid_until)
        _setup("DELETE FROM license_grants WHERE license_id LIKE 'beh-a4%';")
        self._grant(valid_until="NULL")
        assert self._report(*_current_ym()).json()["license"]["effective_state"] == "active"

    def test_report_days_remaining(self):
        # perpetual → None
        gid = self._grant(valid_until="NULL")
        assert self._report(*_current_ym()).json()["license"]["days_remaining"] is None

        # expired → 0
        _setup(f"UPDATE license_grants SET valid_until = NOW() - INTERVAL '1 day' WHERE id='{gid}'")
        assert self._report(*_current_ym()).json()["license"]["days_remaining"] == 0

        # active far future → positive
        _setup("DELETE FROM license_grants WHERE license_id LIKE 'beh-a4%';")
        self._grant(valid_until="NOW() + INTERVAL '30 days'")
        dr = self._report(*_current_ym()).json()["license"]["days_remaining"]
        assert 29 <= dr <= 30, f"days_remaining={dr}"

    def test_report_seat_list_fields_no_secrets(self):
        gid = self._grant(max_devices=5)
        code = self._create_code()
        device_id = self._onboard(code, "a4-fp-seat-000000000001").json()["device_id"]

        resp = self._report(*_current_ym())
        data = resp.json()
        assert len(data["seats"]) == 1
        seat = data["seats"][0]
        assert seat["device_id"] == device_id
        assert seat["device_code"]
        assert seat["device_status"] == "active"
        assert seat["store_id"] == self.store_id
        assert seat["store_code"]
        assert seat["store_name"]
        assert seat["reserved_at"] is not None
        assert seat["anomaly_flags"] == []

        # No secrets anywhere in the payload.
        raw = resp.text.lower()
        for secret in ("hardware_fingerprint", "access_token", "certificate",
                       "serial_number", "password", "private_key"):
            assert secret not in raw, f"leaked secret marker '{secret}'"

    def test_report_endpoint_returns_data(self):
        self._grant(max_devices=5)
        code = self._create_code()
        assert self._onboard(code, "a4-fp-ep-00000000000001").status_code == 200

        resp = self._report(*_current_ym())
        assert resp.status_code == 200
        assert resp.json()["license"]["effective_state"] == "active"
        assert resp.json()["usage"]["occupied"] == 1


@pytest.mark.usefixtures("report_setup")
class TestLicenseReportRlsAndAuth(_ReportBase):
    """SCOPE F #6, #8, #9 — RLS, authorization, validation."""

    def test_ledger_hidden_without_admin_context(self):
        gid = self._grant(max_devices=5)
        dev = self.b.device(self.store_id, self.device_type_id, self.retailer_id, status="active")
        self._seat(dev, gid)

        # Direct app-role read WITHOUT admin context → license tables hidden.
        assert _q("SELECT id FROM license_grants", admin=False) == []
        assert _q("SELECT id FROM license_seats", admin=False) == []
        # With admin context → visible.
        assert len(_q(f"SELECT id FROM license_grants WHERE id='{gid}'", admin=True)) == 1
        assert len(_q(f"SELECT id FROM license_seats WHERE device_id='{dev}'", admin=True)) == 1

    def test_report_requires_admin_rls_context(self):
        """Tamper-sensitive: report must apply the RLS context itself.

        Builds a control-api client with NO get_db override (real app role,
        NOBYPASSRLS). With the ``set_rls_context`` dependency present, a
        system_admin report is non-empty (context elevates to admin). Removing
        the dependency makes license tables invisible → ``effective_state``
        becomes ``missing``.
        """
        self._grant(max_devices=5)
        code = self._create_code()
        assert self._onboard(code, "a4-fp-rls-00000000000001").status_code == 200

        from tests.behavioral.conftest import _load_control_api_app
        from packages.domain.database import set_global_engine

        engine = _cae(_APP_DB_URL, echo=False, poolclass=NullPool)
        set_global_engine(engine)
        raw_app = _load_control_api_app()
        try:
            with TestClient(raw_app) as raw_client:
                resp = raw_client.get(
                    f"/api/v1/identity/licenses/report?year={_current_ym()[0]}&month={_current_ym()[1]}",
                    headers=_auth(self.token_admin),
                )
                assert resp.status_code == 200, resp.text[:200]
                data = resp.json()
                assert data["license"]["effective_state"] == "active"
                assert data["usage"]["occupied"] == 1
        finally:
            await_engine = engine
            asyncio.run(await_engine.dispose())

    def test_report_unauthorized_403(self):
        self._grant(max_devices=5)
        resp = self._report(*_current_ym(), token=self.token_adv)
        assert resp.status_code == 403

    def test_report_invalid_month_422(self):
        resp = self.client.get(
            "/api/v1/identity/licenses/report?year=2026&month=13",
            headers=_auth(self.token_admin),
        )
        assert resp.status_code == 422
        assert resp.json()["detail"]["code"] == "INVALID_MONTH"


@pytest.mark.usefixtures("report_setup")
class TestReconciliation(_ReportBase):
    """SCOPE F #10–#15 — reconciliation drift detection + repair."""

    def test_reconciliation_clean(self):
        self._grant(max_devices=5)
        self.b.device(self.store_id, self.device_type_id, self.retailer_id, status="active")
        # Grandfather all active devices (incl. the production seed device) so
        # the ledger is genuinely consistent.
        _apply_reconcile()

        report = _reconcile()
        assert report.consistent is True
        assert report.findings == []

    def test_reconciliation_active_without_seat(self):
        self._grant(max_devices=5)
        self.b.device(self.store_id, self.device_type_id, self.retailer_id, status="active")

        report = _reconcile()
        assert report.consistent is False
        assert any(f.code == "active_device_without_seat" for f in report.findings)

    def test_reconciliation_inactive_with_seat(self):
        gid = self._grant(max_devices=5)
        dev = self.b.device(self.store_id, self.device_type_id, self.retailer_id, status="inactive")
        self._seat(dev, gid)

        report = _reconcile()
        assert report.consistent is False
        assert any(f.code == "inactive_device_with_seat" for f in report.findings)

    def test_reconciliation_noncurrent_grant(self):
        gid = self._grant(max_devices=5)
        # Historical/superseded grant (not current) — seat under it is drift.
        _setup(f"UPDATE license_grants SET status='superseded' WHERE id='{gid}';")
        dev = self.b.device(self.store_id, self.device_type_id, self.retailer_id, status="active")
        self._seat(dev, gid)

        report = _reconcile()
        assert report.consistent is False
        # The seat is under a non-current grant AND the current grant is missing.
        assert any(f.code == "current_grant_missing" for f in report.findings)

    def test_reconciliation_dry_run_no_change(self):
        self._grant(max_devices=5)
        dev = self.b.device(self.store_id, self.device_type_id, self.retailer_id, status="active")
        # active device without seat → drift.

        before = _q(f"SELECT count(*) AS n FROM license_seats WHERE device_id='{dev}'")[0]["n"]
        report = _reconcile()
        assert report.consistent is False
        after = _q(f"SELECT count(*) AS n FROM license_seats WHERE device_id='{dev}'")[0]["n"]
        assert before == after == 0  # dry-run wrote nothing

    def test_apply_fixes_missing_seat_idempotent(self):
        self._grant(max_devices=5)
        dev = self.b.device(self.store_id, self.device_type_id, self.retailer_id, status="active")

        r1 = _apply_reconcile()
        assert r1.created_seats >= 1  # at least our active-without-seat device
        assert _q(f"SELECT count(*) AS n FROM license_seats WHERE device_id='{dev}' AND released_at IS NULL")[0]["n"] == 1

        # Idempotent: second apply creates nothing new.
        r2 = _apply_reconcile()
        assert r2.created_seats == 0
        assert _q(f"SELECT count(*) AS n FROM license_seats WHERE device_id='{dev}' AND released_at IS NULL")[0]["n"] == 1
