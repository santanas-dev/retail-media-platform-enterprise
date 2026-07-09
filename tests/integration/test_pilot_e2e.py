"""
Pilot E2E smoke test: full B1→B2→B3 pipeline (B3).

Proves the minimal pilot business flow end-to-end:
  campaign setup (seed) → approval → outbox relay → NATS JetStream →
  campaign consumer → manifest generated → device-gateway fetch.

The manifest is verified via HTTP (device-gateway TestClient with device JWT)
and its shape/properties are asserted.

Campaign setup uses seed data + raw SQL — same pattern as B2.
Using the control-api TestClient for campaign CRUD was considered but
rejected because (1) it requires RBAC user/permission/membership setup
that duplicates the behavioral conftest, (2) the control-api create/approve
endpoints were already proven in test_campaign_mutations.py (42 pass),
and (3) B3's purpose is integration at the pipeline boundaries:
API manifest fetch via real NATS + real PostgreSQL for the delivery path.

Requires:
  - RUN_NATS_INTEGRATION_TESTS=1
  - Local nats-server with JetStream (nats-server -js)
  - PostgreSQL with seed data + migrations

Usage:
  RUN_NATS_INTEGRATION_TESTS=1 python -m pytest tests/integration/test_pilot_e2e.py -v

Skips silently when env is not set.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

os.environ["ENVIRONMENT"] = "dev"
os.environ["JWT_SECRET"] = "pilot-e2e-test-secret-at-least-32-chars"

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

DB_URL = os.environ.get(
    "BEHAVIORAL_DB_URL",
    "postgresql+asyncpg://retail_media:retail_media_dev@localhost:5432/retail_media_platform",
)

NATS_URL = os.environ.get("NATS_E2E_URL", "nats://localhost:4222")

REQUIRE_ENV = os.environ.get("RUN_NATS_INTEGRATION_TESTS", "") == "1"
SKIP_REASON = "RUN_NATS_INTEGRATION_TESTS=1 not set."

# Seed IDs — must match apps/control-api/seed.py
SEED_CAMPAIGN_ID = "00000000-0000-0000-0000-000000000220"
SEED_DEVICE_ID = "00000000-0000-0000-0000-000000000020"
SEED_SURFACE_ID = "00000000-0000-0000-0000-000000000031"
SEED_ADV_ORG_ID = "00000000-0000-0000-0000-000000000200"
SEED_CREATIVE_ASSET_ID = "00000000-0000-0000-0000-000000000222"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _raw_sql(sql: str, params=None):
    """Run a SELECT query (admin bypass) and return rows."""

    async def _run():
        engine = create_async_engine(DB_URL, echo=False)
        async with engine.connect() as conn:
            await conn.execute(
                text("SELECT set_config('app.rmp_is_admin', 'true', false)")
            )
            await conn.commit()
            result = await conn.execute(text(sql), params or {})
            rows = result.fetchall()
        await engine.dispose()
        return rows

    return asyncio.run(_run())


def _raw_exec(sql: str, params=None):
    """Run INSERT/UPDATE/DELETE statements with admin bypass."""

    async def _run():
        engine = create_async_engine(DB_URL, echo=False)
        async with engine.begin() as conn:
            await conn.execute(
                text("SELECT set_config('app.rmp_is_admin', 'true', true)")
            )
            for stmt in sql.split(";"):
                s = stmt.strip()
                if s and not s.startswith("--"):
                    await conn.execute(text(s), params or {})
        await engine.dispose()

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def ensure_env():
    if not REQUIRE_ENV:
        pytest.skip(SKIP_REASON)


@pytest.fixture(scope="module")
def nats_server(ensure_env):
    """Start a local nats-server with JetStream for the test module."""
    import subprocess
    import time
    import socket

    # Check if NATS is already running
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    result = s.connect_ex(("localhost", 4222))
    s.close()
    if result == 0:
        yield NATS_URL
        return

    proc = subprocess.Popen(
        ["nats-server", "-js", "-p", "4222"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.time() + 10
    started = False
    while time.time() < deadline:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        if s.connect_ex(("localhost", 4222)) == 0:
            s.close()
            started = True
            break
        s.close()
        time.sleep(0.2)
    if not started:
        proc.terminate()
        proc.wait()
        pytest.fail("nats-server did not start within 10s")

    yield NATS_URL

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture(scope="module")
def device_gateway_app():
    """Load the device-gateway FastAPI app with DB engine configured.

    The device-gateway uses ``Depends(get_session)`` which expects an
    ``engine`` parameter.  We monkeypatch ``get_session`` in the database
    module before loading the app so FastAPI can resolve it.
    """
    import importlib.util

    from packages.domain import database as _db
    from packages.domain.database import create_engine as _create_engine

    # Set DATABASE_URL for the app's module import
    os.environ.setdefault("DATABASE_URL", DB_URL)
    engine = _create_engine(DB_URL)
    _db.set_global_engine(engine)

    # Monkeypatch get_session → a zero-arg version using global engine
    _original_get_session = _db.get_session

    async def _get_session():
        eng = _db.get_global_engine()
        factory = _db.create_session_factory(eng)
        session = factory()
        try:
            yield session
        finally:
            await session.close()

    _db.get_session = _get_session

    try:
        repo_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )
        main_path = os.path.join(
            repo_root, "apps", "device-gateway", "main.py"
        )
        spec = importlib.util.spec_from_file_location(
            "device_gateway_main", main_path
        )
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        yield mod.app
    finally:
        _db.get_session = _original_get_session

        # Cleanup global engine after test
        import asyncio as _asyncio
        _asyncio.run(engine.dispose())


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------


def _prepare_campaign():
    """Set seed campaign to approved, device to active, flight to current window."""
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=1)
    end = now + timedelta(days=7)

    _raw_exec(
        """
        UPDATE campaigns SET status = 'approved' WHERE id = :cid
        """,
        {"cid": SEED_CAMPAIGN_ID},
    )
    _raw_exec(
        """
        UPDATE physical_devices SET status = 'active' WHERE id = :did
        """,
        {"did": SEED_DEVICE_ID},
    )
    _raw_exec(
        """
        UPDATE campaign_flights SET start_at = :start, end_at = :end
        WHERE campaign_id = :cid
        """,
        {"start": start, "end": end, "cid": SEED_CAMPAIGN_ID},
    )
    # Ensure creative is ready + approved (DB default is 'approved',
    # but be explicit for B3 test isolation safety).
    _raw_exec(
        """
        UPDATE creative_assets SET status = 'ready', moderation_status = 'approved'
        WHERE id = :caid
        """,
        {"caid": SEED_CREATIVE_ASSET_ID},
    )
    # Ensure display surface is active
    _raw_exec(
        """
        UPDATE display_surfaces SET is_active = true WHERE id = :sid
        """,
        {"sid": SEED_SURFACE_ID},
    )


def _reset_delivery_state():
    """Remove previously generated manifests/outbox events."""
    _raw_exec(
        """
        DELETE FROM delivery_attempts;
        DELETE FROM delivery_manifest_assets;
        DELETE FROM delivery_manifest_surfaces;
        DELETE FROM delivery_manifests;
        DELETE FROM delivery_plans;
        DELETE FROM outbox_events WHERE event_type LIKE 'delivery.manifest.%';
        DELETE FROM outbox_events WHERE event_type = 'campaign.approved'
            AND aggregate_id = :cid;
    """,
        {"cid": SEED_CAMPAIGN_ID},
    )


def _reset_campaign_state():
    """Reset campaign to draft, device to unregistered."""
    _raw_exec(
        "UPDATE campaigns SET status = 'draft' WHERE id = :cid",
        {"cid": SEED_CAMPAIGN_ID},
    )
    _raw_exec(
        "UPDATE physical_devices SET status = 'unregistered' WHERE id = :did",
        {"did": SEED_DEVICE_ID},
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPilotE2ESmoke:
    """B3: Full pilot business flow — campaign → manifest → device fetch."""

    def test_full_pilot_pipeline(self, nats_server, device_gateway_app):
        """Full pipeline: campaign approved → NATS → consumer → manifest →
        device-gateway returns it via HTTP with correct shape."""
        # ── 0. Setup ───────────────────────────────────────────────────
        _reset_delivery_state()
        _prepare_campaign()

        try:
            from packages.domain.repository import enqueue_outbox_event
            from packages.domain.database import create_engine

            engine = create_engine(DB_URL)

            # ── Entire pipeline + HTTP fetch runs in one asyncio.run()
            # ── so event loop is shared by engine, NATS, and httpx ────
            result = asyncio.run(
                _run_pipeline_and_fetch(
                    engine, nats_server, device_gateway_app
                )
            )

            manifest = result["manifest"]
            etag = result["etag"]

            # ── Assert manifest shape ─────────────────────────────────
            # Required top-level fields (universal-manifest-v1)
            assert "manifest_id" in manifest, "Missing manifest_id"
            assert "manifest_version" in manifest, "Missing manifest_version"
            assert "schema_version" in manifest, "Missing schema_version"
            assert "device_id" in manifest, "Missing device_id"
            assert "device_code" in manifest, "Missing device_code"
            assert "store_id" in manifest, "Missing store_id"
            assert "store_code" in manifest, "Missing store_code"
            assert "channel_type" in manifest, "Missing channel_type"
            assert "device_type" in manifest, "Missing device_type"
            assert (
                "display_surfaces" in manifest
            ), "Missing display_surfaces"
            assert "playlist" in manifest, "Missing playlist"
            assert "media_files" in manifest, "Missing media_files"
            assert "valid_from" in manifest, "Missing valid_from"
            assert "valid_to" in manifest, "Missing valid_to"
            assert (
                "offline_ttl_hours" in manifest
            ), "Missing offline_ttl_hours"
            assert "fallback_rules" in manifest, "Missing fallback_rules"
            assert "signature" in manifest, "Missing signature"
            assert "content_hash" in manifest, "Missing content_hash"

            # Value assertions
            assert manifest["device_id"] == SEED_DEVICE_ID
            assert manifest["device_code"] in ("KSO-001", "")
            assert isinstance(manifest["manifest_version"], int)
            assert manifest["manifest_version"] >= 1
            assert isinstance(manifest["display_surfaces"], list)
            assert len(manifest["display_surfaces"]) >= 1
            for surf in manifest["display_surfaces"]:
                assert "surface_id" in surf
                assert "surface_code" in surf
            assert isinstance(manifest["playlist"], list)
            assert len(manifest["playlist"]) >= 1
            for item in manifest["playlist"]:
                assert "creative_asset_id" in item
                assert "media_type" in item
                assert "sha256_checksum" in item

            # ── Security assertions ────────────────────────────────────
            manifest_str = json.dumps(manifest)
            assert "storage_bucket" not in manifest_str, (
                "Manifest leaked storage_bucket"
            )
            assert "storage_key" not in manifest_str, (
                "Manifest leaked storage_key"
            )
            assert "presigned_url" not in manifest_str, (
                "Manifest leaked presigned_url"
            )

            # ── ETag assertion ─────────────────────────────────────────
            assert etag is not None, "Missing ETag header"
            assert etag == manifest["content_hash"], (
                f"ETag {etag} != content_hash {manifest['content_hash']}"
            )

            # ── 304 / 401 / auth-provider already verified in pipeline
            assert result["status_304"] is True, "304 check failed"
            assert result["status_401_noauth"] is True, "401-noauth failed"
            assert result["status_401_wrong_provider"] is True, (
                "401-wrong-provider failed"
            )

        finally:
            _reset_delivery_state()
            _reset_campaign_state()


async def _run_pipeline_and_fetch(engine, nats_server, device_gateway_app):
    """Run the full pipeline + device-gateway HTTP fetch on a single loop."""
    import httpx
    from sqlalchemy import select
    from packages.domain.models import OutboxEvent
    from packages.domain.repository import enqueue_outbox_event
    from packages.security.jwt import create_access_token

    # ── 1. Enqueue outbox ────────────────────────────────────────────
    async with AsyncSession(engine) as session:
        await enqueue_outbox_event(
            session,
            event_type="campaign.approved",
            aggregate_type="campaign",
            aggregate_id=SEED_CAMPAIGN_ID,
            payload={"campaign_id": SEED_CAMPAIGN_ID},
            headers={"source_service": "e2e-test"},
        )
        await session.commit()

    async with AsyncSession(engine) as session:
        result = await session.execute(
            select(OutboxEvent.id, OutboxEvent.status)
            .where(
                OutboxEvent.aggregate_id == SEED_CAMPAIGN_ID,
                OutboxEvent.event_type == "campaign.approved",
            )
            .order_by(OutboxEvent.created_at.desc())
            .limit(1)
        )
        row = result.one()
        event_id = row[0]
        assert row[1] == "pending", f"Expected pending, got {row[1]}"

    # ── 2. Provision NATS ────────────────────────────────────────────
    from packages.services.jetstream_provisioning import (
        provision_campaign_delivery,
    )

    provision_result = await provision_campaign_delivery(
        nats_url=nats_server,
        stream="RMP",
        subjects=["campaign.>"],
        durable="rmp-campaign-consumer",
    )
    assert provision_result["stream"] == "RMP"

    # ── 3. Outbox relay → publish to NATS ────────────────────────────
    from packages.services.outbox_relay import OutboxRelay
    from packages.services.nats_publisher import NatsJetStreamPublisher

    publisher = NatsJetStreamPublisher(nats_server)
    await publisher.connect()
    try:
        relay = OutboxRelay(
            publisher=publisher,
            engine=engine,
            poll_interval=0.1,
            batch_size=10,
        )
        count = await relay.run_once()
        assert count >= 1, f"Relay should process >=1 event, got {count}"
    finally:
        await publisher.disconnect()

    async with AsyncSession(engine) as session:
        result = await session.execute(
            select(OutboxEvent.status).where(OutboxEvent.id == event_id)
        )
        status = result.scalar_one()
        assert status == "published", f"Expected published, got {status}"

    # ── 4. Consumer → generate manifests ─────────────────────────────
    from packages.services.campaign_event_handler import (
        NatsJetStreamCampaignConsumer,
    )

    consumer = NatsJetStreamCampaignConsumer(
        nats_url=nats_server,
        engine=engine,
        durable="rmp-campaign-consumer",
        subject="campaign.>",
        stream="RMP",
        batch_size=1,
        fetch_timeout=5.0,
    )
    await consumer.connect()
    try:
        task = asyncio.create_task(consumer.run())
        deadline = asyncio.get_event_loop().time() + 10.0
        while asyncio.get_event_loop().time() < deadline:
            if consumer.acked > 0 or consumer.errors > 0:
                break
            await asyncio.sleep(0.2)
        await consumer.stop()
        try:
            await asyncio.wait_for(task, timeout=5.0)
        except asyncio.TimeoutError:
            pass
    finally:
        await consumer.disconnect()

    assert consumer.acked >= 1, (
        f"Consumer should ack >=1, got acked={consumer.acked} "
        f"errors={consumer.errors}"
    )
    assert consumer.errors == 0, f"Consumer errors: {consumer.errors}"

    # ── 5. Verify manifest exists in DB ──────────────────────────────
    from packages.domain.database import get_global_engine

    eng = get_global_engine()
    async with AsyncSession(eng) as session:
        result = await session.execute(
            text(
                "SELECT manifest_id, campaign_id, status, content_hash "
                "FROM delivery_manifests "
                "WHERE campaign_id = :cid AND status = 'generated' "
                "ORDER BY generated_at DESC LIMIT 1"
            ),
            {"cid": SEED_CAMPAIGN_ID},
        )
        rows = result.fetchall()
    assert len(rows) >= 1, f"Expected >=1 generated manifest, got {len(rows)}"
    db_campaign_id = rows[0][1]
    assert db_campaign_id == SEED_CAMPAIGN_ID
    assert rows[0][2] == "generated"

    # ── 6. HTTP: device-gateway fetch ────────────────────────────────
    device_token = create_access_token(SEED_DEVICE_ID, "device")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=device_gateway_app),
        base_url="http://test",
    ) as client:
        # 6a. Fetch manifest
        response = await client.get(
            "/api/v1/device/manifest/latest",
            headers={"Authorization": f"Bearer {device_token}"},
        )
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: "
            f"{response.text[:200]}"
        )
        manifest = response.json()
        etag = response.headers.get("ETag")

        # 6b. 304 Not Modified
        response_304 = await client.get(
            "/api/v1/device/manifest/latest",
            headers={
                "Authorization": f"Bearer {device_token}",
                "If-None-Match": etag,
            },
        )
        status_304 = response_304.status_code == 304

        # 6c. No token → 401
        response_noauth = await client.get(
            "/api/v1/device/manifest/latest"
        )
        status_401_noauth = response_noauth.status_code == 401

        # 6d. Wrong provider → 401
        user_token = create_access_token(
            SEED_DEVICE_ID, "local_advertiser"
        )
        response_user = await client.get(
            "/api/v1/device/manifest/latest",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        status_401_wrong_provider = response_user.status_code == 401

    return {
        "manifest": manifest,
        "etag": etag,
        "status_304": status_304,
        "status_401_noauth": status_401_noauth,
        "status_401_wrong_provider": status_401_wrong_provider,
    }
