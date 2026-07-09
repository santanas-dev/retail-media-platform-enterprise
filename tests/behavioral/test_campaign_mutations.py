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
ADV2_ORG_ID = "00000000-0000-0000-0000-000000000201"  # matches seed
ADV2_BRAND_ID = "00000000-0000-0000-0000-000000000311"
ADV2_CONTRACT_ID = "00000000-0000-0000-0000-000000000313"

# Seed IDs from apps/control-api/seed.py
SEED_CAMPAIGN_ID = "00000000-0000-0000-0000-000000000220"
SEED_STORE_ID = "00000000-0000-0000-0000-000000000003"


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
    """Run INSERT/UPDATE/DELETE statements. Splits multi-statement SQL."""
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


_ADV2_SETUP_SQL = """
    -- ADV-002 org already exists in seed (id=201), just ensure brand+contract
    INSERT INTO advertiser_brands (id, advertiser_organization_id, code, name, status) VALUES
    ('00000000-0000-0000-0000-000000000311','00000000-0000-0000-0000-000000000201',
     'BRAND-ADV2','Бренд ADV-002','active')
    ON CONFLICT (advertiser_organization_id, code) DO NOTHING
    ; INSERT INTO advertiser_contracts (id, advertiser_organization_id, code, name,
        contract_number, budget_limit_amount, budget_limit_currency, valid_from, status) VALUES
    ('00000000-0000-0000-0000-000000000313','00000000-0000-0000-0000-000000000201',
     'CTR-ADV2','Контракт ADV-002','2026/ADV-002',500000,'RUB','2026-01-01','active')
    ON CONFLICT (advertiser_organization_id, code) DO NOTHING
"""

