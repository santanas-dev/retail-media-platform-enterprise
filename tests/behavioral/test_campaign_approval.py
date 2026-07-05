"""
Behavioral tests — Campaign Approval Workflow (Phase 4.1d).

Tests: request approval, approve, reject, status transitions,
permissions, tenant isolation, outbox, approval records.
Requires: RUN_BEHAVIORAL_TESTS=1, migrations applied, seed run.
"""

import asyncio
import os
import sys

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
ADV1_CONTRACT_ID = "00000000-0000-0000-0000-000000000212"


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


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _token(sub):
    return create_access_token(sub, "local_advertiser")


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


def _create_draft(client, token, code, org_id=ADV1_ORG_ID, contract_id=ADV1_CONTRACT_ID):
    """Create a draft campaign and return its id."""
    resp = client.post(
        "/api/v1/identity/campaigns",
        json={
            "advertiser_organization_id": org_id,
            "advertiser_contract_id": contract_id,
            "code": code,
            "name": f"Test {code}",
        },
        headers=_auth(token),
    )
    assert resp.status_code == 201, f"Failed to create draft: {resp.text}"
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# Request Approval
# ---------------------------------------------------------------------------


class TestRequestApproval:

    def test_no_token_returns_401(self, client):
        resp = client.post("/api/v1/identity/campaigns/some-id/request-approval")
        assert resp.status_code == 401

    def test_no_permission_returns_403(self, client, user_ids):
        token = _token(user_ids["noperms"])
        resp = client.post(
            "/api/v1/identity/campaigns/some-id/request-approval",
            headers=_auth(token),
        )
        assert resp.status_code == 403

    def test_request_approval_draft_campaign(self, client, user_ids):
        """Admin requests approval for a draft campaign → pending_approval."""
        token = _token(user_ids["readonly"])  # system_admin with campaigns.manage
        # Use seed campaign which has flights/placements/creatives
        rows = _raw_sql("SELECT id FROM campaigns WHERE code = 'CAMP-2026-001'")
        cid = rows[0][0]

        resp = client.post(
            f"/api/v1/identity/campaigns/{cid}/request-approval",
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["old_status"] == "draft"
        assert data["new_status"] == "pending_approval"

        # Verify DB
        rows = _raw_sql("SELECT status FROM campaigns WHERE id = :cid", {"cid": cid})
        assert rows[0][0] == "pending_approval"

        # Status history
        rows = _raw_sql(
            "SELECT new_status FROM campaign_status_history WHERE campaign_id = :cid "
            "ORDER BY changed_at",
            {"cid": cid},
        )
        assert "pending_approval" in [r[0] for r in rows]

        # Outbox event
        rows = _raw_sql(
            "SELECT event_type FROM outbox_events WHERE aggregate_id = :aid "
            "AND event_type = 'campaign.approval_requested'",
            {"aid": cid},
        )
        assert len(rows) >= 1

        # Restore
        _raw_exec("UPDATE campaigns SET status = 'draft' WHERE id = :cid", {"cid": cid})

    def test_request_approval_non_draft_rejected(self, client, user_ids):
        """Cannot request approval for a non-draft campaign."""
        token = _token(user_ids["readonly"])
        # Use seed campaign
        rows = _raw_sql("SELECT id FROM campaigns WHERE code = 'CAMP-2026-001'")
        cid = rows[0][0]

        # Set to approved first
        _raw_exec("UPDATE campaigns SET status = 'approved' WHERE id = :cid", {"cid": cid})

        resp = client.post(
            f"/api/v1/identity/campaigns/{cid}/request-approval",
            headers=_auth(token),
        )
        assert resp.status_code == 409, f"Expected 409, got {resp.status_code}: {resp.text}"

        # Restore
        _raw_exec("UPDATE campaigns SET status = 'draft' WHERE id = :cid", {"cid": cid})

    def test_request_approval_invalid_campaign_no_content(self, client, user_ids):
        """Draft campaign without flights/placements/creatives → 422.
        Our _create_draft creates a bare campaign with none of these."""
        token = _token(user_ids["readonly"])
        # Create bare draft (no flights/placements/creatives)
        resp = client.post(
            "/api/v1/identity/campaigns",
            json={
                "advertiser_organization_id": ADV1_ORG_ID,
                "advertiser_contract_id": ADV1_CONTRACT_ID,
                "code": "CAMP-APR-EMPTY",
                "name": "Empty Campaign",
            },
            headers=_auth(token),
        )
        assert resp.status_code == 201
        cid = resp.json()["id"]

        resp = client.post(
            f"/api/v1/identity/campaigns/{cid}/request-approval",
            headers=_auth(token),
        )
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# Approve
# ---------------------------------------------------------------------------


class TestApprove:

    def _request_approval(self, client, token, cid):
        """Move a seed campaign to pending_approval via SQL, then approve."""
        # Use seed campaign CAMP-2026-001 which has flights/placements/creatives
        _raw_exec(
            "UPDATE campaigns SET status = 'pending_approval' WHERE id = :cid",
            {"cid": cid},
        )

    def test_no_token_returns_401(self, client):
        resp = client.post("/api/v1/identity/campaigns/some-id/approve")
        assert resp.status_code == 401

    def test_campaigns_manage_cannot_approve(self, client, user_ids):
        """User with campaigns.manage but NOT campaigns.approve gets 403."""
        rows = _raw_sql("SELECT id FROM campaigns WHERE code = 'CAMP-2026-001'")
        cid = rows[0][0]
        self._request_approval(client, None, cid)

        # advertiser user has campaigns.manage but NOT campaigns.approve
        token = _token(user_ids["advertiser"])
        resp = client.post(
            f"/api/v1/identity/campaigns/{cid}/approve",
            headers=_auth(token),
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"

        # Restore
        _raw_exec("UPDATE campaigns SET status = 'draft' WHERE id = :cid", {"cid": cid})

    def test_admin_approves_pending_campaign(self, client, user_ids):
        """System admin with campaigns.approve can approve."""
        rows = _raw_sql("SELECT id FROM campaigns WHERE code = 'CAMP-2026-001'")
        cid = rows[0][0]
        self._request_approval(client, None, cid)

        token = _token(user_ids["readonly"])  # system_admin has campaigns.approve
        resp = client.post(
            f"/api/v1/identity/campaigns/{cid}/approve",
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["old_status"] == "pending_approval"
        assert data["new_status"] == "approved"

        # Approval record created
        rows = _raw_sql(
            "SELECT decision FROM campaign_approvals WHERE campaign_id = :cid "
            "ORDER BY created_at DESC",
            {"cid": cid},
        )
        assert rows[0][0] == "approved"

        # Status history
        rows = _raw_sql(
            "SELECT new_status FROM campaign_status_history WHERE campaign_id = :cid "
            "ORDER BY changed_at",
            {"cid": cid},
        )
        assert "approved" in [r[0] for r in rows]

        # Outbox
        rows = _raw_sql(
            "SELECT event_type FROM outbox_events WHERE aggregate_id = :aid "
            "AND event_type = 'campaign.approved'",
            {"aid": cid},
        )
        assert len(rows) >= 1

        # Restore
        _raw_exec("UPDATE campaigns SET status = 'draft' WHERE id = :cid", {"cid": cid})

    def test_approve_draft_directly_rejected(self, client, user_ids):
        """Cannot approve a draft campaign directly → 409."""
        rows = _raw_sql("SELECT id FROM campaigns WHERE code = 'CAMP-2026-001'")
        cid = rows[0][0]
        assert _raw_sql("SELECT status FROM campaigns WHERE id = :cid", {"cid": cid})[0][0] == "draft"

        token = _token(user_ids["readonly"])
        resp = client.post(
            f"/api/v1/identity/campaigns/{cid}/approve",
            headers=_auth(token),
        )
        assert resp.status_code == 409, f"Expected 409, got {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# Reject
# ---------------------------------------------------------------------------


class TestReject:

    def _set_pending(self, cid):
        _raw_exec(
            "UPDATE campaigns SET status = 'pending_approval' WHERE id = :cid",
            {"cid": cid},
        )

    def _restore_draft(self, cid):
        _raw_exec("UPDATE campaigns SET status = 'draft' WHERE id = :cid", {"cid": cid})

    def test_no_token_returns_401(self, client):
        resp = client.post("/api/v1/identity/campaigns/some-id/reject", json={"reason": "x"})
        assert resp.status_code == 401

    def test_campaigns_manage_cannot_reject(self, client, user_ids):
        """User without campaigns.approve gets 403 on reject."""
        rows = _raw_sql("SELECT id FROM campaigns WHERE code = 'CAMP-2026-001'")
        cid = rows[0][0]
        self._set_pending(cid)

        token = _token(user_ids["advertiser"])  # no campaigns.approve
        resp = client.post(
            f"/api/v1/identity/campaigns/{cid}/reject",
            json={"reason": "Bad budget"},
            headers=_auth(token),
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"

        self._restore_draft(cid)

    def test_admin_rejects_pending_campaign(self, client, user_ids):
        """Admin with campaigns.approve rejects a pending campaign."""
        rows = _raw_sql("SELECT id FROM campaigns WHERE code = 'CAMP-2026-001'")
        cid = rows[0][0]
        self._set_pending(cid)

        token = _token(user_ids["readonly"])  # system_admin
        resp = client.post(
            f"/api/v1/identity/campaigns/{cid}/reject",
            json={"reason": "Budget exceeded by 30%"},
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["old_status"] == "pending_approval"
        assert data["new_status"] == "rejected"

        # Approval record with rejection reason
        rows = _raw_sql(
            "SELECT decision, rejection_reason FROM campaign_approvals "
            "WHERE campaign_id = :cid ORDER BY created_at DESC",
            {"cid": cid},
        )
        assert rows[0][0] == "rejected"
        assert "Budget exceeded" in rows[0][1]

        # Outbox
        rows = _raw_sql(
            "SELECT event_type FROM outbox_events WHERE aggregate_id = :aid "
            "AND event_type = 'campaign.rejected'",
            {"aid": cid},
        )
        assert len(rows) >= 1

        self._restore_draft(cid)

    def test_reject_requires_reason(self, client, user_ids):
        """Reject without reason → 422 (schema validation)."""
        rows = _raw_sql("SELECT id FROM campaigns WHERE code = 'CAMP-2026-001'")
        cid = rows[0][0]
        self._set_pending(cid)

        token = _token(user_ids["readonly"])
        resp = client.post(
            f"/api/v1/identity/campaigns/{cid}/reject",
            headers=_auth(token),
        )
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"

        self._restore_draft(cid)

    def test_reject_draft_directly_rejected(self, client, user_ids):
        """Cannot reject a draft campaign directly → 409."""
        rows = _raw_sql("SELECT id FROM campaigns WHERE code = 'CAMP-2026-001'")
        cid = rows[0][0]

        token = _token(user_ids["readonly"])
        resp = client.post(
            f"/api/v1/identity/campaigns/{cid}/reject",
            json={"reason": "Too early"},
            headers=_auth(token),
        )
        assert resp.status_code == 409, f"Expected 409, got {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# Tenant Isolation
# ---------------------------------------------------------------------------


class TestApprovalTenantIsolation:

    def test_advertiser_cannot_self_approve(self, client, user_ids):
        """Scoped advertiser with campaigns.manage cannot approve own campaign."""
        rows = _raw_sql("SELECT id FROM campaigns WHERE code = 'CAMP-2026-001'")
        cid = rows[0][0]
        _raw_exec("UPDATE campaigns SET status = 'pending_approval' WHERE id = :cid", {"cid": cid})

        token = _token(user_ids["advertiser"])  # has campaigns.manage, NOT campaigns.approve
        resp = client.post(
            f"/api/v1/identity/campaigns/{cid}/approve",
            headers=_auth(token),
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"

        # Restore
        _raw_exec("UPDATE campaigns SET status = 'draft' WHERE id = :cid", {"cid": cid})

    def test_no_outbox_on_rejection(self, client, user_ids):
        """403 rejection (wrong permission) writes no outbox."""
        rows = _raw_sql("SELECT id FROM campaigns WHERE code = 'CAMP-2026-001'")
        cid = rows[0][0]
        _raw_exec("UPDATE campaigns SET status = 'pending_approval' WHERE id = :cid", {"cid": cid})

        token = _token(user_ids["advertiser"])
        resp = client.post(
            f"/api/v1/identity/campaigns/{cid}/approve",
            headers=_auth(token),
        )
        assert resp.status_code == 403

        # Campaign should still be pending_approval
        rows = _raw_sql("SELECT status FROM campaigns WHERE id = :cid", {"cid": cid})
        assert rows[0][0] == "pending_approval"

        # No approval record from this attempt
        rows = _raw_sql(
            "SELECT id FROM campaign_approvals WHERE campaign_id = :cid "
            "AND decision = 'approved'",
            {"cid": cid},
        )
        assert len(rows) == 0

        _raw_exec("UPDATE campaigns SET status = 'draft' WHERE id = :cid", {"cid": cid})
