"""
Behavioral tests — Creative Asset Intake (S-009j).

Tests: standalone creative asset creation (metadata only), auth, scope,
outbox, and NOBYPASSRLS.

Requires: RUN_BEHAVIORAL_TESTS=1, migrations applied, seed run.
"""

import asyncio
import json
import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

os.environ["ENVIRONMENT"] = "dev"

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from packages.security.config import reset_security_config
from packages.security.jwt import create_access_token

DB_URL = os.environ.get(
    "BEHAVIORAL_DB_URL",
    "postgresql+asyncpg://retail_media:retail_media_dev@localhost:5432/retail_media_platform",
)

REQUIRE_ENV = os.environ.get("RUN_BEHAVIORAL_TESTS", "") == "1"
SKIP_REASON = "RUN_BEHAVIORAL_TESTS=1 not set."

ADV1_ORG_ID = "00000000-0000-0000-0000-000000000200"
ADV2_ORG_ID = "00000000-0000-0000-0000-000000000201"  # for cross-org tests


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _token(sub):
    return create_access_token(sub, "local_advertiser")


def _raw_sql(sql: str, params=None):
    async def _run():
        engine = create_async_engine(DB_URL, echo=False)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT set_config('app.rmp_is_admin', 'true', false)"))
            await conn.commit()
            result = await conn.execute(text(sql), params or {})
            rows = result.fetchall()
        await engine.dispose()
        return rows
    return asyncio.run(_run())


def _raw_exec(sql: str, params=None):
    async def _run():
        engine = create_async_engine(DB_URL, echo=False)
        async with engine.begin() as conn:
            await conn.execute(text("SELECT set_config('app.rmp_is_admin', 'true', true)"))
            for stmt in sql.split(";"):
                s = stmt.strip()
                if s and not s.startswith("--"):
                    await conn.execute(text(s), params or {})
        await engine.dispose()
    asyncio.run(_run())


