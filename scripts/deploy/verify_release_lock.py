#!/usr/bin/env python3
"""Verify the immutable pilot image release lock (IMAGE-REGISTRY-001, SCOPE D/E/F).

Self-contained extended verifier over the release lock produced by
``generate_release_lock.py``. Reimplements the core immutability invariants and
adds the extended release checks (schema version, platform, compose-service
mapping, OCI metadata, SBOM/provenance status).

Exit 0 = valid; 1 = errors. Pure ``verify()`` is importable for tests.

Usage:
    python scripts/deploy/verify_release_lock.py --lock images.<tag>.lock.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SUPPORTED_SCHEMA_VERSIONS = {"1.0", "1.1"}
VALID_PLATFORMS = {"linux/amd64"}
VALID_SBOM_STATUS = {"attested", "not-supported"}
VALID_PROVENANCE_STATUS = {"attested", "not-supported"}
_MUTABLE_TAGS = {"latest", "dev", "develop", "main", "master"}
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_PLACEHOLDER_RE = re.compile(r"REPLACE_WITH|TODO|EXAMPLE|PLACEHOLDER", re.IGNORECASE)

DEFAULT_SERVICES = [
    "control-api",
    "device-gateway",
    "orchestrator-worker",
    "admin-web",
    "advertiser-web",
]


def verify(lock: dict, services: list[str] | None = None) -> list[str]:
    """Return a list of validation errors (empty = valid)."""
    services = services or DEFAULT_SERVICES
    errors: list[str] = []

    if not isinstance(lock, dict):
        return ["lock manifest is not a JSON object"]

    # --- Core immutability invariants ---
    release = lock.get("release") or {}
    images = lock.get("images")
    if not isinstance(images, list) or not images:
        errors.append("lock manifest must contain a non-empty 'images' list")
        return errors

    release_version = (release.get("version") or "").strip()
    release_sha = (release.get("git_sha") or "").strip()
    if not release_version or _PLACEHOLDER_RE.search(release_version):
        errors.append("release.version is missing or a placeholder")
    if not release_sha or _PLACEHOLDER_RE.search(release_sha) or len(release_sha) != 40:
        errors.append("release.git_sha is missing/placeholder/not a 40-char SHA")

    seen_services: set[str] = set()
    seen_shas: set[str] = set()
    seen_versions: set[str] = set()
    seen_repos: set[str] = set()

    for i, img in enumerate(images):
        where = f"images[{i}]"
        if not isinstance(img, dict):
            errors.append(f"{where}: not an object")
            continue

        service = (img.get("service") or "").strip()
        repo = (img.get("repository") or "").strip()
        version = (img.get("version") or "").strip()
        sha = (img.get("git_sha") or "").strip()
        digest = (img.get("image_digest") or "").strip()
        source_tag = (img.get("source_tag") or "").strip()

        if not service:
            errors.append(f"{where}: missing 'service'")
        elif service not in services:
            errors.append(f"{where}: service '{service}' not in pilot service list {services}")
        if service in seen_services:
            errors.append(f"{where}: duplicate service '{service}'")
        seen_services.add(service)

        if not repo:
            errors.append(f"{where}: missing 'repository'")
        elif repo.rsplit(":", 1)[-1] in _MUTABLE_TAGS or repo.endswith(":latest"):
            errors.append(f"{where}: repository '{repo}' uses a mutable tag")
        if repo in seen_repos:
            errors.append(f"{where}: duplicate repository '{repo}'")
        seen_repos.add(repo)

        if not digest:
            errors.append(f"{where}: empty image_digest (must be sha256:<hex>)")
        elif _PLACEHOLDER_RE.search(digest):
            errors.append(f"{where}: image_digest is a placeholder, not a real digest")
        elif not _DIGEST_RE.match(digest):
            errors.append(f"{where}: image_digest '{digest}' is not a valid sha256:<hex> digest")

        if not version or _PLACEHOLDER_RE.search(version):
            errors.append(f"{where}: version is missing or a placeholder")
        if not sha or _PLACEHOLDER_RE.search(sha) or len(sha) != 40:
            errors.append(f"{where}: git_sha is missing/placeholder/not 40-char")
        seen_shas.add(sha)
        seen_versions.add(version)

        if source_tag and (source_tag in _MUTABLE_TAGS or source_tag.endswith(":latest")):
            errors.append(f"{where}: source_tag '{source_tag}' is mutable")

        # --- extended per-image checks ---
        img_platform = (img.get("platform") or "").strip()
        if img_platform and img_platform not in VALID_PLATFORMS:
            errors.append(f"{where}: platform '{img_platform}' not in {sorted(VALID_PLATFORMS)}")

        oci = img.get("oci") or {}
        for key in ("version", "revision", "source", "created"):
            if not (oci.get(key) or "").strip():
                errors.append(f"{where}: oci.{key} is missing")

        sbom = (img.get("sbom") or "").strip()
        if sbom not in VALID_SBOM_STATUS:
            errors.append(f"{where}: sbom '{sbom}' not in {sorted(VALID_SBOM_STATUS)}")
        prov = (img.get("provenance") or "").strip()
        if prov not in VALID_PROVENANCE_STATUS:
            errors.append(f"{where}: provenance '{prov}' not in {sorted(VALID_PROVENANCE_STATUS)}")

        img_tag = (img.get("release_tag") or "").strip()
        top_tag = (release.get("tag") or "").strip()
        if top_tag and img_tag and img_tag != top_tag:
            errors.append(f"{where}: release_tag '{img_tag}' != release.tag '{top_tag}'")

    # cross-image consistency
    if len(seen_shas) > 1:
        errors.append(f"mixed git SHAs across images: {sorted(seen_shas)}")
    if len(seen_versions) > 1:
        errors.append(f"mixed versions across images: {sorted(seen_versions)}")
    if release_sha and seen_shas and release_sha not in seen_shas:
        errors.append(f"release.git_sha '{release_sha}' does not match image git_sha {sorted(seen_shas)}")
    if release_version and seen_versions and release_version not in seen_versions:
        errors.append(f"release.version '{release_version}' does not match image versions {sorted(seen_versions)}")

    missing = set(services) - seen_services
    if missing:
        errors.append(f"lock manifest missing services: {sorted(missing)}")
    extra = seen_services - set(services)
    if extra:
        errors.append(f"lock manifest has services not in pilot list: {sorted(extra)}")

    # --- top-level extended checks ---
    schema_version = (lock.get("schema_version") or "").strip()
    if not schema_version:
        errors.append("missing 'schema_version'")
    elif schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        errors.append(f"unsupported schema_version '{schema_version}' (expected {sorted(SUPPORTED_SCHEMA_VERSIONS)})")

    top_tag = (release.get("tag") or "").strip()
    if not top_tag:
        errors.append("release.tag is missing")
    elif top_tag in _MUTABLE_TAGS:
        errors.append(f"release.tag '{top_tag}' is a mutable tag")

    platform = (lock.get("platform") or "").strip()
    if not platform:
        errors.append("missing top-level 'platform'")
    elif platform not in VALID_PLATFORMS:
        errors.append(f"unsupported platform '{platform}' (expected {sorted(VALID_PLATFORMS)})")

    # compose service mapping (explicit multi-service reuse)
    mapping = lock.get("compose_service_mapping") or {}
    if not isinstance(mapping, dict):
        errors.append("compose_service_mapping must be an object")
    else:
        by_service = {img.get("service"): img for img in images if isinstance(img, dict)}
        for compose_svc, image_svc in mapping.items():
            if compose_svc in by_service:
                errors.append(f"compose_service_mapping key '{compose_svc}' collides with a published image service")
            if image_svc not in by_service:
                errors.append(f"compose_service_mapping '{compose_svc}' → unknown image service '{image_svc}'")

    return errors


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--lock", default="images.v0.11.1-pilot-packaging.lock.json")
    p.add_argument("--services", default=None)
    args = p.parse_args()

    services = [s.strip() for s in (args.services or "").split(",") if s.strip()] or None
    lock_path = Path(args.lock)
    if not lock_path.exists():
        print(f"FAIL: lock not found: {lock_path}", file=sys.stderr)
        return 1
    try:
        lock = json.loads(lock_path.read_text())
    except json.JSONDecodeError as e:
        print(f"FAIL: invalid JSON: {e}", file=sys.stderr)
        return 1

    print(f"=== Verifying release lock: {lock_path} ===")
    errors = verify(lock, services)
    if errors:
        for e in errors:
            print(f"  ERROR: {e}")
        print(f"=== Verification FAILED ({len(errors)} errors) ===")
        return 1
    print("=== Verification PASSED — release lock immutable & complete ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
