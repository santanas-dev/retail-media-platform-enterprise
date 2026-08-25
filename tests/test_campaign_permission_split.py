"""
CAMPAIGN-PERMISSION-SPLIT-001 — the permission split is pinned by inventory,
not by memory.

``campaigns.manage`` used to guard both the advertiser's brief writes and the
operator campaign surface, so granting it to the advertiser role let an
advertiser through the permission gate on 17 operator endpoints. These tests
keep the two apart:

* only the three brief writes may carry ``campaign_briefs.manage``;
* no brief route may go back to ``campaigns.manage``;
* the seed must not hand ``campaigns.manage`` to the advertiser role again
  (seeding is additive and runs on every db-migrate, so a stale grant there
  would silently undo migration 036);
* migration 036 must stay a linear revision on top of 035 and must be
  reversible.

Behavioural proof against PostgreSQL lives in
``tests/behavioral/test_campaign_permission_split_001.py`` — these are the
static guards, not a substitute for it.
"""

import ast
import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
API_DIR = REPO / "packages" / "api"
SEED = REPO / "apps" / "control-api" / "seed.py"
MIGRATION = REPO / "apps" / "control-api" / "alembic" / "versions" / "036_campaign_permission_split.py"

OPERATOR_PERM = "campaigns.manage"
BRIEF_PERM = "campaign_briefs.manage"

BRIEF_WRITE_ROUTES = {
    ("POST", "/campaign-briefs"),
    ("PATCH", "/campaign-briefs/{brief_id}"),
    ("POST", "/campaign-briefs/{brief_id}/submit"),
}


def _route_permissions():
    """(permission, method, path, file) for every router endpoint."""
    rows = []
    for path in sorted(API_DIR.rglob("*.py")):
        tree = ast.parse(path.read_text())
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            routes = []
            for dec in fn.decorator_list:
                if (
                    isinstance(dec, ast.Call)
                    and isinstance(dec.func, ast.Attribute)
                    and isinstance(dec.func.value, ast.Name)
                    and dec.func.value.id == "router"
                    and dec.args
                    and isinstance(dec.args[0], ast.Constant)
                ):
                    routes.append((dec.func.attr.upper(), dec.args[0].value))
            if not routes:
                continue
            perms = []
            for default in list(fn.args.defaults) + list(fn.args.kw_defaults):
                if default is None:
                    continue
                for node in ast.walk(default):
                    if (
                        isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Name)
                        and node.func.id in ("require_permission", "require_scoped_permission")
                        and node.args
                        and isinstance(node.args[0], ast.Constant)
                    ):
                        perms.append(node.args[0].value)
            for perm in perms:
                for method, route in routes:
                    rows.append((perm, method, route, path.name))
    return rows


ROUTE_PERMISSIONS = _route_permissions()


def _seed_role_grants():
    """role code -> set of permission codes, parsed out of seed.py."""
    text = SEED.read_text()
    pattern = re.compile(
        r"VALUES \('\{_rp\(\d+\)\}', '\{SEED_ROLE_IDS\[\"([a-z_]+)\"\]\}', "
        r"'\{SEED_PERM_IDS\[\"([a-z_.]+)\"\]\}'\)"
    )
    grants = {}
    for role, perm in pattern.findall(text):
        grants.setdefault(role, set()).add(perm)
    return grants


SEED_GRANTS = _seed_role_grants()


