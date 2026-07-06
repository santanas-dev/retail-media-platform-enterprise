"""
Behavioral tests — Device Gateway Manifest Endpoint (Phase 4.2d).

Tests: valid device fetches manifest, 401/403 errors, 404 no manifest,
cross-device isolation.

Requires: RUN_BEHAVIORAL_TESTS=1, seed data, migration 008, generated manifest.
"""

import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

os.environ["ENVIRONMENT"] = "dev"

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
SEED_SURFACE_ID = "00000000-0000-0000-0000-000000000031"


def _raw_sql(sql: str, params=None):
    async def _run():
        engine = create_async_engine(DB_URL, echo=False)
        async with engine.connect() as conn:
            result = await conn.execute(text(sql), params or {})
            rows = result.fetchall()
        await engine.dispose()
        return rows
    return asyncio.run(_run())


def _raw_exec(sql: str, params=None):
    async def _run():
        engine = create_async_engine(DB_URL, echo=False)
        async with engine.begin() as conn:
            for stmt in sql.split(";"):
                s = stmt.strip()
                if s and not s.startswith("--"):
                    await conn.execute(text(s), params or {})
        await engine.dispose()
    asyncio.run(_run())


@pytest.fixture
def db_available():
    if not REQUIRE_ENV:
        pytest.skip(SKIP_REASON)


def _prepare_approved_campaign_and_manifest():
    """Ensure campaign is approved, device active, and a manifest exists."""
    from datetime import datetime, timezone as _tz, timedelta
    now = datetime.now(_tz.utc)
    start = now - timedelta(days=1)
    end = now + timedelta(days=7)

    _raw_exec(
        "UPDATE campaigns SET status = 'approved' WHERE id = :cid",
        {"cid": SEED_CAMPAIGN_ID},
    )
    _raw_exec(
        "UPDATE physical_devices SET status = 'active' WHERE id = :did",
        {"did": SEED_DEVICE_ID},
    )
    _raw_exec(
        "UPDATE campaign_flights SET start_at = :start, end_at = :end "
        "WHERE campaign_id = :cid",
        {"start": start, "end": end, "cid": SEED_CAMPAIGN_ID},
    )


def _reset_manifest_state():
    _raw_exec("""
        DELETE FROM delivery_attempts;
        DELETE FROM delivery_manifest_assets;
        DELETE FROM delivery_manifest_surfaces;
        DELETE FROM delivery_manifests;
        DELETE FROM delivery_plans;
        DELETE FROM outbox_events WHERE event_type LIKE 'delivery.manifest.%';
    """)


def _generate_manifest():
    """Run the manifest generator to produce a real manifest in the DB."""
    from packages.domain.delivery import generate_manifests_for_campaign

    async def _run():
        engine = create_async_engine(DB_URL, echo=False)
        AsyncSessionLocal = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False,
        )
        async with AsyncSessionLocal() as session:
            result = await generate_manifests_for_campaign(
                session, SEED_CAMPAIGN_ID,
            )
            await session.commit()
            return result
        await engine.dispose()

    return asyncio.run(_run())


def _create_device_token(device_id: str = SEED_DEVICE_ID) -> str:
    """Create a valid device JWT for testing."""
    from packages.security.jwt import create_access_token
    # create_access_token is user-oriented; we craft a device token manually
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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDeviceManifestEndpoint:

    @pytest.fixture(autouse=True)
    def setup(self, db_available):
        _prepare_approved_campaign_and_manifest()
        _reset_manifest_state()
        _generate_manifest()

    def _client(self):
        """Create FastAPI TestClient with device-gateway app and DB override."""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "apps", "device-gateway"))
        from fastapi.testclient import TestClient
        main = __import__("main")
        app = main.app

        # Override get_session to use a real async session
        async def override_get_session():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False,
            )
            async with AsyncSessionLocal() as session:
                yield session
            await engine.dispose()

        app.dependency_overrides[main.get_session] = override_get_session
        return TestClient(app)

    def test_valid_device_fetches_manifest(self):
        client = self._client()
        token = _create_device_token()
        response = client.get(
            "/api/v1/device/manifest/latest",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "manifest_id" in data
        assert data["device_id"] == SEED_DEVICE_ID
        assert len(data.get("display_surfaces", [])) >= 1
        # Verify ETag header present
        assert "etag" in response.headers
        assert response.headers["etag"] == data.get("content_hash", "")

    def test_if_none_match_returns_304(self):
        """If-None-Match matching current content_hash returns 304."""
        client = self._client()
        token = _create_device_token()

        # First fetch to get ETag
        response1 = client.get(
            "/api/v1/device/manifest/latest",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response1.status_code == 200
        etag = response1.headers.get("etag", "")

        # Second fetch with If-None-Match
        response2 = client.get(
            "/api/v1/device/manifest/latest",
            headers={
                "Authorization": f"Bearer {token}",
                "If-None-Match": etag,
            },
        )
        assert response2.status_code == 304
        # 304 must have no body
        assert response2.content == b"" or response2.content == b"null"
        # ETag should still be present on 304
        assert "etag" in response2.headers

    def test_no_auth_returns_401(self):
        client = self._client()
        response = client.get("/api/v1/device/manifest/latest")
        assert response.status_code == 401

    def test_user_token_rejected(self):
        """A user token (auth_provider=ad) must not access device endpoint."""
        client = self._client()
        # Create a user-style token
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
        """Device A cannot access Device B's manifest via different device_id in token."""
        client = self._client()
        # Create token for a different, non-existent device
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
        # Device not found → 404 (no manifest for this device)
        # The endpoint checks device existence first, but the token's sub
        # identifies the device. A non-existent device gets 404.
        assert response.status_code in (401, 403, 404)

    def test_inactive_device_rejected(self):
        """Inactive/offline device must not receive manifest."""
        client = self._client()
        _raw_exec(
            "UPDATE physical_devices SET status = 'offline' WHERE id = :did",
            {"did": SEED_DEVICE_ID},
        )
        token = _create_device_token()
        response = client.get(
            "/api/v1/device/manifest/latest",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
        # Restore
        _raw_exec(
            "UPDATE physical_devices SET status = 'active' WHERE id = :did",
            {"did": SEED_DEVICE_ID},
        )

    def test_no_manifest_returns_404(self):
        """Device with no generated manifests gets 404."""
        client = self._client()
        # Reset manifests but keep device active
        _reset_manifest_state()
        token = _create_device_token()
        response = client.get(
            "/api/v1/device/manifest/latest",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404
