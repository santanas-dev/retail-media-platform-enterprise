"""
Retail Media Platform — Phase 3.5c Scoped Permission Tests.

Tests the ``require_scoped_permission`` FastAPI dependency directly through
a minimal test app with dependency overrides.  No real DB needed — ScopeContext
is injected via ``app.dependency_overrides``.

Coverage:
  1. Global permission passes regardless of scope_type
  2. Advertiser-scoped permission passes for advertiser scope (with perm + scope_ids)
  3. Advertiser_without_scope_ids → SCOPE_RESTRICTED
  4. Cross-scope: advertiser scope does NOT pass branch endpoint
  5. No permission → 403 PERMISSION_DENIED
  6. Empty scope → 403 (SCOPE_RESTRICTED for scoped, PERMISSION_DENIED for unscoped)
  7. Scoped system_admin without global_permissions → PERMISSION_DENIED
  8. Error response does NOT leak scope IDs
  9. Fail-closed: default deny
 10. Only ScopeContext dep (no frontend auth)
 11. No RLS bypass in the dependency itself
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ["ENVIRONMENT"] = "dev"
os.environ["JWT_SECRET"] = "scoped-perm-test-secret-at-least-32c"

from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from packages.domain.scopes import ScopeContext
from packages.api.dependencies import require_scoped_permission


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_test_app(scope_override: ScopeContext) -> FastAPI:
    """Build a FastAPI app with get_scope_context overridden."""
    app = FastAPI()

    @app.get("/global-read")
    async def global_read(_=Depends(require_scoped_permission("organization.read"))):
        return {"ok": True}

    @app.get("/advertiser-read")
    async def advertiser_read(
        _=Depends(require_scoped_permission("organization.read", "advertiser")),
    ):
        return {"ok": True}

    @app.get("/branch-read")
    async def branch_read(
        _=Depends(require_scoped_permission("store.read", "branch")),
    ):
        return {"ok": True}

    async def _fake_scope() -> ScopeContext:
        return scope_override

    from packages.api.dependencies import get_scope_context
    app.dependency_overrides[get_scope_context] = _fake_scope

    return app


def _client_for(scope: ScopeContext) -> TestClient:
    return TestClient(_build_test_app(scope))


def _err(r) -> dict:
    """Extract the inner error detail dict from FastAPI's ``{"detail": {...}}`` wrapper."""
    return r.json()["detail"]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGlobalPermission:
    """Global permission passes regardless of scope_type."""

    def test_admin_with_permission_passes(self):
        scope = ScopeContext.admin("u-a", permissions={"organization.read"})
        c = _client_for(scope)

        assert c.get("/global-read").status_code == 200
        assert c.get("/advertiser-read").status_code == 200

    def test_admin_without_permission_denied(self):
        """Admin without the specific perm → denied on scoped endpoint."""
        scope = ScopeContext.admin("u-a", permissions={"users.read"})
        c = _client_for(scope)

        r = c.get("/advertiser-read")
        assert r.status_code == 403
        assert _err(r)["code"] == "SCOPE_RESTRICTED"

    def test_operator_with_global_permission_passes(self):
        scope = ScopeContext(
            user_id="u-op", role_codes={"operator"},
            global_permissions={"organization.read"},
            all_permissions={"organization.read"},
        )
        c = _client_for(scope)

        assert c.get("/global-read").status_code == 200
        assert c.get("/advertiser-read").status_code == 200

    def test_operator_without_permission_denied(self):
        scope = ScopeContext(
            user_id="u-op", role_codes={"operator"},
            global_permissions={"devices.read"},
            all_permissions={"devices.read"},
        )
        c = _client_for(scope)
        r = c.get("/global-read")
        assert r.status_code == 403
        assert _err(r)["code"] == "PERMISSION_DENIED"


