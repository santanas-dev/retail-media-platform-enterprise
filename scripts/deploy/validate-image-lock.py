#!/usr/bin/env python3
"""Validate the pilot image lock manifest (PILOT-DEPLOYMENT-READINESS-001B, SCOPE C).

Enforces immutable image references.  A valid lock manifest must satisfy:

- every image has a non-empty, sha256:-prefixed ``image_digest``;
- no ``latest`` or otherwise mutable tags;
- a single, consistent ``git_sha`` and ``version`` across all images AND
  matching the top-level ``release`` block (no mixed SHAs);
- the service set matches the pilot compose's packaged services (exact list
  passed via ``--services`` or the default PILOT_SERVICES);
- repository refs are not empty and do not contain ``:latest``.

Exit code 0 = valid; 1 = validation errors.  Prints a per-image summary.

Usage:
    python scripts/deploy/validate-image-lock.py [--lock PATH] [--services a,b,c]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Services the pilot compose packages as first-class runtime/static services.
# (postgres/redis/minio are infra and reference registry images directly.)
DEFAULT_SERVICES = [
    "control-api",
    "device-gateway",
    "orchestrator-worker",
    "admin-web",
    "advertiser-web",
]

# A real content digest must look like sha256:<hex>.  Placeholders and empty
# values are rejected.
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_PLACEHOLDER_RE = re.compile(r"REPLACE_WITH|TODO|EXAMPLE|PLACEHOLDER", re.IGNORECASE)

_MUTABLE_TAGS = {"latest", "dev", "develop", "main", "master"}


def _fail(errors: list[str], msg: str) -> None:
    errors.append(msg)


def validate(lock: dict, services: list[str]) -> list[str]:
    errors: list[str] = []

    if not isinstance(lock, dict):
        return ["lock manifest is not a JSON object"]

    release = lock.get("release") or {}
    images = lock.get("images")
    if not isinstance(images, list) or not images:
        _fail(errors, "lock manifest must contain a non-empty 'images' list")
        return errors

    release_version = (release.get("version") or "").strip()
    release_sha = (release.get("git_sha") or "").strip()

    # Reject placeholder / missing release identity
    if not release_version or _PLACEHOLDER_RE.search(release_version):
        _fail(errors, "release.version is missing or a placeholder")
    if not release_sha or _PLACEHOLDER_RE.search(release_sha) or len(release_sha) != 40:
        _fail(errors, "release.git_sha is missing/placeholder/not a 40-char SHA")

    seen_services: set[str] = set()
    seen_shas: set[str] = set()
    seen_versions: set[str] = set()
    seen_repos: set[str] = set()

    for i, img in enumerate(images):
        where = f"images[{i}]"
        if not isinstance(img, dict):
            _fail(errors, f"{where}: not an object")
            continue

        service = (img.get("service") or "").strip()
        repo = (img.get("repository") or "").strip()
        version = (img.get("version") or "").strip()
        sha = (img.get("git_sha") or "").strip()
        digest = (img.get("image_digest") or "").strip()
        source_tag = (img.get("source_tag") or "").strip()

        # service
        if not service:
            _fail(errors, f"{where}: missing 'service'")
        elif service not in services:
            _fail(errors, f"{where}: service '{service}' not in pilot service list {services}")
        if service in seen_services:
            _fail(errors, f"{where}: duplicate service '{service}'")
        seen_services.add(service)

        # repository
        if not repo:
            _fail(errors, f"{where}: missing 'repository'")
        elif repo.endswith(":latest") or repo.rsplit(":", 1)[-1] in _MUTABLE_TAGS:
            _fail(errors, f"{where}: repository '{repo}' uses a mutable tag")
        if repo in seen_repos:
            _fail(errors, f"{where}: duplicate repository '{repo}'")
        seen_repos.add(repo)

        # digest — the core immutability guarantee
        if not digest:
            _fail(errors, f"{where}: empty image_digest (must be sha256:<hex>)")
        elif _PLACEHOLDER_RE.search(digest):
            _fail(errors, f"{where}: image_digest is a placeholder, not a real digest")
        elif not _DIGEST_RE.match(digest):
            _fail(errors, f"{where}: image_digest '{digest}' is not a valid sha256:<hex> digest")

        # version / git_sha consistency
        if not version or _PLACEHOLDER_RE.search(version):
            _fail(errors, f"{where}: version is missing or a placeholder")
        if not sha or _PLACEHOLDER_RE.search(sha) or len(sha) != 40:
            _fail(errors, f"{where}: git_sha is missing/placeholder/not 40-char")
        seen_shas.add(sha)
        seen_versions.add(version)

        # source_tag must not be mutable
        if source_tag and (source_tag in _MUTABLE_TAGS or source_tag.endswith(":latest")):
            _fail(errors, f"{where}: source_tag '{source_tag}' is mutable")

        print(f"  OK   {service:22} {repo}@sha256:...{digest[-12:]}")

    # Cross-image consistency — no mixed SHAs or versions
    if len(seen_shas) > 1:
        _fail(errors, f"mixed git SHAs across images: {sorted(seen_shas)}")
    if len(seen_versions) > 1:
        _fail(errors, f"mixed versions across images: {sorted(seen_versions)}")
    if release_sha and seen_shas and release_sha not in seen_shas:
        _fail(errors, f"release.git_sha '{release_sha}' does not match image git_sha {sorted(seen_shas)}")
    if release_version and seen_versions and release_version not in seen_versions:
        _fail(errors, f"release.version '{release_version}' does not match image versions {sorted(seen_versions)}")

    # Service set completeness — lock must cover exactly the packaged services
    missing = set(services) - seen_services
    if missing:
        _fail(errors, f"lock manifest missing services: {sorted(missing)}")
    extra = seen_services - set(services)
    if extra:
        _fail(errors, f"lock manifest has services not in pilot list: {sorted(extra)}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", default="infra/deploy/images.lock.json",
                        help="path to lock manifest JSON")
    parser.add_argument("--services", default=None,
                        help="comma-separated service list (default: PILOT_SERVICES)")
    args = parser.parse_args()

    services = [s.strip() for s in (args.services or "").split(",") if s.strip()] \
        if args.services else DEFAULT_SERVICES

    lock_path = Path(args.lock)
    if not lock_path.exists():
        print(f"FAIL: lock manifest not found: {lock_path}", file=sys.stderr)
        return 1

    try:
        lock = json.loads(lock_path.read_text())
    except json.JSONDecodeError as e:
        print(f"FAIL: lock manifest is not valid JSON: {e}", file=sys.stderr)
        return 1

    print(f"=== Validating image lock: {lock_path} ===")
    print(f"=== Expected services: {services} ===")
    errors = validate(lock, services)

    print()
    if errors:
        for e in errors:
            print(f"  ERROR: {e}")
        print(f"=== Validation FAILED ({len(errors)} errors) ===")
        return 1

    print("=== Validation PASSED — all image refs immutable & consistent ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
