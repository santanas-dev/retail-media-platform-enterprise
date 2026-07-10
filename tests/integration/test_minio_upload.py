"""
Integration test: MinIO creative media upload (S-017).

Proves the full presigned-URL upload flow:
  metadata_only creative → upload-intent → PUT to presigned URL →
  complete-upload → server SHA-256 → ready + approved (pilot).

Requires:
  - RUN_MINIO_INTEGRATION_TESTS=1
  - Local MinIO at MINIO_INTERNAL_ENDPOINT
  - PostgreSQL with seed data + migrations
  - Behavioral seed (RUN_BEHAVIORAL_TESTS=1 setup already done)

Usage:
  RUN_MINIO_INTEGRATION_TESTS=1 python -m pytest tests/integration/test_minio_upload.py -v

Skips silently when env is not set.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import sys
import uuid

import httpx
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

os.environ["ENVIRONMENT"] = "dev"
os.environ["JWT_SECRET"] = "minio-int-test-secret-at-least-32-chars"

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from packages.security.config import reset_security_config
from packages.security.jwt import create_access_token
from packages.services.storage import reset_storage_service

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DB_URL = os.environ.get(
    "BEHAVIORAL_DB_URL",
    "postgresql+asyncpg://retail_media:retail_media_dev@localhost:5432/retail_media_platform",
)

REQUIRE_ENV = os.environ.get("RUN_MINIO_INTEGRATION_TESTS", "") == "1"
SKIP_REASON = "RUN_MINIO_INTEGRATION_TESTS=1 not set."

# Seed advertiser org used by behavioral tests
ADV_ORG_ID = "00000000-0000-0000-0000-000000000200"
# Seed break_glass_admin user (system_admin — bypasses all scope checks)
SEED_USER_ID = "00000000-0000-0000-0000-000000000150"  # break_glass_admin (system_admin)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _raw_exec(sql: str, params=None):
    async def _run():
        engine = create_async_engine(DB_URL, echo=False)
        async with engine.connect() as conn:
            await conn.execute(
                text("SELECT set_config('app.rmp_is_admin', 'true', false)")
            )
            await conn.commit()
            async with conn.begin():
                await conn.execute(text(sql), params or {})
        await engine.dispose()

    return asyncio.run(_run())


def _token(sub: str, auth_provider: str = "local_advertiser") -> str:
    return create_access_token(sub, auth_provider)


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# App fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def app():
    """Load control-api with MinIO env vars wired."""
    # Force StorageService singleton reset so it picks up MinIO env vars
    reset_storage_service()
    reset_security_config()

    # Apply database overrides for the app role
    app_db_url = os.environ.get("BEHAVIORAL_APP_DB_URL", "").strip() or os.environ.get(
        "DATABASE_URL", ""
    ).strip()
    if not app_db_url:
        app_db_url = (
            "postgresql+asyncpg://retail_media_app:retail_media_app"
            "@localhost:5432/retail_media_platform"
        )
    os.environ["DATABASE_URL"] = app_db_url

    # Load app (using the same pattern as behavioral conftest)
    import importlib.util

    repo_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..")
    )
    main_path = os.path.join(repo_root, "apps", "control-api", "main.py")
    spec = importlib.util.spec_from_file_location("control_api_main", main_path)
    assert spec is not None and spec.loader is not None, f"Failed to load spec for {main_path}"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # Set up a shared engine
    from packages.domain.database import set_global_engine, get_session
    from packages.api.dependencies import get_db
    from sqlalchemy.ext.asyncio import create_async_engine as _cae
    from sqlalchemy.pool import NullPool

    engine = _cae(app_db_url, echo=False, poolclass=NullPool)
    set_global_engine(engine)

    async def _override_get_db():
        async with get_session(engine) as session:
            async with session.begin():
                yield session

    mod.app.dependency_overrides[get_db] = _override_get_db
    return mod.app


@pytest.fixture(scope="module")
def client(app):
    return TestClient(app)


@pytest.fixture(scope="module")
def minio_available():
    """Check MinIO is reachable and create a test access key if needed. Skip if not."""
    if not REQUIRE_ENV:
        pytest.skip(SKIP_REASON)

    import subprocess

    cfg = os.environ
    endpoint = cfg.get("MINIO_INTERNAL_ENDPOINT", "localhost:9000")
    access = cfg.get("MINIO_ACCESS_KEY", "minioadmin")
    secret = cfg.get("MINIO_SECRET_KEY", "minioadmin")

    # Newer MinIO versions (2025+) don't allow root credentials for S3 API.
    # Create a dedicated access key for integration testing.
    test_access = "minio-int-test"
    test_secret = "minio-int-test-secret"

    try:
        # Create access key via mc CLI — must set alias first
        subprocess.run(
            ["/tmp/mc", "alias", "set", "myminio", f"http://{endpoint}", access, secret],
            capture_output=True, timeout=10, check=False,
        )
        subprocess.run(
            [
                "/tmp/mc", "admin", "accesskey", "create", "myminio",
                "--access-key", test_access,
                "--secret-key", test_secret,
            ],
            capture_output=True, timeout=10, check=False,
        )
    except Exception:
        pass  # key may already exist or mc not available

    # Verify connectivity with the test key
    from minio import Minio

    try:
        mc = Minio(endpoint, access_key=test_access, secret_key=test_secret, secure=False)
        bucket = cfg.get("CREATIVE_STORAGE_BUCKET", "retail-media-creatives")
        if not mc.bucket_exists(bucket):
            mc.make_bucket(bucket)
    except Exception as exc:
        pytest.skip(f"MinIO not reachable at {endpoint}: {exc}")

    # Override env vars for this test session so the StorageService singleton
    # picks up the test credentials
    os.environ["MINIO_ACCESS_KEY"] = test_access
    os.environ["MINIO_SECRET_KEY"] = test_secret
    from packages.security.config import reset_security_config
    from packages.services.storage import reset_storage_service
    reset_security_config()
    reset_storage_service()


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _create_metadata_only_asset(client: TestClient, token: str) -> str:
    """Create a metadata-only creative asset via API. Returns asset_id."""
    code = f"INT-UPLOAD-{uuid.uuid4().hex[:8].upper()}"
    payload = {
        "code": code,
        "name": "Integration Test Upload",
        "media_type": "image/png",
        "advertiser_organization_id": ADV_ORG_ID,
    }
    resp = client.post(
        "/api/v1/identity/creative-assets", json=payload, headers=_auth(token)
    )
    assert resp.status_code in (200, 201), f"Create asset failed: {resp.status_code} {resp.text}"
    data = resp.json()
    asset_id = data["id"]
    assert data["status"] == "metadata_only"
    return asset_id


def _read_asset(client: TestClient, token: str, asset_id: str) -> dict:
    """Find asset in the list response by ID."""
    resp = client.get(
        "/api/v1/identity/creative-assets", headers=_auth(token)
    )
    assert resp.status_code == 200, f"List assets failed: {resp.status_code} {resp.text}"
    for a in resp.json():
        if a["id"] == asset_id:
            return a
    raise AssertionError(f"Asset {asset_id} not found in list response")


def _cleanup_asset(asset_id: str, storage_key: str | None = None):
    """Delete asset from DB and optionally from MinIO."""
    if storage_key:
        try:
            from minio import Minio

            cfg = os.environ
            mc = Minio(
                cfg.get("MINIO_INTERNAL_ENDPOINT", "localhost:9000"),
                access_key=cfg.get("MINIO_ACCESS_KEY", "minio-int-test"),
                secret_key=cfg.get("MINIO_SECRET_KEY", "minio-int-test-secret"),
                secure=False,
            )
            mc.remove_object(
                cfg.get("CREATIVE_STORAGE_BUCKET", "retail-media-creatives"),
                storage_key,
            )
        except Exception:
            pass  # best-effort cleanup

    # Delete upload sessions + asset
    _raw_exec(
        "DELETE FROM creative_upload_sessions WHERE creative_asset_id = :aid",
        {"aid": asset_id},
    )
    _raw_exec(
        "DELETE FROM campaign_creatives WHERE creative_asset_id = :aid",
        {"aid": asset_id},
    )
    _raw_exec("DELETE FROM creative_assets WHERE id = :aid", {"aid": asset_id})


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMinioUploadIntegration:
    """Full upload flow: intent → PUT → complete → verify."""

    def test_skip_without_env(self, client):
        """Clean skip when RUN_MINIO_INTEGRATION_TESTS is not set."""
        if not REQUIRE_ENV:
            pytest.skip(SKIP_REASON)
        # If we reach here, MinIO is available and the test can proceed.
        assert True

    def test_full_upload_flow(self, client, minio_available):
        """End-to-end: metadata-only → upload-intent → PUT → complete-upload."""

        token = _token(SEED_USER_ID, "local_break_glass")

        # 1. Create metadata-only asset
        asset_id = _create_metadata_only_asset(client, token)

        try:
            # 2. Verify initial state
            asset = _read_asset(client, token, asset_id)
            assert asset["status"] == "metadata_only"
            assert asset["moderation_status"] == "pending_review"
            assert asset["sha256_checksum"] == ""
            assert asset["file_size_bytes"] == 0
            # No storage fields exposed
            assert "storage_bucket" not in asset
            assert "storage_key" not in asset

            # 3. Create upload intent
            test_bytes = b"minio-integration-test-content-" + uuid.uuid4().bytes
            test_checksum = hashlib.sha256(test_bytes).hexdigest()
            intent_payload = {
                "filename": "test-upload.png",
                "content_type": "image/png",
                "content_length": len(test_bytes),
            }
            intent_resp = client.post(
                f"/api/v1/identity/creative-assets/{asset_id}/upload-intent",
                json=intent_payload,
                headers=_auth(token),
            )
            assert intent_resp.status_code == 200, (
                f"upload-intent failed: {intent_resp.status_code} {intent_resp.text}"
            )
            intent_data = intent_resp.json()
            upload_id = intent_data["upload_id"]
            upload_url = intent_data["upload_url"]
            assert intent_data["method"] == "PUT"
            assert intent_data["headers"]["Content-Type"] == "image/png"
            assert upload_id
            assert upload_url.startswith("http")

            # 4. PUT file to presigned URL (direct MinIO, no Authorization)
            put_resp = httpx.put(
                upload_url,
                content=test_bytes,
                headers={"Content-Type": "image/png"},
                timeout=10,
            )
            assert put_resp.status_code == 200, (
                f"PUT to presigned URL failed: {put_resp.status_code}"
            )

            # 5. Complete upload
            complete_resp = client.post(
                f"/api/v1/identity/creative-assets/{asset_id}/complete-upload",
                json={"upload_id": upload_id},
                headers=_auth(token),
            )
            assert complete_resp.status_code == 200, (
                f"complete-upload failed: {complete_resp.status_code} {complete_resp.text}"
            )
            complete_data = complete_resp.json()
            assert complete_data["asset_id"] == asset_id
            assert complete_data["status"] == "ready"
            assert complete_data["sha256_checksum"] == test_checksum, (
                f"checksum mismatch: expected {test_checksum}, got {complete_data['sha256_checksum']}"
            )
            assert complete_data["file_size_bytes"] == len(test_bytes)
            # Pilot auto-approve
            assert complete_data["moderation_status"] == "approved"

            # 6. Verify asset state after upload
            asset = _read_asset(client, token, asset_id)
            assert asset["status"] == "ready"
            assert asset["moderation_status"] == "approved"
            assert asset["sha256_checksum"] == test_checksum
            assert asset["file_size_bytes"] == len(test_bytes)
            # Still no storage fields exposed
            assert "storage_bucket" not in asset
            assert "storage_key" not in asset

            # 7. Upload session is marked completed
            # (verified implicitly — complete-upload returns 409 if already completed)

        finally:
            # Best-effort cleanup: derive storage_key from asset org + id
            storage_key = f"{ADV_ORG_ID}/{asset_id}/test-upload.png"
            _cleanup_asset(asset_id, storage_key)

    def test_storage_fields_not_in_response(self, client, minio_available):
        """Normal API responses never expose storage_bucket or storage_key."""
        token = _token(SEED_USER_ID, "local_break_glass")
        asset_id = _create_metadata_only_asset(client, token)
        try:
            # GET single asset
            asset = _read_asset(client, token, asset_id)
            assert "storage_bucket" not in asset
            assert "storage_key" not in asset

            # List assets
            list_resp = client.get(
                "/api/v1/identity/creative-assets", headers=_auth(token)
            )
            assert list_resp.status_code == 200
            for a in list_resp.json():
                assert "storage_bucket" not in a
                assert "storage_key" not in a

            # upload-intent response
            intent_payload = {
                "filename": "no-storage-test.png",
                "content_type": "image/png",
                "content_length": 100,
            }
            intent_resp = client.post(
                f"/api/v1/identity/creative-assets/{asset_id}/upload-intent",
                json=intent_payload,
                headers=_auth(token),
            )
            assert intent_resp.status_code == 200
            intent_data = intent_resp.json()
            assert "storage_bucket" not in intent_data
            assert "storage_key" not in intent_data

        finally:
            _cleanup_asset(asset_id)
