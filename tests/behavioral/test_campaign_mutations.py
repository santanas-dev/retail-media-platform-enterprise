"""
Behavioral tests — Campaign Mutations (Phase 4.1c).
Phase 4.2: tenant isolation (P1 fixes).

Tests: create, update, archive with outbox, transaction safety, permissions,
cross-org isolation, brand/contract org validation.
Requires: RUN_BEHAVIORAL_TESTS=1, migrations applied, seed run.
"""

import asyncio
import json
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

# Well-known IDs from seed + conftest
ADV1_ORG_ID = "00000000-0000-0000-0000-000000000200"
ADV1_BRAND1_ID = "00000000-0000-0000-0000-000000000210"
ADV1_CONTRACT_ID = "00000000-0000-0000-0000-000000000212"
ADV2_ORG_ID = "00000000-0000-0000-0000-000000000300"
ADV2_BRAND_ID = "00000000-0000-0000-0000-000000000310"
ADV2_CONTRACT_ID = "00000000-0000-0000-0000-000000000312"


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
    """Run INSERT/UPDATE/DELETE statements. Splits multi-statement SQL."""
    async def _run():
        engine = create_async_engine(DB_URL, echo=False)
        async with engine.begin() as conn:
            for stmt in sql.split(";"):
                s = stmt.strip()
                if s and not s.startswith("--"):
                    await conn.execute(text(s), params or {})
        await engine.dispose()
    asyncio.run(_run())


_ADV2_SETUP_SQL = """
    INSERT INTO advertiser_organizations (id, code, legal_name, display_name) VALUES
    ('00000000-0000-0000-0000-000000000300','ADV-002',
     'ООО «Тест-Орг 2»', 'Тест-Орг 2')
    ON CONFLICT (code) DO NOTHING
    ; INSERT INTO advertiser_brands (id, advertiser_organization_id, code, name, status) VALUES
    ('00000000-0000-0000-0000-000000000310','00000000-0000-0000-0000-000000000300',
     'BRAND-002','Бренд ADV-002','active')
    ON CONFLICT (advertiser_organization_id, code) DO NOTHING
    ; INSERT INTO advertiser_contracts (id, advertiser_organization_id, code, name,
        contract_number, budget_limit_amount, budget_limit_currency, valid_from, status) VALUES
    ('00000000-0000-0000-0000-000000000312','00000000-0000-0000-0000-000000000300',
     'CONTRACT-002','Контракт ADV-002','2026/ADV-002',500000,'RUB','2026-01-01','active')
    ON CONFLICT (advertiser_organization_id, code) DO NOTHING
"""

_ADV2_CLEANUP_SQL = """
    DELETE FROM advertiser_contracts WHERE id='00000000-0000-0000-0000-000000000312'
    ; DELETE FROM advertiser_brands WHERE id='00000000-0000-0000-0000-000000000310'
    ; DELETE FROM advertiser_organizations WHERE id='00000000-0000-0000-0000-000000000300'
"""


# ---------------------------------------------------------------------------
# Create Campaign
# ---------------------------------------------------------------------------


