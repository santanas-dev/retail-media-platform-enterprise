"""
Behavioral tests - RM-STAB-022: role management does not allow privilege
escalation, against real PostgreSQL as the NOBYPASSRLS app role.

- A scoped role grants nothing on ``require_permission`` routes (ADR-009 §1):
  the P0-6 path "scoped system_admin assigns itself a global role" is closed.
- ``assign_role`` refuses self-assignment and roles that carry permissions
  the actor does not hold globally; ``remove_role`` refuses the same roles.
- The last active system admin (and the last break-glass admin) cannot lose
  the role or be deactivated, including under concurrent requests.
- Taking over or disabling an account is not a way around it: password
  reset, re-activation and deactivation are refused when the target's global
  permissions exceed the actor's; a break-glass account is managed by a global system_admin only.
- Refusals are audited and the audit row survives the 403/409.

Requires: RUN_BEHAVIORAL_TESTS=1, running PostgreSQL, migrations + seed applied.
"""

import asyncio

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from packages.security.config import reset_security_config
from packages.security.jwt import create_access_token
from tests.behavioral.conftest import _get_setup_engine

_ID = "/api/v1/identity"
_ORG = "00000000-0000-0000-0000-000000000200"  # seed ADV-001

ADMIN1 = "beh-022-admin1"
ADMIN2 = "beh-022-admin2"
SECADM = "beh-022-secadm"
SCOPED_SA = "beh-022-scoped-sa"
ADVERTISER = "beh-022-advertiser"
TARGET = "beh-022-target"
_ALL = (ADMIN1, ADMIN2, SECADM, SCOPED_SA, ADVERTISER, TARGET)

_REFERENCE_ROUTES = ("/branches", "/clusters", "/stores", "/display-surfaces")
_OLD_HASH = "beh-022-not-a-real-hash"
_RESET = {"auto_generate_password": True}


def _owner_sql(sql: str, params: dict | None = None, fetch: bool = True):
    """Run SQL as the owner with admin elevation (assertions/setup only)."""

    async def _run():
        async with _get_setup_engine().begin() as conn:
            await conn.execute(text("SELECT set_config('app.rmp_is_admin', 'true', true)"))
            result = await conn.execute(text(sql), params or {})
            return [dict(r._mapping) for r in result] if fetch else None

    return asyncio.run(_run())


def _cleanup():
    for sql in (
        "DELETE FROM audit_events_operational "
        "WHERE actor_user_id LIKE 'beh-022-%' OR target_id LIKE 'beh-022-%'",
        "DELETE FROM refresh_sessions WHERE user_id LIKE 'beh-022-%'",
        "DELETE FROM local_credentials WHERE user_id LIKE 'beh-022-%'",
        "DELETE FROM audit_events_operational WHERE target_id IN "
        "(SELECT id FROM users WHERE username = 'beh-022-created')",
        "DELETE FROM advertiser_user_memberships WHERE user_id IN "
        "(SELECT id FROM users WHERE username = 'beh-022-created')",
        "DELETE FROM local_credentials WHERE user_id IN "
        "(SELECT id FROM users WHERE username = 'beh-022-created')",
        "DELETE FROM user_roles WHERE user_id IN "
        "(SELECT id FROM users WHERE username = 'beh-022-created')",
        "DELETE FROM users WHERE username = 'beh-022-created'",
        "DELETE FROM advertiser_user_memberships WHERE user_id LIKE 'beh-022-%'",
        "DELETE FROM user_roles WHERE user_id LIKE 'beh-022-%'",
        "DELETE FROM users WHERE id LIKE 'beh-022-%'",
    ):
        _owner_sql(sql, fetch=False)


def _add_role(assignment_id: str, user_id: str, role_code: str, scoped: bool = False):
    _owner_sql(
        "INSERT INTO user_roles (id, user_id, role_id, scope_type, scope_id) "
        "SELECT :id, :u, id, :st, :sid FROM roles WHERE code = :code",
        {
            "id": assignment_id, "u": user_id, "code": role_code,
            "st": "advertiser" if scoped else None,
            "sid": _ORG if scoped else None,
        },
        fetch=False,
    )