class TestAdvertiserScopedPermission:
    """Advertiser scope + permission → pass.  Missing either → fail."""

    def test_advertiser_with_scope_and_perm_passes(self):
        scope = ScopeContext(
            user_id="u-adv", role_codes={"advertiser"},
            advertiser_scope_ids={"ADV-001"},
            all_permissions={"organization.read"},
        )
        c = _client_for(scope)
        assert c.get("/advertiser-read").status_code == 200

    def test_advertiser_with_multiple_scopes_passes(self):
        scope = ScopeContext(
            user_id="u-adv", role_codes={"advertiser"},
            advertiser_scope_ids={"ADV-001", "ADV-002"},
            all_permissions={"organization.read"},
        )
        c = _client_for(scope)
        assert c.get("/advertiser-read").status_code == 200

    def test_advertiser_with_scope_but_without_perm_denied(self):
        """Has scope IDs but no organization.read → PERMISSION_DENIED."""
        scope = ScopeContext(
            user_id="u-adv", role_codes={"advertiser"},
            advertiser_scope_ids={"ADV-001"},
            all_permissions=set(),
        )
        c = _client_for(scope)
        r = c.get("/advertiser-read")
        assert r.status_code == 403
        assert _err(r)["code"] == "PERMISSION_DENIED"

    def test_advertiser_without_scope_ids_denied(self):
        """Has permission but no scope IDs → SCOPE_RESTRICTED."""
        scope = ScopeContext(
            user_id="u-adv", role_codes={"advertiser"},
            advertiser_scope_ids=set(),
            all_permissions={"organization.read"},
        )
        c = _client_for(scope)
        r = c.get("/advertiser-read")
        assert r.status_code == 403
        assert _err(r)["code"] == "SCOPE_RESTRICTED"

    def test_advertiser_empty_both_denied(self):
        scope = ScopeContext(
            user_id="u-adv", role_codes={"advertiser"},
            advertiser_scope_ids=set(),
            all_permissions=set(),
        )
        c = _client_for(scope)
        r = c.get("/advertiser-read")
        assert r.status_code == 403
        assert _err(r)["code"] == "SCOPE_RESTRICTED"


class TestCrossScopeDenied:
    """A scoped user for one scope_type does NOT pass another scope_type."""

    def test_advertiser_scope_does_not_pass_branch(self):
        scope = ScopeContext(
            user_id="u-adv", role_codes={"advertiser"},
            advertiser_scope_ids={"ADV-001"},
            all_permissions={"store.read"},
        )
        c = _client_for(scope)
        r = c.get("/branch-read")
        assert r.status_code == 403
        assert _err(r)["code"] == "SCOPE_RESTRICTED"


class TestNoPermission:
    """No permission → 403."""

    def test_deny_all_403(self):
        c = _client_for(ScopeContext.deny_all("u-none"))
        r = c.get("/global-read")
        assert r.status_code == 403
        assert _err(r)["code"] == "PERMISSION_DENIED"

    def test_deny_all_403_scoped(self):
        c = _client_for(ScopeContext.deny_all("u-none"))
        r = c.get("/advertiser-read")
        assert r.status_code == 403
        # deny_all has no scope IDs → SCOPE_RESTRICTED when scope is required
        assert _err(r)["code"] == "SCOPE_RESTRICTED"