@pytest.fixture
def app(db_available):
    import importlib.util
    reset_security_config()
    main_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "apps", "control-api", "main.py",
    )
    spec = importlib.util.spec_from_file_location("control_api_main", main_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.app


@pytest.fixture
def client(app, db_available, test_users):
    return TestClient(app)


@pytest.fixture
def user_ids(test_users):
    return test_users


@pytest.mark.skipif(not REQUIRE_ENV, reason=SKIP_REASON)
class TestCreateCreativeAssetBehavioral:
    """NOBYPASSRLS: creative asset intake endpoint."""

    _CREATED_ASSET_ID = None

    def test_no_token_returns_401(self, client):
        resp = client.post("/api/v1/identity/creative-assets", json={
            "code": "C", "name": "N", "media_type": "image",
        })
        assert resp.status_code == 401

    def test_no_permission_returns_403(self, client, user_ids):
        """User without campaigns.manage gets 403."""
        token = _token(user_ids["noperms"])
        resp = client.post(
            "/api/v1/identity/creative-assets",
            json={"code": "CR-NOPERM", "name": "No Permission", "media_type": "image"},
            headers=_auth(token),
        )
        assert resp.status_code == 403

    def test_authorized_create_succeeds(self, client, user_ids):
        """readonly (system_admin) creates a creative asset — must provide org."""
        token = _token(user_ids["readonly"])
        resp = client.post(
            "/api/v1/identity/creative-assets",
            json={
                "code": "CR-BEH-001",
                "name": "Behavioral Test Creative Asset",
                "media_type": "image",
                "advertiser_organization_id": ADV1_ORG_ID,
                "resolution_w": 1920,
                "resolution_h": 1080,
            },
            headers=_auth(token),
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["code"] == "CR-BEH-001"
        assert data["name"] == "Behavioral Test Creative Asset"
        assert data["media_type"] == "image"
        assert data["resolution_w"] == 1920
        assert data["resolution_h"] == 1080
        assert data["status"] == "metadata_only"
        # P1 fix: no fake checksum — empty string means "no file uploaded"
        assert data["sha256_checksum"] == "", \
            f"Expected empty checksum for metadata-only, got '{data['sha256_checksum']}'"
        aid = data["id"]
        TestCreateCreativeAssetBehavioral._CREATED_ASSET_ID = aid

        # Verify outbox event
        rows = _raw_sql(
            "SELECT event_type, status FROM outbox_events WHERE aggregate_id = :aid",
            {"aid": aid},
        )
        assert len(rows) == 1, f"Expected 1 outbox event, got {len(rows)}"
        assert rows[0][0] == "creative_asset.created"

    def test_response_has_no_storage_fields(self, client, user_ids):
        """CreativeAssetOut must never expose storage_bucket, storage_key,
        or any presigned URL."""
        token = _token(user_ids["readonly"])
        resp = client.post(
            "/api/v1/identity/creative-assets",
            json={"code": "CR-NOSTORAGE", "name": "No Storage", "media_type": "video",
                  "advertiser_organization_id": ADV1_ORG_ID},
            headers=_auth(token),
        )
        assert resp.status_code == 201
        data = resp.json()
        for forbidden in ("storage_bucket", "storage_key", "presigned_url", "s3", "bucket"):
            assert forbidden not in data, f"Response must not contain '{forbidden}'"

    def test_cross_org_create_rejected(self, client, user_ids):
        """Advertiser-scoped user cannot create an asset in another org."""
        # 'advertiser' user is scoped to ADV1_ORG_ID (200)
        token = _token(user_ids["advertiser"])
        resp = client.post(
            "/api/v1/identity/creative-assets",
            json={
                "code": "CR-XORG", "name": "Cross Org Attempt", "media_type": "image",
                "advertiser_organization_id": ADV2_ORG_ID,  # different org
            },
            headers=_auth(token),
        )
        # Scoped user cannot specify an org outside their scope → 422
        assert resp.status_code == 422, (
            f"Expected 422 for cross-org, got {resp.status_code}: {resp.text}"
        )

    @classmethod
    def teardown_class(cls):
        """Cleanup created test assets."""
        if cls._CREATED_ASSET_ID:
            _raw_exec(
                f"DELETE FROM creative_assets WHERE id = '{cls._CREATED_ASSET_ID}'"
            )


# ---------------------------------------------------------------------------
# P1 proof: metadata-only creatives block approval
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not REQUIRE_ENV, reason=SKIP_REASON)
class TestMetadataOnlyBlocksApproval:
    """Proof: metadata-only (empty checksum) creative → approval rejected.

    Uses seed campaign CAMP-2026-001 which already has flights, placements,
    and real creatives.  Attaching a metadata-only creative makes the whole
    campaign un-approvable.
    """

    SEED_CID = "00000000-0000-0000-0000-000000000220"
    _meta_asset_id = None

    def _draft(self):
        _raw_exec("UPDATE campaigns SET status = 'draft' WHERE code = 'CAMP-2026-001'")

    def _cleanup_meta(self):
        if self._meta_asset_id:
            _raw_exec(
                f"DELETE FROM campaign_creatives WHERE creative_asset_id = '{self._meta_asset_id}';"
                f"DELETE FROM creative_assets WHERE id = '{self._meta_asset_id}'"
            )
            self._meta_asset_id = None

    def test_metadata_only_creative_blocks_approval(self, client, user_ids):
        """Attach metadata-only creative → request-approval returns 422."""
        self._draft()
        token = _token(user_ids["readonly"])
        cid = self.SEED_CID

        try:
            # 1. Create metadata-only creative asset (empty checksum)
            resp = client.post(
                "/api/v1/identity/creative-assets",
                json={"code": "CR-PROOF-META", "name": "Proof Metadata Only", "media_type": "image",
                      "advertiser_organization_id": ADV1_ORG_ID},
                headers=_auth(token),
            )
            assert resp.status_code == 201, resp.text
            data = resp.json()
            assert data["sha256_checksum"] == "", "Must be empty for metadata-only"
            assert data["status"] == "metadata_only"
            self._meta_asset_id = data["id"]

            # 2. Attach it to seed campaign
            resp = client.post(
                f"/api/v1/identity/campaigns/{cid}/creatives/attach",
                json={"creative_asset_id": self._meta_asset_id, "sort_order": 99},
                headers=_auth(token),
            )
            assert resp.status_code == 201, f"Attach failed: {resp.text}"

            # 3. Request approval — must be rejected
            resp = client.post(
                f"/api/v1/identity/campaigns/{cid}/request-approval",
                headers=_auth(token),
            )
            assert resp.status_code == 422, (
                f"Expected 422 for metadata-only creative, got {resp.status_code}: {resp.text}"
            )
            detail = resp.json().get("detail", "")
            assert "Metadata-only" in detail or "uploaded files" in detail, (
                f"Missing metadata-only rejection message in: {detail}"
            )

            # 4. Campaign must remain in draft
            rows = _raw_sql("SELECT status FROM campaigns WHERE id = :cid", {"cid": cid})
            assert rows[0][0] == "draft", f"Expected draft, got {rows[0][0]}"

            # 5. No approval outbox event
            rows = _raw_sql(
                "SELECT count(*) FROM outbox_events WHERE aggregate_id = :cid AND event_type = 'campaign.approval_requested'",
                {"cid": cid},
            )
            assert rows[0][0] == 0, f"Expected 0 approval outbox events, got {rows[0][0]}"
        finally:
            self._cleanup_meta()

    def test_missing_checksum_no_fake_stored(self, client, user_ids):
        """Create without checksum → response/DB shows empty string, not fake hash."""
        token = _token(user_ids["readonly"])
        code = f"CR-NOFAKE-{uuid.uuid4().hex[:8]}"

        resp = client.post(
            "/api/v1/identity/creative-assets",
            json={"code": code, "name": "No Fake Checksum", "media_type": "video",
                  "advertiser_organization_id": ADV1_ORG_ID},
            headers=_auth(token),
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["sha256_checksum"] == "", (
            f"Expected empty checksum, got '{data['sha256_checksum']}'"
        )
        assert data["status"] == "metadata_only"

        # Verify DB directly — no fake hash stored
        db_rows = _raw_sql(
            "SELECT sha256_checksum FROM creative_assets WHERE code = :code",
            {"code": code},
        )
        assert db_rows[0][0] == "", (
            f"DB stored '{db_rows[0][0]}' — expected empty string, not fake hash"
        )

        # Cleanup
        _raw_exec(f"DELETE FROM creative_assets WHERE code = '{code}'")

    def test_real_checksum_creative_still_attaches(self, client, user_ids):
        """Real 64-hex checksum creative can be created and attached normally."""
        token = _token(user_ids["readonly"])
        code = f"CR-REAL-{uuid.uuid4().hex[:8]}"
        real_checksum = "a" * 64  # valid 64-char hex

        # Create with real checksum
        resp = client.post(
            "/api/v1/identity/creative-assets",
            json={
                "code": code, "name": "Real Checksum Creative",
                "media_type": "image",
                "advertiser_organization_id": ADV1_ORG_ID,
                "sha256_checksum": real_checksum,
            },
            headers=_auth(token),
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["sha256_checksum"] == real_checksum, (
            f"Expected real checksum, got '{data['sha256_checksum']}'"
        )
        # Status should NOT be metadata_only — it has a real checksum
        assert data["status"] != "metadata_only", (
            f"Real checksum should not produce metadata_only status, got {data['status']}"
        )
        asset_id = data["id"]

        # Can attach to seed campaign
        self._draft()
        resp = client.post(
            f"/api/v1/identity/campaigns/{self.SEED_CID}/creatives/attach",
            json={"creative_asset_id": asset_id, "sort_order": 99},
            headers=_auth(token),
        )
        assert resp.status_code == 201, f"Real creative attach failed: {resp.text}"

        # Cleanup
        _raw_exec(
            f"DELETE FROM campaign_creatives WHERE creative_asset_id = '{asset_id}';"
            f"DELETE FROM creative_assets WHERE id = '{asset_id}'"
        )

    @classmethod
    def teardown_class(cls):
        """Restore seed campaign to draft and remove test artifacts."""
        _raw_exec("UPDATE campaigns SET status = 'draft' WHERE code = 'CAMP-2026-001'")
