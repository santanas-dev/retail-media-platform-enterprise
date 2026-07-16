"""
Behavioral tests — C1: Creative Moderation + Campaign Approval RLS.

Proof that under NOBYPASSRLS:
  - Moderation queue returns only scoped creatives
  - Approval queue returns only scoped campaigns
  - approve/reject works for accessible creatives (no 404)
  - Cross-tenant access is denied
  - Admin sees all

Requires: RUN_BEHAVIORAL_TESTS=1, PostgreSQL, migrations applied.
"""

import asyncio
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from packages.security.config import reset_security_config
from packages.security.jwt import create_access_token

# ---------------------------------------------------------------------------
# DB helper — uses owner connection (bypasses RLS for fixture setup)
# ---------------------------------------------------------------------------

_FIXTURE_DB_URL = os.environ.get(
    "BEHAVIORAL_DB_URL",
    "postgresql+asyncpg://retail_media:retail_media_dev@localhost:5432/"
    "retail_media_platform",
)


def _run_fixture_sql(sql: str):
    """Run SQL with admin bypass for fixture setup."""

    async def _run():
        engine = create_async_engine(_FIXTURE_DB_URL, echo=False)
        try:
            async with engine.begin() as conn:
                await conn.execute(
                    text("SELECT set_config('app.rmp_is_admin', 'true', true)")
                )
                for stmt in sql.split(";"):
                    s = stmt.strip()
                    if s and not s.startswith("--"):
                        await conn.execute(text(s))
        finally:
            await engine.dispose()

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Fixture IDs
# ---------------------------------------------------------------------------

ORG_A = "beh-c1-org-a-000000000000000001"
ORG_B = "beh-c1-org-b-000000000000000002"
MOD_USER = "beh-c1-mod-000000000000000001"
MOD_ROLE = "beh-c1-role-mod-000000000001"
MOD_LC = "beh-c1-lc-0000000000000000001"
MOD_AUM = "beh-c1-aum-000000000000000001"
MOD_UR = "beh-c1-ur-0000000000000000001"

CREATIVE_A_ID = "beh-c1-cr-a-000000000000000001"
CREATIVE_B_ID = "beh-c1-cr-b-000000000000000002"
CAMPAIGN_A_ID = "beh-c1-camp-a-00000000000000001"

ADMIN_USER = "beh-c1-admin-0000000000000001"
ADMIN_LC = "beh-c1-alc-000000000000000001"
ADMIN_UR = "beh-c1-aur-000000000000000001"
MOD_USERNAME = "beh-c1-mod"


