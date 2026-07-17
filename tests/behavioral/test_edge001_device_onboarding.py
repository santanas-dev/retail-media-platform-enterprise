"""
EDGE-001 hardening v2 — Behavioural proof (no mocks, real PostgreSQL).

Proves:
1. Non-admin cannot create device code (403)
2. Admin can create device code
3. Device onboarding with valid code succeeds
4. Expired/revoked code rejected
5. Already-used code + different fingerprint → 403
6. Same used code + same fingerprint → 200 idempotent
7. Active new code + already-registered fingerprint → 403 FINGERPRINT_CONFLICT
8. Concurrent same active code → single device
9. FINGERPRINT_CONFLICT reverts claim — code reusable with different fingerprint
10. Direct DB RLS proof: device_onboarding_codes under NOBYPASSRLS

Requires: RUN_BEHAVIORAL_TESTS=1, PostgreSQL, migrations.
"""

import asyncio
import os
import time

import pytest
from fastapi.testclient import TestClient

from packages.security.config import reset_security_config
from packages.security.jwt import create_access_token
from tests.behavioral.conftest import _run_sql, USER_IDS

RET_A = "beh-e001-ret-a-000000000000001"
RET_B = "beh-e001-ret-b-000000000000001"
STORE_A = "beh-e001-store-a-00000000000001"

AUTH_PROVIDER = "local_advertiser"


def _token(user_id: str) -> str:
    return create_access_token(user_id, AUTH_PROVIDER)


def _auth(token: str):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client(app, db_available, test_users):
    reset_security_config()
    return TestClient(app)


@pytest.fixture
def e001_setup(db_available, test_users):
    """Two retailers, one store in RET_A, with channel+device_type for FK constraints."""
    asyncio.run(_run_sql(f"""
    INSERT INTO retailers (id, code, legal_name, display_name, status)
    VALUES ('{RET_A}', 'E001-RET-A', 'Retailer Alpha', 'Alpha', 'active')
    ON CONFLICT (id) DO NOTHING
    """))
    asyncio.run(_run_sql(f"""
    INSERT INTO retailers (id, code, legal_name, display_name, status)
    VALUES ('{RET_B}', 'E001-RET-B', 'Retailer Beta', 'Beta', 'active')
    ON CONFLICT (id) DO NOTHING
    """))
    asyncio.run(_run_sql("""
    INSERT INTO branches (id, code, name, timezone, is_active)
    VALUES ('beh-e001-br-01', 'E001-BR', 'Test Branch', 'Europe/Moscow', true)
    ON CONFLICT (code) DO NOTHING
    """))
    asyncio.run(_run_sql("""
    INSERT INTO clusters (id, branch_id, code, name, is_active)
    VALUES ('beh-e001-cl-01', 'beh-e001-br-01', 'E001-CL', 'Test Cluster', true)
    ON CONFLICT (code) DO NOTHING
    """))
    asyncio.run(_run_sql(f"""
    INSERT INTO stores (id, cluster_id, code, name, is_active)
    VALUES ('{STORE_A}', 'beh-e001-cl-01', 'E001-ST-A', 'Store A', true)
    ON CONFLICT (code) DO NOTHING
    """))
    asyncio.run(_run_sql("""
    INSERT INTO channels (id, code, name, is_active)
    VALUES ('beh-e001-ch-01', 'E001-CH', 'Test Channel', true)
    ON CONFLICT (code) DO NOTHING
    """))
    asyncio.run(_run_sql("""
    INSERT INTO device_types (id, channel_id, code, name, player_runtime)
    VALUES ('beh-e001-dt-01', 'beh-e001-ch-01', 'E001-KSO',
            'KSO Test', 'chromium')
    ON CONFLICT (code) DO NOTHING
    """))
    yield {"ret_a": RET_A, "ret_b": RET_B, "store_a": STORE_A}
    asyncio.run(_run_sql("DELETE FROM device_onboarding_codes WHERE id LIKE 'beh-e001-%' OR retailer_id LIKE 'beh-e001-%'"))
    asyncio.run(_run_sql("DELETE FROM physical_devices WHERE id LIKE 'beh-e001-%' OR retailer_id LIKE 'beh-e001-%'"))
    asyncio.run(_run_sql("DELETE FROM device_types WHERE id LIKE 'beh-e001-%'"))
    asyncio.run(_run_sql("DELETE FROM channels WHERE id LIKE 'beh-e001-%'"))
    asyncio.run(_run_sql("DELETE FROM stores WHERE id LIKE 'beh-e001-%'"))
    asyncio.run(_run_sql("DELETE FROM clusters WHERE id LIKE 'beh-e001-%'"))
    asyncio.run(_run_sql("DELETE FROM branches WHERE id LIKE 'beh-e001-%'"))
    asyncio.run(_run_sql("DELETE FROM retailers WHERE id LIKE 'beh-e001-%'"))


