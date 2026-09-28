"""
Behavioral tests - RM-STAB-018 (OD-046): refresh-token replay detection and
atomic rotation, against real PostgreSQL as the NOBYPASSRLS app role.

- A rotated token presented again after the reuse grace window revokes the
  whole token family, writes ``auth.refresh.replay_detected`` and the
  revocation is committed even though the response is 401.
- Inside the grace window (parallel refresh from several portal tabs) the
  replay is rejected without burning the family.
- Concurrent refreshes with one token produce exactly one successor session.

Requires: RUN_BEHAVIORAL_TESTS=1, running PostgreSQL, migrations + seed applied.
"""

import asyncio

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from packages.security.config import reset_security_config
from packages.security.tokens import hash_token
from tests.behavioral.conftest import _get_setup_engine

_USER = "beh-av-00000000000000000004"
_REFRESH = "/api/v1/auth/refresh"


@pytest.fixture
def client(app, db_available, test_users):
    reset_security_config()
    return TestClient(app)


def _login(client, test_users) -> str:
    resp = client.post("/api/v1/auth/login", json={
        "username_or_email": "beh-advertiser",
        "password": test_users["password"],
        "auth_provider": "local_advertiser",
    })
    assert resp.status_code == 200, resp.text
    cookie = resp.cookies.get("refresh_token")
    assert cookie
    return cookie


def _refresh(client, cookie: str):
    client.cookies.clear()
    client.cookies.set("refresh_token", cookie)
    return client.post(_REFRESH)


def _owner_sql(sql: str, params: dict | None = None, fetch: bool = True):
    """Run SQL as the owner with admin elevation (assertions/setup only)."""

    async def _run():
        async with _get_setup_engine().begin() as conn:
            await conn.execute(text("SELECT set_config('app.rmp_is_admin', 'true', true)"))
            result = await conn.execute(text(sql), params or {})
            return [dict(r._mapping) for r in result] if fetch else None

    return asyncio.run(_run())


def _session_row(cookie: str) -> dict:
    rows = _owner_sql(
        "SELECT id, token_family_id, rotated_at, revoked_at FROM refresh_sessions "
        "WHERE token_hash = :h",
        {"h": hash_token(cookie)},
    )
    assert len(rows) == 1
    return rows[0]


def _family(family_id: str) -> list[dict]:
    return _owner_sql(
        "SELECT id, rotated_at, revoked_at FROM refresh_sessions "
        "WHERE token_family_id = :f ORDER BY issued_at",
        {"f": family_id},
    )


def _age_rotation(session_id: str, seconds: int) -> None:
    _owner_sql(
        "UPDATE refresh_sessions SET rotated_at = now() - make_interval(secs => :s) "
        "WHERE id = :id",
        {"s": seconds, "id": session_id},
        fetch=False,
    )


