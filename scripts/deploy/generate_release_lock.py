#!/usr/bin/env python3
"""Generate the immutable pilot image release lock (IMAGE-REGISTRY-001, SCOPE D).

Builds a release lock manifest from per-image digests + release metadata and
writes a SHA256SUMS checksum file. Pure functions are importable for tests.

Usage:
    python scripts/deploy/generate-release-lock.py \\
        --release-tag v0.11.1-pilot-packaging \\
        --sha 90c4bb1a9c7d1b2d5dbf6bef180d942dd5336275 \\
        --platform linux/amd64 \\
        --registry ghcr.io/santanas-dev/rmp-pilot \\
        --digests-file /tmp/digests.json \\
        --sbom attested --provenance attested \\
        --out images.v0.11.1-pilot-packaging.lock.json \\
        --checksums-out SHA256SUMS

``digests-file`` is a JSON object mapping service name -> "sha256:<hex>".
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REGISTRY = "ghcr.io/santanas-dev/rmp-pilot"
SERVICES = [
    "control-api",
    "device-gateway",
    "orchestrator-worker",
    "admin-web",
    "advertiser-web",
]
# Compose services that reuse a published image (not built separately).
COMPOSE_SERVICE_MAPPING = {"db-migrate": "control-api"}


def build_lock(
    release_tag: str,
    git_sha: str,
    platform: str,
    registry: str,
    digests: dict[str, str],
    build_timestamp: str | None = None,
    sbom: str = "attested",
    provenance: str = "attested",
) -> dict:
    """Assemble the release lock manifest."""
    if not release_tag:
        raise ValueError("release_tag is required")
    if len(git_sha) != 40:
        raise ValueError(f"git_sha must be 40 chars, got {len(git_sha)}")
    if set(digests.keys()) != set(SERVICES):
        missing = set(SERVICES) - set(digests.keys())
        extra = set(digests.keys()) - set(SERVICES)
        raise ValueError(f"digests must cover exactly {SERVICES}; missing={sorted(missing)} extra={sorted(extra)}")

    ts = build_timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    images = []
    for service in SERVICES:
        digest = digests[service]
        if not digest.startswith("sha256:"):
            raise ValueError(f"digest for {service} must start with sha256:, got {digest!r}")
        images.append({
            "service": service,
            "repository": f"{registry}/{service}",
            "release_tag": release_tag,
            "image_digest": digest,
            "git_sha": git_sha,
            "version": release_tag,
            "source_tag": release_tag,
            "platform": platform,
            "build_timestamp": ts,
            "oci": {
                "version": release_tag,
                "revision": git_sha,
                "source": f"https://github.com/santanas-dev/retail-media-platform-enterprise",
                "created": ts,
            },
            "sbom": sbom,
            "provenance": provenance,
        })

    return {
        "schema_version": "1.1",
        "release": {
            "tag": release_tag,
            "version": release_tag,
            "git_sha": git_sha,
        },
        "generated_at": ts,
        "platform": platform,
        "registry": registry,
        "expected_services": SERVICES,
        "compose_service_mapping": COMPOSE_SERVICE_MAPPING,
        "images": images,
    }


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def write_lock_and_checksums(
    lock: dict,
    out_path: Path,
    checksums_path: Path | None = None,
) -> str:
    """Write the lock JSON and (optionally) a SHA256SUMS sidecar. Returns lock checksum hex."""
    out_path.write_text(json.dumps(lock, indent=2) + "\n")
    checksum = sha256_of(out_path)
    if checksums_path is not None:
        checksums_path.write_text(f"{checksum}  {out_path.name}\n")
    return checksum


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--release-tag", required=True)
    p.add_argument("--sha", required=True, help="40-char release commit SHA")
    p.add_argument("--platform", default="linux/amd64")
    p.add_argument("--registry", default=REGISTRY)
    p.add_argument("--digests-file", required=True, help="JSON file: service -> sha256:...")
    p.add_argument("--build-timestamp", default=None)
    p.add_argument("--sbom", default="attested")
    p.add_argument("--provenance", default="attested")
    p.add_argument("--out", required=True)
    p.add_argument("--checksums-out", default=None)
    args = p.parse_args()

    digests = json.loads(Path(args.digests_file).read_text())
    lock = build_lock(
        args.release_tag, args.sha, args.platform, args.registry,
        digests, args.build_timestamp, args.sbom, args.provenance,
    )
    checksum = write_lock_and_checksums(
        lock, Path(args.out),
        Path(args.checksums_out) if args.checksums_out else None,
    )
    print(f"lock written → {args.out}")
    print(f"lock sha256 = {checksum}")
    for img in lock["images"]:
        print(f"  {img['service']:22} {img['repository']}@{img['image_digest']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