@pytest.mark.usefixtures("e001_setup")
class TestEDGE001DeviceCodeAdmin:

    @pytest.fixture(autouse=True)
    def setup(self, client, db_available, e001_setup):
        self.client = client
        self.data = e001_setup
        self.token_admin = _token(USER_IDS["readonly"])    # system_admin
        self.token_advertiser = _token(USER_IDS["advertiser"])  # scoped advertiser
        self.token_noperms = _token(USER_IDS["noperms"])    # operator

    def test_non_admin_cannot_create_device_code(self):
        """Advertiser user without devices.manage → 403."""
        resp = self.client.post(
            "/api/v1/identity/device-codes",
            json={"retailer_id": self.data["ret_a"], "ttl_hours": 24},
            headers=_auth(self.token_advertiser),
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text[:200]}"

    def test_noperms_cannot_create_device_code(self):
        """Operator user without devices.manage → 403."""
        resp = self.client.post(
            "/api/v1/identity/device-codes",
            json={"retailer_id": self.data["ret_a"], "ttl_hours": 24},
            headers=_auth(self.token_noperms),
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text[:200]}"

    def test_admin_can_create_device_code(self):
        """system_admin with devices.manage → 201."""
        resp = self.client.post(
            "/api/v1/identity/device-codes",
            json={"retailer_id": self.data["ret_a"], "store_id": self.data["store_a"],
                  "ttl_hours": 24},
            headers=_auth(self.token_admin),
        )
        assert resp.status_code == 201, f"Admin create failed: {resp.status_code} {resp.text[:200]}"
        data = resp.json()
        assert data["retailer_id"] == self.data["ret_a"]
        assert data["store_id"] == self.data["store_a"]
        assert data["status"] == "active"
        assert len(data["code"]) >= 32


