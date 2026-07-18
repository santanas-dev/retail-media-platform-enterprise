"""
EDGE-004 — Device Heartbeat behavioural proof under NOBYPASSRLS.

Proves POST /api/v1/device/heartbeat through the real device-gateway:
- Device JWT → 200, last_heartbeat_at + health_state updated in DB
- User token → 401 (auth_provider != "device")
- Invalid/expired token → 401
- Inactive/revoked device → 403
- Device A cannot heartbeat for device B (JWT sub = A, device_id from JWT)
- Client-supplied device_id in body is ignored (not even a field)
- Empty health_state defaults to "healthy"
- Direct DB RLS proof: app role sees only its own device
"""

import asyncio
import os
import sys

import pytest
from fastapi.testclient import TestClient

from packages.security.jwt import create_access_token
from tests.behavioral.conftest import _run_sql

RET_A = "beh-e004-ret-a-00000000000001"
RET_B = "beh-e004-ret-b-00000000000002"
STORE_A = "beh-e004-store-a-0000000000001"
STORE_B = "beh-e004-store-b-0000000000002"
DEVICE_A_ID = "beh-e004-dev-a-00000000000001"
DEVICE_B_ID = "beh-e004-dev-b-00000000000002"
DEVICE_INACTIVE_ID = "beh-e004-dev-inactive-0000001"

_AUTH_PROV = "device"


def _token(device_id: str) -> str:
    return create_access_token(device_id, _AUTH_PROV)


def _auth(token: str):
    return {"Authorization": f"Bearer {token}"}


# ── Fixture ────────────────────────────────────────────────────────────────


@pytest.fixture
def e004_setup(db_available):
    """Two retailers (A and B), each with one active device, plus one inactive."""

    # Retailers
    asyncio.run(_run_sql(f"""
    INSERT INTO retailers (id, code, legal_name, display_name, status)
    VALUES ('{RET_A}', 'E004-RET-A', 'Retailer Alpha', 'Alpha', 'active')
    ON CONFLICT (id) DO NOTHING;
    """))
    asyncio.run(_run_sql(f"""
    INSERT INTO retailers (id, code, legal_name, display_name, status)
    VALUES ('{RET_B}', 'E004-RET-B', 'Retailer Beta', 'Beta', 'active')
    ON CONFLICT (id) DO NOTHING;
    """))

    # Branch → Cluster → Stores
    asyncio.run(_run_sql("""
    INSERT INTO branches (id, code, name, timezone, is_active)
    VALUES ('beh-e004-br-01', 'E004-BR', 'Test Branch', 'Europe/Moscow', true)
    ON CONFLICT (code) DO NOTHING;
    """))
    asyncio.run(_run_sql("""
    INSERT INTO clusters (id, branch_id, code, name, is_active)
    VALUES ('beh-e004-cl-01', 'beh-e004-br-01', 'E004-CL', 'Test Cluster', true)
    ON CONFLICT (code) DO NOTHING;
    """))
    asyncio.run(_run_sql(f"""
    INSERT INTO stores (id, cluster_id, code, name, is_active)
    VALUES ('{STORE_A}', 'beh-e004-cl-01', 'E004-ST-A', 'Store A', true)
    ON CONFLICT (code) DO NOTHING;
    """))
    asyncio.run(_run_sql(f"""
    INSERT INTO stores (id, cluster_id, code, name, is_active, retailer_id)
    VALUES ('{STORE_B}', 'beh-e004-cl-01', 'E004-ST-B', 'Store B', true, '{RET_B}')
    ON CONFLICT (code) DO NOTHING;
    """))

    # Channel → Device Type
    asyncio.run(_run_sql("""
    INSERT INTO channels (id, code, name, is_active)
    VALUES ('beh-e004-ch-01', 'E004-CH', 'Test Channel', true)
    ON CONFLICT (code) DO NOTHING;
    """))
    asyncio.run(_run_sql("""
    INSERT INTO device_types (id, channel_id, code, name, player_runtime)
    VALUES ('beh-e004-dt-01', 'beh-e004-ch-01', 'E004-KSO',
            'KSO Test', 'chromium')
    ON CONFLICT (code) DO NOTHING;
    """))

    # Devices
    asyncio.run(_run_sql(f"""
    INSERT INTO physical_devices (id, store_id, device_type_id, code,
        hardware_fingerprint, status, retailer_id)
    VALUES ('{DEVICE_A_ID}', '{STORE_A}', 'beh-e004-dt-01', 'E004-DEV-A',
        'e004-fp-a', 'active', '{RET_A}')
    ON CONFLICT (id) DO NOTHING;
    """))
    asyncio.run(_run_sql(f"""
    INSERT INTO physical_devices (id, store_id, device_type_id, code,
        hardware_fingerprint, status, retailer_id)
    VALUES ('{DEVICE_B_ID}', '{STORE_B}', 'beh-e004-dt-01', 'E004-DEV-B',
        'e004-fp-b', 'active', '{RET_B}')
    ON CONFLICT (id) DO NOTHING;
    """))
    asyncio.run(_run_sql(f"""
    INSERT INTO physical_devices (id, store_id, device_type_id, code,
        hardware_fingerprint, status, retailer_id)
    VALUES ('{DEVICE_INACTIVE_ID}', '{STORE_A}', 'beh-e004-dt-01', 'E004-DEV-INACT',
        'e004-fp-inact', 'revoked', '{RET_A}')
    ON CONFLICT (id) DO NOTHING;
    """))

    yield

    # Cleanup
    for tbl in ("physical_devices", "device_types", "channels",
                "stores", "clusters", "branches", "retailers"):
        asyncio.run(_run_sql(f"DELETE FROM {tbl} WHERE id LIKE 'beh-e004-%'"))


