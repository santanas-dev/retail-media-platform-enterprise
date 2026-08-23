"""Unified backup manifest — schema, build, and validation (PILOT-DEPLOYMENT-READINESS-001C).

Ties PostgreSQL and MinIO to a single logical (quiesced) point in time. The
manifest is the single artifact a restore drill validates against before
touching a target.

Design rules (SCOPE C / 001C-FU):
  - No credentials, tokens, password values, or private keys may ever be
    serialised into the manifest.
  - All integrity fields are recomputed at restore time (never trusted from
    the manifest alone).
  - Every known stateful component MUST be explicitly classified with a
    disposition + recovery procedure. A manifest that silently omits a
    component is rejected — you cannot forget NATS, Redis, etc.
  - A quiesced backup MUST carry quiescence evidence; consistency_mode
    "quiesced" without evidence is rejected.

The module is dependency-free (stdlib only) so it can be unit-tested without
a database or MinIO.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MANIFEST_SCHEMA_VERSION = "1.1"
MANIFEST_FORMAT = "rmp-backup-manifest"
CONSISTENCY_MODE = "quiesced"

# Every stateful component that a Layer-1 backup must account for. Validation
# REQUIRES each of these to be present in the `components` classification
# (SCOPE 1 of 001C-FU — a manifest cannot silently forget a component).
KNOWN_STATEFUL_COMPONENTS = ("postgres", "minio", "redis", "nats")

# Allowed disposition values. "backed_up" = included in this backup artifact.
# "excluded_*" = intentionally not included, with a mandatory reason +
# recovery_procedure proving the data is derivable or disposable.
ALLOWED_DISPOSITIONS = (
    "backed_up",
    "excluded_replayable",
    "excluded_disposable",
)

# Sensitive keys that must never appear (case-insensitive substring) in a
# serialised manifest. Kept deliberately narrow and semantic.
_SENSITIVE_SUBSTRINGS = (
    "password",
    "secret",
    "token",
    "private_key",
    "access_key",
    "credential",
    "authorization",
    "jwt",
)

# Tables whose row counts are captured as control points (SCOPE C / SCOPE F).
CONTROL_TABLES = (
    "advertiser_organizations",
    "advertiser_brands",
    "advertiser_contracts",
    "advertiser_contacts",
    "campaigns",
    "campaign_flights",
    "campaign_placements",
    "creative_assets",
    "campaign_creatives",
    "campaign_status_history",
    "commerce_tariff_versions",
    "commerce_price_items",
    "commerce_orders",
    "commerce_order_lines",
    "physical_devices",
    "device_status_history",
    "license_grants",
    "license_seats",
    "audit_events_operational",
)


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(131_072)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Stateful-component classification (001C-FU SCOPE 1)
# ---------------------------------------------------------------------------

def default_component_classification() -> dict[str, dict[str, str]]:
    """Standard Layer-1 classification for every known stateful component.

    The classification is evidence-backed by code/config:

    - postgres: authoritative business state → backed_up (pg_dump custom).
    - minio: authoritative binary objects (creatives, contract PDFs) → backed_up.
    - redis: cache semantics only (S-0xx) → excluded_disposable.
    - nats: JetStream is enabled (-js) and has durable stream "RMP" + consumer
      "rmp-campaign-consumer", but the authoritative source of truth is the
      PostgreSQL outbox_events table (events are written there first and
      published with Nats-Msg-Id=event_id for dedup). Full recovery is via
      idempotent provisioning (provision_campaign_delivery) + outbox relay
      replay. See docs/runbook/nats-backup-restore.md → excluded_replayable.
    """
    return {
        "postgres": {
            "disposition": "backed_up",
            "reason": "authoritative business state (schema + rows)",
            "recovery_procedure": "pg_restore --clean --if-exists --no-owner --no-privileges",
        },
        "minio": {
            "disposition": "backed_up",
            "reason": "authoritative binary objects (creatives, contract PDFs)",
            "recovery_procedure": "minio_restore.py per-bucket (key/sha256 verified)",
        },
        "redis": {
            "disposition": "excluded_disposable",
            "reason": "cache semantics — not a source of truth, no durable business state",
            "recovery_procedure": "restart empty; caches repopulate from PostgreSQL/MinIO",
        },
        "nats": {
            "disposition": "excluded_replayable",
            "reason": (
                "JetStream transport only; authoritative source of truth is "
                "PostgreSQL outbox_events. Every event written to outbox first, "
                "published with Nats-Msg-Id=event_id dedup. Stream/consumer are "
                "recreated idempotently at startup (NATS_AUTO_PROVISION)."
            ),
            "recovery_procedure": (
                "start nats-server -js → provision_campaign_delivery() → "
                "outbox relay replays pending events (dedup-safe via Nats-Msg-Id)"
            ),
        },
    }


# ---------------------------------------------------------------------------
# Secret scanning
# ---------------------------------------------------------------------------

def _walk_for_secrets(obj: Any, path: str = "$") -> list[str]:
    """Recursively find keys/values that look like secrets.

    - A dictionary KEY is flagged if it is sensitive by name.
    - A string VALUE is flagged only if it is actual credential material:
      a DSN with an embedded password, a PEM private key block, or a JWT.

    Returns human-readable paths. Does NOT return the offending values.
    """
    hits: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if _looks_sensitive_key(str(k)):
                hits.append(f"{path}.{k} (key)")
            hits.extend(_walk_for_secrets(v, f"{path}.{k}"))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            hits.extend(_walk_for_secrets(v, f"{path}[{i}]"))
    elif isinstance(obj, str):
        if _looks_like_credential_value(obj):
            hits.append(f"{path} (value)")
    return hits


_DSN_WITH_PASSWORD = re.compile(r"[a-zA-Z][a-zA-Z0-9+.-]*://[^/@\s]+:[^/@\s]+@")
_PEM_PRIVATE_KEY = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
# Real JWTs have long base64url segments; requiring >=10 chars per segment avoids
# false positives on dotted version strings like "001C-1.0.0".
_JWT = re.compile(r"^[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}$")


def _looks_sensitive_key(s: str) -> bool:
    lowered = s.lower()
    return any(sub in lowered for sub in _SENSITIVE_SUBSTRINGS)


def _looks_like_credential_value(s: str) -> bool:
    if _DSN_WITH_PASSWORD.search(s):
        return True
    if _PEM_PRIVATE_KEY.search(s):
        return True
    if _JWT.fullmatch(s):
        return True
    return False


def _validate_no_secrets(obj: Any) -> None:
    hits = _walk_for_secrets(obj)
    if hits:
        raise ValueError(f"manifest contains sensitive fields: {', '.join(hits)}")


def _require(obj: dict[str, Any], *keys: str) -> None:
    missing = [k for k in keys if k not in obj]
    if missing:
        raise ValueError(f"missing required manifest fields: {', '.join(missing)}")


# ---------------------------------------------------------------------------
# Quiescence evidence (001C-FU SCOPE 2)
# ---------------------------------------------------------------------------

QUIESCE_MODES = ("writers-stopped", "maintenance")


def check_quiescence_evidence(
    environment: str,
    quiesce_mode: str,
    quiesce_evidence: str,
) -> list[str]:
    """Refuse a quiesced backup without proven quiescence (fail-closed).

    In pilot/production, consistency_mode=quiesced is a lie unless the
    invocation proves writers were stopped or maintenance was entered. In dev
    (and the CI drill) quiescence is by-construction (no app writers).
    """
    if environment in ("dev", "drill"):
        return []
    if quiesce_mode not in QUIESCE_MODES:
        return [
            "quiesced backup requires quiescence evidence "
            f"(quiesce_mode must be one of {QUIESCE_MODES}, got {quiesce_mode!r})"
        ]
    if not quiesce_evidence or not quiesce_evidence.strip():
        return ["quiesced backup requires a non-empty quiesce_evidence string"]
    return []


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build_manifest(
    *,
    backup_dir: Path,
    git_sha: str,
    version: str,
    alembic_head: str,
    postgres_server_version: str,
    minio_server_version: str,
    dump_file: Path,
    dump_sha256: str,
    row_counts: dict[str, int],
    buckets: dict[str, dict[str, Any]],
    backup_tool_version: str,
    encryption_enabled: bool = False,
    encryption_status: str = "none",
    rpo_target_seconds: int = 0,
    environment: str = "pilot",
    quiesce_mode: str = "writers-stopped",
    quiesce_evidence: str = "",
    components: dict[str, dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Assemble the unified manifest dictionary."""
    generated_at = utcnow()
    comps = components if components is not None else default_component_classification()
    manifest: dict[str, Any] = {
        "manifest_version": MANIFEST_SCHEMA_VERSION,
        "format": MANIFEST_FORMAT,
        "consistency_mode": CONSISTENCY_MODE,
        "generated_at_utc": generated_at,
        "source": {
            "git_sha": git_sha,
            "version": version,
            "environment": environment,
        },
        "postgres": {
            "server_version": postgres_server_version,
            "alembic_head": alembic_head,
            "dump_file": str(dump_file),
            "dump_sha256": dump_sha256,
            "dump_format": "custom",
            "row_counts": dict(row_counts),
            "backup_tool_version": backup_tool_version,
        },
        "minio": {
            "server_version": minio_server_version,
            "buckets": buckets,
            "backup_tool_version": backup_tool_version,
        },
        "quiescence": {
            "mode": quiesce_mode,
            "evidence": quiesce_evidence,
            "verified_at_utc": generated_at,
        },
        "components": comps,
        "encryption": {
            "enabled": encryption_enabled,
            "status": encryption_status,
        },
        "rpo": {
            "target_seconds": rpo_target_seconds,
            "note": "0 = quiesced dataset (no writers during backup)",
        },
        "backup_tool_version": backup_tool_version,
        "backup_dir": str(backup_dir),
    }
    return manifest