class TestScopedAdminNotGlobal:
    """Scoped system_admin without global_permissions is NOT a global admin."""

    def test_scoped_system_admin_with_scope_but_no_perm(self):
        """Has advertiser scope + system_admin role, but no organization.read → denied."""
        scope = ScopeContext(
            user_id="u-ba", is_admin=False,
            role_codes={"system_admin"},
            global_permissions=set(),
            advertiser_scope_ids={"ADV-001"},
            all_permissions=set(),
        )
        c = _client_for(scope)
        r = c.get("/advertiser-read")
        assert r.status_code == 403
        assert _err(r)["code"] == "PERMISSION_DENIED"

    def test_scoped_security_admin_no_global_perm(self):
        scope = ScopeContext(
            user_id="u-sec", is_admin=False,
            role_codes={"security_admin"},
            global_permissions=set(),
            all_permissions=set(),
        )
        c = _client_for(scope)
        r = c.get("/global-read")
        assert r.status_code == 403
        assert _err(r)["code"] == "PERMISSION_DENIED"

    def test_scoped_admin_with_perm_and_scope_passes(self):
        """Scoped admin WITH the right perm + scope → passes."""
        scope = ScopeContext(
            user_id="u-ba", is_admin=False,
            role_codes={"system_admin"},
            global_permissions=set(),
            advertiser_scope_ids={"ADV-001"},
            all_permissions={"organization.read"},
        )
        c = _client_for(scope)
        assert c.get("/advertiser-read").status_code == 200


class TestErrorResponseNoLeak:
    """403 errors must NOT leak scope IDs or internal state."""

    def test_permission_denied_no_scope_ids(self):
        c = _client_for(ScopeContext.deny_all("u-none"))
        r = c.get("/global-read")
        assert r.status_code == 403
        body_str = str(r.json())
        assert "ADV-" not in body_str
        assert "scope_ids" not in body_str.lower()

    def test_scope_restricted_no_scope_ids(self):
        scope = ScopeContext(
            user_id="u-adv", role_codes={"advertiser"},
            advertiser_scope_ids=set(),
            all_permissions=set(),
        )
        c = _client_for(scope)
        r = c.get("/advertiser-read")
        assert r.status_code == 403
        body_str = str(r.json())
        assert "ADV-" not in body_str
        assert "scope_ids" not in body_str.lower()

    def test_minimal_error_structure(self):
        """Error response: only code + message inside detail, no extra keys."""
        c = _client_for(ScopeContext.deny_all("u-none"))
        r = c.get("/advertiser-read")
        assert r.status_code == 403
        detail = _err(r)
        assert set(detail.keys()) == {"code", "message"}
        for forbidden in ("traceback", "debug", "exception", "scope_id", "internal"):
            assert forbidden not in {k.lower() for k in detail.keys()}


class TestFailClosed:
    """require_scoped_permission is fail-closed by default."""

    def test_fresh_scope_context_deny_all(self):
        scope = ScopeContext(user_id="u-fresh")
        assert scope.is_admin is False
        assert scope.global_permissions == set()
        assert scope.all_permissions == set()
        assert scope.advertiser_scope_ids == set()
        assert not bool(scope)

    def test_missing_scope_context_fails(self):
        c = _client_for(ScopeContext.deny_all())
        r = c.get("/advertiser-read")
        assert r.status_code == 403

    def test_partial_scope_no_permission_fails(self):
        scope = ScopeContext(
            user_id="u-partial", role_codes={"advertiser"},
            advertiser_scope_ids={"ADV-001"},
            all_permissions=set(),
        )
        c = _client_for(scope)
        r = c.get("/branch-read")
        assert r.status_code == 403


class TestScopeContextOnlyDep:
    """require_scoped_permission uses only ScopeContext and db — no frontend auth."""

    def test_only_scope_context_dependency(self):
        import inspect

        dep = require_scoped_permission("test.perm", "advertiser")
        sig = inspect.signature(dep)
        param_names = list(sig.parameters.keys())

        assert "db" in param_names
        assert "scope" in param_names
        for forbidden in ("request", "cookie", "header", "session", "token", "frontend"):
            assert forbidden not in param_names


class TestNoRlsBypass:
    """require_scoped_permission does NOT bypass RLS — it delegates to ScopeContext."""

    def test_delegates_to_scope_context(self):
        import inspect

        dep = require_scoped_permission("test.perm")
        src = inspect.getsource(dep)

        assert "set_config" not in src.lower()
        assert "execute" not in src.lower()
        assert "rls" not in src.lower()
        assert "scope." in src