class TestRefreshReplay:

    def test_replay_after_grace_revokes_family(self, client, test_users):
        old = _login(client, test_users)
        r1 = _refresh(client, old)
        assert r1.status_code == 200, r1.text
        successor = r1.cookies.get("refresh_token")
        assert successor and successor != old

        old_row = _session_row(old)
        _age_rotation(old_row["id"], 60)

        replay = _refresh(client, old)
        assert replay.status_code == 401
        assert replay.json()["detail"]["code"] == "INVALID_TOKEN"

        # Revocation survived the 401 - the successor is dead too.
        family = _family(old_row["token_family_id"])
        assert len(family) == 2
        assert all(row["revoked_at"] is not None for row in family)
        stolen = _refresh(client, successor)
        assert stolen.status_code == 401

        audit = _owner_sql(
            "SELECT actor_user_id, target_id, details_json FROM audit_events_operational "
            "WHERE action = 'auth.refresh.replay_detected' AND target_id = :t",
            {"t": old_row["id"]},
        )
        assert len(audit) == 1
        assert audit[0]["actor_user_id"] == _USER
        assert audit[0]["details_json"]["token_family_id"] == old_row["token_family_id"]
        assert audit[0]["details_json"]["revoked_sessions"] == 2

    def test_replay_detected_after_session_limit_revoked_rotated_row(
        self, client, test_users,
    ):
        """The max-sessions limit on login revokes the oldest rows - rotated
        ones first. Replay of such a row must still burn the live successor."""
        old = _login(client, test_users)
        r1 = _refresh(client, old)
        assert r1.status_code == 200, r1.text
        successor = r1.cookies.get("refresh_token")
        for _ in range(5):
            _login(client, test_users)

        old_row = _session_row(old)
        assert old_row["revoked_at"] is not None
        assert _session_row(successor)["revoked_at"] is None
        _age_rotation(old_row["id"], 60)

        replay = _refresh(client, old)
        assert replay.status_code == 401
        assert _session_row(successor)["revoked_at"] is not None
        audit = _owner_sql(
            "SELECT details_json FROM audit_events_operational "
            "WHERE action = 'auth.refresh.replay_detected' AND target_id = :t",
            {"t": old_row["id"]},
        )
        assert [a["details_json"]["revoked_sessions"] for a in audit] == [1]

    def test_replay_within_grace_keeps_family(self, client, test_users):
        old = _login(client, test_users)
        r1 = _refresh(client, old)
        assert r1.status_code == 200, r1.text
        successor = r1.cookies.get("refresh_token")

        replay = _refresh(client, old)
        assert replay.status_code == 401

        old_row = _session_row(old)
        family = _family(old_row["token_family_id"])
        assert all(row["revoked_at"] is None for row in family)
        audit = _owner_sql(
            "SELECT action, target_id FROM audit_events_operational "
            "WHERE action LIKE 'auth.refresh.%' AND actor_user_id = :u",
            {"u": _USER},
        )
        assert audit == [
            {"action": "auth.refresh.reuse_within_grace", "target_id": old_row["id"]},
        ]

        r2 = _refresh(client, successor)
        assert r2.status_code == 200, r2.text

    def test_concurrent_refresh_yields_one_successor(self, app, client, test_users):
        old = _login(client, test_users)
        family_id = _session_row(old)["token_family_id"]

        async def _one():
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport, base_url="http://testserver",
                cookies={"refresh_token": old},
            ) as ac:
                return await ac.post(_REFRESH)

        async def _race():
            return await asyncio.gather(*[_one() for _ in range(4)])

        statuses = sorted(r.status_code for r in asyncio.run(_race()))
        assert statuses == [200, 401, 401, 401], statuses

        family = _family(family_id)
        assert len(family) == 2, family
        assert all(row["revoked_at"] is None for row in family)

    def test_inactive_user_refresh_revokes_session(self, client, test_users):
        """The USER_INACTIVE revoke is committed before the 401 as well."""
        cookie = _login(client, test_users)
        _owner_sql(
            "UPDATE users SET status = 'disabled' WHERE id = :u", {"u": _USER},
            fetch=False,
        )
        resp = _refresh(client, cookie)
        assert resp.status_code == 401
        assert _session_row(cookie)["revoked_at"] is not None


def _post_concurrently(app, cookies: list[str]):
    async def _one(cookie):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver",
            cookies={"refresh_token": cookie},
        ) as ac:
            return await ac.post(_REFRESH)

    async def _all():
        return await asyncio.gather(*[_one(c) for c in cookies])

    return asyncio.run(_all())


class TestFamilySerialisation:
    """Every operation on one token family is serialised: a family revoke can
    neither miss a successor issued concurrently nor deadlock with another."""

    def _chain(self, client, test_users, length: int) -> list[str]:
        tokens = [_login(client, test_users)]
        for _ in range(length - 1):
            resp = _refresh(client, tokens[-1])
            assert resp.status_code == 200, resp.text
            tokens.append(resp.cookies.get("refresh_token"))
        return tokens

    def test_two_replays_in_one_family_do_not_deadlock(self, app, client, test_users):
        for _ in range(10):
            t1, t2, _t3 = self._chain(client, test_users, 3)
            _age_rotation(_session_row(t1)["id"], 60)
            _age_rotation(_session_row(t2)["id"], 60)

            statuses = sorted(r.status_code for r in _post_concurrently(app, [t1, t2]))
            assert statuses == [401, 401], statuses
            family = _family(_session_row(t1)["token_family_id"])
            assert all(row["revoked_at"] is not None for row in family), family

    def test_replay_racing_live_refresh_leaves_no_survivor(self, app, client, test_users):
        for _ in range(10):
            stolen, live = self._chain(client, test_users, 2)
            _age_rotation(_session_row(stolen)["id"], 60)

            statuses = {r.status_code for r in _post_concurrently(app, [stolen, live])}
            assert statuses <= {200, 401}, statuses
            family = _family(_session_row(stolen)["token_family_id"])
            survivors = [row for row in family if row["revoked_at"] is None]
            assert survivors == [], family
