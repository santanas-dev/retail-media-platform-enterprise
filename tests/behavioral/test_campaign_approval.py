"""
Behavioral tests — Campaign Approval Workflow (Phase 4.1d).

Tests: request approval, approve, reject, status transitions,
permissions, tenant isolation, outbox, approval records,
idempotency, contract validation, cross-org rejection.
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
# ADV-002 org for cross-org tests (not in seed — created inline)
ADV2_ORG_ID = "00000000-0000-0000-0000-000000000201"


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
            # Session-level RLS bypass for verification queries (S-008)
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


def _cid():
    """Return the seed campaign CAMP-2026-001 id."""
    return _raw_sql("SELECT id FROM campaigns WHERE code = 'CAMP-2026-001'")[0][0]


def _draft():
    """Restore CAMP-2026-001 to draft status, clean all test artifacts."""
    _raw_exec(
        "UPDATE campaigns SET status = 'draft' WHERE code = 'CAMP-2026-001'"
    )
    cid = _raw_sql("SELECT id FROM campaigns WHERE code = 'CAMP-2026-001'")[0][0]
    _raw_exec(
        "DELETE FROM outbox_events WHERE aggregate_id = :cid;"
        " DELETE FROM campaign_approvals WHERE campaign_id = :cid;"
        " DELETE FROM campaign_status_history WHERE campaign_id = :cid"
        "  AND changed_by LIKE 'beh-%'",
        {"cid": cid},
    )


def _pending():
    """Set CAMP-2026-001 to pending_approval via SQL (simulates prior request)."""
    _raw_exec(
        "UPDATE campaigns SET status = 'pending_approval' WHERE code = 'CAMP-2026-001'"
    )
    # Also write a status_history row so requested_at lookup works
    _raw_exec(
        "INSERT INTO campaign_status_history (id, campaign_id, old_status, new_status, changed_by, changed_at, reason) "
        "SELECT gen_random_uuid(), id, 'draft', 'pending_approval', "
        "'beh-so-00000000000000000005', NOW(), 'Approval requested (test)' "
        "FROM campaigns WHERE code = 'CAMP-2026-001'"
    )


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
        _draft()
        token = _token(user_ids["readonly"])
        cid = _cid()

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

        _draft()

    def test_request_approval_non_draft_rejected(self, client, user_ids):
        """Cannot request approval for a non-draft campaign."""
        _draft()
        token = _token(user_ids["readonly"])
        cid = _cid()
        _raw_exec("UPDATE campaigns SET status = 'approved' WHERE id = :cid", {"cid": cid})

        resp = client.post(
            f"/api/v1/identity/campaigns/{cid}/request-approval",
            headers=_auth(token),
        )
        assert resp.status_code == 409, f"Expected 409, got {resp.status_code}: {resp.text}"

        _draft()

    def test_request_approval_invalid_campaign_no_content(self, client, user_ids):
        """Draft campaign without flights/placements/creatives → 422."""
        _draft()
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

    def test_no_token_returns_401(self, client):
        resp = client.post("/api/v1/identity/campaigns/some-id/approve")
        assert resp.status_code == 401

    def test_campaigns_manage_cannot_approve(self, client, user_ids):
        """User with campaigns.manage but NOT campaigns.approve gets 403."""
        _draft()
        _pending()
        cid = _cid()

        token = _token(user_ids["advertiser"])  # has campaigns.manage, NOT campaigns.approve
        resp = client.post(
            f"/api/v1/identity/campaigns/{cid}/approve",
            headers=_auth(token),
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"

        _draft()

    def test_admin_approves_pending_campaign(self, client, user_ids):
        """System admin with campaigns.approve can approve."""
        _draft()
        _pending()
        cid = _cid()

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

        _draft()

    def test_approve_draft_directly_rejected(self, client, user_ids):
        """Cannot approve a draft campaign directly → 409."""
        _draft()
        cid = _cid()
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

    def test_no_token_returns_401(self, client):
        resp = client.post("/api/v1/identity/campaigns/some-id/reject", json={"reason": "x"})
        assert resp.status_code == 401

    def test_campaigns_manage_cannot_reject(self, client, user_ids):
        """User without campaigns.approve gets 403 on reject."""
        _draft()
        _pending()
        cid = _cid()

        token = _token(user_ids["advertiser"])
        resp = client.post(
            f"/api/v1/identity/campaigns/{cid}/reject",
            json={"reason": "Bad budget"},
            headers=_auth(token),
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"

        _draft()

    def test_admin_rejects_pending_campaign(self, client, user_ids):
        """Admin with campaigns.approve rejects a pending campaign."""
        _draft()
        _pending()
        cid = _cid()

        token = _token(user_ids["readonly"])
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

        _draft()

    def test_reject_requires_reason(self, client, user_ids):
        """Reject without reason → 422 (schema validation)."""
        _draft()
        _pending()
        cid = _cid()

        token = _token(user_ids["readonly"])
        resp = client.post(
            f"/api/v1/identity/campaigns/{cid}/reject",
            headers=_auth(token),
        )
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"

        _draft()

    def test_reject_draft_directly_rejected(self, client, user_ids):
        """Cannot reject a draft campaign directly → 409."""
        _draft()
        cid = _cid()

        token = _token(user_ids["readonly"])
        resp = client.post(
            f"/api/v1/identity/campaigns/{cid}/reject",
            json={"reason": "Too early"},
            headers=_auth(token),
        )
        assert resp.status_code == 409, f"Expected 409, got {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# Idempotency (P1-3)
# ---------------------------------------------------------------------------


class TestIdempotency:

    def test_duplicate_request_approval_rejected(self, client, user_ids):
        """Re-request approval on already pending_approval → 409, no outbox."""
        _draft()
        _pending()
        cid = _cid()

        # Count current outbox events
        before = len(_raw_sql(
            "SELECT id FROM outbox_events WHERE aggregate_id = :aid",
            {"aid": cid},
        ))

        token = _token(user_ids["readonly"])
        resp = client.post(
            f"/api/v1/identity/campaigns/{cid}/request-approval",
            headers=_auth(token),
        )
        assert resp.status_code == 409, f"Expected 409, got {resp.status_code}: {resp.text}"

        # Status unchanged
        rows = _raw_sql("SELECT status FROM campaigns WHERE id = :cid", {"cid": cid})
        assert rows[0][0] == "pending_approval"

        # No new outbox event from failed request
        after = len(_raw_sql(
            "SELECT id FROM outbox_events WHERE aggregate_id = :aid",
            {"aid": cid},
        ))
        assert after == before

        _draft()

    def test_duplicate_approve_rejected(self, client, user_ids):
        """Re-approve already approved campaign → 409, no outbox."""
        _draft()
        _pending()
        cid = _cid()

        token = _token(user_ids["readonly"])
        # First approve — should succeed
        resp = client.post(
            f"/api/v1/identity/campaigns/{cid}/approve",
            headers=_auth(token),
        )
        assert resp.status_code == 200

        # Count outbox events after successful approve
        after_first = len(_raw_sql(
            "SELECT id FROM outbox_events WHERE aggregate_id = :aid",
            {"aid": cid},
        ))

        # Second approve — should fail
        resp = client.post(
            f"/api/v1/identity/campaigns/{cid}/approve",
            headers=_auth(token),
        )
        assert resp.status_code == 409, f"Expected 409, got {resp.status_code}: {resp.text}"

        # No new outbox from failed second approve
        after_second = len(_raw_sql(
            "SELECT id FROM outbox_events WHERE aggregate_id = :aid",
            {"aid": cid},
        ))
        assert after_second == after_first

        _draft()

    def test_duplicate_reject_rejected(self, client, user_ids):
        """Re-reject already rejected campaign → 409, no outbox."""
        _draft()
        _pending()
        cid = _cid()

        token = _token(user_ids["readonly"])
        # First reject — should succeed
        resp = client.post(
            f"/api/v1/identity/campaigns/{cid}/reject",
            json={"reason": "First rejection"},
            headers=_auth(token),
        )
        assert resp.status_code == 200

        # Count outbox events
        after_first = len(_raw_sql(
            "SELECT id FROM outbox_events WHERE aggregate_id = :aid",
            {"aid": cid},
        ))

        # Second reject — should fail
        resp = client.post(
            f"/api/v1/identity/campaigns/{cid}/reject",
            json={"reason": "Second rejection"},
            headers=_auth(token),
        )
        assert resp.status_code == 409, f"Expected 409, got {resp.status_code}: {resp.text}"

        # No new outbox
        after_second = len(_raw_sql(
            "SELECT id FROM outbox_events WHERE aggregate_id = :aid",
            {"aid": cid},
        ))
        assert after_second == after_first

        _draft()

    def test_approve_reject_archived_rejected(self, client, user_ids):
        """Cannot approve/reject an archived campaign → 409."""
        _draft()
        cid = _cid()
        _raw_exec("UPDATE campaigns SET status = 'archived' WHERE id = :cid", {"cid": cid})

        token = _token(user_ids["readonly"])
        resp = client.post(
            f"/api/v1/identity/campaigns/{cid}/approve",
            headers=_auth(token),
        )
        assert resp.status_code == 409, f"Approve on archived: expected 409, got {resp.status_code}"

        resp = client.post(
            f"/api/v1/identity/campaigns/{cid}/reject",
            json={"reason": "Too late"},
            headers=_auth(token),
        )
        assert resp.status_code == 409, f"Reject on archived: expected 409, got {resp.status_code}"

        _draft()


# ---------------------------------------------------------------------------
# Tenant Isolation (P2-4 + self-approve)
# ---------------------------------------------------------------------------


class TestApprovalTenantIsolation:

    def test_advertiser_cannot_self_approve(self, client, user_ids):
        """Scoped advertiser with campaigns.manage cannot approve own campaign."""
        _draft()
        _pending()
        cid = _cid()

        token = _token(user_ids["advertiser"])  # has campaigns.manage, NOT campaigns.approve
        resp = client.post(
            f"/api/v1/identity/campaigns/{cid}/approve",
            headers=_auth(token),
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"

        _draft()

    def test_no_outbox_on_rejection(self, client, user_ids):
        """403 rejection (wrong permission) writes no outbox."""
        _draft()
        _pending()
        cid = _cid()

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

        _draft()

    def test_cross_org_approver_blocked(self, client, user_ids):
        """Scoped approver for ADV-002 cannot approve ADV-001's campaign → 403.

        Creates a temporary user with campaigns.approve + advertiser scope
        on ADV-002, then tries to approve CAMP-2026-001 (ADV-001 org).
        Uses try/finally so role_permissions cleanup runs even on assertion failure.
        """
        _draft()
        _pending()
        cid = _cid()

        # Create ADV-002 org inline
        _raw_exec("""
            INSERT INTO advertiser_organizations (id, code, legal_name, display_name, status, created_at, updated_at)
            VALUES (:oid, 'ADV-002', 'ADV-002 Legal', 'ADV-002', 'active', NOW(), NOW())
            ON CONFLICT (id) DO NOTHING
        """, {"oid": ADV2_ORG_ID})

        approver_id = "beh-xa-00000000000000000001"
        # Pre-cleanup in case previous run aborted
        _raw_exec("""
            DELETE FROM campaign_status_history WHERE changed_by = :uid
            ; DELETE FROM campaign_approvals WHERE reviewed_by = :uid
            ; DELETE FROM advertiser_user_memberships WHERE user_id = :uid
            ; DELETE FROM local_credentials WHERE user_id = :uid
            ; DELETE FROM user_roles WHERE user_id = :uid
            ; DELETE FROM users WHERE id = :uid
            ; DELETE FROM role_permissions WHERE role_id = (SELECT id FROM roles WHERE code = 'advertiser')
              AND permission_id = (SELECT id FROM permissions WHERE code = 'campaigns.approve')
        """, {"uid": approver_id})

        # Grant campaigns.approve to advertiser role — wrapped in finally
        _raw_exec("""
            INSERT INTO role_permissions (id, role_id, permission_id)
            SELECT gen_random_uuid(), r.id, p.id FROM roles r, permissions p
            WHERE r.code = 'advertiser' AND p.code = 'campaigns.approve'
            AND NOT EXISTS (
                SELECT 1 FROM role_permissions rp
                WHERE rp.role_id = r.id AND rp.permission_id = p.id
            )
        """)
        try:
            _raw_exec("""
                INSERT INTO users (id, code, username, email, display_name, auth_provider, status)
                  VALUES (:uid, 'BEH-XA', 'beh-xapprover', 'beh-xa@t.local', 'Beh XA', 'local_advertiser', 'active')
                ; INSERT INTO local_credentials (id, user_id, credential_type, password_hash, status)
                  VALUES ('lc-beh-xa', :uid, 'local_advertiser', '$2b$04$test', 'active')
                ; INSERT INTO advertiser_user_memberships (id, user_id, advertiser_organization_id, status, created_at)
                  VALUES ('aum-beh-xa', :uid, :oid2, 'active', NOW())
                ; INSERT INTO user_roles (id, user_id, role_id)
                  SELECT 'ur-beh-xa', :uid, id FROM roles WHERE code = 'advertiser'
            """, {"uid": approver_id, "oid2": ADV2_ORG_ID})

            token = _token(approver_id)
            resp = client.post(
                f"/api/v1/identity/campaigns/{cid}/approve",
                headers=_auth(token),
            )
            assert resp.status_code == 403, (
                f"Cross-org approve: expected 403, got {resp.status_code}: {resp.text}"
            )

            # Campaign unchanged
            rows = _raw_sql("SELECT status FROM campaigns WHERE id = :cid", {"cid": cid})
            assert rows[0][0] == "pending_approval"

            # No approval record from cross-org attempt
            rows = _raw_sql(
                "SELECT id FROM campaign_approvals WHERE reviewed_by = :uid",
                {"uid": approver_id},
            )
            assert len(rows) == 0, f"Expected 0 approval rows for cross-org approver, got {len(rows)}"
        finally:
            # Cleanup — always runs, even if assertions fail
            _raw_exec("""
                DELETE FROM campaign_status_history WHERE changed_by = :uid
                ; DELETE FROM campaign_approvals WHERE reviewed_by = :uid
                ; DELETE FROM advertiser_user_memberships WHERE user_id = :uid
                ; DELETE FROM local_credentials WHERE user_id = :uid
                ; DELETE FROM user_roles WHERE user_id = :uid
                ; DELETE FROM users WHERE id = :uid
                ; DELETE FROM role_permissions WHERE role_id = (SELECT id FROM roles WHERE code = 'advertiser')
                  AND permission_id = (SELECT id FROM permissions WHERE code = 'campaigns.approve')
            """, {"uid": approver_id})

        _draft()


# ---------------------------------------------------------------------------
# Flight/Contract Validation (P1-2)
# ---------------------------------------------------------------------------


class TestFlightContractValidation:

    def test_flight_outside_contract_blocked(self, client, user_ids):
        """Campaign with flight outside contract window → 422, no outbox."""
        _draft()
        cid = _cid()
        token = _token(user_ids["readonly"])

        # Contract valid_from = 2025-12-31T21:00Z, valid_until = NULL
        # Create a temp flight with start_at before valid_from
        _raw_exec("""
            INSERT INTO campaign_flights (id, campaign_id, name, start_at, end_at, created_at)
            VALUES ('flight-outside-01', :cid, 'Outside flight',
                    '2025-01-01T00:00:00Z', '2025-06-01T00:00:00Z', NOW())
        """, {"cid": cid})

        resp = client.post(
            f"/api/v1/identity/campaigns/{cid}/request-approval",
            headers=_auth(token),
        )
        assert resp.status_code == 422, (
            f"Flight outside contract: expected 422, got {resp.status_code}: {resp.text}"
        )

        # Campaign still in draft
        rows = _raw_sql("SELECT status FROM campaigns WHERE id = :cid", {"cid": cid})
        assert rows[0][0] == "draft"

        # No outbox event from failed request
        rows = _raw_sql(
            "SELECT id FROM outbox_events WHERE aggregate_id = :aid "
            "AND event_type = 'campaign.approval_requested'",
            {"aid": cid},
        )
        assert len(rows) == 0, f"Expected 0 outbox events, got {len(rows)}"

        # Clean up the out-of-contract flight
        _raw_exec("DELETE FROM campaign_flights WHERE id = 'flight-outside-01'")
        _draft()

    def test_flight_past_valid_until_blocked(self, client, user_ids):
        """Campaign with flight past contract valid_until → 422, no outbox."""
        _draft()
        cid = _cid()
        token = _token(user_ids["readonly"])

        # Create temp contract with finite valid_until, swap campaign to it
        _raw_exec("""
            INSERT INTO advertiser_contracts (id, advertiser_organization_id, code, name,
                valid_from, valid_until, status, created_at, updated_at)
            VALUES ('contract-temp-end', :oid, 'TEMP-END', 'Contract with end date',
                    '2025-06-01T00:00:00Z', '2025-12-31T23:59:59Z', 'active', NOW(), NOW())
            ON CONFLICT (id) DO NOTHING
        """, {"oid": ADV1_ORG_ID})
        _raw_exec(
            "UPDATE campaigns SET advertiser_contract_id = 'contract-temp-end' WHERE id = :cid",
            {"cid": cid},
        )

        # Create a flight whose end_at exceeds valid_until (2025-12-31)
        _raw_exec("""
            INSERT INTO campaign_flights (id, campaign_id, name, start_at, end_at, created_at)
            VALUES ('flight-past-end', :cid, 'Past-end flight',
                    '2025-07-01T00:00:00Z', '2026-06-01T00:00:00Z', NOW())
        """, {"cid": cid})

        resp = client.post(
            f"/api/v1/identity/campaigns/{cid}/request-approval",
            headers=_auth(token),
        )
        assert resp.status_code == 422, (
            f"Flight past valid_until: expected 422, got {resp.status_code}: {resp.text}"
        )

        # Campaign still in draft
        rows = _raw_sql("SELECT status FROM campaigns WHERE id = :cid", {"cid": cid})
        assert rows[0][0] == "draft"

        # No outbox event from failed request
        rows = _raw_sql(
            "SELECT id FROM outbox_events WHERE aggregate_id = :aid "
            "AND event_type = 'campaign.approval_requested'",
            {"aid": cid},
        )
        assert len(rows) == 0, f"Expected 0 outbox events, got {len(rows)}"

        # Restore
        _raw_exec("DELETE FROM campaign_flights WHERE id = 'flight-past-end'")
        _raw_exec(
            "UPDATE campaigns SET advertiser_contract_id = :ctr WHERE id = :cid",
            {"cid": cid, "ctr": ADV1_CONTRACT_ID},
        )
        _raw_exec("DELETE FROM advertiser_contracts WHERE id = 'contract-temp-end'")
        _draft()


# ---------------------------------------------------------------------------
# requested_at semantics (P1-1 proof)
# ---------------------------------------------------------------------------


class TestRequestedAtSemantics:

    def test_requested_at_not_decision_time(self, client, user_ids):
        """requested_at is the request timestamp, not the decision timestamp."""
        import time
        _draft()
        cid = _cid()
        token = _token(user_ids["readonly"])

        # Request approval via API (writes status_history with timestamp)
        resp = client.post(
            f"/api/v1/identity/campaigns/{cid}/request-approval",
            headers=_auth(token),
        )
        assert resp.status_code == 200

        # Small delay to ensure timestamps differ
        time.sleep(0.2)

        # Approve
        resp = client.post(
            f"/api/v1/identity/campaigns/{cid}/approve",
            headers=_auth(token),
        )
        assert resp.status_code == 200

        # Check approval record: requested_at should differ from reviewed_at
        rows = _raw_sql(
            "SELECT requested_at, reviewed_at FROM campaign_approvals "
            "WHERE campaign_id = :cid ORDER BY created_at DESC",
            {"cid": cid},
        )
        assert len(rows) >= 1
        req_at = rows[0][0]
        rev_at = rows[0][1]
        assert req_at is not None and rev_at is not None
        assert req_at < rev_at, (
            f"requested_at ({req_at}) should be before reviewed_at ({rev_at})"
        )

        _draft()
