"""
Behavioral tests — CAMPAIGN-PERMISSION-SPLIT-001.

An advertiser may submit its own brief and read its own campaigns; it must not
reach operator campaign management. Before the split both surfaces sat behind
``campaigns.manage``, so the advertiser role passed the permission gate on
campaign create, edit and the whole lifecycle — a valid payload would have been
accepted.

Every claim here is a real request against a real PostgreSQL, with the app
connected as ``retail_media_app`` (NOBYPASSRLS). In particular the operator
create is proven with a **valid** payload, not just a malformed one: a 422 on
garbage would only show that validation ran, not that authorisation refused.

Requires: RUN_BEHAVIORAL_TESTS=1, PostgreSQL, migrations through 036.
"""

import asyncio
import os
import uuid

import pytest
from fastapi.testclient import TestClient

from packages.security.config import reset_security_config
from packages.security.jwt import create_access_token
from tests.behavioral.conftest import _run_sql, USER_IDS

# RM-STAB-001: единый контракт BEHAVIORAL_APP_DB_URL
from tests.behavioral.dsn import raw_dsn

# The default retailer: briefs are written with the column default
# retailer_id, so both orgs must live under it for the brief RLS
# WITH CHECK to pass. Both orgs share it, which is what makes the
# advertiser dimension the only discriminator in the isolation cases.
RET = "00000000-0000-4000-a000-000000000001"
ORG_A = "cps-org-a-00000000000001"
ORG_B = "cps-org-b-00000000000001"
CTR_A = "cps-ctr-a-00000000000001"
CTR_B = "cps-ctr-b-00000000000001"
CAMP_A = "cps-camp-a-0000000000001"
CAMP_B = "cps-camp-b-0000000000001"
FLIGHT_B = "cps-fl-b-000000000000001"
USER_A = "cps-usr-a-00000000000001"
AUTH_PROVIDER = "local_advertiser"

OPERATOR_PERM = "campaigns.manage"
BRIEF_PERM = "campaign_briefs.manage"

IDENT = "/api/v1/identity"


def _token(user_id: str) -> str:
    return create_access_token(user_id, AUTH_PROVIDER)


def _auth(token: str):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client(app, db_available, test_users):
    reset_security_config()
    return TestClient(app)


_CLEANUP = [
    # Rows the tests create carry generated ids, so clean by ownership too:
    # a brief made through the API is keyed by created_by, and a campaign made
    # by the operator case by its CPS- code.
    "DELETE FROM campaign_briefs WHERE id LIKE 'cps-%' OR created_by LIKE 'cps-%'",
    "DELETE FROM campaign_status_history WHERE campaign_id IN "
    "(SELECT id FROM campaigns WHERE id LIKE 'cps-%' OR code LIKE 'CPS-%')",
    "DELETE FROM campaign_approvals WHERE campaign_id IN "
    "(SELECT id FROM campaigns WHERE id LIKE 'cps-%' OR code LIKE 'CPS-%')",
    "DELETE FROM campaign_creatives WHERE campaign_id IN "
    "(SELECT id FROM campaigns WHERE id LIKE 'cps-%' OR code LIKE 'CPS-%')",
    "DELETE FROM campaign_placements WHERE campaign_id IN "
    "(SELECT id FROM campaigns WHERE id LIKE 'cps-%' OR code LIKE 'CPS-%')",
    "DELETE FROM campaign_flights WHERE campaign_id IN "
    "(SELECT id FROM campaigns WHERE id LIKE 'cps-%' OR code LIKE 'CPS-%')",
    "DELETE FROM outbox_events WHERE aggregate_id IN "
    "(SELECT id FROM campaigns WHERE id LIKE 'cps-%' OR code LIKE 'CPS-%')",
    "DELETE FROM campaigns WHERE id LIKE 'cps-%' OR code LIKE 'CPS-%'",
    "DELETE FROM advertiser_contracts WHERE id LIKE 'cps-%'",
    "DELETE FROM advertiser_user_memberships WHERE id LIKE 'aum-cps-%'",
    "DELETE FROM user_roles WHERE id LIKE 'ur-cps-%'",
    "DELETE FROM role_permissions WHERE id LIKE 'rp-cps-%'",
    "DELETE FROM local_credentials WHERE id LIKE 'lc-cps-%'",
    "DELETE FROM refresh_sessions WHERE user_id LIKE 'cps-%'",
    "DELETE FROM users WHERE id LIKE 'cps-%'",
    "DELETE FROM advertiser_organizations WHERE id LIKE 'cps-%'",
]


