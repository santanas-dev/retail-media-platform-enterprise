"""
Behavioral tests — AUTHZ-CROSS-PORTAL-001: advertiser isolation on
campaign-derived tables.

Migration 020 (ADR-018) moved every "derived" table (the campaign children
that carry no ``advertiser_organization_id`` of their own) onto a
retailer-only RLS policy.  That silently dropped the advertiser dimension:
two advertisers under the same retailer could read each other's flights,
placements, creatives, approvals and status history through the ordinary
list endpoints, even though ``campaigns`` itself stayed correctly scoped.

These tests pin the restored two-level rule for the five derived tables that
an advertiser can reach through the identity API:

  campaign_flights, campaign_placements, campaign_creatives,
  campaign_approvals, campaign_status_history

Both layers are proven:
  * API — a real ``advertiser`` role scoped to ORG_A must never see ORG_B rows.
  * DB  — the same statement under ``retail_media_app`` (NOBYPASSRLS).

Deliberately NOT covered here: delivery_* and pop_* stay retailer-only by
design — device-gateway authenticates a device and sets a retailer scope with
no advertiser scope at all (apps/device-gateway/main.py), so tightening those
tables would break manifest delivery and PoP ingestion.  Their advertiser
protection lives in the API layer (``_require_campaign_visible``).

Requires: RUN_BEHAVIORAL_TESTS=1, PostgreSQL, migrations.
"""

import asyncio
import os

import pytest
from fastapi.testclient import TestClient

from packages.security.config import reset_security_config
from packages.security.jwt import create_access_token
from tests.behavioral.conftest import _run_sql, USER_IDS

RET = "axp-ret-000000000000000001"
BRANCH = "axp-branch-0000000000000001"
ORG_A = "axp-org-a-00000000000001"
ORG_B = "axp-org-b-00000000000001"
CTR_A = "axp-ctr-a-00000000000001"
CTR_B = "axp-ctr-b-00000000000001"
CAMP_A = "axp-camp-a-0000000000001"
CAMP_B = "axp-camp-b-0000000000001"
FLIGHT_A = "axp-fl-a-000000000000001"
FLIGHT_B = "axp-fl-b-000000000000001"
PLACE_A = "axp-pl-a-000000000000001"
PLACE_B = "axp-pl-b-000000000000001"
ASSET_A = "axp-as-a-000000000000001"
ASSET_B = "axp-as-b-000000000000001"
CCREA_A = "axp-cc-a-000000000000001"
CCREA_B = "axp-cc-b-000000000000001"
HIST_A = "axp-hs-a-000000000000001"
HIST_B = "axp-hs-b-000000000000001"
APPR_A = "axp-ap-a-000000000000001"
APPR_B = "axp-ap-b-000000000000001"
USER_A = "axp-usr-a-00000000000001"
USER_B = "axp-usr-b-00000000000001"
AUTH_PROVIDER = "local_advertiser"

# (endpoint, id_of_org_a_row, id_of_org_b_row)
DERIVED_ENDPOINTS = [
    ("/api/v1/identity/campaign-flights", FLIGHT_A, FLIGHT_B),
    ("/api/v1/identity/campaign-placements", PLACE_A, PLACE_B),
    ("/api/v1/identity/campaign-creatives", CCREA_A, CCREA_B),
    ("/api/v1/identity/campaign-approvals", APPR_A, APPR_B),
    ("/api/v1/identity/campaign-status-history", HIST_A, HIST_B),
]

# (table, id_of_org_a_row, id_of_org_b_row)
DERIVED_TABLES = [
    ("campaign_flights", FLIGHT_A, FLIGHT_B),
    ("campaign_placements", PLACE_A, PLACE_B),
    ("campaign_creatives", CCREA_A, CCREA_B),
    ("campaign_approvals", APPR_A, APPR_B),
    ("campaign_status_history", HIST_A, HIST_B),
]


def _token(user_id: str) -> str:
    return create_access_token(user_id, AUTH_PROVIDER)


def _auth(token: str):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client(app, db_available, test_users):
    reset_security_config()
    return TestClient(app)


@pytest.fixture
def strict_client(app, db_available, test_users):
    """A client whose ``get_db`` does NOT pre-elevate the session to admin.

    ``tests/behavioral/conftest.py`` overrides ``get_db`` so every behavioral
    request starts with ``app.rmp_is_admin='true'``; endpoints that call
    ``set_rls_context`` overwrite it with the caller's real scope, but an
    endpoint that forgets to still sees every row.  That is precisely the
    defect these ``/auth/me`` tests pin, so this fixture restores the
    production dependency for their duration.
    """
    from packages.api.dependencies import get_db
    from packages.domain.database import get_global_engine, get_session

    reset_security_config()

    async def _strict_get_db():
        async with get_session(get_global_engine()) as session:
            async with session.begin():
                yield session

    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = _strict_get_db
    try:
        yield TestClient(app)
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous


def _org_fixture_sql(org, ctr, camp, flight, place, asset, ccrea, hist, appr, tag):
    """One advertiser org with a full campaign subtree, all under RET."""
    return [
        f"""INSERT INTO advertiser_organizations
              (id, code, legal_name, display_name, status, retailer_id)
            VALUES ('{org}', 'AXP-ORG-{tag}', 'Org {tag}', 'Org {tag}', 'active', '{RET}')
            ON CONFLICT (id) DO NOTHING""",
        f"""INSERT INTO advertiser_contracts
              (id, advertiser_organization_id, code, name, status, retailer_id)
            VALUES ('{ctr}', '{org}', 'AXP-CTR-{tag}', 'Contract {tag}', 'active', '{RET}')
            ON CONFLICT (id) DO NOTHING""",
        f"""INSERT INTO campaigns
              (id, advertiser_organization_id, advertiser_contract_id, code, name,
               status, retailer_id)
            VALUES ('{camp}', '{org}', '{ctr}', 'AXP-CAMP-{tag}', 'Campaign {tag}',
                    'draft', '{RET}')""",
        f"""INSERT INTO campaign_flights
              (id, campaign_id, start_at, end_at, retailer_id)
            VALUES ('{flight}', '{camp}', NOW(), NOW() + INTERVAL '7 days', '{RET}')""",
        f"""INSERT INTO campaign_placements
              (id, campaign_id, branch_id, retailer_id)
            VALUES ('{place}', '{camp}', '{BRANCH}', '{RET}')""",
        f"""INSERT INTO creative_assets
              (id, advertiser_organization_id, code, name, media_type, storage_bucket,
               storage_key, sha256_checksum, file_size_bytes, retailer_id)
            VALUES ('{asset}', '{org}', 'AXP-AS-{tag}', 'Asset {tag}', 'image/png',
                    'creatives', 'axp/{tag}.png', '{"0" * 64}', 1024, '{RET}')""",
        f"""INSERT INTO campaign_creatives
              (id, campaign_id, creative_asset_id, retailer_id)
            VALUES ('{ccrea}', '{camp}', '{asset}', '{RET}')""",
        f"""INSERT INTO campaign_status_history
              (id, campaign_id, new_status, changed_by, retailer_id)
            VALUES ('{hist}', '{camp}', 'draft', '{USER_IDS["advertiser"]}', '{RET}')""",
        f"""INSERT INTO campaign_approvals
              (id, campaign_id, requested_by, requested_at, retailer_id)
            VALUES ('{appr}', '{camp}', '{USER_IDS["advertiser"]}', NOW(), '{RET}')""",
    ]


def _scoped_user_sql(user_id, org, code, tag):
    return [
        f"""INSERT INTO users (id, code, username, email, display_name, auth_provider, status)
            VALUES ('{user_id}', '{code}', 'axp-{tag}', 'axp-{tag}@t.local',
                    'AXP {tag}', '{AUTH_PROVIDER}', 'active')""",
        f"""INSERT INTO local_credentials (id, user_id, credential_type, password_hash, status)
            VALUES ('lc-axp-{tag}', '{user_id}', '{AUTH_PROVIDER}',
                    '$2b$04${"a" * 53}', 'active')""",
        f"""INSERT INTO user_roles (id, user_id, role_id, scope_type, scope_id)
            SELECT 'ur-axp-{tag}', '{user_id}',
                   (SELECT id FROM roles WHERE code='advertiser'), 'advertiser', '{org}'""",
        f"""INSERT INTO advertiser_user_memberships
              (id, user_id, advertiser_organization_id, status)
            VALUES ('aum-axp-{tag}', '{user_id}', '{org}', 'active')""",
    ]


_CLEANUP = [
    "DELETE FROM campaign_approvals WHERE id LIKE 'axp-%'",
    "DELETE FROM campaign_status_history WHERE id LIKE 'axp-%'",
    "DELETE FROM campaign_creatives WHERE id LIKE 'axp-%'",
    "DELETE FROM creative_assets WHERE id LIKE 'axp-%'",
    "DELETE FROM campaign_placements WHERE id LIKE 'axp-%'",
    "DELETE FROM campaign_flights WHERE id LIKE 'axp-%'",
    "DELETE FROM outbox_events WHERE aggregate_id LIKE 'axp-%'",
    "DELETE FROM campaigns WHERE id LIKE 'axp-%'",
    "DELETE FROM advertiser_contracts WHERE id LIKE 'axp-%'",
    "DELETE FROM advertiser_user_memberships WHERE id LIKE 'aum-axp-%'",
    "DELETE FROM user_roles WHERE id LIKE 'ur-axp-%'",
    "DELETE FROM local_credentials WHERE id LIKE 'lc-axp-%'",
    "DELETE FROM refresh_sessions WHERE user_id LIKE 'axp-%'",
    "DELETE FROM users WHERE id LIKE 'axp-%'",
    "DELETE FROM advertiser_organizations WHERE id LIKE 'axp-%'",
    "DELETE FROM branches WHERE id LIKE 'axp-%'",
    "DELETE FROM retailers WHERE id LIKE 'axp-%'",
]


