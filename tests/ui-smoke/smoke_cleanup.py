"""Smoke-user cleanup — single source of truth for test-owned user deletion.

The UI-smoke suite creates ``smoke_*`` / ``selogin-*`` users on a long-lived DB.
This module defines which usernames are smoke-owned, builds the FK-safe DELETE
statements, and (fail-closed) executes them via ``psql``.

Shared by the conftest session fixture and the behavioral regression test
(``tests/behavioral/test_smoke_cleanup_safety.py``) so the fixture's *actual*
SQL is what gets tested — no drift between the cleanup and its guard.
"""
from __future__ import annotations

import os
import subprocess

# Username prefixes that mark a user as owned by the UI-smoke suite. Every smoke
# test MUST create users with one of these prefixes. Seed users
# (`break_glass_admin`, `advertiser_test`) and real DEV/local users never match.
SMOKE_USERNAME_PREFIXES = ("smoke", "selogin")

# FK-safe delete order. All `users` FKs are ON DELETE NO ACTION, so children are
# deleted before `users`. `advertiser_invites` references users via
# `accepted_by_user_id` (NOT `accepted_by`) — see enterprise-ui-smoke-stability.md.
_CHILD_FK_COLUMNS = (
    ("refresh_sessions", "user_id"),
    ("password_reset_tokens", "user_id"),
    ("audit_events_operational", "actor_user_id"),
    ("advertiser_invites", "accepted_by_user_id"),
    ("advertiser_user_memberships", "user_id"),
    ("user_access_scopes", "user_id"),
    ("user_roles", "user_id"),
    ("local_credentials", "user_id"),
)


def is_smoke_owned_username(username: str | None) -> bool:
    """True iff ``username`` is owned by the smoke suite (matches a smoke prefix)."""
    return bool(username) and username.startswith(SMOKE_USERNAME_PREFIXES)


def smoke_where_clause() -> str:
    """SQL predicate selecting smoke-owned users. Parameter-free, psql-safe."""
    return " OR ".join(f"username LIKE '{p}%'" for p in SMOKE_USERNAME_PREFIXES)


def smoke_delete_statements() -> list[tuple[str, str]]:
    """Ordered ``(table, sql)`` DELETE statements for FK-safe smoke-user removal."""
    where = smoke_where_clause()
    stmts = [
        (t, f"DELETE FROM {t} WHERE {col} IN (SELECT id FROM users WHERE {where})")
        for t, col in _CHILD_FK_COLUMNS
    ]
    stmts.append(("users", f"DELETE FROM users WHERE {where}"))
    return stmts


def _psql_delete_count(psql_bin: str, url: str, sql: str) -> int:
    proc = subprocess.run([psql_bin, url, "-c", sql], capture_output=True, text=True)
    if proc.returncode != 0:
        # Never silently swallow FK failures (see enterprise-ui-smoke-stability.md
        # gotcha — capture_output=True hides the error otherwise).
        raise RuntimeError(f"psql DELETE failed: {proc.stderr.strip()}")
    for line in proc.stdout.splitlines():
        if line.strip().upper().startswith("DELETE"):
            parts = line.strip().split()
            if len(parts) >= 2 and parts[1].isdigit():
                return int(parts[1])
    return 0


def delete_smoke_users(db_url: str, psql_bin: str = "psql") -> dict[str, int]:
    """Delete smoke-owned users (and FK children) via psql; return row counts.

    Fail-closed: raises RuntimeError unless ``UI_SMOKE_RUN`` is set — this must
    never run against a non-test database. Logs only per-table row counts, never
    credentials.
    """
    if not os.environ.get("UI_SMOKE_RUN"):
        raise RuntimeError(
            "smoke-user cleanup is disabled outside UI_SMOKE_RUN (fail-closed)"
        )
    clean_url = db_url.replace("+asyncpg", "")
    counts: dict[str, int] = {}
    for table, sql in smoke_delete_statements():
        counts[table] = _psql_delete_count(psql_bin, clean_url, sql)
    return counts