@pytest.fixture
def actors(db_available):
    _cleanup()
    for uid in _ALL:
        _owner_sql(
            "INSERT INTO users (id, code, username, email, display_name, auth_provider, status) "
            "VALUES (:id, :code, :id, :email, :id, 'local_advertiser', 'active')",
            {"id": uid, "code": uid.upper(), "email": f"{uid}@t.local"},
            fetch=False,
        )
    _add_role("ur-022-admin1", ADMIN1, "system_admin")
    _add_role("ur-022-admin2", ADMIN2, "system_admin")
    _add_role("ur-022-secadm", SECADM, "security_admin")
    _add_role("ur-022-scoped-sa", SCOPED_SA, "system_admin", scoped=True)
    _add_role("ur-022-advertiser", ADVERTISER, "advertiser", scoped=True)
    _add_role("ur-022-target", TARGET, "operator")
    _owner_sql(
        "INSERT INTO advertiser_user_memberships (id, user_id, advertiser_organization_id, status) "
        "VALUES ('aum-022-adv', :u, :o, 'active')",
        {"u": ADVERTISER, "o": _ORG},
        fetch=False,
    )
    for uid in (ADVERTISER, TARGET, ADMIN2):
        _owner_sql(
            "INSERT INTO local_credentials (id, user_id, credential_type, password_hash, status) "
            "VALUES (:id, :u, 'local_advertiser', :h, 'active')",
            {"id": f"lc-{uid}", "u": uid, "h": _OLD_HASH},
            fetch=False,
        )
    yield
    _cleanup()


@pytest.fixture
def only_test_admins(actors):
    """Make ADMIN1/ADMIN2 the only active global system admins for the test."""
    others = _owner_sql(
        "SELECT DISTINCT u.id FROM users u "
        "JOIN user_roles ur ON ur.user_id = u.id JOIN roles r ON r.id = ur.role_id "
        "WHERE u.status = 'active' AND r.code = 'system_admin' AND ur.scope_type IS NULL "
        "AND u.id NOT LIKE 'beh-022-%'"
    )
    ids = [row["id"] for row in others]
    for uid in ids:
        _owner_sql("UPDATE users SET status = 'inactive' WHERE id = :id", {"id": uid}, fetch=False)
    yield
    for uid in ids:
        _owner_sql("UPDATE users SET status = 'active' WHERE id = :id", {"id": uid}, fetch=False)


@pytest.fixture
def client(app, actors):
    reset_security_config()
    return TestClient(app)


def _auth(user_id: str) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user_id, 'local_advertiser')}"}


def _assignments(user_id: str) -> list[dict]:
    return _owner_sql(
        "SELECT ur.id, r.code, ur.scope_type FROM user_roles ur "
        "JOIN roles r ON r.id = ur.role_id WHERE ur.user_id = :u ORDER BY r.code, ur.id",
        {"u": user_id},
    )


def _audit(action: str, target_id: str) -> list[dict]:
    return _owner_sql(
        "SELECT actor_user_id, target_type, target_id, details_json "
        "FROM audit_events_operational WHERE action = :a AND target_id = :t "
        "ORDER BY created_at",
        {"a": action, "t": target_id},
    )


def _break_glass_admin() -> dict:
    rows = _owner_sql(
        "SELECT u.id AS user_id, ur.id AS assignment_id FROM users u "
        "JOIN user_roles ur ON ur.user_id = u.id JOIN roles r ON r.id = ur.role_id "
        "WHERE u.is_break_glass AND u.status = 'active' "
        "AND r.code = 'system_admin' AND ur.scope_type IS NULL"
    )
    assert len(rows) == 1, rows
    return rows[0]


def _password_hash(user_id: str) -> str:
    return _owner_sql(
        "SELECT password_hash FROM local_credentials WHERE user_id = :u", {"u": user_id},
    )[0]["password_hash"]


def _status(user_id: str) -> str:
    return _owner_sql("SELECT status FROM users WHERE id = :u", {"u": user_id})[0]["status"]


