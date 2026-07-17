"""
EDGE-002 — Manifest Delivery behavioural proof (real PostgreSQL, no mocks).

Proves:
1. Physical devices with retailer A visible under scope A, NOT under scope B
2. Direct DB RLS proof under retail_media_app / NOBYPASSRLS
3. Admin bypass sees all devices

Note: HTTP-level manifest endpoint tests run in the unit suite
(test_phase4_2d_device_gateway.py) against the device-gateway app.
The behavioural conftest provides the control-api app, not device-gateway.

Requires: RUN_BEHAVIORAL_TESTS=1, PostgreSQL, migrations.
"""

import asyncio
import os

import pytest

from tests.behavioral.conftest import _run_sql

RET_A = "beh-e002-ret-a-000000000000001"
RET_B = "beh-e002-ret-b-000000000000001"
STORE_A = "beh-e002-store-a-00000000000001"
DEVICE_A = "beh-e002-dev-a-000000000000001"
DEVICE_B = "beh-e002-dev-b-000000000000001"


@pytest.fixture
def e002_setup(db_available, test_users):
    """Two retailers, one store each, one device each."""
    asyncio.run(_run_sql(f"""
    INSERT INTO retailers (id, code, legal_name, display_name, status)
    VALUES ('{RET_A}', 'E002-RET-A', 'Retailer Alpha', 'Alpha', 'active')
    ON CONFLICT (id) DO NOTHING
    """))
    asyncio.run(_run_sql(f"""
    INSERT INTO retailers (id, code, legal_name, display_name, status)
    VALUES ('{RET_B}', 'E002-RET-B', 'Retailer Beta', 'Beta', 'active')
    ON CONFLICT (id) DO NOTHING
    """))
    asyncio.run(_run_sql("""
    INSERT INTO branches (id, code, name, timezone, is_active)
    VALUES ('beh-e002-br-01', 'E002-BR', 'Test Branch', 'Europe/Moscow', true)
    ON CONFLICT (code) DO NOTHING
    """))
    asyncio.run(_run_sql("""
    INSERT INTO clusters (id, branch_id, code, name, is_active)
    VALUES ('beh-e002-cl-01', 'beh-e002-br-01', 'E002-CL', 'Test Cluster', true)
    ON CONFLICT (code) DO NOTHING
    """))
    asyncio.run(_run_sql(f"""
    INSERT INTO stores (id, cluster_id, code, name, is_active)
    VALUES ('{STORE_A}', 'beh-e002-cl-01', 'E002-ST-A', 'Store A', true)
    ON CONFLICT (code) DO NOTHING
    """))
    asyncio.run(_run_sql("""
    INSERT INTO channels (id, code, name, is_active)
    VALUES ('beh-e002-ch-01', 'E002-CH', 'Test Channel', true)
    ON CONFLICT (code) DO NOTHING
    """))
    asyncio.run(_run_sql("""
    INSERT INTO device_types (id, channel_id, code, name, player_runtime)
    VALUES ('beh-e002-dt-01', 'beh-e002-ch-01', 'E002-KSO',
            'KSO Test', 'chromium')
    ON CONFLICT (code) DO NOTHING
    """))
    asyncio.run(_run_sql(f"""
    INSERT INTO physical_devices (id, store_id, device_type_id, code,
        hardware_fingerprint, status, retailer_id)
    VALUES ('{DEVICE_A}', '{STORE_A}', 'beh-e002-dt-01', 'E002-DEV-A',
        'e002-fp-a', 'active', '{RET_A}')
    ON CONFLICT (id) DO NOTHING
    """))
    asyncio.run(_run_sql(f"""
    INSERT INTO physical_devices (id, store_id, device_type_id, code,
        hardware_fingerprint, status, retailer_id)
    VALUES ('{DEVICE_B}', '{STORE_A}', 'beh-e002-dt-01', 'E002-DEV-B',
        'e002-fp-b', 'active', '{RET_B}')
    ON CONFLICT (id) DO NOTHING
    """))
    yield {"ret_a": RET_A, "ret_b": RET_B, "store_a": STORE_A,
           "device_a": DEVICE_A, "device_b": DEVICE_B}
    asyncio.run(_run_sql("DELETE FROM delivery_manifests WHERE physical_device_id LIKE 'beh-e002-%'"))
    asyncio.run(_run_sql("DELETE FROM physical_devices WHERE id LIKE 'beh-e002-%'"))
    asyncio.run(_run_sql("DELETE FROM device_types WHERE id LIKE 'beh-e002-%'"))
    asyncio.run(_run_sql("DELETE FROM channels WHERE id LIKE 'beh-e002-%'"))
    asyncio.run(_run_sql("DELETE FROM stores WHERE id LIKE 'beh-e002-%'"))
    asyncio.run(_run_sql("DELETE FROM clusters WHERE id LIKE 'beh-e002-%'"))
    asyncio.run(_run_sql("DELETE FROM branches WHERE id LIKE 'beh-e002-%'"))
    asyncio.run(_run_sql("DELETE FROM retailers WHERE id LIKE 'beh-e002-%'"))