@pytest.fixture
def cps_setup(db_available, test_users):
    """Two advertiser orgs in one retailer; a scoped advertiser user on ORG_A."""
    for stmt in _CLEANUP:
        asyncio.run(_run_sql(stmt))

    for org, ctr, camp, tag in ((ORG_A, CTR_A, CAMP_A, "A"), (ORG_B, CTR_B, CAMP_B, "B")):
        asyncio.run(_run_sql(f"""
        INSERT INTO advertiser_organizations (id, code, legal_name, display_name, status, retailer_id)
        VALUES ('{org}', 'CPS-ORG-{tag}', 'Org {tag}', 'Org {tag}', 'active', '{RET}')
        ON CONFLICT (id) DO NOTHING"""))
        asyncio.run(_run_sql(f"""
        INSERT INTO advertiser_contracts (id, advertiser_organization_id, code, name, status, retailer_id)
        VALUES ('{ctr}', '{org}', 'CPS-CTR-{tag}', 'Contract {tag}', 'active', '{RET}')
        ON CONFLICT (id) DO NOTHING"""))
        asyncio.run(_run_sql(f"""
        INSERT INTO campaigns (id, advertiser_organization_id, advertiser_contract_id,
                               code, name, status, retailer_id)
        VALUES ('{camp}', '{org}', '{ctr}', 'CPS-CAMP-{tag}', 'Campaign {tag}', 'draft', '{RET}')"""))
    asyncio.run(_run_sql(f"""
    INSERT INTO campaign_flights (id, campaign_id, start_at, end_at, retailer_id)
    VALUES ('{FLIGHT_B}', '{CAMP_B}', NOW(), NOW() + INTERVAL '7 days', '{RET}')"""))

    asyncio.run(_run_sql(f"""
    INSERT INTO users (id, code, username, email, display_name, auth_provider, status)
    VALUES ('{USER_A}', 'CPS-A', 'cps-advertiser', 'cps-a@t.local', 'CPS A',
            '{AUTH_PROVIDER}', 'active')"""))
    asyncio.run(_run_sql(f"""
    INSERT INTO local_credentials (id, user_id, credential_type, password_hash, status)
    VALUES ('lc-cps-a', '{USER_A}', '{AUTH_PROVIDER}', '$2b$04${"a" * 53}', 'active')"""))
    asyncio.run(_run_sql(f"""
    INSERT INTO user_roles (id, user_id, role_id, scope_type, scope_id)
    SELECT 'ur-cps-a', '{USER_A}', (SELECT id FROM roles WHERE code='advertiser'),
           'advertiser', '{ORG_A}'"""))
    asyncio.run(_run_sql(f"""
    INSERT INTO advertiser_user_memberships (id, user_id, advertiser_organization_id, status)
    VALUES ('aum-cps-a', '{USER_A}', '{ORG_A}', 'active')"""))

    yield {"org_a": ORG_A, "org_b": ORG_B}

    for stmt in _CLEANUP:
        asyncio.run(_run_sql(stmt))


async def _campaign_count() -> int:
    """Row count read with the fixture (admin) connection, so RLS cannot hide
    a row that a leak actually created."""
    from sqlalchemy import text
    from tests.behavioral.conftest import _get_setup_engine
    engine = _get_setup_engine()
    async with engine.begin() as conn:
        await conn.execute(text("SELECT set_config('app.rmp_is_admin', 'true', true)"))
        res = await conn.execute(text("SELECT count(*) FROM campaigns"))
        return res.scalar_one()


def _valid_campaign_payload(org: str, contract: str) -> dict:
    return {
        "advertiser_organization_id": org,
        "advertiser_contract_id": contract,
        "code": f"CPS-NEW-{uuid.uuid4().hex[:8]}",
        "name": "Кампания, которую рекламодателю нельзя создавать",
        "placement_basis": "commercial",
    }


