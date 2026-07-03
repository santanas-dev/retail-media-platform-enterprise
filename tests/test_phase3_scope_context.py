"""
Unit tests for ScopeContext and scope resolution (Phase 3.5b).

Tests the dataclass logic without database — covers admin detection,
scoped vs unscoped roles, and deny-all semantics.
"""

import pytest

from packages.domain.scopes import ADMIN_ROLE_CODES, ScopeContext


class TestScopeContextAdmin:
    """Admin detection is based on unscoped system_admin/security_admin roles."""

    def test_unscoped_system_admin_is_admin(self):
        ctx = ScopeContext(
            user_id="u-admin",
            is_admin=True,
            role_codes={"system_admin"},
            global_permissions={"users.read", "users.manage"},
        )
        assert ctx.is_admin is True
        assert "system_admin" in ctx.role_codes
        assert "users.read" in ctx.global_permissions

    def test_unscoped_security_admin_is_admin(self):
        ctx = ScopeContext(
            user_id="u-sec",
            is_admin=True,
            role_codes={"security_admin"},
            global_permissions={"audit.read"},
        )
        assert ctx.is_admin is True

    def test_operator_is_not_admin_even_with_all_permissions(self):
        """operator role with many permissions is NOT admin."""
        ctx = ScopeContext(
            user_id="u-op",
            is_admin=False,
            role_codes={"operator"},
            global_permissions={"users.read", "roles.read", "devices.read"},
        )
        assert ctx.is_admin is False
        # Still has permissions — just not admin
        assert ctx.global_permissions

    def test_scoped_system_admin_is_not_global_admin(self):
        """system_admin with branch scope is NOT a global admin."""
        ctx = ScopeContext(
            user_id="u-branch-admin",
            is_admin=False,
            role_codes={"system_admin"},
            global_permissions=set(),
            advertiser_scope_ids=set(),
        )
        assert ctx.is_admin is False
        assert not ctx.global_permissions


class TestScopeContextDenyAll:
    """Empty scopes = deny-all."""

    def test_default_deny_all(self):
        ctx = ScopeContext.deny_all("u-none")
        assert ctx.is_admin is False
        assert ctx.global_permissions == set()
        assert ctx.advertiser_scope_ids == set()
        assert ctx.role_codes == set()

    def test_deny_all_is_falsy(self):
        ctx = ScopeContext.deny_all()
        assert not bool(ctx)

    def test_admin_is_truthy(self):
        ctx = ScopeContext.admin("u-a")
        assert bool(ctx)

    def test_user_with_global_permissions_is_truthy(self):
        ctx = ScopeContext(
            user_id="u-op",
            role_codes={"operator"},
            global_permissions={"devices.read"},
        )
        assert bool(ctx)

    def test_user_with_advertiser_scopes_is_truthy(self):
        ctx = ScopeContext(
            user_id="u-adv",
            role_codes={"advertiser"},
            advertiser_scope_ids={"ADV-001"},
        )
        assert bool(ctx)


class TestScopeContextFactory:
    """Factory methods."""

    def test_admin_factory_defaults(self):
        ctx = ScopeContext.admin("u-a")
        assert ctx.user_id == "u-a"
        assert ctx.is_admin is True
        assert "system_admin" in ctx.role_codes

    def test_admin_factory_with_permissions(self):
        ctx = ScopeContext.admin("u-a", permissions={"users.read", "audit.read"})
        assert ctx.global_permissions == {"users.read", "audit.read"}

    def test_deny_all_factory_defaults(self):
        ctx = ScopeContext.deny_all()
        assert ctx.user_id == ""
        assert not ctx

    def test_deny_all_factory_with_user_id(self):
        ctx = ScopeContext.deny_all("u-none")
        assert ctx.user_id == "u-none"
        assert not ctx


class TestAdvertiserScope:
    """Advertiser scope does NOT make a user admin."""

    def test_advertiser_scope_only(self):
        ctx = ScopeContext(
            user_id="u-adv",
            role_codes={"advertiser"},
            advertiser_scope_ids={"ADV-001"},
        )
        assert ctx.is_admin is False
        assert ctx.global_permissions == set()
        assert ctx.advertiser_scope_ids == {"ADV-001"}

    def test_multiple_advertiser_scopes(self):
        ctx = ScopeContext(
            user_id="u-multi",
            role_codes={"advertiser"},
            advertiser_scope_ids={"ADV-001", "ADV-002"},
        )
        assert ctx.advertiser_scope_ids == {"ADV-001", "ADV-002"}
        assert ctx.is_admin is False


class TestADMIN_ROLE_CODES:
    """Only system_admin and security_admin are admin roles."""

    def test_admin_role_codes(self):
        assert "system_admin" in ADMIN_ROLE_CODES
        assert "security_admin" in ADMIN_ROLE_CODES

    def test_operator_not_admin(self):
        assert "operator" not in ADMIN_ROLE_CODES

    def test_advertiser_not_admin(self):
        assert "advertiser" not in ADMIN_ROLE_CODES