class TestScopedRoleGrantsNoGlobalPermission:

    def test_scoped_system_admin_cannot_assign_itself_a_global_role(self, client):
        """P0-6: scoped system_admin -> PUT /users/{self}/roles -> global admin."""
        resp = client.put(
            f"{_ID}/users/{SCOPED_SA}/roles",
            json={"role_code": "system_admin"},
            headers=_auth(SCOPED_SA),
        )
        assert resp.status_code == 403, resp.text
        assert resp.json()["detail"]["code"] == "PERMISSION_DENIED"
        assert _assignments(SCOPED_SA) == [
            {"id": "ur-022-scoped-sa", "code": "system_admin", "scope_type": "advertiser"},
        ]

    @pytest.mark.parametrize("method,path", [
        ("GET", "/users"),
        ("GET", "/roles"),
        ("GET", "/audit-events"),
        ("GET", "/devices"),
        ("GET", "/campaigns/approval-queue"),
        ("GET", "/creative-assets/moderation-queue"),
        ("POST", f"/users/{TARGET}/deactivate"),
        ("POST", f"/users/{TARGET}/reset-password"),
    ])
    def test_scoped_system_admin_denied_on_global_routes(self, client, method, path):
        resp = client.request(
            method, f"{_ID}{path}", headers=_auth(SCOPED_SA),
            json={"auto_generate_password": True} if method == "POST" else None,
        )
        assert resp.status_code == 403, resp.text
        assert resp.json()["detail"]["code"] == "PERMISSION_DENIED"
        assert _status(TARGET) == "active"

    @pytest.mark.parametrize("path", _REFERENCE_ROUTES)
    def test_scoped_advertiser_denied_on_reference_routes(self, client, path):
        resp = client.get(f"{_ID}{path}", headers=_auth(ADVERTISER))
        assert resp.status_code == 403, resp.text
        assert resp.json()["detail"]["code"] == "PERMISSION_DENIED"

    def test_scoped_advertiser_keeps_its_permissions_in_me(self, client):
        """/auth/me still reports scoped permissions - the portal UI needs them."""
        resp = client.get("/api/v1/auth/me", headers=_auth(ADVERTISER))
        assert resp.status_code == 200, resp.text
        perms = set(resp.json()["permissions"])
        assert {"campaigns.read", "campaign_briefs.manage", "creatives.read"} <= perms

    def test_global_admin_still_passes(self, client):
        resp = client.get(f"{_ID}/users", headers=_auth(ADMIN1))
        assert resp.status_code == 200, resp.text


class TestAssignRoleGuards:

    def test_admin_assigns_role_to_another_user(self, client):
        resp = client.put(
            f"{_ID}/users/{TARGET}/roles",
            json={"role_code": "analyst"},
            headers=_auth(ADMIN1),
        )
        assert resp.status_code == 201, resp.text
        assert {a["code"] for a in _assignments(TARGET)} == {"analyst", "operator"}
        assert len(_audit("user.role_assigned", TARGET)) == 1
        assert _audit("user.role_assign_denied", TARGET) == []

    def test_self_assignment_refused_and_audited(self, client):
        resp = client.put(
            f"{_ID}/users/{ADMIN1}/roles",
            json={"role_code": "operator"},
            headers=_auth(ADMIN1),
        )
        assert resp.status_code == 403, resp.text
        assert resp.json()["detail"] == {
            "code": "SELF_ROLE_ASSIGNMENT_FORBIDDEN",
            "message": "Cannot assign a role to yourself",
        }
        assert [a["code"] for a in _assignments(ADMIN1)] == ["system_admin"]
        events = _audit("user.role_assign_denied", ADMIN1)
        assert len(events) == 1
        assert events[0]["actor_user_id"] == ADMIN1
        assert events[0]["target_type"] == "user"
        assert events[0]["details_json"] == {
            "role_code": "operator", "scope_type": None, "scope_id": None,
            "reason": "self_assign",
        }

    @pytest.mark.parametrize("role_code,scoped", [
        ("system_admin", False),
        ("system_admin", True),
        ("operator", False),
    ])
    def test_role_above_actor_refused_and_audited(self, client, role_code, scoped):
        """security_admin lacks permissions carried by system_admin and operator."""
        body = {"role_code": role_code}
        if scoped:
            body.update(scope_type="advertiser", scope_id=_ORG)
        before = _assignments(TARGET)
        resp = client.put(f"{_ID}/users/{TARGET}/roles", json=body, headers=_auth(SECADM))
        assert resp.status_code == 403, resp.text
        assert resp.json()["detail"] == {
            "code": "ROLE_EXCEEDS_ACTOR_PERMISSIONS",
            "message": "Cannot assign a role that exceeds your own permissions",
        }
        assert _assignments(TARGET) == before
        events = _audit("user.role_assign_denied", TARGET)
        assert len(events) == 1
        assert events[0]["actor_user_id"] == SECADM
        assert events[0]["details_json"] == {
            "role_code": role_code,
            "scope_type": "advertiser" if scoped else None,
            "scope_id": _ORG if scoped else None,
            "reason": "exceeds_actor_permissions",
        }

    def test_security_admin_cannot_escalate_through_role_assignment(self, client):
        """No role the security_admin may hand out makes anyone a system_admin."""
        client.put(
            f"{_ID}/users/{TARGET}/roles",
            json={"role_code": "system_admin"},
            headers=_auth(SECADM),
        )
        resp = client.get(f"{_ID}/emergency/status", headers=_auth(TARGET))
        assert resp.status_code == 403, resp.text