@pytest.mark.usefixtures("cps_setup")
class TestCampaignPermissionSplit:

    @pytest.fixture(autouse=True)
    def setup(self, client, db_available, cps_setup):
        self.client = client
        self.token_adv = _token(USER_A)
        self.token_admin = _token(USER_IDS["readonly"])

    # -- the permission the advertiser actually holds -----------------------

    def test_advertiser_holds_brief_permission_and_not_operator(self):
        resp = self.client.get("/api/v1/auth/me", headers=_auth(self.token_adv))
        assert resp.status_code == 200, resp.text[:200]
        perms = set(resp.json()["permissions"])
        assert BRIEF_PERM in perms, f"brief permission missing: {sorted(perms)}"
        assert OPERATOR_PERM not in perms, (
            f"advertiser still carries {OPERATOR_PERM}: {sorted(perms)}"
        )

    # -- operator campaign management is refused ----------------------------

    def test_operator_create_with_valid_payload_is_403_and_creates_nothing(self):
        before = asyncio.run(_campaign_count())
        resp = self.client.post(
            f"{IDENT}/campaigns",
            headers=_auth(self.token_adv),
            json=_valid_campaign_payload(ORG_A, CTR_A),
        )
        assert resp.status_code == 403, (
            f"a valid operator payload must be refused by the permission gate, "
            f"got {resp.status_code}: {resp.text[:200]}"
        )
        after = asyncio.run(_campaign_count())
        assert after == before, f"campaign rows changed: {before} -> {after}"

    def test_operator_create_with_malformed_payload_is_403_not_422(self):
        """The gate must run before body validation — otherwise a 422 would be
        the only thing standing between the caller and a created row."""
        before = asyncio.run(_campaign_count())
        resp = self.client.post(
            f"{IDENT}/campaigns", headers=_auth(self.token_adv), json={},
        )
        assert resp.status_code == 403, (
            f"expected 403 before validation, got {resp.status_code}: {resp.text[:200]}"
        )
        assert asyncio.run(_campaign_count()) == before

    @pytest.mark.parametrize("method,path,body", [
        ("PATCH", f"{IDENT}/campaigns/{CAMP_A}", {"name": "переименовано"}),
        ("POST", f"{IDENT}/campaigns/{CAMP_A}/activate", None),
        ("POST", f"{IDENT}/campaigns/{CAMP_A}/pause", None),
        ("POST", f"{IDENT}/campaigns/{CAMP_A}/complete", None),
        ("POST", f"{IDENT}/campaigns/{CAMP_A}/archive", None),
        ("POST", f"{IDENT}/campaigns/{CAMP_A}/request-approval", None),
        ("POST", f"{IDENT}/campaigns/{CAMP_A}/flights",
         {"start_at": "2026-09-01T00:00:00Z", "end_at": "2026-09-30T00:00:00Z"}),
        ("POST", f"{IDENT}/campaigns/{CAMP_A}/placements", {"branch_id": None}),
        ("POST", f"{IDENT}/campaigns/{CAMP_A}/creatives/attach", {"creative_asset_id": "x"}),
        ("POST", f"{IDENT}/creative-assets", {"code": "X", "name": "X"}),
    ])
    def test_operator_lifecycle_and_composition_refused(self, method, path, body):
        resp = self.client.request(
            method, path, headers=_auth(self.token_adv), json=body or {},
        )
        assert resp.status_code == 403, (
            f"{method} {path} must be 403 for an advertiser, "
            f"got {resp.status_code}: {resp.text[:160]}"
        )

    # -- the brief journey still works --------------------------------------

    def test_brief_journey_create_update_submit(self):
        created = self.client.post(
            f"{IDENT}/campaign-briefs",
            headers=_auth(self.token_adv),
            json={"title": "Заявка на размещение", "objective": "Охват"},
        )
        assert created.status_code == 201, f"brief create: {created.status_code} {created.text[:200]}"
        brief_id = created.json()["id"]

        updated = self.client.patch(
            f"{IDENT}/campaign-briefs/{brief_id}",
            headers=_auth(self.token_adv),
            json={"comment": "уточнение"},
        )
        assert updated.status_code == 200, f"brief update: {updated.status_code} {updated.text[:200]}"

        submitted = self.client.post(
            f"{IDENT}/campaign-briefs/{brief_id}/submit", headers=_auth(self.token_adv),
        )
        assert submitted.status_code == 200, f"brief submit: {submitted.status_code} {submitted.text[:200]}"
        assert submitted.json()["status"] == "submitted"

    # -- reads: own yes, foreign no -----------------------------------------

    def test_advertiser_reads_own_campaigns_only(self):
        resp = self.client.get(f"{IDENT}/campaigns?limit=500", headers=_auth(self.token_adv))
        assert resp.status_code == 200, resp.text[:200]
        items = resp.json()["items"]
        ids = {c["id"] for c in items}
        assert CAMP_A in ids, f"own campaign missing: {sorted(ids)}"
        assert CAMP_B not in ids, "foreign campaign leaked"
        assert {c["advertiser_organization_id"] for c in items} == {ORG_A}

    def test_advertiser_does_not_see_foreign_child_rows(self):
        resp = self.client.get(f"{IDENT}/campaign-flights", headers=_auth(self.token_adv))
        assert resp.status_code == 200, resp.text[:200]
        assert FLIGHT_B not in {row["id"] for row in resp.json()}, "ORG_B flight leaked"

    # -- operator flows did not regress -------------------------------------

    def test_admin_can_still_create_and_manage_campaigns(self):
        before = asyncio.run(_campaign_count())
        created = self.client.post(
            f"{IDENT}/campaigns",
            headers=_auth(self.token_admin),
            json=_valid_campaign_payload(ORG_A, CTR_A),
        )
        assert created.status_code == 201, (
            f"operator campaign create regressed: {created.status_code} {created.text[:200]}"
        )
        assert asyncio.run(_campaign_count()) == before + 1
        campaign_id = created.json()["id"]

        patched = self.client.patch(
            f"{IDENT}/campaigns/{campaign_id}",
            headers=_auth(self.token_admin),
            json={"name": "переименовано оператором"},
        )
        assert patched.status_code == 200, (
            f"operator campaign edit regressed: {patched.status_code} {patched.text[:200]}"
        )

    def test_admin_can_read_the_brief_surface(self):
        resp = self.client.get(f"{IDENT}/campaign-briefs", headers=_auth(self.token_admin))
        assert resp.status_code == 200, resp.text[:200]

    # -- DB layer, retail_media_app / NOBYPASSRLS ---------------------------

    def test_direct_db_role_grants_under_nobypassrls(self):
        """The grant table itself, read by the unprivileged app role."""
        import asyncpg

        app_db_url = raw_dsn()

        async def _prove():
            conn = await asyncpg.connect(app_db_url)
            try:
                role = await conn.fetchrow(
                    "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user")
                assert role is not None and not role["rolsuper"] and not role["rolbypassrls"], \
                    "this proof requires a non-superuser NOBYPASSRLS role"

                rows = await conn.fetch("""
                    SELECT r.code AS role_code, p.code AS perm_code
                    FROM role_permissions rp
                    JOIN roles r ON r.id = rp.role_id
                    JOIN permissions p ON p.id = rp.permission_id
                    WHERE p.code = ANY($1::text[])
                """, [OPERATOR_PERM, BRIEF_PERM])
                grants = {(r["role_code"], r["perm_code"]) for r in rows}

                assert ("advertiser", OPERATOR_PERM) not in grants, \
                    "the advertiser role still holds campaigns.manage in the database"
                assert ("advertiser", BRIEF_PERM) in grants, \
                    "the advertiser role lost the brief permission"
                assert ("system_admin", OPERATOR_PERM) in grants
                assert ("security_admin", OPERATOR_PERM) in grants
            finally:
                await conn.close()

        asyncio.run(_prove())

    # -- tamper: the security test must be load-bearing ---------------------

    def test_tamper_regranting_operator_permission_opens_the_gate(self):
        """Put ``campaigns.manage`` back on the advertiser role and the refusal
        turns into acceptance — which is exactly what the tests above would
        catch. The grant is removed again in the finally block."""
        before = asyncio.run(_campaign_count())
        try:
            asyncio.run(_run_sql("""
                INSERT INTO role_permissions (id, role_id, permission_id)
                SELECT 'rp-cps-tamper', r.id, p.id FROM roles r, permissions p
                WHERE r.code = 'advertiser' AND p.code = 'campaigns.manage'
                ON CONFLICT (role_id, permission_id) DO NOTHING
            """))
            resp = self.client.post(
                f"{IDENT}/campaigns", headers=_auth(self.token_adv), json={},
            )
            assert resp.status_code == 422, (
                "with campaigns.manage restored the advertiser must pass the "
                f"permission gate and fail on validation instead; got {resp.status_code}"
            )
        finally:
            asyncio.run(_run_sql("""
                DELETE FROM role_permissions rp USING roles r, permissions p
                WHERE rp.role_id = r.id AND rp.permission_id = p.id
                  AND r.code = 'advertiser' AND p.code = 'campaigns.manage'
            """))

        restored = self.client.post(
            f"{IDENT}/campaigns", headers=_auth(self.token_adv), json={},
        )
        assert restored.status_code == 403, "the tamper was not undone"
        assert asyncio.run(_campaign_count()) == before, "the tamper created a row"