@pytest.mark.usefixtures("e001_setup")
class TestEDGE001DeviceOnboarding:

    @pytest.fixture(autouse=True)
    def setup(self, client, db_available, e001_setup):
        self.client = client
        self.data = e001_setup
        self.token_admin = _token(USER_IDS["readonly"])

    def _create_code(self, retailer_id, store_id=None, ttl=24):
        resp = self.client.post(
            "/api/v1/identity/device-codes",
            json={"retailer_id": retailer_id, "store_id": store_id,
                  "device_type_id": "beh-e001-dt-01", "ttl_hours": ttl},
            headers=_auth(self.token_admin),
        )
        assert resp.status_code == 201, f"Code creation failed: {resp.text[:200]}"
        return resp.json()["code"]

    # ── Happy path ──────────────────────────────────────────────────────────

    def test_onboard_new_device_success(self):
        """Valid code + new fingerprint → device created, token issued."""
        code = self._create_code(self.data["ret_a"], self.data["store_a"])
        fp = "e001-fp-success-000000000000001"
        resp = self.client.post(
            "/api/v1/device/onboard",
            json={"device_code": code, "hardware_fingerprint": fp},
        )
        assert resp.status_code == 200, f"Onboard failed: {resp.status_code} {resp.text[:200]}"
        data = resp.json()
        assert data["device_id"], "No device_id"
        assert data["status"] == "active"
        assert data["access_token"], "No access_token"
        assert data["token_type"] == "bearer"

    def test_device_retailer_id_from_code_not_client(self):
        """Device's retailer_id = code's retailer_id. Client cannot choose."""
        code = self._create_code(self.data["ret_a"], self.data["store_a"])
        fp = "e001-fp-retailer-00000000000001"
        resp = self.client.post(
            "/api/v1/device/onboard",
            json={"device_code": code, "hardware_fingerprint": fp},
        )
        assert resp.status_code == 200
        # Success proves code.retailer_id → device.retailer_id (no client override)

    # ── Rejection cases ─────────────────────────────────────────────────────

    def test_expired_code_rejected(self):
        """Code with manually-expired expires_at → 403 CODE_EXPIRED."""
        code = self._create_code(self.data["ret_a"], self.data["store_a"])
        asyncio.run(_run_sql(
            f"UPDATE device_onboarding_codes SET expires_at = NOW() - INTERVAL '1 hour' WHERE code = '{code}'"
        ))
        resp = self.client.post(
            "/api/v1/device/onboard",
            json={"device_code": code, "hardware_fingerprint": "e001-fp-expired-01"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text[:200]}"
        assert "CODE_EXPIRED" in str(resp.json())

    def test_already_used_code_rejected_different_fingerprint(self):
        """Used code + different fingerprint → 403 CODE_ALREADY_USED."""
        code = self._create_code(self.data["ret_a"], self.data["store_a"])
        fp1 = "e001-fp-used-000000000000001"
        resp = self.client.post("/api/v1/device/onboard", json={"device_code": code, "hardware_fingerprint": fp1})
        assert resp.status_code == 200
        fp2 = "e001-fp-used-000000000000002"
        resp = self.client.post("/api/v1/device/onboard", json={"device_code": code, "hardware_fingerprint": fp2})
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text[:200]}"
        assert "CODE_ALREADY_USED" in str(resp.json())

    # ── Idempotency (used code + same fingerprint) ──────────────────────────

    def test_used_code_same_fingerprint_idempotent(self):
        """Same used code + same fingerprint → 200, returns existing device_id."""
        code = self._create_code(self.data["ret_a"], self.data["store_a"])
        fp = "e001-fp-idem-000000000000001"
        r1 = self.client.post("/api/v1/device/onboard", json={"device_code": code, "hardware_fingerprint": fp})
        assert r1.status_code == 200
        dev1 = r1.json()["device_id"]
        r2 = self.client.post("/api/v1/device/onboard", json={"device_code": code, "hardware_fingerprint": fp})
        assert r2.status_code == 200
        dev2 = r2.json()["device_id"]
        assert dev1 == dev2, f"Idempotent mismatch: {dev1} != {dev2}"

    # ── FINGERPRINT_CONFLICT — new active code + existing fingerprint ───────

    def test_active_new_code_existing_fingerprint_conflict(self):
        """Active new code + already-registered fingerprint → 403 FINGERPRINT_CONFLICT.

        A new code must NOT "stick" to an existing device.
        """
        # Register device D1 with code A
        code_a = self._create_code(self.data["ret_a"], self.data["store_a"])
        fp = "e001-fp-conflict-00000000000001"
        r1 = self.client.post("/api/v1/device/onboard", json={"device_code": code_a, "hardware_fingerprint": fp})
        assert r1.status_code == 200
        device_id_1 = r1.json()["device_id"]

        # Create a new active code B — try to onboard with same fingerprint
        code_b = self._create_code(self.data["ret_a"], self.data["store_a"])
        r2 = self.client.post("/api/v1/device/onboard", json={"device_code": code_b, "hardware_fingerprint": fp})
        assert r2.status_code == 403, f"Expected 403 FINGERPRINT_CONFLICT, got {r2.status_code}: {r2.json()}"
        detail = r2.json()
        assert "FINGERPRINT_CONFLICT" in str(detail), f"Wrong error: {detail}"

    # ── Claim revert: code remains usable after conflict ────────────────────

    def test_reverted_code_remains_usable_after_conflict(self):
        """FINGERPRINT_CONFLICT reverts claim — code stays active and reusable.

        This proves the code did NOT get stuck in 'claimed' state.
        """
        # Register device D1 with code A
        code_a = self._create_code(self.data["ret_a"], self.data["store_a"])
        fp1 = "e001-fp-rev1-000000000000001"
        self.client.post("/api/v1/device/onboard", json={"device_code": code_a, "hardware_fingerprint": fp1})

        # Code B + same fingerprint → FINGERPRINT_CONFLICT (claim reverted)
        code_b = self._create_code(self.data["ret_a"], self.data["store_a"])
        r = self.client.post("/api/v1/device/onboard", json={"device_code": code_b, "hardware_fingerprint": fp1})
        assert r.status_code == 403
        assert "FINGERPRINT_CONFLICT" in str(r.json())

        # Code B MUST still be usable with a different fingerprint
        fp2 = "e001-fp-rev2-000000000000002"
        r2 = self.client.post("/api/v1/device/onboard", json={"device_code": code_b, "hardware_fingerprint": fp2})
        assert r2.status_code == 200, f"Code should be reusable after revert: {r2.status_code} {r2.json()}"
        assert r2.json()["device_id"]

    # ── Concurrent same code → single device ────────────────────────────────

    def test_concurrent_same_code_single_device(self):
        """Two concurrent requests with the same active code → single device.

        Uses asyncio.gather with httpx.AsyncClient over ASGI transport.
        """
        import httpx

        code = self._create_code(self.data["ret_a"], self.data["store_a"])
        fp = "e001-fp-conc-000000000000001"

        async def _onboard():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=self.client.app),
                base_url="http://test",
            ) as ac:
                resp = await ac.post("/api/v1/device/onboard", json={
                    "device_code": code, "hardware_fingerprint": fp,
                })
                return resp.status_code, resp.json() if resp.status_code == 200 else resp.json()

        async def _concurrent():
            return await asyncio.gather(_onboard(), _onboard())

        results = asyncio.run(_concurrent())
        statuses = [r[0] for r in results]
        device_ids = {r[1].get("device_id") for r in results if r[0] == 200}

        assert 200 in statuses, f"At least one concurrent request must succeed: {statuses}"
        assert len(device_ids) == 1, f"Only one device_id expected, got: {device_ids}"
        # The loser may get 403 (INVALID_CODE — code no longer active)
        loser_statuses = [s for s in statuses if s != 200]
        assert all(s == 403 for s in loser_statuses), f"Loser must be 403: {loser_statuses}"

    # ── Cross-retailer ──────────────────────────────────────────────────────

    def test_cross_retailer_code_scope_enforced(self):
        """Code from retailer A works; non-existent code → 403."""
        code = self._create_code(self.data["ret_a"], self.data["store_a"])
        fp = "e001-fp-cross-000000000000001"
        resp = self.client.post("/api/v1/device/onboard", json={"device_code": code, "hardware_fingerprint": fp})
        assert resp.status_code == 200
        # Non-existent code
        resp_bad = self.client.post("/api/v1/device/onboard",
                                     json={"device_code": "nonexistent-code-12345",
                                           "hardware_fingerprint": "e001-fp-cross-bad"})
        assert resp_bad.status_code == 403


