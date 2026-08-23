#!/usr/bin/env python3
"""Validate a pilot environment file (PILOT-DEPLOYMENT-READINESS-001B, SCOPE E).

Rejects dev defaults, weak/short secrets, and dev-only flags in pilot/production.
Reads KEY=VALUE lines from a dotenv-style file (no interpolation, no source).

Exit 0 = valid; 1 = errors.  Never prints secret values (only names + redacted
length/prefix class).

Usage:
    python scripts/deploy/validate-pilot-env.py [--env PATH]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

DEFAULT_ENV = "infra/deploy/.env.pilot"

# Values that are hard-rejected anywhere (dev defaults / weak secrets).
_REJECTED_EXACT = {
    "minioadmin",
    "retail_media_owner_pass",
    "retail_media_app_pass",
    "dev-secret-do-not-use-in-production",
    "dev-manifest-signing-key-at-least-32-chars",
    "change_me",
    "changeme",
    "password",
    "secret",
    "test",
}

_WEAK_SUBSTRINGS = ("REPLACE_WITH", "EXAMPLE", "TODO", "PLACEHOLDER")

# Minimum lengths for secrets.
_MIN_SECRET_LEN = 32
_MIN_METRICS_TOKEN_LEN = 16

# Secret-like variable names that must not be empty/weak/short.
_SECRET_KEYS = {
    "POSTGRES_OWNER_PASSWORD",
    "POSTGRES_APP_PASSWORD",
    "JWT_SECRET",
    "MANIFEST_SIGNING_KEY",
    "MINIO_ROOT_PASSWORD",
    "MINIO_SECRET_KEY",
    "MINIO_ACCESS_KEY",
    "METRICS_AUTH_TOKEN",
}

# Variable names whose value must be a strong URL/password (not localhost/dev).
_DEV_FORBIDDEN_URLS = ("DATABASE_URL", "MIGRATION_DATABASE_URL")

# Flags that must be explicitly false in pilot.
_MUST_BE_FALSE = ("SEED_DEV_CREDENTIALS", "LICENSE_DEV_INGEST_ENABLED")


def _parse_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip()
    return env


def _redact(value: str) -> str:
    if len(value) <= 4:
        return "<len %d>" % len(value)
    return f"<len {len(value)}>"


def _url_password(url: str) -> str:
    """Extract the password portion of a postgres URL, or '' if none."""
    try:
        auth = url.split("@")[0] if "@" in url else ""
        return auth.rsplit(":", 1)[-1] if ":" in auth else ""
    except Exception:
        return ""


def validate(env: dict[str, str]) -> list[str]:
    errors: list[str] = []

    environment = env.get("ENVIRONMENT", "").lower()
    if environment not in ("pilot", "production", "staging"):
        errors.append(
            f"ENVIRONMENT must be 'pilot'/'production'/'staging', got '{environment or '(unset)'}'"
        )

    # Version identity — mandatory in pilot
    for key in ("RMP_VERSION", "RMP_GIT_SHA"):
        val = env.get(key, "")
        if not val or any(w in val.upper() for w in _WEAK_SUBSTRINGS):
            errors.append(f"{key} missing or placeholder")
    git_sha = env.get("RMP_GIT_SHA", "")
    if git_sha and not re.fullmatch(r"[0-9a-f]{40}", git_sha):
        errors.append(f"RMP_GIT_SHA is not a 40-char hex SHA")

    # Secret values — not empty, not weak, not short, not placeholder
    for key in _SECRET_KEYS:
        val = env.get(key, "")
        low = val.lower().strip()
        if not val:
            errors.append(f"{key} is empty")
            continue
        if any(w in val.upper() for w in _WEAK_SUBSTRINGS):
            errors.append(f"{key} is a placeholder ({_redact(val)})")
        if low in _REJECTED_EXACT:
            errors.append(f"{key} uses a forbidden dev/weak value ({_redact(val)})")
        if key == "METRICS_AUTH_TOKEN":
            if len(val) < _MIN_METRICS_TOKEN_LEN:
                errors.append(f"{key} too short ({_redact(val)})")
        else:
            if len(val) < _MIN_SECRET_LEN:
                errors.append(f"{key} too short ({_redact(val)})")

    # DB URLs — no localhost, no dev passwords
    for key in _DEV_FORBIDDEN_URLS:
        val = env.get(key, "")
        if not val:
            errors.append(f"{key} is empty")
            continue
        low = val.lower()
        if any(h in low for h in ("localhost", "127.0.0.1", "0.0.0.0", "[::1]")):
            errors.append(f"{key} uses a localhost address ({_redact(val)})")
        # Check only the password portion, not the host (host may legitimately
        # be named 'postgres').
        password = _url_password(val)
        if password in ("retail_media_owner_pass", "retail_media_app_pass", "postgres"):
            errors.append(f"{key} contains a known dev password")
        if any(w in val.upper() for w in _WEAK_SUBSTRINGS):
            errors.append(f"{key} is a placeholder ({_redact(val)})")

    # CORS — no wildcard, no localhost
    cors = env.get("CORS_ALLOWED_ORIGINS", "")
    if not cors:
        errors.append("CORS_ALLOWED_ORIGINS is empty")
    else:
        for origin in [o.strip() for o in cors.split(",") if o.strip()]:
            low = origin.lower()
            if origin == "*":
                errors.append("CORS_ALLOWED_ORIGINS contains wildcard '*'")
            elif any(h in low for h in ("localhost", "127.0.0.1", "0.0.0.0", "[::1]")):
                errors.append(f"CORS_ALLOWED_ORIGINS contains a dev origin ({origin})")
        if any(w in cors.upper() for w in _WEAK_SUBSTRINGS):
            errors.append("CORS_ALLOWED_ORIGINS is a placeholder")

    # Dev-only flags must be false
    for key in _MUST_BE_FALSE:
        val = env.get(key, "").lower()
        if val in ("true", "1", "yes"):
            errors.append(f"{key} must be false in pilot (got '{val}')")

    # MinIO public endpoint must not be empty/placeholder
    minio_pub = env.get("MINIO_PUBLIC_ENDPOINT", "")
    if not minio_pub or any(w in minio_pub.upper() for w in _WEAK_SUBSTRINGS):
        errors.append("MINIO_PUBLIC_ENDPOINT is empty or placeholder")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", default=DEFAULT_ENV, help="path to env file")
    args = parser.parse_args()

    path = Path(args.env)
    if not path.exists():
        print(f"FAIL: env file not found: {path}", file=sys.stderr)
        return 1

    env = _parse_env(path)
    errors = validate(env)

    print(f"=== Validating pilot env: {path} ===")
    print(f"=== {len(env)} variables parsed ===")
    if errors:
        for e in errors:
            print(f"  ERROR: {e}")
        print(f"=== Validation FAILED ({len(errors)} errors) ===")
        return 1
    print("=== Validation PASSED — no dev defaults, secrets strong ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
