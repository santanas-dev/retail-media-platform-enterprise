"""Pure check helpers for the restore drill (SCOPE F / SCOPE G).

Dependency-free, deterministic functions so the negative matrix can be
unit-tested without a database or MinIO. Each returns a list of violation
messages (empty = pass).
"""

from __future__ import annotations

from typing import Any


def check_alembic_head(actual: str, expected: str) -> list[str]:
    """Wrong alembic head → refuse acceptance (SCOPE G #7)."""
    if not expected:
        return ["expected alembic head is empty — cannot verify"]
    if actual != expected:
        return [f"alembic head mismatch: expected {expected!r}, got {actual!r}"]
    return []


def check_app_role_nobypassrls(rolsuper: bool, rolbypassrls: bool) -> list[str]:
    """Runtime app role must NOT be superuser and must NOT have BYPASSRLS (SCOPE G #8)."""
    problems: list[str] = []
    if rolsuper:
        problems.append("app role is superuser — refuse acceptance")
    if rolbypassrls:
        problems.append("app role has BYPASSRLS — refuse acceptance")
    return problems


def check_production_encryption(environment: str, encryption_enabled: bool) -> list[str]:
    """Production mode without encryption configuration → fail closed (SCOPE G #10)."""
    if environment == "production" and not encryption_enabled:
        return ["production backup requires encryption (encryption_enabled=false) — fail closed"]
    return []


def check_money_exact(
    actual: Any, expected: Any, label: str,
) -> list[str]:
    """Commerce money values must be exact (SCOPE F). Uses Decimal-aware compare."""
    from decimal import Decimal

    try:
        a = Decimal(str(actual))
        e = Decimal(str(expected))
    except Exception:
        return [f"{label}: non-numeric value actual={actual!r} expected={expected!r}"]
    if a != e:
        return [f"{label}: money mismatch actual={a} expected={e}"]
    return []


def check_license_peak(open_seats: int, released_seats: int, expected_peak: int) -> list[str]:
    """Exact peak = open + released historical intervals (SCOPE F)."""
    peak = open_seats + released_seats
    if peak != expected_peak:
        return [f"license seat peak mismatch: got {peak}, expected {expected_peak}"]
    return []
