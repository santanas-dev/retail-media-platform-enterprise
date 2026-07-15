"""
Behavioral tests — Device Gateway Manifest Endpoint (Phase 4.2d).

Tests: valid device fetches manifest, 401/403 errors, 404 no manifest,
cross-device isolation.

Requires: RUN_BEHAVIORAL_TESTS=1, seed data, migration 008, generated manifest.

Due to a known Starlette BaseHTTPMiddleware + TestClient event-loop
conflict on the second sequential request, the 304 (ETag) test uses
asyncio.run() with httpx.AsyncClient directly.
"""

import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

os.environ["ENVIRONMENT"] = "dev"
os.environ["MANIFEST_SIGNING_KEY"] = (
    "behavioral-test-signing-key-at-least-32-chars"
)

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

DB_URL = os.environ.get(
    "BEHAVIORAL_DB_URL",
    "postgresql+asyncpg://retail_media:retail_media_dev@localhost:5432/retail_media_platform",
)

REQUIRE_ENV = os.environ.get("RUN_BEHAVIORAL_TESTS", "") == "1"
SKIP_REASON = "RUN_BEHAVIORAL_TESTS=1 not set."

SEED_CAMPAIGN_ID = "00000000-0000-0000-0000-000000000220"
SEED_DEVICE_ID = "00000000-0000-0000-0000-000000000020"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _run_raw_dml(sql: str, params=None):
    engine = create_async_engine(
        DB_URL, echo=False,
        connect_args={"command_timeout": 10},
        pool_size=1, max_overflow=0,
    )
    async with engine.begin() as conn:
        await conn.execute(
            text("SELECT set_config('app.rmp_is_admin', 'true', true)")
        )
        for stmt in sql.split(";"):
            s = stmt.strip()
            if s and not s.startswith("--"):
                await conn.execute(text(s), params or {})
    await engine.dispose()


async def _prepare():
    from datetime import datetime, timezone as _tz, timedelta
    now = datetime.now(_tz.utc)
    start = now - timedelta(days=1)
    end = now + timedelta(days=365)
    await _run_raw_dml(
        "UPDATE campaigns SET status = 'approved' WHERE id = :cid",
        {"cid": SEED_CAMPAIGN_ID},
    )
    await _run_raw_dml(
        "UPDATE physical_devices SET status = 'active' WHERE id = :did",
        {"did": SEED_DEVICE_ID},
    )
    await _run_raw_dml(
        "UPDATE campaign_flights SET start_at = :start, end_at = :end "
        "WHERE campaign_id = :cid",
        {"start": start, "end": end, "cid": SEED_CAMPAIGN_ID},
    )
    # Update contract validity to cover the flight window
    await _run_raw_dml(
        "UPDATE advertiser_contracts SET valid_from = :start, valid_until = :end "
        "WHERE id IN ("
        "  SELECT advertiser_contract_id FROM campaigns"
        "  WHERE id = :cid"
        ")",
        {"start": start, "end": end, "cid": SEED_CAMPAIGN_ID},
    )


async def _reset():
    await _run_raw_dml("""
        DELETE FROM delivery_attempts;
        DELETE FROM delivery_manifest_assets;
        DELETE FROM delivery_manifest_surfaces;
        DELETE FROM delivery_manifests;
        DELETE FROM delivery_plans;
        DELETE FROM outbox_events WHERE event_type LIKE 'delivery.manifest.%';
    """)


async def _generate():
    from packages.domain.delivery import generate_manifests_for_campaign
    engine = create_async_engine(
        DB_URL, echo=False,
        connect_args={"command_timeout": 10},
        pool_size=1, max_overflow=0,
    )
    AsyncSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False,
    )
    async with AsyncSessionLocal() as session:
        result = await generate_manifests_for_campaign(
            session, SEED_CAMPAIGN_ID,
        )
        await session.commit()
    await engine.dispose()
    return result


def _run_sync(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _run_setup():
    _run_sync(_prepare())
    _run_sync(_reset())
    _run_sync(_generate())


def _create_device_token(device_id: str = SEED_DEVICE_ID) -> str:
    import time, uuid, jwt as pyjwt
    from packages.security.config import get_security_config
    cfg = get_security_config()
    now = int(time.time())
    claims = {
        "sub": device_id,
        "auth_provider": "device",
        "device_code": "DEV-001",
        "store_id": "00000000-0000-0000-0000-000000000003",
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + (cfg.jwt_access_token_ttl_minutes * 60),
        "iss": cfg.jwt_issuer,
        "aud": cfg.jwt_audience,
    }
    return pyjwt.encode(claims, cfg.jwt_secret, algorithm=cfg.jwt_algorithm)


def _make_test_client():
    sys.path.insert(
        0,
        os.path.join(
            os.path.dirname(__file__), "..", "..", "apps", "device-gateway",
        ),
    )
    from fastapi.testclient import TestClient
    import importlib
    if "main" in sys.modules:
        del sys.modules["main"]
    main = __import__("main")

    main.app.dependency_overrides.clear()

    engine = create_async_engine(DB_URL, echo=False)
    main.set_global_engine(engine)

    async def override_get_db():
        AsyncSessionLocal = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False,
        )
        async with AsyncSessionLocal() as session:
            yield session

    main.app.dependency_overrides[main.get_db] = override_get_db
    return TestClient(main.app)