# ── Real endpoint tests (TestClient against device-gateway) ─────────────────


@pytest.mark.usefixtures("e004_setup")
class TestEDGE004HeartbeatEndpoint:
    """Real device-gateway heartbeat endpoint under NOBYPASSRLS."""

    @pytest.fixture(autouse=True)
    def setup(self, db_available):
        sys.path.insert(
            0,
            os.path.join(
                os.path.dirname(__file__), "..", "..", "apps", "device-gateway"
            ),
        )
        sys.modules.pop("main", None)
        import main as app_mod

        self.app_mod = app_mod
        self.client = TestClient(app_mod.app)

    # ── Positive paths ──────────────────────────────────────────────────

    def test_device_a_heartbeat_200_updates_db(self):
        """Device A (active) → 200, health_state updated in DB."""
        resp = self.client.post(
            "/api/v1/device/heartbeat",
            json={
                "health_state": "healthy",
                "runtime_version": "v2.1.0",
                "player_version": "build-42",
            },
            headers=_auth(_token(DEVICE_A_ID)),
        )
        assert resp.status_code == 200, (
            f"Expected 200, got {resp.status_code}: {resp.text[:300]}"
        )
        data = resp.json()
        assert data["status"] == "accepted"
        assert "server_time" in data
        assert data["health_state"] == "healthy"

    def test_heartbeat_defaults_health_state_to_healthy(self):
        """Empty body → defaults health_state='healthy'."""
        resp = self.client.post(
            "/api/v1/device/heartbeat",
            json={},
            headers=_auth(_token(DEVICE_A_ID)),
        )
        assert resp.status_code == 200, (
            f"Expected 200, got {resp.status_code}: {resp.text[:300]}"
        )
        data = resp.json()
        assert data["health_state"] == "healthy"

    def test_heartbeat_updates_last_heartbeat_at_in_db(self):
        """Send heartbeat → DB row updated: last_heartbeat_at non-null, payload matches."""
        import asyncpg

        async def _check():
            url = os.environ.get("DATABASE_URL", "").strip()
            if not url:
                pytest.skip("DATABASE_URL not set")
            url = url.replace("postgresql+asyncpg://", "postgresql://")
            conn = await asyncpg.connect(url)
            try:
                # ── Pre-read: last_heartbeat_at must be NULL (never heartbeat before) ──
                before = await conn.fetchrow(
                    "SELECT last_heartbeat_at, health_state, runtime_version, "
                    "player_version FROM physical_devices WHERE id = $1",
                    DEVICE_A_ID,
                )
                assert before is not None, "Device A should exist in DB"
                assert before[0] is None, (
                    f"Expected NULL before heartbeat, got {before[0]}"
                )

                # ── Action: send heartbeat via real endpoint ──
                resp = self.client.post(
                    "/api/v1/device/heartbeat",
                    json={
                        "health_state": "degraded",
                        "runtime_version": "rt-1.2.3",
                        "player_version": "player-build-99",
                    },
                    headers=_auth(_token(DEVICE_A_ID)),
                )
                assert resp.status_code == 200, (
                    f"Heartbeat POST expected 200, got {resp.status_code}: {resp.text[:200]}"
                )

                # ── Post-read: assert DB reflects the heartbeat ──
                after = await conn.fetchrow(
                    "SELECT last_heartbeat_at, health_state, runtime_version, "
                    "player_version FROM physical_devices WHERE id = $1",
                    DEVICE_A_ID,
                )
                assert after is not None
                assert after[0] is not None, (
                    "last_heartbeat_at still NULL after heartbeat"
                )
                assert after[1] == "degraded", (
                    f"health_state mismatch: expected 'degraded', got {after[1]}"
                )
                assert after[2] == "rt-1.2.3", (
                    f"runtime_version mismatch: got {after[2]}"
                )
                assert after[3] == "player-build-99", (
                    f"player_version mismatch: got {after[3]}"
                )
                # Timestamp must be strictly after pre-read NULL (= never set)
                # and within last 60 seconds
                from datetime import datetime, timezone
                now = datetime.now(tz=timezone.utc)
                diff = (now - after[0]).total_seconds()
                assert 0 <= diff < 60, (
                    f"Heartbeat timestamp too far from now: {diff:.0f}s"
                )
            finally:
                await conn.close()

        asyncio.run(_check())

    # ── Negative paths ──────────────────────────────────────────────────

    def test_user_token_rejected_401(self):
        """User JWT (auth_provider='local_advertiser') → 401."""
        user_token = create_access_token("user-abc", "local_advertiser")
        resp = self.client.post(
            "/api/v1/device/heartbeat",
            json={},
            headers=_auth(user_token),
        )
        assert resp.status_code == 401, (
            f"Expected 401, got {resp.status_code}: {resp.text[:300]}"
        )

    def test_missing_auth_401(self):
        """No auth → 401."""
        resp = self.client.post(
            "/api/v1/device/heartbeat",
            json={},
        )
        assert resp.status_code == 401

    def test_invalid_token_401(self):
        """Garbage token → 401."""
        resp = self.client.post(
            "/api/v1/device/heartbeat",
            json={},
            headers={"Authorization": "Bearer garbage-token"},
        )
        assert resp.status_code == 401

    def test_inactive_device_rejected_403(self):
        """Revoked device → 403 (set_device_rls_context rejects it)."""
        resp = self.client.post(
            "/api/v1/device/heartbeat",
            json={},
            headers=_auth(_token(DEVICE_INACTIVE_ID)),
        )
        assert resp.status_code == 403, (
            f"Expected 403 for revoked device, got {resp.status_code}: "
            f"{resp.text[:300]}"
        )

    def test_device_a_cannot_heartbeat_for_device_b(self):
        """Device A JWT targets device A. Device B must NOT be updated.

        This is implicit: the endpoint uses device_id from JWT sub,
        not from payload.  Device A token → updates device A only.
        """
        resp = self.client.post(
            "/api/v1/device/heartbeat",
            json={"health_state": "degraded"},
            headers=_auth(_token(DEVICE_A_ID)),
        )
        assert resp.status_code == 200

        # Verify device B was NOT touched
        import asyncpg

        async def _check():
            url = os.environ.get("DATABASE_URL", "").strip()
            if not url:
                pytest.skip("DATABASE_URL not set")
            url = url.replace("postgresql+asyncpg://", "postgresql://")
            conn = await asyncpg.connect(url)
            try:
                row = await conn.fetchrow(
                    "SELECT health_state FROM physical_devices WHERE id = $1",
                    DEVICE_B_ID,
                )
                # Device B should NOT have "degraded" from device A's heartbeat
                assert row is None or row[0] != "degraded", (
                    f"Device B health_state leaked from device A: {row[0] if row else 'N/A'}"
                )
            finally:
                await conn.close()

        asyncio.run(_check())

    # ── Payload device_id spoof ─────────────────────────────────────────

    def test_client_device_id_in_body_ignored(self):
        """device_id is NOT a field in HeartbeatRequest at all.

        Even if someone sends it via extra fields, the endpoint
        uses JWT sub — not the payload.
        """
        resp = self.client.post(
            "/api/v1/device/heartbeat",
            json={"device_id": "evil-device", "health_state": "unhealthy"},
            headers=_auth(_token(DEVICE_A_ID)),
        )
        # Should still accept (extra field ignored) and update device A
        assert resp.status_code == 200, (
            f"Expected 200, got {resp.status_code}: {resp.text[:300]}"
        )
        data = resp.json()
        assert data["status"] == "accepted"