@pytest.fixture
def axp_setup(db_available, test_users):
    """Two advertiser orgs inside ONE retailer, each with a full campaign subtree."""
    for stmt in _CLEANUP:
        asyncio.run(_run_sql(stmt))
    asyncio.run(_run_sql(f"""
    INSERT INTO retailers (id, code, legal_name, display_name, status)
    VALUES ('{RET}', 'AXP-RETAILER', 'AXP Retailer', 'AXP', 'active')
    ON CONFLICT (id) DO NOTHING"""))
    asyncio.run(_run_sql(f"""
    INSERT INTO branches (id, code, name, retailer_id)
    VALUES ('{BRANCH}', 'AXP-BRANCH', 'AXP Branch', '{RET}')
    ON CONFLICT (id) DO NOTHING"""))
    for stmt in _org_fixture_sql(ORG_A, CTR_A, CAMP_A, FLIGHT_A, PLACE_A,
                                ASSET_A, CCREA_A, HIST_A, APPR_A, "A"):
        asyncio.run(_run_sql(stmt))
    for stmt in _org_fixture_sql(ORG_B, CTR_B, CAMP_B, FLIGHT_B, PLACE_B,
                                ASSET_B, CCREA_B, HIST_B, APPR_B, "B"):
        asyncio.run(_run_sql(stmt))
    for stmt in _scoped_user_sql(USER_A, ORG_A, 'BEH-AXP-A', 'a'):
        asyncio.run(_run_sql(stmt))
    for stmt in _scoped_user_sql(USER_B, ORG_B, 'BEH-AXP-B', 'b'):
        asyncio.run(_run_sql(stmt))
    yield {"ret": RET, "org_a": ORG_A, "org_b": ORG_B}
    for stmt in _CLEANUP:
        asyncio.run(_run_sql(stmt))