@pytest.fixture(scope="module")
def c1_fixtures():
    """Set up C1 test fixtures: 2 orgs, creatives, campaign, scoped moderator."""
    import bcrypt

    ph = bcrypt.hashpw(
        "Test1234!".encode(), bcrypt.gensalt()
    ).decode()

    _run_fixture_sql(f"""
    -- Ensure creatives.moderate + campaigns.approve permissions exist
    ; INSERT INTO permissions (id, code, name) VALUES
      ('00000000-0000-0000-0000-000000000117','creatives.moderate','Модерация креативов')
      ON CONFLICT (code) DO NOTHING
    ; INSERT INTO permissions (id, code, name) VALUES
      ('00000000-0000-0000-0000-00000000010e','campaigns.approve','Согласование кампаний')
      ON CONFLICT (code) DO NOTHING
    ;

    -- Clean up any previous C1 test data
    DELETE FROM campaign_status_history WHERE campaign_id LIKE 'beh-c1-%'
    ; DELETE FROM campaign_placements WHERE campaign_id LIKE 'beh-c1-%'
    ; DELETE FROM campaign_creatives WHERE campaign_id LIKE 'beh-c1-%'
         OR creative_asset_id LIKE 'beh-c1-%'
    ; DELETE FROM campaign_flights WHERE campaign_id LIKE 'beh-c1-%'
    ; DELETE FROM campaign_approvals WHERE campaign_id LIKE 'beh-c1-%'
    ; DELETE FROM campaigns WHERE id LIKE 'beh-c1-%'
    ; DELETE FROM creative_assets WHERE id LIKE 'beh-c1-%'
    ; DELETE FROM outbox_events WHERE aggregate_id LIKE 'beh-c1-%'
    ; DELETE FROM audit_events_operational WHERE actor_user_id LIKE 'beh-c1-%'
         OR target_id LIKE 'beh-c1-%'
    ; DELETE FROM advertiser_user_memberships WHERE user_id LIKE 'beh-c1-%'
    ; DELETE FROM refresh_sessions WHERE user_id LIKE 'beh-c1-%'
    ; DELETE FROM local_credentials WHERE user_id LIKE 'beh-c1-%'
    ; DELETE FROM user_roles WHERE user_id LIKE 'beh-c1-%'
    ; DELETE FROM users WHERE id LIKE 'beh-c1-%'
    ; DELETE FROM advertiser_organizations WHERE id LIKE 'beh-c1-%'
    ; DELETE FROM advertiser_contracts WHERE id LIKE 'beh-c1-%'

    -- Org A (moderator's org)
    ; INSERT INTO advertiser_organizations (id, code, legal_name, display_name, status)
      VALUES ('{ORG_A}', 'C1-ORG-A', 'ООО Тест-А', 'Тест-А', 'active')
    ; INSERT INTO advertiser_contracts (id, advertiser_organization_id, code, name, status)
      VALUES ('beh-c1-ctr-a','{ORG_A}', 'C1-CTR-A', 'C1 Contract A', 'active')

    -- Org B (cross-tenant)
    ; INSERT INTO advertiser_organizations (id, code, legal_name, display_name, status)
      VALUES ('{ORG_B}', 'C1-ORG-B', 'ООО Тест-Б', 'Тест-Б', 'active')
    ; INSERT INTO advertiser_contracts (id, advertiser_organization_id, code, name, status)
      VALUES ('beh-c1-ctr-b','{ORG_B}', 'C1-CTR-B', 'C1 Contract B', 'active')

    -- Scoped moderator user (must exist before creatives/campaigns reference it)
    ; INSERT INTO users (id, code, username, email, display_name, auth_provider, status)
      VALUES ('{MOD_USER}', 'C1-MOD', '{MOD_USERNAME}', 'c1-mod@t.local',
              'C1 Moderator', 'local_advertiser', 'active')
    ; INSERT INTO local_credentials (id, user_id, credential_type, password_hash, status)
      VALUES ('{MOD_LC}', '{MOD_USER}', 'local_advertiser', '{ph}', 'active')
    -- Scoped advertiser role + membership
    ; INSERT INTO user_roles (id, user_id, role_id, scope_type, scope_id)
      SELECT '{MOD_UR}', '{MOD_USER}',
             COALESCE((SELECT id FROM roles WHERE code='advertiser'),
                      '00000000-0000-0000-0000-000000000114'),
             'advertiser', '{ORG_A}'
    ; INSERT INTO advertiser_user_memberships
        (id, user_id, advertiser_organization_id, status)
      VALUES ('{MOD_AUM}', '{MOD_USER}', '{ORG_A}', 'active')

    -- Admin user (unscoped system_admin)
    ; INSERT INTO users (id, code, username, email, display_name, auth_provider, status)
      VALUES ('{ADMIN_USER}', 'C1-ADM', 'beh-c1-admin', 'c1-admin@t.local',
              'C1 Admin', 'local_advertiser', 'active')
    ; INSERT INTO local_credentials (id, user_id, credential_type, password_hash, status)
      VALUES ('{ADMIN_LC}', '{ADMIN_USER}', 'local_advertiser', '{ph}', 'active')
    ; INSERT INTO user_roles (id, user_id, role_id)
      SELECT '{ADMIN_UR}', '{ADMIN_USER}', id FROM roles WHERE code='system_admin'
    -- Grant creatives.moderate + campaigns.approve to advertiser role (scoped moderator)
    ; INSERT INTO role_permissions (id, role_id, permission_id)
      SELECT 'rp-c1-mod-cr', r.id, p.id
      FROM roles r CROSS JOIN permissions p
      WHERE r.code='advertiser' AND p.code='creatives.moderate'
      AND NOT EXISTS (
        SELECT 1 FROM role_permissions
        WHERE role_id=r.id AND permission_id=p.id
      )
    ; INSERT INTO role_permissions (id, role_id, permission_id)
      SELECT 'rp-c1-ap-camp', r.id, p.id
      FROM roles r CROSS JOIN permissions p
      WHERE r.code='advertiser' AND p.code='campaigns.approve'
      AND NOT EXISTS (
        SELECT 1 FROM role_permissions
        WHERE role_id=r.id AND permission_id=p.id
      )

    -- Creative in Org A
    ; INSERT INTO creative_assets
        (id, advertiser_organization_id, code, name, media_type,
         storage_bucket, storage_key, sha256_checksum, file_size_bytes,
         status, moderation_status, created_by)
      VALUES
        ('{CREATIVE_A_ID}', '{ORG_A}', 'C1-CR-A', 'Creative A', 'image/png',
         'test-bucket', 'test/c1-cr-a.png',
         'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
         1024, 'ready', 'pending_review', '{MOD_USER}')

    -- Creative in Org B (cross-tenant)
    ; INSERT INTO creative_assets
        (id, advertiser_organization_id, code, name, media_type,
         storage_bucket, storage_key, sha256_checksum, file_size_bytes,
         status, moderation_status, created_by)
      VALUES
        ('{CREATIVE_B_ID}', '{ORG_B}', 'C1-CR-B', 'Creative B', 'image/png',
         'test-bucket', 'test/c1-cr-b.png',
         'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
         2048, 'ready', 'pending_review', '{MOD_USER}')

    -- Campaign in Org A (pending_approval)
    ; INSERT INTO campaigns
        (id, advertiser_organization_id, advertiser_contract_id,
         code, name, status, priority, created_by)
      VALUES
        ('{CAMPAIGN_A_ID}', '{ORG_A}', 'beh-c1-ctr-a',
         'C1-CAMP-A', 'Campaign A', 'pending_approval', 0, '{MOD_USER}')
    -- Status history entry (required for approval queue JOIN)
    ; INSERT INTO campaign_status_history
        (id, campaign_id, old_status, new_status, changed_by, changed_at)
      VALUES
        ('beh-c1-csh-000000000000000001', '{CAMPAIGN_A_ID}',
         'draft', 'pending_approval', '{MOD_USER}', NOW())
    """)

    yield

    # Teardown
    _run_fixture_sql(f"""
    DELETE FROM campaign_status_history WHERE campaign_id LIKE 'beh-c1-%'
    ; DELETE FROM campaign_placements WHERE campaign_id LIKE 'beh-c1-%'
    ; DELETE FROM campaign_creatives WHERE campaign_id LIKE 'beh-c1-%'
         OR creative_asset_id LIKE 'beh-c1-%'
    ; DELETE FROM campaign_flights WHERE campaign_id LIKE 'beh-c1-%'
    ; DELETE FROM campaign_approvals WHERE campaign_id LIKE 'beh-c1-%'
    ; DELETE FROM campaigns WHERE id LIKE 'beh-c1-%'
    ; DELETE FROM creative_assets WHERE id LIKE 'beh-c1-%'
    ; DELETE FROM outbox_events WHERE aggregate_id LIKE 'beh-c1-%'
    ; DELETE FROM audit_events_operational WHERE actor_user_id LIKE 'beh-c1-%'
         OR target_id LIKE 'beh-c1-%'
    ; DELETE FROM role_permissions WHERE id LIKE 'rp-c1-%'
    ; DELETE FROM advertiser_user_memberships WHERE user_id LIKE 'beh-c1-%'
    ; DELETE FROM refresh_sessions WHERE user_id LIKE 'beh-c1-%'
    ; DELETE FROM local_credentials WHERE user_id LIKE 'beh-c1-%'
    ; DELETE FROM user_roles WHERE user_id LIKE 'beh-c1-%'
    ; DELETE FROM users WHERE id LIKE 'beh-c1-%'
    ; DELETE FROM advertiser_contracts WHERE id LIKE 'beh-c1-%'
    ; DELETE FROM advertiser_organizations WHERE id LIKE 'beh-c1-%'
    """)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _token_mod():
    """Token for the scoped C1 moderator (org-A scope + creatives.moderate)."""
    return create_access_token(MOD_USER, "local_advertiser")