# ---------------------------------------------------------------------------
# Validate
# ---------------------------------------------------------------------------

def validate_manifest(manifest: dict[str, Any]) -> None:
    """Validate structural + integrity + secret-safety + classification.

    Raises ValueError on the first violation.
    """
    if not isinstance(manifest, dict):
        raise ValueError("manifest must be a JSON object")
    _require(manifest, "manifest_version", "format", "consistency_mode", "generated_at_utc")
    if manifest["format"] != MANIFEST_FORMAT:
        raise ValueError(f"unexpected format: {manifest['format']}")
    if manifest["consistency_mode"] != CONSISTENCY_MODE:
        raise ValueError(f"unexpected consistency_mode: {manifest['consistency_mode']}")
    _require(manifest, "source", "postgres", "minio", "encryption", "rpo",
             "quiescence", "components")
    _require(manifest["source"], "git_sha", "version", "environment")
    _require(
        manifest["postgres"],
        "server_version", "alembic_head", "dump_file", "dump_sha256",
        "row_counts", "backup_tool_version",
    )
    _require(manifest["minio"], "server_version", "buckets", "backup_tool_version")
    _require(manifest["encryption"], "enabled", "status")
    _require(manifest["rpo"], "target_seconds")

    # Quiescence evidence must be coherent with consistency_mode (SCOPE 2).
    _require(manifest["quiescence"], "mode", "evidence")
    env = manifest["source"]["environment"]
    problems = check_quiescence_evidence(
        env,
        manifest["quiescence"]["mode"],
        manifest["quiescence"]["evidence"],
    )
    if problems:
        raise ValueError(problems[0])

    # Every known stateful component must be classified (SCOPE 1) — a manifest
    # that silently forgets a component is rejected.
    comps = manifest["components"]
    if not isinstance(comps, dict):
        raise ValueError("components must be an object")
    missing = [c for c in KNOWN_STATEFUL_COMPONENTS if c not in comps]
    if missing:
        raise ValueError(
            f"manifest is missing classification for stateful components: {', '.join(missing)}"
        )
    for name, meta in comps.items():
        _require(meta, "disposition", "reason", "recovery_procedure")
        if meta["disposition"] not in ALLOWED_DISPOSITIONS:
            raise ValueError(
                f"component {name!r}: invalid disposition {meta['disposition']!r}"
            )
        if meta["disposition"].startswith("excluded_"):
            if not meta["reason"].strip() or not meta["recovery_procedure"].strip():
                raise ValueError(
                    f"component {name!r}: excluded_* disposition requires non-empty "
                    f"reason and recovery_procedure"
                )

    # Integrity field shapes
    dump_sha = manifest["postgres"]["dump_sha256"]
    if not isinstance(dump_sha, str) or not re.fullmatch(r"[0-9a-f]{64}", dump_sha):
        raise ValueError("dump_sha256 must be a 64-char hex string")
    if not isinstance(manifest["postgres"]["row_counts"], dict):
        raise ValueError("row_counts must be an object")
    for tbl, cnt in manifest["postgres"]["row_counts"].items():
        if not isinstance(cnt, int) or cnt < 0:
            raise ValueError(f"row_counts[{tbl!r}] must be a non-negative int")

    buckets = manifest["minio"]["buckets"]
    if not isinstance(buckets, dict):
        raise ValueError("minio.buckets must be an object")
    for bucket, bmeta in buckets.items():
        _require(bmeta, "object_count", "total_size_bytes", "objects")
        if not isinstance(bmeta["object_count"], int) or bmeta["object_count"] < 0:
            raise ValueError(f"bucket {bucket!r}: object_count must be a non-negative int")
        objects = bmeta["objects"]
        if not isinstance(objects, list):
            raise ValueError(f"bucket {bucket!r}: objects must be a list")
        if len(objects) != bmeta["object_count"]:
            raise ValueError(
                f"bucket {bucket!r}: object_count={bmeta['object_count']} "
                f"but len(objects)={len(objects)}"
            )
        for o in objects:
            _require(o, "key", "size", "sha256")
            if not re.fullmatch(r"[0-9a-f]{64}", o["sha256"]):
                raise ValueError(f"bucket {bucket!r}: object {o['key']!r} has bad sha256")

    # No secrets anywhere in the manifest.
    _validate_no_secrets(manifest)