@pytest.mark.usefixtures("e002_setup")
class TestEDGE002RLSDirectDB:

    @pytest.fixture(autouse=True)
    def setup(self, db_available, e002_setup):
        self.data = e002_setup

    def test_device_tenant_isolation_scope_a(self):
        """Device in retailer A visible under scope A, NOT scope B."""
        ret_a = self.data["ret_a"]
        ret_b = self.data["ret_b"]
        dev_a = self.data["device_a"]
        dev_b = self.data["device_b"]

        import asyncpg
        APP_DB_URL = os.environ.get(
            "BEHAVIORAL_APP_DB_URL",
            "postgresql://retail_media_app:***@localhost:5432/retail_media_platform",
        ).replace("***", "retail_media_app")

        async def _prove():
            conn = await asyncpg.connect(APP_DB_URL)
            try:
                await conn.execute(
                    "SELECT set_config('app.rmp_scope_retailer_ids', $1, false)", ret_a)
                await conn.execute(
                    "SELECT set_config('app.rmp_is_admin', 'false', false)")
                rows = await conn.fetch(
                    "SELECT id, retailer_id FROM physical_devices WHERE id IN ($1, $2)",
                    dev_a, dev_b)
                ids = {r["id"] for r in rows}
                assert dev_a in ids, f"Scope A missing device A: {ids}"
                assert dev_b not in ids, f"Scope A leaked device B: {ids}"
            finally:
                await conn.close()

        asyncio.run(_prove())

    def test_device_tenant_isolation_scope_b(self):
        """Device in retailer B visible under scope B, NOT scope A."""
        ret_b = self.data["ret_b"]
        dev_a = self.data["device_a"]
        dev_b = self.data["device_b"]

        import asyncpg
        APP_DB_URL = os.environ.get(
            "BEHAVIORAL_APP_DB_URL",
            "postgresql://retail_media_app:***@localhost:5432/retail_media_platform",
        ).replace("***", "retail_media_app")

        async def _prove():
            conn = await asyncpg.connect(APP_DB_URL)
            try:
                await conn.execute(
                    "SELECT set_config('app.rmp_scope_retailer_ids', $1, false)", ret_b)
                await conn.execute(
                    "SELECT set_config('app.rmp_is_admin', 'false', false)")
                rows = await conn.fetch(
                    "SELECT id FROM physical_devices WHERE id IN ($1, $2)", dev_a, dev_b)
                ids = {r["id"] for r in rows}
                assert dev_b in ids, f"Scope B missing device B: {ids}"
                assert dev_a not in ids, f"Scope B leaked device A: {ids}"
            finally:
                await conn.close()

        asyncio.run(_prove())

    def test_empty_scope_deny_all(self):
        """Empty scope → no devices visible."""
        dev_a = self.data["device_a"]
        dev_b = self.data["device_b"]

        import asyncpg
        APP_DB_URL = os.environ.get(
            "BEHAVIORAL_APP_DB_URL",
            "postgresql://retail_media_app:***@localhost:5432/retail_media_platform",
        ).replace("***", "retail_media_app")

        async def _prove():
            conn = await asyncpg.connect(APP_DB_URL)
            try:
                await conn.execute(
                    "SELECT set_config('app.rmp_scope_retailer_ids', '', false)")
                await conn.execute(
                    "SELECT set_config('app.rmp_is_admin', 'false', false)")
                rows = await conn.fetch(
                    "SELECT id FROM physical_devices WHERE id IN ($1, $2)", dev_a, dev_b)
                assert len(rows) == 0, \
                    f"Empty scope deny-all failed: {[r['id'] for r in rows]}"
            finally:
                await conn.close()

        asyncio.run(_prove())

    def test_admin_bypass_sees_all(self):
        """Admin scope → both devices visible."""
        dev_a = self.data["device_a"]
        dev_b = self.data["device_b"]

        import asyncpg
        APP_DB_URL = os.environ.get(
            "BEHAVIORAL_APP_DB_URL",
            "postgresql://retail_media_app:***@localhost:5432/retail_media_platform",
        ).replace("***", "retail_media_app")

        async def _prove():
            conn = await asyncpg.connect(APP_DB_URL)
            try:
                await conn.execute(
                    "SELECT set_config('app.rmp_scope_retailer_ids', '', false)")
                await conn.execute(
                    "SELECT set_config('app.rmp_is_admin', 'true', false)")
                rows = await conn.fetch(
                    "SELECT id FROM physical_devices WHERE id IN ($1, $2)", dev_a, dev_b)
                ids = {r["id"] for r in rows}
                assert dev_a in ids, "Admin missing device A"
                assert dev_b in ids, "Admin missing device B"
            finally:
                await conn.close()

        asyncio.run(_prove())

    def test_device_retailer_id_field_present(self):
        """Devices created with retailer_id keep it after round-trip."""
        dev_a = self.data["device_a"]
        ret_a = self.data["ret_a"]
        dev_b = self.data["device_b"]
        ret_b = self.data["ret_b"]

        import asyncpg
        APP_DB_URL = os.environ.get(
            "BEHAVIORAL_APP_DB_URL",
            "postgresql://retail_media_app:***@localhost:5432/retail_media_platform",
        ).replace("***", "retail_media_app")

        async def _prove():
            conn = await asyncpg.connect(APP_DB_URL)
            try:
                await conn.execute(
                    "SELECT set_config('app.rmp_is_admin', 'true', false)")
                rows = await conn.fetch(
                    "SELECT id, retailer_id FROM physical_devices WHERE id IN ($1, $2)",
                    dev_a, dev_b)
                by_id = {r["id"]: r["retailer_id"] for r in rows}
                assert by_id.get(dev_a) == ret_a, \
                    f"Device A retailer mismatch: {by_id.get(dev_a)} != {ret_a}"
                assert by_id.get(dev_b) == ret_b, \
                    f"Device B retailer mismatch: {by_id.get(dev_b)} != {ret_b}"
            finally:
                await conn.close()

        asyncio.run(_prove())
