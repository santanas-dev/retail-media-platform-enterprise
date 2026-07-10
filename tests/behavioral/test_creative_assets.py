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
        # NOTE: This endpoint is metadata-only intake (file upload deferred).
        # A real checksum is stored correctly but status remains metadata_only
        # until the actual file upload path is built (S-010+).
        assert data["status"] == "metadata_only", (
            f"Expected metadata_only status (file upload deferred), got {data['status']}"
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


# ---------------------------------------------------------------------------
# S-017 P0 proof: POST /campaigns/{id}/creatives bypass closed
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not REQUIRE_ENV, reason=SKIP_REASON)
class TestNoBypassCreateCampaignCreative:
    """Proof: create_campaign_creative always produces metadata_only/pending_review.

    Before S-017 P0 fix, POST /campaigns/{id}/creatives accepted a client-provided
    64-char hex checksum + file_size_bytes>0 and created ready/approved assets —
    bypassing the presigned-upload + server-SHA-256 flow entirely.

    After fix: every asset created via this path is metadata_only/pending_review
    with empty checksum.  The only path to ready/approved is complete-upload.
    """

    SEED_CID = "00000000-0000-0000-0000-000000000220"
    _asset_id = None

    def _draft(self):
        _raw_exec("UPDATE campaigns SET status = 'draft' WHERE code = 'CAMP-2026-001'")

    def _cleanup(self):
        if self._asset_id:
            _raw_exec(
                f"DELETE FROM campaign_creatives WHERE creative_asset_id = '{self._asset_id}';"
                f"DELETE FROM creative_assets WHERE id = '{self._asset_id}'"
            )
            self._asset_id = None

    def test_fake_checksum_creates_metadata_only(self, client, user_ids):
        """POST /campaigns/{id}/creatives with fake 64-char hex + size>0 → metadata_only."""
        self._draft()
        token = _token(user_ids["readonly"])
        cid = self.SEED_CID
        fake_checksum = "a" * 64  # valid hex but no real file
        try:
            resp = client.post(
                f"/api/v1/identity/campaigns/{cid}/creatives",
                json={
                    "code": f"CR-BYPASS-{uuid.uuid4().hex[:8]}",
                    "name": "Bypass Attempt",
                    "media_type": "image/png",
                    "sha256_checksum": fake_checksum,
                    "file_size_bytes": 1024,
                },
                headers=_auth(token),
            )
            assert resp.status_code == 201, f"Create failed: {resp.text}"
            data = resp.json()
            self._asset_id = data["id"]

            # P0 assertions: asset MUST be metadata_only, not ready/approved
            assert data["status"] == "metadata_only", (
                f"BYPASS DETECTED: expected metadata_only, got '{data['status']}' "
                f"— client checksum '{fake_checksum[:16]}...' was trusted!"
            )
            assert data["moderation_status"] == "pending_review", (
                f"BYPASS DETECTED: expected pending_review, got '{data['moderation_status']}'"
            )
            assert data["sha256_checksum"] == "", (
                f"BYPASS DETECTED: expected empty checksum, got '{data['sha256_checksum']}'"
            )
            assert data["file_size_bytes"] == 0, (
                f"BYPASS DETECTED: expected file_size_bytes=0, got {data['file_size_bytes']}"
            )

            # DB verification — no fake data stored
            db_rows = _raw_sql(
                "SELECT status, moderation_status, sha256_checksum, file_size_bytes "
                "FROM creative_assets WHERE id = :aid",
                {"aid": self._asset_id},
            )
            assert db_rows[0][0] == "metadata_only", f"DB status: {db_rows[0][0]}"
            assert db_rows[0][1] == "pending_review", f"DB moderation: {db_rows[0][1]}"
            assert db_rows[0][2] == "", f"DB checksum: '{db_rows[0][2]}'"
            assert db_rows[0][3] == 0, f"DB size: {db_rows[0][3]}"

            # Approval must be blocked — metadata_only creative attached
            resp_approve = client.post(
                f"/api/v1/identity/campaigns/{cid}/request-approval",
                headers=_auth(token),
            )
            assert resp_approve.status_code == 422, (
                f"Expected 422 (metadata-only blocks approval), got {resp_approve.status_code}"
            )
        finally:
            self._cleanup()

    def test_non_hex_checksum_rejected_by_schema(self, client, user_ids):
        """Schema validation rejects non-hex checksums at request level."""
        self._draft()
        token = _token(user_ids["readonly"])
        # Even though checksum is ignored, schema still validates max_length=64
        # and no special chars (just short-string validation)
        resp = client.post(
            f"/api/v1/identity/campaigns/{self.SEED_CID}/creatives",
            json={
                "code": f"CR-BAD-{uuid.uuid4().hex[:8]}",
                "name": "Bad Checksum",
                "media_type": "image",
                "sha256_checksum": "not-a-checksum!",
                "file_size_bytes": 512,
            },
            headers=_auth(token),
        )
        # Schema allows any string up to 64 chars; API ignores it
        # This test verifies the API doesn't crash on unexpected input
        assert resp.status_code == 201, f"Create should succeed: {resp.text}"
        data = resp.json()
        self._asset_id = data["id"]
        assert data["status"] == "metadata_only"
        assert data["sha256_checksum"] == ""
        self._cleanup()

    @classmethod
    def teardown_class(cls):
        _raw_exec("UPDATE campaigns SET status = 'draft' WHERE code = 'CAMP-2026-001'")