# ═══════════════════════════════════════════════════════════════════════════
# Direct DB RLS proof — app role with app.rmp_device_id bootstrap
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.usefixtures("e004_setup")
class TestEDGE004DirectDBRLS:
    """Direct DB RLS proof: app-role sees only its own device row."""

    def _app_db_url(self):
        url = os.environ.get("DATABASE_URL", "").strip()
        if not url:
            pytest.skip("DATABASE_URL not set")
        return url.replace("postgresql+asyncpg://", "postgresql://")

    def test_bootstrap_sees_only_device_a(self):
        """app.rmp_device_id = A → sees device A row, NOT device B."""
        import asyncpg

        async def _run():
            conn = await asyncpg.connect(self._app_db_url())
            try:
                await conn.execute(
                    "SELECT set_config('app.rmp_device_id', $1, false)",
                    DEVICE_A_ID,
                )
                rows = await conn.fetch("SELECT id FROM physical_devices")
                ids = [r[0] for r in rows]
                assert DEVICE_A_ID in ids, (
                    f"Device A ({DEVICE_A_ID}) not visible with bootstrap"
                )
                assert DEVICE_B_ID not in ids, (
                    f"Device B ({DEVICE_B_ID}) leaked via device A bootstrap"
                )
                assert len(ids) == 1, (
                    f"Expected exactly 1 device, got {len(ids)}: {ids}"
                )
            finally:
                await conn.close()

        asyncio.run(_run())

    def test_no_bootstrap_sees_zero(self):
        """Without app.rmp_device_id, app role sees ZERO physical_devices."""
        import asyncpg

        async def _run():
            conn = await asyncpg.connect(self._app_db_url())
            try:
                rows = await conn.fetch("SELECT id FROM physical_devices")
                ids = [r[0] for r in rows]
                beh_ids = [i for i in ids if i.startswith("beh-e004-")]
                assert beh_ids == [], (
                    f"Expected empty list for beh-e004 devices (RLS deny all), got: {beh_ids}"
                )
            finally:
                await conn.close()

        asyncio.run(_run())

    def test_bootstrap_sees_only_device_b(self):
        """app.rmp_device_id = B → sees device B row, NOT device A."""
        import asyncpg

        async def _run():
            conn = await asyncpg.connect(self._app_db_url())
            try:
                await conn.execute(
                    "SELECT set_config('app.rmp_device_id', $1, false)",
                    DEVICE_B_ID,
                )
                rows = await conn.fetch("SELECT id FROM physical_devices")
                ids = [r[0] for r in rows]
                assert DEVICE_B_ID in ids, (
                    f"Device B ({DEVICE_B_ID}) not visible with bootstrap"
                )
                assert DEVICE_A_ID not in ids, (
                    f"Device A ({DEVICE_A_ID}) leaked via device B bootstrap"
                )
                assert len(ids) == 1, (
                    f"Expected exactly 1 device, got {len(ids)}: {ids}"
                )
            finally:
                await conn.close()

        asyncio.run(_run())
