"""Regression: smoke-user cleanup deletes ONLY smoke-owned users.

Locks the safety contract of the UI-smoke session cleanup fixture:

* smoke-owned usernames (``smoke*`` / ``selogin*``) are deleted,
* seed users and non-smoke users are preserved,
* fail-closed outside ``UI_SMOKE_RUN``,
* FK-safe statement ordering (children before ``users``).

The DB-backed test executes the *same* SQL the conftest fixture runs (via
``smoke_cleanup.smoke_delete_statements()``), so the cleanup cannot drift from
its guard.
"""
import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ui-smoke"))
import smoke_cleanup  # noqa: E402


# ── Pure / no-DB tests (always run) ─────────────────────────────────────────


def test_is_smoke_owned_username_matches_smoke_prefixes():
    for name in (
        "smoke_adv_abcd1234",
        "smoke-reset-x",
        "smoke_deact_12345678",
        "selogin-123@example.com",
    ):
        assert smoke_cleanup.is_smoke_owned_username(name), name


def test_is_smoke_owned_username_rejects_seed_and_real_users():
    for name in (
        "break_glass_admin",
        "advertiser_test",
        "local_advertiser",
        "system_admin",
        "operator",
        "ivanov",
        "alice@example.com",
        "ООО Логин",
        None,
        "",
    ):
        assert not smoke_cleanup.is_smoke_owned_username(name), repr(name)


def test_smoke_where_clause_scopes_to_smoke_only():
    where = smoke_cleanup.smoke_where_clause()
    assert "username LIKE 'smoke%'" in where
    assert "username LIKE 'selogin%'" in where
    assert "break_glass" not in where
    assert "advertiser_test" not in where


def test_smoke_delete_statements_are_fk_safe_ordered():
    stmts = smoke_cleanup.smoke_delete_statements()
    tables = [t for t, _ in stmts]
    assert tables[-1] == "users", "users must be deleted last"
    for child in (
        "refresh_sessions",
        "password_reset_tokens",
        "audit_events_operational",
        "advertiser_invites",
        "advertiser_user_memberships",
        "user_access_scopes",
        "user_roles",
        "local_credentials",
    ):
        assert child in tables
        assert tables.index(child) < tables.index("users"), child
    # advertiser_invites FK column is accepted_by_user_id, not accepted_by
    invites_sql = dict(stmts)["advertiser_invites"]
    assert "accepted_by_user_id" in invites_sql


def test_delete_smoke_users_is_fail_closed(monkeypatch):
    monkeypatch.delenv("UI_SMOKE_RUN", raising=False)
    with pytest.raises(RuntimeError, match="fail-closed"):
        smoke_cleanup.delete_smoke_users("postgresql://user:pass@localhost/db")


# ── DB-backed test (behavioral job, real Postgres) ──────────────────────────


@pytest.mark.skipif(
    not (
        os.environ.get("RUN_BEHAVIORAL_TESTS")
        and os.environ.get("BEHAVIORAL_DB_URL")
    ),
    reason="requires RUN_BEHAVIORAL_TESTS + BEHAVIORAL_DB_URL (behavioral job)",
)
def test_delete_smoke_users_deletes_smoke_preserves_seed_and_nonsmoke():
    from sqlalchemy import create_engine, text

    url = os.environ["BEHAVIORAL_DB_URL"].replace("+asyncpg", "")
    engine = create_engine(url, echo=False)

    suffix = uuid.uuid4().hex[:8]
    smoke_user = f"smoke_cln_{suffix}"
    nonsmoke_user = f"keep_cln_{suffix}"
    seed_user = "break_glass_admin"

    def _insert(username: str, code: str) -> None:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO users (id, code, username, display_name, auth_provider, status, is_break_glass) "
                    "VALUES (:id, :code, :username, :dn, 'local', 'active', false) "
                    "ON CONFLICT (username) DO NOTHING"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "code": code,
                    "username": username,
                    "dn": "smoke-cleanup-regression",
                },
            )

    def _exists(username: str) -> bool:
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT 1 FROM users WHERE username = :u"), {"u": username}
            ).fetchone()
        return row is not None

    try:
        _insert(smoke_user, f"SMOKE_CLN_{suffix}")
        _insert(nonsmoke_user, f"KEEP_CLN_{suffix}")

        # Precondition: seed user exists, so "preserved" is a meaningful check.
        assert _exists(seed_user), f"seed user {seed_user} missing — cannot verify preservation"
        assert _exists(smoke_user), "smoke user insert failed"
        assert _exists(nonsmoke_user), "non-smoke user insert failed"

        # Execute the exact production DELETE statements the fixture runs.
        with engine.begin() as conn:
            for _table, sql in smoke_cleanup.smoke_delete_statements():
                conn.execute(text(sql))

        assert not _exists(smoke_user), "smoke-owned user was NOT deleted"
        assert _exists(nonsmoke_user), "non-smoke user was deleted (over-broad marker)"
        assert _exists(seed_user), "seed user was deleted (over-broad marker)"
    finally:
        with engine.begin() as conn:
            conn.execute(
                text("DELETE FROM users WHERE username IN (:a, :b)"),
                {"a": smoke_user, "b": nonsmoke_user},
            )
        engine.dispose()
