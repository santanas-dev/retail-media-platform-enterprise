"""Retail Media Platform — immutable version identity (PILOT-DEPLOYMENT-READINESS-001B).

Single source of truth for build/deploy metadata exposed via ``GET /version``.

Values are **injected at build/deploy time** through environment variables
(RMP_VERSION, RMP_GIT_SHA, RMP_BUILD_TIME, RMP_SCHEMA_HEAD).  This module:

- never invokes ``git``;
- never reads the working directory or filesystem;
- never returns secrets, host paths, or an environment dump.

Fail-closed policy:
- In pilot/production/staging, missing RMP_VERSION / RMP_GIT_SHA /
  RMP_BUILD_TIME raises RuntimeError (the version endpoint then returns 503).
- In dev/test, missing values fall back to honest ``dev`` / ``unknown`` —
  never a production-looking identity.
"""

from __future__ import annotations

import os

# Environments where build metadata is mandatory (fail-closed).
_STRICT_ENVIRONMENTS = ("production", "prod", "staging", "pilot")

# Explicitly dev-like environments (honest fallback allowed).
_DEV_ENVIRONMENTS = ("dev", "development", "local", "test")


def _env(name: str) -> str:
    """Read an env var, stripped. Empty string means 'unset'."""
    return os.environ.get(name, "").strip()


def environment_name() -> str:
    """Return the normalized environment name (lowercase)."""
    env = _env("ENVIRONMENT").lower()
    if not env:
        # Unset ENVIRONMENT: infer.  Under pytest → test; otherwise dev.
        if _env("PYTEST_CURRENT_TEST"):
            return "test"
        return "dev"
    return env


def is_strict_environment() -> bool:
    """True when build metadata is mandatory (pilot/prod/staging)."""
    return environment_name() in _STRICT_ENVIRONMENTS


def build_version_payload(service: str) -> dict:
    """Return the version payload for a service, or raise RuntimeError.

    ``service`` is the RMP service name (control-api, device-gateway, …).
    In strict environments, missing version/git_sha/build_time is fatal.
    In dev/test, they fall back to honest dev/unknown placeholders.
    """
    env = environment_name()
    strict = env in _STRICT_ENVIRONMENTS

    version = _env("RMP_VERSION")
    git_sha = _env("RMP_GIT_SHA")
    build_time = _env("RMP_BUILD_TIME")
    schema_head = _env("RMP_SCHEMA_HEAD")  # optional — service-specific

    missing: list[str] = []
    for name, value in (
        ("RMP_VERSION", version),
        ("RMP_GIT_SHA", git_sha),
        ("RMP_BUILD_TIME", build_time),
    ):
        if not value:
            missing.append(name)

    if strict and missing:
        raise RuntimeError(
            "build metadata missing in strict environment "
            f"(environment={env}): {', '.join(missing)}"
        )

    if not strict:
        version = version or "dev"
        git_sha = git_sha or "unknown"
        build_time = build_time or "unknown"

    return {
        "service": service,
        "version": version,
        "git_sha": git_sha,
        "build_time": build_time,
        "schema_head": schema_head or None,
        "environment": env,
    }


# Fields a version payload is expected to carry (for validation elsewhere).
VERSION_FIELDS = (
    "service",
    "version",
    "git_sha",
    "build_time",
    "schema_head",
    "environment",
)