class TestRemoveRoleGuards:

    def test_admin_removes_role_when_another_admin_remains(self, client):
        resp = client.delete(
            f"{_ID}/users/{ADMIN2}/roles/ur-022-admin2", headers=_auth(ADMIN1),
        )
        assert resp.status_code == 204, resp.text
        assert _assignments(ADMIN2) == []
        assert len(_audit("user.role_removed", ADMIN2)) == 1

    def test_role_above_actor_cannot_be_removed(self, client):
        resp = client.delete(
            f"{_ID}/users/{ADMIN1}/roles/ur-022-admin1", headers=_auth(SECADM),
        )
        assert resp.status_code == 403, resp.text
        assert resp.json()["detail"] == {
            "code": "ROLE_EXCEEDS_ACTOR_PERMISSIONS",
            "message": "Cannot remove a role that exceeds your own permissions",
        }
        assert [a["id"] for a in _assignments(ADMIN1)] == ["ur-022-admin1"]
        events = _audit("user.role_remove_denied", ADMIN1)
        assert len(events) == 1
        assert events[0]["actor_user_id"] == SECADM
        assert events[0]["details_json"] == {
            "role_code": "system_admin", "scope_type": None, "scope_id": None,
            "reason": "exceeds_actor_permissions",
        }

    def test_last_system_admin_role_cannot_be_removed(self, client, only_test_admins):
        first = client.delete(
            f"{_ID}/users/{ADMIN2}/roles/ur-022-admin2", headers=_auth(ADMIN1),
        )
        assert first.status_code == 204, first.text

        # ADMIN1 is now the only active global system admin, incl. removing own role.
        resp = client.delete(
            f"{_ID}/users/{ADMIN1}/roles/ur-022-admin1", headers=_auth(ADMIN1),
        )
        assert resp.status_code == 409, resp.text
        assert resp.json()["detail"] == {
            "code": "LAST_SYSTEM_ADMIN",
            "message": "Cannot remove the last active system admin role",
        }
        assert [a["id"] for a in _assignments(ADMIN1)] == ["ur-022-admin1"]
        events = _audit("user.role_remove_denied", ADMIN1)
        assert len(events) == 1
        assert events[0]["details_json"]["reason"] == "last_system_admin"

    def test_scoped_system_admin_is_not_counted_as_admin(self, client, only_test_admins):
        """A scoped system_admin assignment neither counts nor is protected."""
        client.delete(f"{_ID}/users/{ADMIN2}/roles/ur-022-admin2", headers=_auth(ADMIN1))
        # SCOPED_SA still holds a scoped system_admin: ADMIN1 stays "the last one".
        resp = client.delete(
            f"{_ID}/users/{ADMIN1}/roles/ur-022-admin1", headers=_auth(ADMIN1),
        )
        assert resp.status_code == 409, resp.text
        removed = client.delete(
            f"{_ID}/users/{SCOPED_SA}/roles/ur-022-scoped-sa", headers=_auth(ADMIN1),
        )
        assert removed.status_code == 204, removed.text

    def test_last_break_glass_admin_keeps_system_admin_role(self, client):
        bg = _break_glass_admin()
        try:
            resp = client.delete(
                f"{_ID}/users/{bg['user_id']}/roles/{bg['assignment_id']}",
                headers=_auth(ADMIN1),
            )
            assert resp.status_code == 409, resp.text
            assert resp.json()["detail"]["code"] == "LAST_BREAK_GLASS_ADMIN"
            assert [a["id"] for a in _assignments(bg["user_id"])] == [bg["assignment_id"]]
            events = _audit("user.role_remove_denied", bg["user_id"])
            assert len(events) == 1
            assert events[0]["details_json"]["reason"] == "last_break_glass_admin"
        finally:
            # A failing run must not leave the seed without its break-glass admin.
            _owner_sql(
                "INSERT INTO user_roles (id, user_id, role_id) "
                "SELECT CAST(:id AS varchar), CAST(:u AS varchar), r.id FROM roles r "
                "WHERE r.code = 'system_admin' "
                "AND NOT EXISTS (SELECT 1 FROM user_roles WHERE id = CAST(:id AS varchar))",
                {"id": bg["assignment_id"], "u": bg["user_id"]}, fetch=False,
            )
            _owner_sql(
                "DELETE FROM audit_events_operational WHERE target_id = :t "
                "AND action IN ('user.role_remove_denied', 'user.role_removed')",
                {"t": bg["user_id"]}, fetch=False,
            )