def _run_async_with_setup(app):
    """Run async httpx requests in a dedicated event loop with a fresh 
    engine/lifespan.  Used for multi-request tests that hit the Starlette 
    TestClient event-loop conflict."""
    import httpx
    import importlib

    sys.path.insert(
        0,
        os.path.join(
            os.path.dirname(__file__), "..", "..", "apps", "device-gateway",
        ),
    )
    if "main" in sys.modules:
        del sys.modules["main"]
    main = __import__("main")
    main.app.dependency_overrides.clear()

    engine = create_async_engine(DB_URL, echo=False)
    main.set_global_engine(engine)

    async def override_get_db():
        AsyncSessionLocal = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False,
        )
        async with AsyncSessionLocal() as session:
            yield session

    main.app.dependency_overrides[main.get_db] = override_get_db

    async def _run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=main.app),
            base_url="http://testserver",
        ) as client:
            return await app(client)

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_run())
    finally:
        loop.run_until_complete(engine.dispose())
        loop.close()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDeviceManifestEndpoint:

    @pytest.fixture(autouse=True)
    def setup(self, db_available):
        pass

    def test_valid_device_fetches_manifest(self):
        _run_setup()
        client = _make_test_client()
        token = _create_device_token()
        response = client.get(
            "/api/v1/device/manifest/latest",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert "manifest_id" in data
        assert data["device_id"] == SEED_DEVICE_ID
        assert len(data.get("display_surfaces", [])) >= 1
        assert "etag" in response.headers
        assert response.headers["etag"].strip('"') == data.get("content_hash", "")
        assert "channel_type" in data, "Missing channel_type"
        assert "offline_ttl_hours" in data, "Missing offline_ttl_hours"
        # ── S-035c: signature must be non-empty when signing key is configured ──
        sig = data.get("signature", {})
        assert sig.get("algorithm") == "HMAC-SHA256", (
            "Missing or wrong signature algorithm"
        )
        sig_value = sig.get("value", "")
        assert len(sig_value) == 64, (
            f"Expected 64-char hex HMAC-SHA256 signature, got {len(sig_value)}"
        )
        unsafe = (
            "storage_bucket", "storage_key", "presigned_url",
            "access_key", "secret_key", "token", "password",
        )
        body = str(data).lower()
        for term in unsafe:
            assert term not in body, f"Manifest leaks {term}"

    def test_if_none_match_returns_304(self):
        """Uses httpx.AsyncClient directly to avoid Starlette
        TestClient's BaseHTTPMiddleware event-loop conflict on
        the second sequential request."""
        import httpx
        _run_sync(_prepare())
        _run_sync(_reset())
        _run_sync(_generate())
        token = _create_device_token()
        _engine_ref = []

        async def _test(client):
            # First fetch
            resp1 = await client.get(
                "/api/v1/device/manifest/latest",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp1.status_code == 200
            etag = resp1.headers.get("etag", "")
            assert etag, "ETag must be non-empty"

            # Second fetch with If-None-Match
            resp2 = await client.get(
                "/api/v1/device/manifest/latest",
                headers={
                    "Authorization": f"Bearer {token}",
                    "If-None-Match": etag,
                },
            )
            assert resp2.status_code == 304
            assert resp2.content == b""
            assert "etag" in resp2.headers

        _run_async_with_setup(_test)

    def test_no_auth_returns_401(self):
        client = _make_test_client()
        response = client.get("/api/v1/device/manifest/latest")
        assert response.status_code == 401

    def test_user_token_rejected(self):
        client = _make_test_client()
        import time, uuid, jwt as pyjwt
        from packages.security.config import get_security_config
        cfg = get_security_config()
        now = int(time.time())
        claims = {
            "sub": "some-user-id",
            "auth_provider": "ad",
            "jti": str(uuid.uuid4()),
            "iat": now,
            "exp": now + 900,
            "iss": cfg.jwt_issuer,
            "aud": cfg.jwt_audience,
        }
        user_token = pyjwt.encode(claims, cfg.jwt_secret, algorithm=cfg.jwt_algorithm)
        response = client.get(
            "/api/v1/device/manifest/latest",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 401

    def test_another_device_manifest_isolation(self):
        _run_setup()
        client = _make_test_client()
        import time, uuid, jwt as pyjwt
        from packages.security.config import get_security_config
        cfg = get_security_config()
        now = int(time.time())
        other_device_id = "00000000-0000-0000-0000-000000000099"
        claims = {
            "sub": other_device_id,
            "auth_provider": "device",
            "device_code": "DEV-099",
            "jti": str(uuid.uuid4()),
            "iat": now,
            "exp": now + 900,
            "iss": cfg.jwt_issuer,
            "aud": cfg.jwt_audience,
        }
        token = pyjwt.encode(claims, cfg.jwt_secret, algorithm=cfg.jwt_algorithm)
        response = client.get(
            "/api/v1/device/manifest/latest",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404

    def test_inactive_device_rejected(self):
        _run_setup()
        _run_sync(
            _run_raw_dml(
                "UPDATE physical_devices SET status = 'offline' WHERE id = :did",
                {"did": SEED_DEVICE_ID},
            )
        )
        client = _make_test_client()
        token = _create_device_token()
        response = client.get(
            "/api/v1/device/manifest/latest",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    def test_no_manifest_returns_404(self):
        _run_sync(_prepare())
        _run_sync(_reset())
        client = _make_test_client()
        token = _create_device_token()
        response = client.get(
            "/api/v1/device/manifest/latest",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404