# ---------------------------------------------------------------------------
# require_scoped_permission decision logic (Phase 3.5c)
# ---------------------------------------------------------------------------


def _check_scoped(scope, perm_code, scope_type=None):
    """Simulate require_scoped_permission decision without FastAPI Depends.

    Returns (allowed, code) where code is None on pass or the 403 reason.
    """
    # 1. Admin bypass (unscoped admin + perm)
    if scope.is_admin and perm_code in scope.global_permissions:
        return True, None
    # 2. Global permission
    if perm_code in scope.global_permissions:
        return True, None
    # 3. Scoped access — advertiser scope type
    if scope_type == "advertiser":
        if scope.advertiser_scope_ids and perm_code in scope.all_permissions:
            return True, None
        if scope.advertiser_scope_ids:
            return False, "PERMISSION_DENIED"
        return False, "SCOPE_RESTRICTED"
    # 4. Other scope types (branch, cluster, store) — deferred
    if scope_type is not None:
        return False, "SCOPE_RESTRICTED"
    # 5. No permission
    return False, "PERMISSION_DENIED"


class TestScopedPermissionGlobal:
    """Global permission passes regardless of scope."""

    def test_admin_with_permission_passes(self):
        scope = ScopeContext.admin("u-a", permissions={"organization.read"})
        ok, _ = _check_scoped(scope, "organization.read", "advertiser")
        assert ok is True

    def test_admin_without_permission_fails(self):
        scope = ScopeContext.admin("u-a", permissions={"users.read"})
        ok, code = _check_scoped(scope, "organization.read", "advertiser")
        assert ok is False
        # Admin flag alone doesn't grant advertiser scope
        assert code == "SCOPE_RESTRICTED"

    def test_operator_with_org_read_passes(self):
        scope = ScopeContext(
            user_id="u-op", role_codes={"operator"},
            global_permissions={"organization.read"},
        )
        ok, _ = _check_scoped(scope, "organization.read", "advertiser")
        assert ok is True

    def test_operator_without_org_read_fails(self):
        scope = ScopeContext(
            user_id="u-op", role_codes={"operator"},
            global_permissions={"devices.read"},
        )
        ok, code = _check_scoped(scope, "organization.read", "advertiser")
        assert ok is False


class TestScopedPermissionAdvertiser:
    """Advertiser scoped access."""

    def test_advertiser_with_scope_passes(self):
        scope = ScopeContext(
            user_id="u-adv", role_codes={"advertiser"},
            advertiser_scope_ids={"ADV-001"},
            all_permissions={"organization.read"},
        )
        ok, _ = _check_scoped(scope, "organization.read", "advertiser")
        assert ok is True

    def test_advertiser_without_scope_fails(self):
        scope = ScopeContext(
            user_id="u-adv", role_codes={"advertiser"},
            advertiser_scope_ids=set(),
            all_permissions={"organization.read"},
        )
        ok, code = _check_scoped(scope, "organization.read", "advertiser")
        assert ok is False
        assert code == "SCOPE_RESTRICTED"

    def test_advertiser_without_permission_fails(self):
        """Advertiser scope alone doesn't grant global organization.read."""
        scope = ScopeContext(
            user_id="u-adv", role_codes={"advertiser"},
            advertiser_scope_ids={"ADV-001"},
            all_permissions=set(),
        )
        ok, _ = _check_scoped(scope, "organization.read")
        assert ok is False


class TestScopedPermissionScopedAdmin:
    """Scoped system_admin is NOT a global admin."""

    def test_scoped_admin_without_global_permission_fails(self):
        """system_admin with branch scope has no global_permissions."""
        scope = ScopeContext(
            user_id="u-branch-admin",
            is_admin=False,
            role_codes={"system_admin"},
            global_permissions=set(),
        )
        ok, code = _check_scoped(scope, "organization.read", "advertiser")
        assert ok is False

    def test_scoped_admin_with_global_permission_passes(self):
        """system_admin with unscoped role has global_permissions."""
        scope = ScopeContext.admin("u-a", permissions={"organization.read"})
        ok, _ = _check_scoped(scope, "organization.read", "advertiser")
        assert ok is True


class TestScopedPermissionEmptyScope:
    """Empty scopes = deny-all."""

    def test_empty_scope_fails(self):
        scope = ScopeContext.deny_all("u-none")
        ok, code = _check_scoped(scope, "organization.read", "advertiser")
        assert ok is False

    def test_empty_scope_without_scope_type_fails(self):
        scope = ScopeContext.deny_all("u-none")
        ok, code = _check_scoped(scope, "organization.read")
        assert ok is False