class TestDeactivateGuards:

    _DENIED = {
        "code": "TARGET_EXCEEDS_ACTOR_PERMISSIONS",
        "message": "Cannot manage a user whose permissions exceed your own",
    }

    @pytest.mark.parametrize("target", [ADMIN1, TARGET])
    def test_security_admin_cannot_deactivate_outranking_user(self, client, target):
        """system_admin and operator hold global permissions security_admin lacks."""
        resp = client.post(f"{_ID}/users/{target}/deactivate", headers=_auth(SECADM))
        assert resp.status_code == 403, resp.text
        assert resp.json()["detail"] == self._DENIED
        assert _status(target) == "active"
        events = _audit("user.deactivate_denied", target)
        assert len(events) == 1
        assert events[0]["actor_user_id"] == SECADM
        assert events[0]["details_json"] == {"reason": "exceeds_actor_permissions"}

    def test_security_admin_cannot_deactivate_break_glass(self, client):
        bg = _break_glass_admin()["user_id"]
        try:
            resp = client.post(f"{_ID}/users/{bg}/deactivate", headers=_auth(SECADM))
            assert resp.status_code == 403, resp.text
            assert resp.json()["detail"] == self._DENIED
            assert _status(bg) == "active"
            events = _audit("user.deactivate_denied", bg)
            assert len(events) == 1
            assert events[0]["details_json"] == {"reason": "break_glass_requires_system_admin"}
        finally:
            _owner_sql("UPDATE users SET status = 'active' WHERE id = :u", {"u": bg}, fetch=False)
            _owner_sql(
                "DELETE FROM audit_events_operational WHERE target_id = :t "
                "AND action LIKE 'user.deactivate%'", {"t": bg}, fetch=False,
            )

    def test_security_admin_cannot_take_the_admins_out(self, client, only_test_admins):
        """With every system_admin out of reach, none of them can be disabled."""
        for admin in (ADMIN1, ADMIN2):
            resp = client.post(f"{_ID}/users/{admin}/deactivate", headers=_auth(SECADM))
            assert resp.status_code == 403, resp.text
        assert _status(ADMIN1) == "active" and _status(ADMIN2) == "active"

    def test_system_admin_deactivates_another_admin(self, client):
        resp = client.post(f"{_ID}/users/{ADMIN2}/deactivate", headers=_auth(ADMIN1))
        assert resp.status_code == 200, resp.text
        assert _status(ADMIN2) == "inactive"
        assert _audit("user.deactivate_denied", ADMIN2) == []

    def test_security_admin_deactivates_scoped_users(self, client):
        """Scoped roles carry no global permissions: a scoped system_admin is
        neither an administrator nor out of a security_admin's reach."""
        for target in (SCOPED_SA, ADVERTISER):
            resp = client.post(f"{_ID}/users/{target}/deactivate", headers=_auth(SECADM))
            assert resp.status_code == 200, resp.text
            assert _status(target) == "inactive"