class TestCreateCampaign:

    def test_no_token_returns_401(self, client):
        resp = client.post("/api/v1/identity/campaigns", json={
            "advertiser_organization_id": "x",
            "advertiser_contract_id": "y",
            "code": "C",
            "name": "N",
        })
        assert resp.status_code == 401

    def test_no_permission_returns_403(self, client, user_ids):
        """User without campaigns.manage gets 403."""
        token = _token(user_ids["noperms"])  # operator — campaigns.read only
        resp = client.post(
            "/api/v1/identity/campaigns",
            json={
                "advertiser_organization_id": ADV1_ORG_ID,
                "advertiser_contract_id": ADV1_CONTRACT_ID,
                "code": "CAMP-NOPERM",
                "name": "No Permission",
            },
            headers=_auth(token),
        )
        assert resp.status_code == 403

    def test_admin_creates_draft_campaign(self, client, user_ids):
        """Admin with campaigns.manage creates a draft campaign."""
        token = _token(user_ids["readonly"])  # system_admin
        resp = client.post(
            "/api/v1/identity/campaigns",
            json={
                "advertiser_organization_id": ADV1_ORG_ID,
                "advertiser_contract_id": ADV1_CONTRACT_ID,
                "code": "CAMP-BEH-001",
                "name": "Behavioral Test Campaign",
            },
            headers=_auth(token),
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["code"] == "CAMP-BEH-001"
        assert data["status"] == "draft"
        cid = data["id"]

        # Verify outbox event exists
        rows = _raw_sql(
            "SELECT event_type, status FROM outbox_events WHERE aggregate_id = :aid",
            {"aid": cid},
        )
        event_types = {r[0] for r in rows}
        assert "campaign.created" in event_types, f"No campaign.created event for {cid}"

        # Verify status history
        rows = _raw_sql(
            "SELECT new_status FROM campaign_status_history WHERE campaign_id = :cid",
            {"cid": cid},
        )
        assert len(rows) >= 1
        assert rows[0][0] == "draft"

    def test_create_writes_outbox_in_same_transaction(self, client, user_ids):
        """Outbox event INSERT is in the same logical transaction.
        Proved by: commit → both campaign and outbox event exist."""
        token = _token(user_ids["readonly"])
        resp = client.post(
            "/api/v1/identity/campaigns",
            json={
                "advertiser_organization_id": ADV1_ORG_ID,
                "advertiser_contract_id": ADV1_CONTRACT_ID,
                "code": "CAMP-BEH-TXN",
                "name": "Transaction Test",
            },
            headers=_auth(token),
        )
        assert resp.status_code == 201
        cid = resp.json()["id"]

        # Both campaign and outbox event must exist
        camp_rows = _raw_sql("SELECT id FROM campaigns WHERE id = :cid", {"cid": cid})
        outbox_rows = _raw_sql(
            "SELECT id FROM outbox_events WHERE aggregate_id = :cid",
            {"cid": cid},
        )
        assert len(camp_rows) == 1
        assert len(outbox_rows) >= 1


# ---------------------------------------------------------------------------
# Tenant Isolation — Create (Phase 4.2 P1)
# ---------------------------------------------------------------------------


class TestCreateCampaignTenantIsolation:

    @pytest.fixture(autouse=True)
    def _setup_adv2(self, db_available):
        """Create ADV-002 test org with brand/contract for cross-org tests."""
        _raw_exec(_ADV2_SETUP_SQL)
        yield
        _raw_exec(_ADV2_CLEANUP_SQL)

    def _token_for(self, user_ids, key):
        return _token(user_ids[key])

    def test_scoped_advertiser_cannot_create_for_other_org(self, client, user_ids):
        """Scoped advertiser (ADV-001) cannot create campaign for ADV-002."""
        token = self._token_for(user_ids, "advertiser")
        resp = client.post(
            "/api/v1/identity/campaigns",
            json={
                "advertiser_organization_id": ADV2_ORG_ID,
                "advertiser_contract_id": ADV2_CONTRACT_ID,
                "code": "CAMP-XORG",
                "name": "Cross Org",
            },
            headers=_auth(token),
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"

    def test_scoped_advertiser_cannot_use_cross_org_brand(self, client, user_ids):
        """Scoped advertiser (ADV-001) cannot create campaign with ADV-002 brand."""
        token = self._token_for(user_ids, "advertiser")
        resp = client.post(
            "/api/v1/identity/campaigns",
            json={
                "advertiser_organization_id": ADV1_ORG_ID,
                "advertiser_brand_id": ADV2_BRAND_ID,
                "advertiser_contract_id": ADV1_CONTRACT_ID,
                "code": "CAMP-XBRAND",
                "name": "Cross Brand",
            },
            headers=_auth(token),
        )
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"

    def test_scoped_advertiser_cannot_use_cross_org_contract(self, client, user_ids):
        """Scoped advertiser (ADV-001) cannot create campaign with ADV-002 contract."""
        token = self._token_for(user_ids, "advertiser")
        resp = client.post(
            "/api/v1/identity/campaigns",
            json={
                "advertiser_organization_id": ADV1_ORG_ID,
                "advertiser_contract_id": ADV2_CONTRACT_ID,
                "code": "CAMP-XCTR",
                "name": "Cross Contract",
            },
            headers=_auth(token),
        )
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"

    def test_scoped_advertiser_can_create_for_own_org(self, client, user_ids):
        """Scoped advertiser (ADV-001) CAN create campaign for ADV-001."""
        token = self._token_for(user_ids, "advertiser")
        resp = client.post(
            "/api/v1/identity/campaigns",
            json={
                "advertiser_organization_id": ADV1_ORG_ID,
                "advertiser_contract_id": ADV1_CONTRACT_ID,
                "code": "CAMP-SCOPED-OK",
                "name": "Scoped OK",
            },
            headers=_auth(token),
        )
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
        assert resp.json()["status"] == "draft"

    def test_admin_can_create_for_any_org(self, client, user_ids):
        """Unscoped admin can create campaign for ADV-002."""
        token = self._token_for(user_ids, "readonly")  # system_admin
        resp = client.post(
            "/api/v1/identity/campaigns",
            json={
                "advertiser_organization_id": ADV2_ORG_ID,
                "advertiser_contract_id": ADV2_CONTRACT_ID,
                "code": "CAMP-ADMIN-XORG",
                "name": "Admin Cross Org",
            },
            headers=_auth(token),
        )
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"

    def test_admin_cannot_use_cross_org_contract_with_wrong_org(self, client, user_ids):
        """Admin cannot pair ADV1 org with ADV2 contract (brand/contract checks
        apply to everyone, not just scoped users)."""
        token = self._token_for(user_ids, "readonly")
        resp = client.post(
            "/api/v1/identity/campaigns",
            json={
                "advertiser_organization_id": ADV1_ORG_ID,
                "advertiser_contract_id": ADV2_CONTRACT_ID,
                "code": "CAMP-ADMIN-XCTR",
                "name": "Admin Cross Contract",
            },
            headers=_auth(token),
        )
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"

    def test_nonexistent_contract_same_as_cross_org(self, client, user_ids):
        """Nonexistent contract → 422 with same generic message as cross-org.
        No existence oracle: indistinguishable from cross-org reference."""
        token = self._token_for(user_ids, "readonly")
        nonexistent_id = "00000000-0000-0000-0000-ffffffffffff"

        resp = client.post(
            "/api/v1/identity/campaigns",
            json={
                "advertiser_organization_id": ADV1_ORG_ID,
                "advertiser_contract_id": nonexistent_id,
                "code": "CAMP-NOEX-CTR",
                "name": "Nonexistent Contract",
            },
            headers=_auth(token),
        )
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"
        # Must be same message as cross-org
        assert "Invalid advertiser contract reference" in resp.text

        # No campaign created
        rows = _raw_sql("SELECT id FROM campaigns WHERE code = 'CAMP-NOEX-CTR'")
        assert len(rows) == 0

    def test_nonexistent_brand_same_as_cross_org(self, client, user_ids):
        """Nonexistent brand → 422 with same generic message as cross-org."""
        token = self._token_for(user_ids, "readonly")
        nonexistent_id = "00000000-0000-0000-0000-eeeeeeeeeeee"

        resp = client.post(
            "/api/v1/identity/campaigns",
            json={
                "advertiser_organization_id": ADV1_ORG_ID,
                "advertiser_brand_id": nonexistent_id,
                "advertiser_contract_id": ADV1_CONTRACT_ID,
                "code": "CAMP-NOEX-BR",
                "name": "Nonexistent Brand",
            },
            headers=_auth(token),
        )
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"
        assert "Invalid advertiser brand reference" in resp.text

        # No campaign created
        rows = _raw_sql("SELECT id FROM campaigns WHERE code = 'CAMP-NOEX-BR'")
        assert len(rows) == 0

    def test_wrong_org_rejection_does_not_write_outbox(self, client, user_ids):
        """P2: scope rejection → no campaign, no outbox event."""
        token = self._token_for(user_ids, "advertiser")
        resp = client.post(
            "/api/v1/identity/campaigns",
            json={
                "advertiser_organization_id": ADV2_ORG_ID,
                "advertiser_contract_id": ADV2_CONTRACT_ID,
                "code": "CAMP-NOBOX",
                "name": "No Outbox",
            },
            headers=_auth(token),
        )
        assert resp.status_code == 403

        # No campaign with that code
        rows = _raw_sql(
            "SELECT id FROM campaigns WHERE code = :code",
            {"code": "CAMP-NOBOX"},
        )
        assert len(rows) == 0, "Campaign should not exist after 403 rejection"

        # No outbox event for it either
        outbox_rows = _raw_sql(
            "SELECT id FROM outbox_events WHERE aggregate_id IN "
            "(SELECT id FROM campaigns WHERE code = :code)",
            {"code": "CAMP-NOBOX"},
        )
        assert len(outbox_rows) == 0, "Outbox event should not exist after 403 rejection"


# ---------------------------------------------------------------------------
# Update Campaign
# ---------------------------------------------------------------------------


class TestUpdateCampaign:

    def _create_draft(self, client, token, code):
        resp = client.post(
            "/api/v1/identity/campaigns",
            json={
                "advertiser_organization_id": ADV1_ORG_ID,
                "advertiser_contract_id": ADV1_CONTRACT_ID,
                "code": code,
                "name": f"Test {code}",
            },
            headers=_auth(token),
        )
        return resp.json()["id"]

    def test_update_draft_campaign(self, client, user_ids):
        token = _token(user_ids["readonly"])
        cid = self._create_draft(client, token, "CAMP-BEH-UPD")

        resp = client.patch(
            f"/api/v1/identity/campaigns/{cid}",
            json={"name": "Updated Campaign Name"},
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["name"] == "Updated Campaign Name"

        # Outbox event for update
        rows = _raw_sql(
            "SELECT event_type FROM outbox_events WHERE aggregate_id = :aid "
            "AND event_type = 'campaign.updated'",
            {"aid": cid},
        )
        assert len(rows) >= 1

    def test_update_non_draft_rejected(self, client, user_ids):
        """P2 fix: cannot update a campaign in non-draft status.
        Uses seed campaign CAMP-2026-001 — change its status, then PATCH."""
        token = _token(user_ids["readonly"])

        # Find the seed campaign
        rows = _raw_sql(
            "SELECT id, status FROM campaigns WHERE code = 'CAMP-2026-001'"
        )
        assert len(rows) == 1
        cid, old_status = rows[0][0], rows[0][1]
        assert old_status == "draft"

        # Change status to 'active' via direct SQL (simulating approved state)
        _raw_exec(
            "UPDATE campaigns SET status = 'active' WHERE id = :cid",
            {"cid": cid},
        )

        # Now PATCH must fail because it's not draft
        resp = client.patch(
            f"/api/v1/identity/campaigns/{cid}",
            json={"name": "Should Not Work"},
            headers=_auth(token),
        )
        assert resp.status_code == 409, (
            f"Expected 409 (non-draft), got {resp.status_code}: {resp.text}"
        )

        # Restore status
        _raw_exec(
            "UPDATE campaigns SET status = 'draft' WHERE id = :cid",
            {"cid": cid},
        )

    def test_no_token_update_returns_401(self, client):
        resp = client.patch(
            "/api/v1/identity/campaigns/some-id",
            json={"name": "x"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Update/Archive Tenant Isolation (Phase 4.2 P1)
# ---------------------------------------------------------------------------


class TestUpdateArchiveTenantIsolation:

    @pytest.fixture(autouse=True)
    def _setup_adv2(self, db_available):
        """Create ADV-002 test org with brand/contract for cross-org tests."""
        _raw_exec(_ADV2_SETUP_SQL)
        yield
        _raw_exec(_ADV2_CLEANUP_SQL)

    def _create_draft(self, client, token, code, org_id=ADV1_ORG_ID, contract_id=ADV1_CONTRACT_ID):
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
        return resp.json()["id"]

    def test_scoped_advertiser_cannot_update_other_org_campaign(self, client, user_ids):
        """Scoped advertiser (ADV-001) cannot PATCH a campaign owned by ADV-002."""
        # Admin creates a campaign for ADV-002
        admin_token = _token(user_ids["readonly"])
        cid = self._create_draft(
            client, admin_token, "CAMP-ISO-UPD",
            org_id=ADV2_ORG_ID, contract_id=ADV2_CONTRACT_ID,
        )

        # Scoped advertiser tries to PATCH it
        scoped_token = _token(user_ids["advertiser"])
        resp = client.patch(
            f"/api/v1/identity/campaigns/{cid}",
            json={"name": "Hijack Attempt"},
            headers=_auth(scoped_token),
        )
        assert resp.status_code == 403, (
            f"Expected 403 (scope), got {resp.status_code}: {resp.text}"
        )

    def test_scoped_advertiser_cannot_archive_other_org_campaign(self, client, user_ids):
        """Scoped advertiser (ADV-001) cannot archive a campaign owned by ADV-002."""
        admin_token = _token(user_ids["readonly"])
        cid = self._create_draft(
            client, admin_token, "CAMP-ISO-ARCH",
            org_id=ADV2_ORG_ID, contract_id=ADV2_CONTRACT_ID,
        )

        scoped_token = _token(user_ids["advertiser"])
        resp = client.post(
            f"/api/v1/identity/campaigns/{cid}/archive",
            headers=_auth(scoped_token),
        )
        assert resp.status_code == 403, (
            f"Expected 403 (scope), got {resp.status_code}: {resp.text}"
        )

    def test_admin_can_update_any_org_campaign(self, client, user_ids):
        """Admin can PATCH campaign from any org."""
        admin_token = _token(user_ids["readonly"])
        cid = self._create_draft(
            client, admin_token, "CAMP-ADM-UPD",
            org_id=ADV2_ORG_ID, contract_id=ADV2_CONTRACT_ID,
        )

        resp = client.patch(
            f"/api/v1/identity/campaigns/{cid}",
            json={"name": "Admin Update Any Org"},
            headers=_auth(admin_token),
        )
        assert resp.status_code == 200, resp.text


# ---------------------------------------------------------------------------
# Archive Campaign
# ---------------------------------------------------------------------------


class TestArchiveCampaign:

    def _create_draft(self, client, token, code):
        resp = client.post(
            "/api/v1/identity/campaigns",
            json={
                "advertiser_organization_id": ADV1_ORG_ID,
                "advertiser_contract_id": ADV1_CONTRACT_ID,
                "code": code,
                "name": f"Test {code}",
            },
            headers=_auth(token),
        )
        return resp.json()["id"]

    def test_archive_draft_campaign(self, client, user_ids):
        token = _token(user_ids["readonly"])
        cid = self._create_draft(client, token, "CAMP-BEH-ARCH")

        resp = client.post(
            f"/api/v1/identity/campaigns/{cid}/archive",
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["campaign_id"] == cid
        assert data["old_status"] == "draft"
        assert data["new_status"] == "archived"

        # Verify campaign status changed
        rows = _raw_sql(
            "SELECT status FROM campaigns WHERE id = :cid",
            {"cid": cid},
        )
        assert rows[0][0] == "archived"

        # Status history row written
        rows = _raw_sql(
            "SELECT new_status FROM campaign_status_history WHERE campaign_id = :cid "
            "ORDER BY changed_at",
            {"cid": cid},
        )
        statuses = [r[0] for r in rows]
        assert "archived" in statuses

        # Outbox event
        rows = _raw_sql(
            "SELECT event_type FROM outbox_events WHERE aggregate_id = :aid "
            "AND event_type = 'campaign.archived'",
            {"aid": cid},
        )
        assert len(rows) >= 1

    def test_archive_nonexistent_returns_404(self, client, user_ids):
        token = _token(user_ids["readonly"])
        resp = client.post(
            "/api/v1/identity/campaigns/00000000-0000-0000-0000-000000000999/archive",
            headers=_auth(token),
        )
        assert resp.status_code == 404

    def test_no_token_archive_returns_401(self, client):
        resp = client.post("/api/v1/identity/campaigns/some-id/archive")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# S-008: DB write RLS enforcement (Phase 4.1e)
# ---------------------------------------------------------------------------
# Tests prove campaign mutations succeed/fail correctly under
# NOBYPASSRLS when the app connects as retail_media_app.


class TestRLSWriteEnforcement:
    """DB-layer RLS must allow in-scope writes and reject cross-scope.

    These tests send HTTP requests through the FastAPI app (TestClient).
    When DATABASE_URL points to a NOBYPASSRLS role (CI), the DB RLS
    policies enforce the same tenant isolation as the app-layer checks.
    """

    def test_admin_creates_campaign_rls_pass(self, client, user_ids):
        """Admin creates campaign — RLS INSERT policy allows (admin bypass)."""
        token = _token(user_ids["readonly"])  # system_admin
        resp = client.post(
            "/api/v1/identity/campaigns",
            json={
                "advertiser_organization_id": ADV1_ORG_ID,
                "advertiser_contract_id": ADV1_CONTRACT_ID,
                "code": "RLS-ADMIN-001",
                "name": "RLS Admin Create",
            },
            headers=_auth(token),
        )
        assert resp.status_code == 201, resp.text

    def test_scoped_advertiser_creates_in_own_org_rls_pass(self, client, user_ids):
        """Scoped advertiser creates campaign in own org — RLS allows."""
        token = _token(user_ids["advertiser"])
        resp = client.post(
            "/api/v1/identity/campaigns",
            json={
                "advertiser_organization_id": ADV1_ORG_ID,
                "advertiser_contract_id": ADV1_CONTRACT_ID,
                "code": "RLS-SCOPED-001",
                "name": "RLS Scoped Create",
            },
            headers=_auth(token),
        )
        assert resp.status_code == 201, resp.text

    def test_cross_org_create_rejected_by_rls(self, client, user_ids):
        """Scoped advertiser → foreign org → DB RLS blocks INSERT.

        The app-layer check (S-004) returns 403 first, but even if
        bypassed, the DB RLS would reject the INSERT.
        """
        token = _token(user_ids["advertiser"])
        # ADV2_ORG_ID is not in the advertiser's scope
        resp = client.post(
            "/api/v1/identity/campaigns",
            json={
                "advertiser_organization_id": ADV2_ORG_ID,
                "advertiser_contract_id": ADV2_CONTRACT_ID,
                "code": "RLS-XORG-001",
                "name": "RLS Cross Org",
            },
            headers=_auth(token),
        )
        assert resp.status_code == 403, (
            f"Expected 403 cross-org rejection, got {resp.status_code}: {resp.text}"
        )

    def test_no_outbox_on_rejected_write(self, client, user_ids):
        """Rejected campaign create must not leave outbox rows."""
        token = _token(user_ids["advertiser"])
        resp = client.post(
            "/api/v1/identity/campaigns",
            json={
                "advertiser_organization_id": ADV2_ORG_ID,
                "advertiser_contract_id": ADV2_CONTRACT_ID,
                "code": "RLS-NOOUTBOX",
                "name": "No Outbox",
            },
            headers=_auth(token),
        )
        assert resp.status_code == 403

        # Verify no outbox event for rejected campaign
        rows = _raw_sql(
            "SELECT COUNT(*) FROM outbox_events WHERE aggregate_id IN "
            "(SELECT id FROM campaigns WHERE code = 'RLS-NOOUTBOX')",
        )
        assert rows[0][0] == 0, "Outbox row found for rejected campaign"