@pytest.mark.usefixtures("axp_setup")
class TestAuthzCrossPortalDerivedRLS:

    @pytest.fixture(autouse=True)
    def setup(self, client, strict_client, db_available, axp_setup):
        self.client = client
        self.strict_client = strict_client
        self.token_a = _token(USER_A)
        self.token_b = _token(USER_B)
        self.token_admin = _token(USER_IDS["readonly"])

    # -- API layer, real advertiser role -----------------------------------

    @pytest.mark.parametrize("endpoint,id_a,id_b", DERIVED_ENDPOINTS)
    def test_advertiser_a_does_not_see_org_b_rows(self, endpoint, id_a, id_b):
        resp = self.client.get(endpoint, headers=_auth(self.token_a))
        assert resp.status_code == 200, f"{endpoint}: {resp.status_code} {resp.text[:200]}"
        ids = {row["id"] for row in resp.json()}
        assert id_a in ids, f"{endpoint}: own row {id_a} missing from {sorted(ids)}"
        assert id_b not in ids, f"{endpoint}: ORG_B row {id_b} leaked to ORG_A"

    @pytest.mark.parametrize("endpoint,id_a,id_b", DERIVED_ENDPOINTS)
    def test_advertiser_b_does_not_see_org_a_rows(self, endpoint, id_a, id_b):
        resp = self.client.get(endpoint, headers=_auth(self.token_b))
        assert resp.status_code == 200, f"{endpoint}: {resp.status_code} {resp.text[:200]}"
        ids = {row["id"] for row in resp.json()}
        assert id_b in ids, f"{endpoint}: own row {id_b} missing from {sorted(ids)}"
        assert id_a not in ids, f"{endpoint}: ORG_A row {id_a} leaked to ORG_B"

    def test_campaigns_list_still_scoped(self):
        """Control: the parent table was never broken and must stay correct."""
        resp = self.client.get("/api/v1/identity/campaigns?limit=500",
                               headers=_auth(self.token_a))
        assert resp.status_code == 200, resp.text[:200]
        items = resp.json()["items"]
        ids = {c["id"] for c in items}
        assert CAMP_A in ids, f"own campaign missing: {sorted(ids)}"
        assert CAMP_B not in ids, "ORG_B campaign leaked"
        assert {c["advertiser_organization_id"] for c in items} == {ORG_A}, \
            "campaign list contains a foreign advertiser_organization_id"

    @pytest.mark.parametrize("endpoint,id_a,id_b", DERIVED_ENDPOINTS)
    def test_admin_still_sees_both(self, endpoint, id_a, id_b):
        """No regression for admin: is_admin bypass keeps full visibility."""
        resp = self.client.get(endpoint, headers=_auth(self.token_admin))
        assert resp.status_code == 200, f"{endpoint}: {resp.status_code} {resp.text[:200]}"
        ids = {row["id"] for row in resp.json()}
        assert id_a in ids, f"{endpoint}: admin missing {id_a}"
        assert id_b in ids, f"{endpoint}: admin missing {id_b}"

    # -- /auth/me must identify the advertiser cabinet session --------------

    def test_me_resolves_own_advertiser_organization(self):
        """AUTHZ-CROSS-PORTAL-001: advertiser_organizations is RLS-protected
        since migration 020, so /auth/me must run with the caller's RLS
        context — otherwise the field silently resolves to null and no client
        can tell an advertiser session from an operator one."""
        resp = self.strict_client.get("/api/v1/auth/me", headers=_auth(self.token_a))
        assert resp.status_code == 200, resp.text[:200]
        me = resp.json()
        assert me["advertiser_organization_id"] == ORG_A, \
            f"expected {ORG_A}, got {me['advertiser_organization_id']}"
        assert me["advertiser_organization"] is not None, \
            "advertiser_organization payload missing"
        assert me["advertiser_organization"]["id"] == ORG_A

    def test_me_for_operator_has_no_advertiser_organization(self):
        """The same field stays null for an internal (non-cabinet) user."""
        resp = self.strict_client.get("/api/v1/auth/me", headers=_auth(self.token_admin))
        assert resp.status_code == 200, resp.text[:200]
        me = resp.json()
        assert me["advertiser_organization_id"] is None, \
            f"operator leaked an advertiser org: {me['advertiser_organization_id']}"

    # -- DB layer, retail_media_app / NOBYPASSRLS ---------------------------

    def test_direct_db_rls_proof_derived_tables(self):
        """Same statements under retail_media_app (NOBYPASSRLS).

        Both orgs share ONE retailer, so retailer scope cannot be the
        discriminator here — only the advertiser dimension can.
        """
        import asyncpg

        app_db_url = os.environ.get(
            "BEHAVIORAL_APP_DB_URL",
            "postgresql://retail_media_app:***@localhost:5432/retail_media_platform",
        ).replace("***", "retail_media_app")

        async def _prove():
            conn = await asyncpg.connect(app_db_url)
            try:
                role = await conn.fetchrow(
                    "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user")
                assert role is not None, "current_user not found in pg_roles"
                assert not role["rolsuper"], "RLS proof requires a non-superuser role"
                assert not role["rolbypassrls"], "RLS proof requires NOBYPASSRLS"

                async def scope(is_admin, retailers, advertisers):
                    await conn.execute(
                        "SELECT set_config('app.rmp_is_admin', $1, false)", is_admin)
                    await conn.execute(
                        "SELECT set_config('app.rmp_scope_retailer_ids', $1, false)", retailers)
                    await conn.execute(
                        "SELECT set_config('app.rmp_scope_advertiser_ids', $1, false)", advertisers)

                for table, id_a, id_b in DERIVED_TABLES:
                    await scope("false", RET, ORG_A)
                    ids = {r["id"] for r in await conn.fetch(f"SELECT id FROM {table}")}
                    assert id_a in ids, f"{table}: ORG_A scope lost its own row {id_a}"
                    assert id_b not in ids, f"{table}: ORG_A scope leaked ORG_B row {id_b}"

                    await scope("false", RET, ORG_B)
                    ids = {r["id"] for r in await conn.fetch(f"SELECT id FROM {table}")}
                    assert id_b in ids, f"{table}: ORG_B scope lost its own row {id_b}"
                    assert id_a not in ids, f"{table}: ORG_B scope leaked ORG_A row {id_a}"

                    await scope("false", RET, "")
                    ids = {r["id"] for r in await conn.fetch(f"SELECT id FROM {table}")}
                    assert id_a not in ids and id_b not in ids, \
                        f"{table}: empty advertiser scope is not fail-closed"

                    await scope("false", "", ORG_A)
                    ids = {r["id"] for r in await conn.fetch(f"SELECT id FROM {table}")}
                    assert id_a not in ids, \
                        f"{table}: empty retailer scope is not fail-closed"

                    await scope("true", "", "")
                    ids = {r["id"] for r in await conn.fetch(f"SELECT id FROM {table}")}
                    assert id_a in ids and id_b in ids, \
                        f"{table}: admin bypass regressed"
            finally:
                await conn.close()

        asyncio.run(_prove())