class TestAccountTakeoverGuards:
    """Password reset / re-activation of an account that outranks the actor."""

    _DENIED = {
        "code": "TARGET_EXCEEDS_ACTOR_PERMISSIONS",
        "message": "Cannot manage a user whose permissions exceed your own",
    }

    def test_security_admin_cannot_reset_break_glass_password(self, client):
        """The takeover path: security_admin -> reset break-glass -> system_admin."""
        bg = _break_glass_admin()["user_id"]
        before = _password_hash(bg)
        try:
            resp = client.post(
                f"{_ID}/users/{bg}/reset-password", json=_RESET, headers=_auth(SECADM),
            )
            assert resp.status_code == 403, resp.text
            assert resp.json()["detail"] == self._DENIED
            assert "one_time_password" not in resp.text
            assert _password_hash(bg) == before
            events = _audit("user.password_reset_denied", bg)
            assert len(events) == 1
            assert events[0]["actor_user_id"] == SECADM
            assert events[0]["details_json"] == {"reason": "break_glass_requires_system_admin"}
        finally:
            _owner_sql(
                "UPDATE local_credentials SET password_hash = :h WHERE user_id = :u",
                {"h": before, "u": bg}, fetch=False,
            )
            _owner_sql(
                "DELETE FROM audit_events_operational WHERE target_id = :t "
                "AND action LIKE 'user.password_reset%'", {"t": bg}, fetch=False,
            )

    @pytest.mark.parametrize("target", [ADMIN2, TARGET])
    def test_security_admin_cannot_reset_password_of_outranking_user(self, client, target):
        """system_admin and operator hold global permissions security_admin lacks."""
        resp = client.post(
            f"{_ID}/users/{target}/reset-password", json=_RESET, headers=_auth(SECADM),
        )
        assert resp.status_code == 403, resp.text
        assert resp.json()["detail"] == self._DENIED
        assert _password_hash(target) == _OLD_HASH
        events = _audit("user.password_reset_denied", target)
        assert len(events) == 1
        assert events[0]["details_json"] == {"reason": "exceeds_actor_permissions"}

    def test_security_admin_resets_password_of_scoped_advertiser(self, client):
        """A scoped role carries no global permissions - support flow keeps working."""
        resp = client.post(
            f"{_ID}/users/{ADVERTISER}/reset-password", json=_RESET, headers=_auth(SECADM),
        )
        assert resp.status_code == 200, resp.text
        assert _password_hash(ADVERTISER) != _OLD_HASH
        assert _audit("user.password_reset_denied", ADVERTISER) == []

    def test_system_admin_resets_password_of_another_admin(self, client):
        resp = client.post(
            f"{_ID}/users/{ADMIN2}/reset-password", json=_RESET, headers=_auth(ADMIN1),
        )
        assert resp.status_code == 200, resp.text
        assert _password_hash(ADMIN2) != _OLD_HASH

    def test_security_admin_cannot_reactivate_system_admin(self, client):
        _owner_sql("UPDATE users SET status = 'inactive' WHERE id = :u", {"u": ADMIN2}, fetch=False)
        resp = client.post(f"{_ID}/users/{ADMIN2}/activate", headers=_auth(SECADM))
        assert resp.status_code == 403, resp.text
        assert resp.json()["detail"] == self._DENIED
        assert _status(ADMIN2) == "inactive"
        events = _audit("user.activate_denied", ADMIN2)
        assert len(events) == 1
        assert events[0]["details_json"] == {"reason": "exceeds_actor_permissions"}

        allowed = client.post(f"{_ID}/users/{ADMIN2}/activate", headers=_auth(ADMIN1))
        assert allowed.status_code == 200, allowed.text
        assert _status(ADMIN2) == "active"

    def test_security_admin_reactivates_scoped_advertiser(self, client):
        _owner_sql(
            "UPDATE users SET status = 'inactive' WHERE id = :u", {"u": ADVERTISER}, fetch=False,
        )
        resp = client.post(f"{_ID}/users/{ADVERTISER}/activate", headers=_auth(SECADM))
        assert resp.status_code == 200, resp.text

    def test_creating_an_advertiser_is_an_accepted_exception(self, client):
        """users.manage may create an advertiser although the advertiser role
        carries permissions a security_admin lacks: the role is fixed and
        scoped, so the new account holds no global permission."""
        resp = client.post(
            f"{_ID}/users/local-advertiser",
            json={
                "username": "beh-022-created", "display_name": "Beh 022 created",
                "advertiser_organization_id": _ORG, "auto_generate_password": True,
            },
            headers=_auth(SECADM),
        )
        assert resp.status_code == 201, resp.text
        created = resp.json()["user_id"]
        assert [(a["code"], a["scope_type"]) for a in _assignments(created)] == [
            ("advertiser", "advertiser"),
        ]
        denied = client.get(f"{_ID}/users", headers=_auth(created))
        assert denied.status_code == 403, denied.text