def write_manifest(manifest: dict[str, Any], path: Path) -> Path:
    """Serialize a manifest to disk after validating it. Raises on secret leak."""
    validate_manifest(manifest)
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
    return path


def load_manifest(path: Path) -> dict[str, Any]:
    """Load and validate a manifest from disk."""
    with open(path) as f:
        manifest = json.load(f)
    validate_manifest(manifest)
    return manifest


def verify_manifest_against_disk(manifest: dict[str, Any], backup_dir: Path) -> list[str]:
    """Recompute integrity of the DB dump and every object on disk.

    Returns a list of human-readable failure strings (empty = verified).
    Never trusts manifest checksums.
    """
    problems: list[str] = []

    dump_rel = manifest["postgres"]["dump_file"]
    dump_path = backup_dir / dump_rel
    if not dump_path.exists():
        problems.append(f"DB dump missing: {dump_path}")
    else:
        actual = sha256_file(dump_path)
        if actual != manifest["postgres"]["dump_sha256"]:
            problems.append(
                f"DB dump checksum mismatch: manifest={manifest['postgres']['dump_sha256'][:12]}… "
                f"actual={actual[:12]}…"
            )

    for bucket, bmeta in manifest["minio"]["buckets"].items():
        for o in bmeta["objects"]:
            rel = o.get("data_rel") or f"minio/{bucket}/{o['key']}"
            obj_path = backup_dir / rel
            if not obj_path.exists():
                problems.append(f"MinIO object missing: {bucket}/{o['key']}")
                continue
            if obj_path.stat().st_size != o["size"]:
                problems.append(
                    f"MinIO object size mismatch: {bucket}/{o['key']} "
                    f"manifest={o['size']} actual={obj_path.stat().st_size}"
                )
            actual = sha256_file(obj_path)
            if actual != o["sha256"]:
                problems.append(
                    f"MinIO object checksum mismatch: {bucket}/{o['key']} "
                    f"manifest={o['sha256'][:12]}… actual={actual[:12]}…"
                )

    return problems


if __name__ == "__main__":  # pragma: no cover - convenience CLI
    import argparse

    p = argparse.ArgumentParser(description="Validate a unified backup manifest")
    p.add_argument("manifest_path", type=Path)
    p.add_argument("--verify-disk", action="store_true",
                   help="also recompute dump/object checksums against backup_dir")
    args = p.parse_args()

    manifest = load_manifest(args.manifest_path)
    print(f"manifest valid: {manifest['postgres']['alembic_head']} "
          f"({manifest['postgres']['row_counts']})")
    if args.verify_disk:
        backup_dir = Path(manifest["backup_dir"])
        problems = verify_manifest_against_disk(manifest, backup_dir)
        if problems:
            for pr in problems:
                print(f"  FAIL: {pr}")
            raise SystemExit(1)
        print("disk verification: OK")