def _token_admin():
    """Token for system admin (unscoped, sees everything)."""
    return create_access_token(ADMIN_USER, "local_advertiser")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("c1_fixtures")
class TestC1ModerationQueueRLS:
    """Moderation queue RLS: scoped user sees only their org's creatives."""

    @pytest.fixture(autouse=True)
    def setup_client(self, app, db_available):
        reset_security_config()
        self.client = TestClient(app)

    def test_moderation_queue_scoped_sees_only_own_creatives(self):
        """Scoped moderator sees only Org A creatives in moderation queue."""
        resp = self.client.get(
            "/api/v1/identity/creative-assets/moderation-queue"
            "?moderation_status=pending_review",
            headers=_auth(_token_mod()),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        items = body["items"]
        assert len(items) >= 1
        creative_ids = {item["id"] for item in items}
        assert CREATIVE_A_ID in creative_ids, (
            "Scoped moderator should see Org A creative"
        )
        assert CREATIVE_B_ID not in creative_ids, (
            "Scoped moderator MUST NOT see Org B creative — RLS breach"
        )

    def test_moderation_queue_admin_sees_all(self):
        """Admin sees all creatives across all orgs."""
        resp = self.client.get(
            "/api/v1/identity/creative-assets/moderation-queue"
            "?moderation_status=pending_review",
            headers=_auth(_token_admin()),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        items = body["items"]
        creative_ids = {item["id"] for item in items}
        assert CREATIVE_A_ID in creative_ids, "Admin should see Org A creative"
        assert CREATIVE_B_ID in creative_ids, "Admin should see Org B creative"


@pytest.mark.usefixtures("c1_fixtures")
class TestC1ApproveReject:
    """Approve/reject creative: works for accessible, 404 for cross-tenant."""

    @pytest.fixture(autouse=True)
    def setup_client(self, app, db_available):
        reset_security_config()
        self.client = TestClient(app)

    def test_approve_accessible_creative_no_404(self):
        """Scoped moderator approves own org creative — must not 404."""
        resp = self.client.post(
            f"/api/v1/identity/creative-assets/{CREATIVE_A_ID}/approve",
            headers=_auth(_token_mod()),
        )
        assert resp.status_code == 200, (
            f"Expected 200 for accessible creative, got {resp.status_code}: {resp.text}"
        )
        body = resp.json()
        assert body["moderation_status"] == "approved"

    def test_reject_accessible_creative_no_404(self):
        """Scoped moderator rejects own org creative — must not 404."""
        # First set it back to pending_review
        _run_fixture_sql(f"""
        UPDATE creative_assets SET moderation_status='pending_review'
        WHERE id='{CREATIVE_A_ID}'
        """)
        reset_security_config()
        self.client = TestClient(self.client.app)

        resp = self.client.post(
            f"/api/v1/identity/creative-assets/{CREATIVE_A_ID}/reject",
            json={"reason": "Не соответствует требованиям"},
            headers=_auth(_token_mod()),
        )
        assert resp.status_code == 200, (
            f"Expected 200 for accessible creative, got {resp.status_code}: {resp.text}"
        )
        body = resp.json()
        assert body["moderation_status"] == "rejected"

    def test_approve_cross_tenant_creative_returns_404(self):
        """Scoped moderator tries to approve Org B creative → 404 (RLS)."""
        resp = self.client.post(
            f"/api/v1/identity/creative-assets/{CREATIVE_B_ID}/approve",
            headers=_auth(_token_mod()),
        )
        assert resp.status_code == 404, (
            f"Cross-tenant approve must return 404, got {resp.status_code}: {resp.text}"
        )

    def test_admin_approve_cross_tenant_works(self):
        """Admin can approve any creative (unscoped)."""
        resp = self.client.post(
            f"/api/v1/identity/creative-assets/{CREATIVE_B_ID}/approve",
            headers=_auth(_token_admin()),
        )
        assert resp.status_code == 200, (
            f"Admin should be able to approve any creative, got {resp.status_code}"
        )
        body = resp.json()
        assert body["moderation_status"] == "approved"


@pytest.mark.usefixtures("c1_fixtures")
class TestC1ApprovalQueueRLS:
    """Campaign approval queue RLS: scoped user sees only their org's campaigns."""

    @pytest.fixture(autouse=True)
    def setup_client(self, app, db_available):
        reset_security_config()
        self.client = TestClient(app)

    def test_approval_queue_admin_sees_pending(self):
        """Admin sees pending_approval campaigns."""
        resp = self.client.get(
            "/api/v1/identity/campaigns/approval-queue?status=pending_approval",
            headers=_auth(_token_admin()),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        items = body["items"]
        campaign_ids = {item["campaign_id"] for item in items}
        assert CAMPAIGN_A_ID in campaign_ids, (
            "Admin should see pending campaign"
        )

    def test_approval_queue_scoped_sees_own_campaigns(self):
        """Scoped moderator sees only campaigns from their org."""
        resp = self.client.get(
            "/api/v1/identity/campaigns/approval-queue?status=pending_approval",
            headers=_auth(_token_mod()),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        items = body["items"]
        campaign_ids = {item["campaign_id"] for item in items}
        assert CAMPAIGN_A_ID in campaign_ids, (
            "Scoped moderator should see their org's pending campaign"
        )
        # Verify no cross-tenant campaigns
        for item in items:
            assert item.get("advertiser_organization_id") in (ORG_A, None), (
                f"Cross-tenant campaign leak: {item['id']} belongs to "
                f"{item.get('advertiser_organization_id')}"
            )
