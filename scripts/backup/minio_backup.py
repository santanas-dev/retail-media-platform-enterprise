#!/usr/bin/env python3
"""
MinIO bucket backup script for Retail Media Platform.

Downloads all objects from a MinIO bucket to a local directory and writes
a manifest JSON with object metadata, SHA-256 checksums, and counts.

Usage:
    MINIO_ENDPOINT=localhost:9000 \
    MINIO_ACCESS_KEY=... \
    MINIO_SECRET_KEY=... \
    MINIO_BUCKET=retail-media-creatives \
    BACKUP_DIR=/backups/minio \
    python scripts/backup/minio_backup.py

Optional:
    KEEP_LAST=7         — keep only last N backups
    KEEP_OLDER_THAN_DAYS=30 — remove backups older than D days

Uses MinIO Python SDK — no mc CLI dependency.
Never prints secrets. Masked endpoint credentials in output.
Idempotent — overwrites same-named backup dir.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from minio import Minio
from minio.error import S3Error


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_env() -> dict[str, str]:
    """Read required env vars. Exits with error if any are missing."""
    required = ["MINIO_ENDPOINT", "MINIO_ACCESS_KEY", "MINIO_SECRET_KEY", "MINIO_BUCKET"]
    cfg: dict[str, str] = {}
    missing = []
    for key in required:
        val = os.environ.get(key, "").strip()
        if not val:
            missing.append(key)
        cfg[key] = val
    if missing:
        print(f"ERROR: missing required env vars: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)
    return cfg


def _redact(val: str) -> str:
    """Redact a secret-like value for safe output."""
    if len(val) <= 4:
        return "***"
    return val[:2] + "***" + val[-2:]


def _clean_old_backups(backup_dir: Path, keep_last: int | None, older_than_days: int | None) -> list[Path]:
    """Remove old backup directories. Returns list of removed paths."""
    removed: list[Path] = []
    if keep_last is None and older_than_days is None:
        return removed

    # Find backup dirs matching pattern YYYYMMDDTHHMMSSZ
    pattern = "????????T??????Z"
    dirs = sorted(
        [d for d in backup_dir.iterdir() if d.is_dir() and len(d.name) == 16],
        key=lambda d: d.name,
    )

    # Keep-last retention
    if keep_last is not None and len(dirs) > keep_last:
        for d in dirs[: -keep_last]:
            shutil.rmtree(d, ignore_errors=True)
            removed.append(d)

    # Older-than-days retention (on remaining dirs)
    if older_than_days is not None:
        cutoff = _now().replace(hour=0, minute=0, second=0, microsecond=0)
        for d in list(dirs):
            try:
                dt = datetime.strptime(d.name, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
                if (cutoff - dt).days > older_than_days:
                    if d.exists():
                        shutil.rmtree(d, ignore_errors=True)
                        removed.append(d)
            except ValueError:
                pass

    return removed


# ---------------------------------------------------------------------------
# Backup
# ---------------------------------------------------------------------------

def list_all_objects(client: Minio, bucket: str) -> list[dict[str, Any]]:
    """List all objects in bucket. Returns list of {key, size, last_modified, etag}."""
    objects: list[dict[str, Any]] = []
    try:
        for obj in client.list_objects(bucket, recursive=True):
            objects.append({
                "key": obj.object_name,
                "size": obj.size,
                "last_modified": obj.last_modified.isoformat() if obj.last_modified else None,
                "etag": obj.etag,
            })
    except S3Error as exc:
        print(f"ERROR: cannot list bucket '{bucket}': {exc}", file=sys.stderr)
        sys.exit(1)
    return objects


def download_object(client: Minio, bucket: str, obj_key: str, dest_path: Path) -> str:
    """Download a single object to dest_path. Returns SHA-256 hex digest."""
    try:
        response = client.get_object(bucket, obj_key)
    except S3Error as exc:
        print(f"ERROR: cannot download '{obj_key}': {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        h = hashlib.sha256()
        with open(dest_path, "wb") as f:
            while True:
                chunk = response.read(131_072)  # 128 KB
                if not chunk:
                    break
                h.update(chunk)
                f.write(chunk)
        return h.hexdigest()
    finally:
        response.close()
        response.release_conn()


def run_backup(cfg: dict[str, str], backup_root: Path, timestamp: str) -> Path:
    """Execute backup: list → download → manifest. Returns backup dir path."""
    client = Minio(
        cfg["MINIO_ENDPOINT"],
        access_key=cfg["MINIO_ACCESS_KEY"],
        secret_key=cfg["MINIO_SECRET_KEY"],
        secure=False,
    )

    bucket = cfg["MINIO_BUCKET"]

    # Ensure bucket exists
    try:
        if not client.bucket_exists(bucket):
            print(f"ERROR: bucket '{bucket}' does not exist", file=sys.stderr)
            sys.exit(1)
    except S3Error as exc:
        print(f"ERROR: cannot check bucket '{bucket}': {exc}", file=sys.stderr)
        sys.exit(1)

    # List all objects
    print(f"Listing objects in bucket '{bucket}'...")
    objects = list_all_objects(client, bucket)
    print(f"  Found {len(objects)} object(s)")

    # Create backup directory
    backup_dir = backup_root / timestamp
    data_dir = backup_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    # Download each object
    manifest_objects: list[dict[str, Any]] = []
    total_bytes = 0
    for i, obj in enumerate(objects, 1):
        key = obj["key"]
        # Replicate object key structure under data/
        dest = data_dir / key
        print(f"  [{i}/{len(objects)}] {key} ({obj['size']} bytes)", end="", flush=True)
        sha256 = download_object(client, bucket, key, dest)
        print(f" sha256={sha256[:12]}...", flush=True)
        manifest_objects.append({
            "key": key,
            "size": obj["size"],
            "sha256": sha256,
            "last_modified": obj["last_modified"],
            "etag": obj["etag"],
        })
        total_bytes += obj["size"]

    # Write manifest
    manifest = {
        "bucket": bucket,
        "generated_at": _now().isoformat(),
        "backup_timestamp": timestamp,
        "object_count": len(manifest_objects),
        "total_size_bytes": total_bytes,
        "objects": manifest_objects,
    }
    manifest_path = backup_dir / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    return backup_dir


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    cfg = _parse_env()

    backup_root = Path(os.environ.get("BACKUP_DIR", str(Path.cwd() / "backups" / "minio")))
    backup_root.mkdir(parents=True, exist_ok=True)

    keep_last = None
    if os.environ.get("KEEP_LAST"):
        keep_last = int(os.environ["KEEP_LAST"])

    older_than_days = None
    if os.environ.get("KEEP_OLDER_THAN_DAYS"):
        older_than_days = int(os.environ["KEEP_OLDER_THAN_DAYS"])

    timestamp = _now().strftime("%Y%m%dT%H%M%SZ")

    print("=" * 60)
    print("MinIO Bucket Backup")
    print("=" * 60)

    # Run backup
    backup_dir = run_backup(cfg, backup_root, timestamp)

    # Read manifest for summary
    with open(backup_dir / "manifest.json") as f:
        manifest = json.load(f)

    # Retention cleanup
    removed = _clean_old_backups(backup_root, keep_last, older_than_days)

    # Safe summary — no secrets
    size_bytes = manifest["total_size_bytes"]
    if size_bytes < 1024:
        size_str = f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        size_str = f"{size_bytes / 1024:.1f} KB"
    else:
        size_str = f"{size_bytes / (1024 * 1024):.1f} MB"

    print()
    print("=== Backup Summary ===")
    print(f"  Directory:    {backup_dir}")
    print(f"  Bucket:       {manifest['bucket']}")
    print(f"  Objects:      {manifest['object_count']}")
    print(f"  Total size:   {size_str}")
    print(f"  Manifest:     {backup_dir / 'manifest.json'}")
    print(f"  Endpoint:     {cfg['MINIO_ENDPOINT']}")
    print(f"  Access key:   {_redact(cfg['MINIO_ACCESS_KEY'])}")
    print(f"  Time:         {_now().strftime('%Y-%m-%d %H:%M:%S UTC')}")

    if keep_last is not None:
        print(f"  Retention:    keep last {keep_last}")
    if older_than_days is not None:
        print(f"  Retention:    older than {older_than_days} days")

    if removed:
        print(f"  Cleaned:      {len(removed)} old backup(s) removed")
    else:
        print("  Cleaned:      0 old backups removed")
    print("=== Status: SUCCESS ===")

    return 0


if __name__ == "__main__":
    sys.exit(main())