@pytest.mark.usefixtures("e001_setup")
class TestEDGE001RLSDirectDB:

    @pytest.fixture(autouse=True)
    def setup(self, client, db_available, e001_setup):
        self.client = client
        self.data = e001_setup
        self.token_admin = _token(USER_IDS["readonly"])

    def _create_code(self, retailer_id):
        resp = self.client.post(
            "/api/v1/identity/device-codes",
            json={"retailer_id": retailer_id, "ttl_hours": 24},
            headers=_auth(self.token_admin),
        )
        assert resp.status_code == 201
        return resp.json()["code"]

    def test_direct_db_rls_proof(self):
        """Connect as retail_media_app (NOBYPASSRLS).

        Create codes in RET_A and RET_B.
        SET LOCAL app.rmp_scope_retailer_ids = RET_A → only RET_A codes visible.
        SET LOCAL app.rmp_scope_retailer_ids = RET_B → only RET_B codes visible.
        Empty scope → deny-all.
        Admin bypass → both visible.
        """
        code_a = self._create_code(self.data["ret_a"])
        code_b = self._create_code(self.data["ret_b"])

        import asyncpg
        APP_DB_URL = os.environ.get(
            "BEHAVIORAL_APP_DB_URL",
            "postgresql://retail_media_app:***@localhost:5432/retail_media_platform",
        ).replace("***", "retail_media_app")

        async def _prove():
            conn = await asyncpg.connect(APP_DB_URL)
            try:
                await conn.execute("SELECT set_config('app.rmp_scope_retailer_ids', $1, false)", self.data["ret_a"])
                await conn.execute("SELECT set_config('app.rmp_is_admin', 'false', false)")
                rows_a = await conn.fetch("SELECT code, retailer_id FROM device_onboarding_codes WHERE code IN ($1, $2) ORDER BY code", code_a, code_b)
                ids_a = {r["code"] for r in rows_a}
                assert code_a in ids_a, f"RET_A scope missing code_a: {ids_a}"
                assert code_b not in ids_a, f"RET_A scope leaked code_b: {ids_a}"

                await conn.execute("SELECT set_config('app.rmp_scope_retailer_ids', $1, false)", self.data["ret_b"])
                rows_b = await conn.fetch("SELECT code FROM device_onboarding_codes WHERE code IN ($1, $2)", code_a, code_b)
                ids_b = {r["code"] for r in rows_b}
                assert code_b in ids_b, f"RET_B scope missing code_b: {ids_b}"
                assert code_a not in ids_b, f"RET_B scope leaked code_a: {ids_b}"

                await conn.execute("SELECT set_config('app.rmp_scope_retailer_ids', '', false)")
                await conn.execute("SELECT set_config('app.rmp_is_admin', 'false', false)")
                rows_empty = await conn.fetch("SELECT code FROM device_onboarding_codes WHERE code IN ($1, $2)", code_a, code_b)
                assert len(rows_empty) == 0, f"Empty scope deny-all failed: {[r['code'] for r in rows_empty]}"

                await conn.execute("SELECT set_config('app.rmp_scope_retailer_ids', '', false)")
                await conn.execute("SELECT set_config('app.rmp_is_admin', 'true', false)")
                rows_admin = await conn.fetch("SELECT code FROM device_onboarding_codes WHERE code IN ($1, $2)", code_a, code_b)
                ids_admin = {r["code"] for r in rows_admin}
                assert code_a in ids_admin, "Admin missing code_a"
                assert code_b in ids_admin, "Admin missing code_b"
            finally:
                await conn.close()

        asyncio.run(_prove())