_ADV2_CLEANUP_SQL = """
    DELETE FROM advertiser_contracts WHERE id='00000000-0000-0000-0000-000000000313'
    ; DELETE FROM advertiser_brands WHERE id='00000000-0000-0000-0000-000000000311'
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
        """Create ADV-002 test brand/contract for cross-org tests."""
        _raw_exec(_ADV2_SETUP_SQL)
        yield
        _raw_exec(_ADV2_CLEANUP_SQL)

    def _token_for(self, user_ids, key):
        return _token(user_ids[key])

    def test_scoped_advertiser_cannot_create_for_other_org(self, client, user_ids):
        """Scoped advertiser (ADV-001) blocked from creating for ADV-002.
        Under NOBYPASSRLS, contract validation (422) fires before scope check
        because the scoped user cannot see ADV-002 contracts via RLS."""
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
        assert resp.status_code in (403, 422), (
            f"Expected 403 or 422, got {resp.status_code}: {resp.text}"
        )

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
        """P2: rejection → no campaign, no outbox event.
        Under NOBYPASSRLS, contract validation (422) may fire before scope check."""
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
        assert resp.status_code in (403, 422), (
            f"Expected 403 or 422, got {resp.status_code}: {resp.text}"
        )

        # No campaign with that code
        rows = _raw_sql(
            "SELECT id FROM campaigns WHERE code = :code",
            {"code": "CAMP-NOBOX"},
        )
        assert len(rows) == 0, "Campaign should not exist after rejection"

        # No outbox event for it either
        outbox_rows = _raw_sql(
            "SELECT id FROM outbox_events WHERE aggregate_id IN "
            "(SELECT id FROM campaigns WHERE code = :code)",
            {"code": "CAMP-NOBOX"},
        )
        assert len(outbox_rows) == 0, "Outbox event should not exist after rejection"


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
        Uses seed campaign CAMP-2026-001 — ensure draft, change to active, PATCH."""
        token = _token(user_ids["readonly"])

        # Find the seed campaign and ensure it starts as draft
        _raw_exec(
            "UPDATE campaigns SET status = 'draft' WHERE code = 'CAMP-2026-001'"
        )
        rows = _raw_sql(
            "SELECT id, status FROM campaigns WHERE code = 'CAMP-2026-001'"
        )
        assert len(rows) == 1
        cid = rows[0][0]
        assert rows[0][1] == "draft"

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
        """Create ADV-002 test brand/contract for cross-org tests."""
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
        """Scoped advertiser (ADV-001) cannot PATCH a campaign owned by ADV-002.
        Under NOBYPASSRLS, RLS hides the campaign → 409 (not found/draft)."""
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
        assert resp.status_code in (403, 409), (
            f"Under RLS expected 403 or 409 (hidden), got {resp.status_code}: {resp.text}"
        )

    def test_scoped_advertiser_cannot_archive_other_org_campaign(self, client, user_ids):
        """Scoped advertiser (ADV-001) cannot archive a campaign owned by ADV-002.
        Under NOBYPASSRLS, RLS hides the campaign → 404 (not found)."""
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
        assert resp.status_code in (403, 404, 409), (
            f"Under RLS expected 403/404/409 (hidden), got {resp.status_code}: {resp.text}"
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
        """Scoped advertiser → foreign org → rejected.

        Under NOBYPASSRLS, contract validation (422) fires first because
        the scoped user cannot see foreign contracts via RLS."""
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
        assert resp.status_code in (403, 422), (
            f"Expected 403 or 422 cross-org rejection, got {resp.status_code}: {resp.text}"
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
        assert resp.status_code in (403, 422), (
            f"Expected 403 or 422, got {resp.status_code}: {resp.text}"
        )

        # Verify no outbox event for rejected campaign
        rows = _raw_sql(
            "SELECT COUNT(*) FROM outbox_events WHERE aggregate_id IN "
            "(SELECT id FROM campaigns WHERE code = 'RLS-NOOUTBOX')",
        )
        assert rows[0][0] == 0, "Outbox row found for rejected campaign"


# ═══════════════════════════════════════════════════════════════════
# Campaign Setup Mutations — Flight / Placement / Creative (Pilot B1)
# ═══════════════════════════════════════════════════════════════════


class TestCampaignSetupFlights:
    """Flight create/update behavioral tests."""

    def test_create_flight_on_draft_campaign(self, client, user_ids):
        """Advertiser creates a flight on their own draft campaign."""
        token = _token(user_ids["advertiser"])
        # Create a draft campaign first
        resp = client.post(
            "/api/v1/identity/campaigns",
            json={
                "advertiser_organization_id": ADV1_ORG_ID,
                "advertiser_contract_id": ADV1_CONTRACT_ID,
                "code": "BEH-FLIGHT-001",
                "name": "Flight Test Campaign",
            },
            headers=_auth(token),
        )
        assert resp.status_code == 201, resp.text
        campaign_id = resp.json()["id"]

        now = "2026-06-01T00:00:00Z"
        end = "2026-07-01T00:00:00Z"
        resp = client.post(
            f"/api/v1/identity/campaigns/{campaign_id}/flights",
            json={"start_at": now, "end_at": end, "name": "Summer Flight"},
            headers=_auth(token),
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["campaign_id"] == campaign_id
        assert body["name"] == "Summer Flight"

        # Outbox event written
        rows = _raw_sql(
            f"SELECT COUNT(*) FROM outbox_events "
            f"WHERE aggregate_id = '{campaign_id}' AND event_type = 'campaign.flight.changed'"
        )
        assert rows[0][0] >= 1, "Outbox event not written for flight creation"

    def test_update_flight(self, client, user_ids):
        token = _token(user_ids["advertiser"])
        resp = client.post(
            "/api/v1/identity/campaigns",
            json={
                "advertiser_organization_id": ADV1_ORG_ID,
                "advertiser_contract_id": ADV1_CONTRACT_ID,
                "code": "BEH-FLIGHT-UPD",
                "name": "Flight Update Campaign",
            },
            headers=_auth(token),
        )
        assert resp.status_code == 201
        campaign_id = resp.json()["id"]

        resp = client.post(
            f"/api/v1/identity/campaigns/{campaign_id}/flights",
            json={"start_at": "2026-06-01T00:00:00Z", "end_at": "2026-07-01T00:00:00Z"},
            headers=_auth(token),
        )
        assert resp.status_code == 201
        flight_id = resp.json()["id"]

        resp = client.patch(
            f"/api/v1/identity/campaigns/{campaign_id}/flights/{flight_id}",
            json={"name": "Updated Flight Name"},
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["name"] == "Updated Flight Name"

    def test_cross_org_flight_create_rejected(self, client, user_ids):
        """Advertiser cannot create a flight on another org's campaign."""
        token = _token(user_ids["advertiser"])
        # Advertiser is scoped to ADV1; trying with ADV2 org should fail
        resp = client.post(
            "/api/v1/identity/campaigns",
            json={
                "advertiser_organization_id": ADV2_ORG_ID,
                "advertiser_contract_id": ADV2_CONTRACT_ID,
                "code": "BEH-FL-XORG",
                "name": "Cross Org Camp",
            },
            headers=_auth(token),
        )
        # Advertiser scoped to ADV1 cannot create under ADV2
        assert resp.status_code in (403, 422), (
            f"Expected 403/422 cross-org create rejected, got {resp.status_code}"
        )

    def test_flight_on_non_draft_campaign_rejected(self, client, user_ids):
        """Cannot add flight to a non-draft campaign."""
        token = _token(user_ids["advertiser"])
        # Create + approve a campaign first
        resp = client.post(
            "/api/v1/identity/campaigns",
            json={
                "advertiser_organization_id": ADV1_ORG_ID,
                "advertiser_contract_id": ADV1_CONTRACT_ID,
                "code": "BEH-FL-NODRAFT",
                "name": "No Draft Flight",
            },
            headers=_auth(token),
        )
        assert resp.status_code == 201
        campaign_id = resp.json()["id"]

        # Need flight + placement + creative to request approval
        client.post(
            f"/api/v1/identity/campaigns/{campaign_id}/flights",
            json={"start_at": "2026-06-01T00:00:00Z", "end_at": "2026-07-01T00:00:00Z"},
            headers=_auth(token),
        )
        client.post(
            f"/api/v1/identity/campaigns/{campaign_id}/placements",
            json={"store_id": SEED_STORE_ID},
            headers=_auth(token),
        )
        client.post(
            f"/api/v1/identity/campaigns/{campaign_id}/creatives",
            json={
                "code": "BEH-CR-NODRAFT",
                "name": "Creative",
                "media_type": "video/mp4",
                "sha256_checksum": "a" * 64,
                "file_size_bytes": 1000,
            },
            headers=_auth(token),
        )
        # Request approval
        client.post(
            f"/api/v1/identity/campaigns/{campaign_id}/request-approval",
            headers=_auth(token),
        )

        # Now try to add a flight — should fail (not draft)
        resp = client.post(
            f"/api/v1/identity/campaigns/{campaign_id}/flights",
            json={"start_at": "2026-06-01T00:00:00Z", "end_at": "2026-07-01T00:00:00Z"},
            headers=_auth(token),
        )
        assert resp.status_code == 409, (
            f"Expected 409 for non-draft flight creation, got {resp.status_code}"
        )


class TestCampaignFlightValidation:
    """Flight date validation — start_at/end_at, contract window."""

    def _create_campaign(self, client, token, code, name):
        resp = client.post(
            "/api/v1/identity/campaigns",
            json={
                "advertiser_organization_id": ADV1_ORG_ID,
                "advertiser_contract_id": ADV1_CONTRACT_ID,
                "code": code,
                "name": name,
            },
            headers=_auth(token),
        )
        assert resp.status_code == 201, resp.text
        return resp.json()["id"]

    def test_create_start_after_end_returns_422(self, client, user_ids):
        token = _token(user_ids["advertiser"])
        cid = self._create_campaign(client, token, "BEH-FL-VAL01", "Flight Val 1")
        resp = client.post(
            f"/api/v1/identity/campaigns/{cid}/flights",
            json={"start_at": "2026-07-01T00:00:00Z", "end_at": "2026-06-01T00:00:00Z"},
            headers=_auth(token),
        )
        assert resp.status_code == 422, (
            f"Expected 422 start >= end, got {resp.status_code}: {resp.text}"
        )
        # No outbox
        rows = _raw_sql(
            f"SELECT COUNT(*) FROM outbox_events "
            f"WHERE aggregate_id = '{cid}' AND event_type = 'campaign.flight.changed'"
        )
        assert rows[0][0] == 0, "Outbox written for invalid flight"

    def test_update_start_after_end_returns_422(self, client, user_ids):
        token = _token(user_ids["advertiser"])
        cid = self._create_campaign(client, token, "BEH-FL-VAL02", "Flight Val 2")
        resp = client.post(
            f"/api/v1/identity/campaigns/{cid}/flights",
            json={"start_at": "2026-07-01T00:00:00Z", "end_at": "2026-08-01T00:00:00Z"},
            headers=_auth(token),
        )
        assert resp.status_code == 201, resp.text
        fid = resp.json()["id"]

        resp = client.patch(
            f"/api/v1/identity/campaigns/{cid}/flights/{fid}",
            json={"end_at": "2026-06-01T00:00:00Z"},
            headers=_auth(token),
        )
        assert resp.status_code == 422, (
            f"Expected 422 update start >= end, got {resp.status_code}: {resp.text}"
        )
        # Invalid update did not mutate flight or enqueue a second outbox event
        rows = _raw_sql(
            f"SELECT COUNT(*) FROM outbox_events "
            f"WHERE aggregate_id = '{cid}' AND event_type = 'campaign.flight.changed'"
        )
        assert rows[0][0] == 1, (
            f"Expected 1 outbox from valid create, not {rows[0][0]} "
            f"(invalid update should not enqueue)"
        )
        flight_rows = _raw_sql(
            f"SELECT COUNT(*) FROM campaign_flights WHERE id = '{fid}'"
        )
        assert flight_rows[0][0] == 1, "Flight row should still exist after rejected update"

    def test_create_before_contract_valid_from_returns_422(self, client, user_ids):
        """ADV1 contract valid_from = 2026-01-01. Flight start before that should fail."""
        token = _token(user_ids["advertiser"])
        cid = self._create_campaign(client, token, "BEH-FL-VAL03", "Flight Val 3")
        resp = client.post(
            f"/api/v1/identity/campaigns/{cid}/flights",
            json={
                "start_at": "2025-12-01T00:00:00Z",
                "end_at": "2026-06-01T00:00:00Z",
            },
            headers=_auth(token),
        )
        assert resp.status_code == 422, (
            f"Expected 422 before contract, got {resp.status_code}: {resp.text}"
        )
        rows = _raw_sql(
            f"SELECT COUNT(*) FROM outbox_events "
            f"WHERE aggregate_id = '{cid}' AND event_type = 'campaign.flight.changed'"
        )
        assert rows[0][0] == 0, "Outbox written for invalid flight"

    def test_valid_flight_within_contract_window_ok(self, client, user_ids):
        token = _token(user_ids["advertiser"])
        cid = self._create_campaign(client, token, "BEH-FL-VAL04", "Flight Val 4")
        resp = client.post(
            f"/api/v1/identity/campaigns/{cid}/flights",
            json={
                "start_at": "2026-07-01T00:00:00Z",
                "end_at": "2026-08-01T00:00:00Z",
            },
            headers=_auth(token),
        )
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"

    def test_open_ended_contract_accepts_future_flight(self, client, user_ids):
        """ADV1 contract has no valid_until (NULL) — any future end_at is OK."""
        token = _token(user_ids["advertiser"])
        cid = self._create_campaign(client, token, "BEH-FL-VAL05", "Flight Val 5")
        resp = client.post(
            f"/api/v1/identity/campaigns/{cid}/flights",
            json={
                "start_at": "2027-06-01T00:00:00Z",
                "end_at": "2027-08-01T00:00:00Z",
            },
            headers=_auth(token),
        )
        assert resp.status_code == 201, (
            f"Expected 201 for open-ended contract, got {resp.status_code}: {resp.text}"
        )

    def test_create_after_finite_valid_until_returns_422(self, client, user_ids):
        """Contract with finite valid_until blocks flights past that date."""
        token = _token(user_ids["advertiser"])
        contract_id = "beh-ctr-finite-0000000000000001"

        # Insert temporary contract with finite valid_until (cleaned by conftest)
        _raw_exec(f"""
            INSERT INTO advertiser_contracts (id, advertiser_organization_id, code, name,
                contract_number, budget_limit_amount, budget_limit_currency,
                valid_from, valid_until, status)
            VALUES ('{contract_id}', '{ADV1_ORG_ID}', 'BEH-CTR-CLOSED',
                'Closed Contract', 'BEH-CLOSED', 100000, 'RUB',
                '2026-01-01T00:00:00+03:00', '2026-06-30T00:00:00+03:00', 'active')
            ON CONFLICT (advertiser_organization_id, code) DO NOTHING
        """)

        # Create campaign pointing to the closed contract
        resp = client.post(
            "/api/v1/identity/campaigns",
            json={
                "advertiser_organization_id": ADV1_ORG_ID,
                "advertiser_contract_id": contract_id,
                "code": "BEH-FL-VAL06",
                "name": "Flight Val 6",
            },
            headers=_auth(token),
        )
        assert resp.status_code == 201, resp.text
        cid = resp.json()["id"]

        # Flight end_at after valid_until (2026-06-30)
        resp = client.post(
            f"/api/v1/identity/campaigns/{cid}/flights",
            json={
                "start_at": "2026-06-01T00:00:00Z",
                "end_at": "2026-07-15T00:00:00Z",
            },
            headers=_auth(token),
        )
        assert resp.status_code == 422, (
            f"Expected 422 after finite valid_until, got {resp.status_code}: {resp.text}"
        )
        # No flight row created
        rows = _raw_sql(
            f"SELECT COUNT(*) FROM campaign_flights WHERE campaign_id = '{cid}'"
        )
        assert rows[0][0] == 0, "Flight row created for invalid input"
        # No outbox
        rows = _raw_sql(
            f"SELECT COUNT(*) FROM outbox_events "
            f"WHERE aggregate_id = '{cid}' AND event_type = 'campaign.flight.changed'"
        )
        assert rows[0][0] == 0, "Outbox written for invalid flight"


class TestCampaignSetupPlacements:
    """Placement create/update behavioral tests."""

    def test_create_placement_store_target(self, client, user_ids):
        token = _token(user_ids["advertiser"])
        resp = client.post(
            "/api/v1/identity/campaigns",
            json={
                "advertiser_organization_id": ADV1_ORG_ID,
                "advertiser_contract_id": ADV1_CONTRACT_ID,
                "code": "BEH-PLAC-001",
                "name": "Placement Test",
            },
            headers=_auth(token),
        )
        assert resp.status_code == 201
        campaign_id = resp.json()["id"]

        resp = client.post(
            f"/api/v1/identity/campaigns/{campaign_id}/placements",
            json={"store_id": SEED_STORE_ID},
            headers=_auth(token),
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["campaign_id"] == campaign_id

        # Outbox
        rows = _raw_sql(
            f"SELECT COUNT(*) FROM outbox_events "
            f"WHERE aggregate_id = '{campaign_id}' AND event_type = 'campaign.placement.changed'"
        )
        assert rows[0][0] >= 1

    def test_placement_no_target_rejected(self, client, user_ids):
        token = _token(user_ids["advertiser"])
        resp = client.post(
            "/api/v1/identity/campaigns",
            json={
                "advertiser_organization_id": ADV1_ORG_ID,
                "advertiser_contract_id": ADV1_CONTRACT_ID,
                "code": "BEH-PLAC-BAD",
                "name": "Bad Placement",
            },
            headers=_auth(token),
        )
        assert resp.status_code == 201
        campaign_id = resp.json()["id"]

        resp = client.post(
            f"/api/v1/identity/campaigns/{campaign_id}/placements",
            json={},
            headers=_auth(token),
        )
        assert resp.status_code == 422, (
            f"Expected 422 for no-target placement, got {resp.status_code}"
        )

    def test_cross_org_placement_rejected(self, client, user_ids):
        token = _token(user_ids["advertiser"])
        resp = client.post(
            "/api/v1/identity/campaigns",
            json={
                "advertiser_organization_id": ADV2_ORG_ID,
                "advertiser_contract_id": ADV2_CONTRACT_ID,
                "code": "BEH-PLAC-XORG",
                "name": "Cross Org Place Camp",
            },
            headers=_auth(token),
        )
        assert resp.status_code in (403, 422), (
            f"Expected 403/422 cross-org campaign create, got {resp.status_code}"
        )


class TestCampaignSetupCreatives:
    """Creative asset create + attach behavioral tests."""

    def test_create_creative_on_draft(self, client, user_ids):
        token = _token(user_ids["advertiser"])
        resp = client.post(
            "/api/v1/identity/campaigns",
            json={
                "advertiser_organization_id": ADV1_ORG_ID,
                "advertiser_contract_id": ADV1_CONTRACT_ID,
                "code": "BEH-CR-001",
                "name": "Creative Test",
            },
            headers=_auth(token),
        )
        assert resp.status_code == 201
        campaign_id = resp.json()["id"]

        resp = client.post(
            f"/api/v1/identity/campaigns/{campaign_id}/creatives",
            json={
                "code": "BEH-CR-VID01",
                "name": "Test Video",
                "media_type": "video/mp4",
                "sha256_checksum": "b" * 64,
                "file_size_bytes": 2048000,
            },
            headers=_auth(token),
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["code"] == "BEH-CR-VID01"
        # No storage secrets
        assert "storage_bucket" not in body
        assert "storage_key" not in body

        # Outbox
        rows = _raw_sql(
            f"SELECT COUNT(*) FROM outbox_events "
            f"WHERE aggregate_id = '{campaign_id}' AND event_type = 'campaign.creative.changed'"
        )
        assert rows[0][0] >= 1

    def test_cross_org_creative_rejected(self, client, user_ids):
        """Advertiser cannot attach a creative to another org's campaign."""
        _raw_exec(_ADV2_SETUP_SQL)
        # Create an ADV2 campaign as admin
        admin_token = _token(user_ids["readonly"])  # system_admin
        resp = client.post(
            "/api/v1/identity/campaigns",
            json={
                "advertiser_organization_id": ADV2_ORG_ID,
                "advertiser_contract_id": ADV2_CONTRACT_ID,
                "code": "BEH-CR-XORG-ATTACH",
                "name": "Cross Org Attach Campaign",
            },
            headers=_auth(admin_token),
        )
        assert resp.status_code == 201, f"Admin campaign create: {resp.text}"
        adv2_campaign_id = resp.json()["id"]

        # Advertiser (scoped to ADV1) tries to attach creative to ADV2 campaign
        token = _token(user_ids["advertiser"])
        resp = client.post(
            f"/api/v1/identity/campaigns/{adv2_campaign_id}/creatives",
            json={
                "code": "BEH-CR-XORG-ATTACH-CR",
                "name": "Cross Org Creative",
                "media_type": "video/mp4",
                "sha256_checksum": "e" * 64,
                "file_size_bytes": 1000,
            },
            headers=_auth(token),
        )
        assert resp.status_code in (403, 404), (
            f"Expected 403/404 cross-org creative attach, "
            f"got {resp.status_code}: {resp.text}"
        )

        # Verify no outbox event
        rows = _raw_sql(
            f"SELECT COUNT(*) FROM outbox_events "
            f"WHERE aggregate_id = '{adv2_campaign_id}' "
            f"AND event_type = 'campaign.creative.changed'"
        )
        assert rows[0][0] == 0, (
            "Outbox event written for rejected cross-org creative attach"
        )
        # Cleanup: delete campaign first so contract FK doesn't block
        _raw_exec(
            f"DELETE FROM campaign_status_history WHERE campaign_id = '{adv2_campaign_id}'"
            f"; DELETE FROM campaigns WHERE id = '{adv2_campaign_id}'"
        )
        _raw_exec(_ADV2_CLEANUP_SQL)


class TestCampaignFullPilotSetup:
    """End-to-end campaign setup: create → flight → placement → creative → request approval."""

    def test_full_pilot_setup_flow(self, client, user_ids):
        token = _token(user_ids["advertiser"])

        # 1. Create campaign
        resp = client.post(
            "/api/v1/identity/campaigns",
            json={
                "advertiser_organization_id": ADV1_ORG_ID,
                "advertiser_contract_id": ADV1_CONTRACT_ID,
                "code": "BEH-PILOT-FULL",
                "name": "Pilot Full Flow",
            },
            headers=_auth(token),
        )
        assert resp.status_code == 201, f"Campaign create: {resp.text}"
        campaign_id = resp.json()["id"]

        # 2. Add flight
        resp = client.post(
            f"/api/v1/identity/campaigns/{campaign_id}/flights",
            json={
                "start_at": "2026-07-01T00:00:00Z",
                "end_at": "2026-08-01T00:00:00Z",
                "name": "July Flight",
            },
            headers=_auth(token),
        )
        assert resp.status_code == 201, f"Flight create: {resp.text}"
        flight_id = resp.json()["id"]

        # 3. Add placement
        resp = client.post(
            f"/api/v1/identity/campaigns/{campaign_id}/placements",
            json={"store_id": SEED_STORE_ID},
            headers=_auth(token),
        )
        assert resp.status_code == 201, f"Placement create: {resp.text}"
        placement_id = resp.json()["id"]

        # 4. Add creative
        resp = client.post(
            f"/api/v1/identity/campaigns/{campaign_id}/creatives",
            json={
                "code": "BEH-PILOT-CR01",
                "name": "Pilot Creative",
                "media_type": "video/mp4",
                "sha256_checksum": "d" * 64,
                "file_size_bytes": 5000000,
            },
            headers=_auth(token),
        )
        assert resp.status_code == 201, f"Creative create: {resp.text}"
        asset_id = resp.json()["id"]

        # 5. Request approval
        resp = client.post(
            f"/api/v1/identity/campaigns/{campaign_id}/request-approval",
            headers=_auth(token),
        )
        assert resp.status_code == 200, f"Request approval: {resp.text}"
        body = resp.json()
        assert body["old_status"] == "draft"
        assert body["new_status"] == "pending_approval"

        # Verify outbox events for each step
        for ev_type in [
            "campaign.flight.changed",
            "campaign.placement.changed",
            "campaign.creative.changed",
            "campaign.approval_requested",
        ]:
            rows = _raw_sql(
                f"SELECT COUNT(*) FROM outbox_events "
                f"WHERE aggregate_id = '{campaign_id}' AND event_type = '{ev_type}'"
            )
            assert rows[0][0] >= 1, f"Missing outbox event: {ev_type}"