class TestConcurrentLastAdmin:
    """Two admins acting on each other at once must not leave zero admins."""

    @staticmethod
    def _race(app, calls):
        async def _one(method, path, actor):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport, base_url="http://testserver",
            ) as ac:
                return await ac.request(method, path, headers=_auth(actor))

        async def _all():
            return await asyncio.gather(*[_one(*c) for c in calls])

        return asyncio.run(_all())

    def _active_admins(self) -> int:
        return _owner_sql(
            "SELECT count(DISTINCT u.id) AS n FROM users u "
            "JOIN user_roles ur ON ur.user_id = u.id JOIN roles r ON r.id = ur.role_id "
            "WHERE u.status = 'active' AND r.code = 'system_admin' AND ur.scope_type IS NULL"
        )[0]["n"]

    def test_concurrent_role_removal_keeps_one_admin(self, app, client, only_test_admins):
        results = self._race(app, [
            ("DELETE", f"{_ID}/users/{ADMIN2}/roles/ur-022-admin2", ADMIN1),
            ("DELETE", f"{_ID}/users/{ADMIN1}/roles/ur-022-admin1", ADMIN2),
        ])
        assert sorted(r.status_code for r in results) == [204, 409], [r.text for r in results]
        assert self._active_admins() == 1

    def test_concurrent_deactivation_keeps_one_admin(self, app, client, only_test_admins):
        results = self._race(app, [
            ("POST", f"{_ID}/users/{ADMIN2}/deactivate", ADMIN1),
            ("POST", f"{_ID}/users/{ADMIN1}/deactivate", ADMIN2),
        ])
        assert sorted(r.status_code for r in results) == [200, 409], [r.text for r in results]
        assert self._active_admins() == 1

    def test_concurrent_removal_and_deactivation_keep_one_admin(
        self, app, client, only_test_admins,
    ):
        results = self._race(app, [
            ("DELETE", f"{_ID}/users/{ADMIN2}/roles/ur-022-admin2", ADMIN1),
            ("POST", f"{_ID}/users/{ADMIN1}/deactivate", ADMIN2),
        ])
        removal, deactivation = (r.status_code for r in results)
        # Deactivation first: ADMIN1 is disabled, then its role removal hits
        # the last-admin guard. Removal first: ADMIN2 no longer outranks
        # anyone, so its deactivation of ADMIN1 is refused.
        assert (removal, deactivation) in ((409, 200), (204, 403)), [
            r.text for r in results
        ]
        assert self._active_admins() == 1