class TestPermissionInventory:
    """The route inventory is computed from the source, never hand-tallied."""

    def test_brief_writes_use_the_brief_permission(self):
        guarded = {
            (method, route)
            for perm, method, route, _ in ROUTE_PERMISSIONS
            if perm == BRIEF_PERM
        }
        assert guarded == BRIEF_WRITE_ROUTES, (
            f"campaign_briefs.manage must guard exactly the three brief writes; "
            f"got {sorted(guarded)}"
        )

    def test_no_brief_route_falls_back_to_operator_permission(self):
        offenders = [
            (method, route, file)
            for perm, method, route, file in ROUTE_PERMISSIONS
            if perm == OPERATOR_PERM and route.startswith("/campaign-briefs")
        ]
        assert offenders == [], f"brief routes back on campaigns.manage: {offenders}"

    def test_operator_permission_still_guards_the_campaign_surface(self):
        guarded = {
            route
            for perm, _, route, _ in ROUTE_PERMISSIONS
            if perm == OPERATOR_PERM
        }
        # A representative, non-exhaustive set: create, edit, lifecycle,
        # composition and creative upload must all still require it.
        for route in (
            "/campaigns",
            "/campaigns/{campaign_id}",
            "/campaigns/{campaign_id}/activate",
            "/campaigns/{campaign_id}/pause",
            "/campaigns/{campaign_id}/complete",
            "/campaigns/{campaign_id}/archive",
            "/campaigns/{campaign_id}/request-approval",
            "/campaigns/{campaign_id}/flights",
            "/campaigns/{campaign_id}/placements",
            "/campaigns/{campaign_id}/creatives/attach",
            "/creative-assets",
        ):
            assert route in guarded, f"{route} no longer requires {OPERATOR_PERM}"

    def test_the_two_permissions_never_guard_the_same_route(self):
        operator_routes = {
            (m, r) for p, m, r, _ in ROUTE_PERMISSIONS if p == OPERATOR_PERM
        }
        brief_routes = {
            (m, r) for p, m, r, _ in ROUTE_PERMISSIONS if p == BRIEF_PERM
        }
        assert operator_routes & brief_routes == set(), (
            "a route guarded by both permissions would make the split meaningless: "
            f"{sorted(operator_routes & brief_routes)}"
        )

    def test_brief_reads_stay_on_campaigns_read(self):
        reads = {
            (method, route)
            for perm, method, route, _ in ROUTE_PERMISSIONS
            if perm == "campaigns.read" and route.startswith("/campaign-briefs")
        }
        assert ("GET", "/campaign-briefs") in reads
        assert ("GET", "/campaign-briefs/{brief_id}") in reads


class TestSeedReconciliation:
    """Seeding is additive and runs on every db-migrate."""

    def test_advertiser_role_does_not_get_operator_permission(self):
        assert OPERATOR_PERM not in SEED_GRANTS["advertiser"], (
            "seed would hand campaigns.manage back to the advertiser role on the "
            "next db-migrate, silently undoing migration 036"
        )

    def test_advertiser_role_gets_the_brief_permission(self):
        assert BRIEF_PERM in SEED_GRANTS["advertiser"]

    def test_internal_roles_keep_operator_permission(self):
        for role in ("system_admin", "security_admin"):
            assert OPERATOR_PERM in SEED_GRANTS[role], f"{role} lost {OPERATOR_PERM}"

    def test_operator_and_analyst_roles_get_neither_write_permission(self):
        for role in ("operator", "analyst"):
            assert OPERATOR_PERM not in SEED_GRANTS[role]
            assert BRIEF_PERM not in SEED_GRANTS[role]

    def test_permission_row_is_seeded(self):
        text = SEED.read_text()
        assert f"'{BRIEF_PERM}'" in text, "permissions row for the brief permission is missing"


class TestMigration036:
    def test_is_a_linear_revision_on_top_of_035(self):
        text = MIGRATION.read_text()
        assert 'revision: str = "036"' in text
        assert 'down_revision: Union[str, None] = "035"' in text

    def test_upgrade_revokes_the_advertiser_grant(self):
        text = MIGRATION.read_text()
        tree = ast.parse(text)
        upgrade = next(
            n for n in tree.body
            if isinstance(n, ast.FunctionDef) and n.name == "upgrade"
        )
        calls = [
            (n.func.id, [a.id if isinstance(a, ast.Name) else getattr(a, "value", None) for a in n.args])
            for n in ast.walk(upgrade)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
        ]
        assert any(name == "_revoke" for name, _ in calls), "upgrade never revokes anything"
        assert any(name == "_grant" for name, _ in calls), "upgrade never grants anything"

    def test_downgrade_exists_and_is_documented_as_widening(self):
        text = MIGRATION.read_text()
        assert "def downgrade()" in text
        assert "WIDEN" in text.upper(), (
            "a downgrade that re-grants operator rights must say so in the file"
        )

    def test_migration_is_idempotent_by_construction(self):
        text = MIGRATION.read_text()
        assert "ON CONFLICT" in text, "grants must be ON CONFLICT DO NOTHING"
