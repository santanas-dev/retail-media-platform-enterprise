#!/usr/bin/env python3
"""
MinIO bucket restore script for Retail Media Platform.

Restores objects from a backup directory (created by minio_backup.py) into
a target MinIO bucket. Requires explicit confirmation.

Usage:
    # Check/validate mode — inspect backup without restoring
    python scripts/restore/minio_restore.py /backups/minio/20260101T000000Z --check

    # Dry-run — simulate restore, no writes
    python scripts/restore/minio_restore.py /backups/minio/20260101T000000Z --dry-run

    # Restore (confirmation required)
    MINIO_ENDPOINT=localhost:9000 \\
    MINIO_ACCESS_KEY=... \\
    MINIO_SECRET_KEY=*** \\
    MINIO_BUCKET=retail-media-creatives \\
    REQUIRE_RESTORE_CONFIRMATION=yes \\
    python scripts/restore/minio_restore.py /backups/minio/20260101T000000Z

    # Restore to a different bucket (e.g. restore drill target)
    TARGET_MINIO_BUCKET=rmp-restore-target \\
    REQUIRE_RESTORE_CONFIRMATION=yes \\
    python scripts/restore/minio_restore.py /backups/minio/20260101T000000Z

Options:
    --check           Validate manifest + data only, no restore
    --dry-run         Simulate restore, show what would be uploaded
    --overwrite       Overwrite existing objects in target (default: skip existing)
    --verbose         Print per-object status

Uses MinIO Python SDK.
Never prints secrets.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from minio import Minio
from minio.error import S3Error


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _redact(val: str) -> str:
    if len(val) <= 4:
        return "***"
    return val[:2] + "***" + val[-2:]


def _parse_target_env() -> dict[str, str]:
    """Read target MinIO env vars."""
    required = ["MINIO_ENDPOINT", "MINIO_ACCESS_KEY", "MINIO_SECRET_KEY"]
    cfg: dict[str, str] = {}
    missing = []
    for key in required:
        val = os.environ.get(key, "").strip()
        if not val:
            missing.append(key)
        cfg[key] = val
    # MINIO_BUCKET or TARGET_MINIO_BUCKET (override)
    cfg["bucket"] = os.environ.get("TARGET_MINIO_BUCKET") or os.environ.get("MINIO_BUCKET", "").strip()
    if not cfg["bucket"]:
        missing.append("MINIO_BUCKET")
    if missing:
        print(f"ERROR: missing required env vars: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)
    return cfg


def _load_manifest(backup_dir: Path) -> dict[str, Any]:
    """Load and validate manifest.json from backup directory."""
    manifest_path = backup_dir / "manifest.json"
    if not manifest_path.exists():
        print(f"ERROR: manifest.json not found in {backup_dir}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(manifest_path) as f:
            manifest = json.load(f)
    except json.JSONDecodeError as exc:
        print(f"ERROR: invalid manifest.json: {exc}", file=sys.stderr)
        sys.exit(1)

    required = ["bucket", "generated_at", "object_count", "total_size_bytes", "objects"]
    missing = [k for k in required if k not in manifest]
    if missing:
        print(f"ERROR: manifest.json missing fields: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    # Validate all objects have data files
    data_dir = backup_dir / "data"
    for obj in manifest["objects"]:
        key = obj["key"]
        data_path = data_dir / key
        if not data_path.exists():
            print(f"ERROR: object data file missing: {data_path}", file=sys.stderr)
            sys.exit(1)
        actual_size = data_path.stat().st_size
        if actual_size != obj["size"]:
            print(
                f"ERROR: size mismatch for '{key}': "
                f"manifest={obj['size']}, actual={actual_size}",
                file=sys.stderr,
            )
            sys.exit(1)

    return manifest


def _verify_object_sha256(data_path: Path, expected: str) -> bool:
    """Compute SHA-256 of a local file and compare to expected."""
    h = hashlib.sha256()
    with open(data_path, "rb") as f:
        while True:
            chunk = f.read(131_072)
            if not chunk:
                break
            h.update(chunk)
    actual = h.hexdigest()
    return actual == expected


def _file_size_str(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


# ---------------------------------------------------------------------------
# Check mode
# ---------------------------------------------------------------------------

def check_backup(backup_dir: Path, args: argparse.Namespace) -> int:
    """Validate manifest + data integrity without restoring."""
    manifest = _load_manifest(backup_dir)
    data_dir = backup_dir / "data"

    print("=" * 60)
    print("Check Mode: Validating Backup")
    print("=" * 60)
    print(f"  Backup dir:  {backup_dir}")
    print(f"  Bucket:      {manifest['bucket']}")
    print(f"  Generated:   {manifest['generated_at']}")
    print(f"  Objects:     {manifest['object_count']}")
    print(f"  Total size:  {_file_size_str(manifest['total_size_bytes'])}")
    print()

    errors = 0
    verified = 0
    for i, obj in enumerate(manifest["objects"], 1):
        key = obj["key"]
        data_path = data_dir / key
        expected_sha = obj.get("sha256", "")

        if not expected_sha:
            print(f"  [{i}/{manifest['object_count']}] {key} — SKIP (no sha256 in manifest)")
            continue

        if args.verbose:
            print(f"  [{i}/{manifest['object_count']}] {key} — verifying sha256...", end="", flush=True)

        if _verify_object_sha256(data_path, expected_sha):
            verified += 1
            if args.verbose:
                print(" OK")
        else:
            errors += 1
            print(f"  [{i}/{manifest['object_count']}] {key} — SHA256 MISMATCH")

    print()
    if errors == 0:
        print(f"=== Check Mode: VALID — all {verified} objects verified ===")
        return 0
    else:
        print(f"=== Check Mode: INVALID — {errors} checksum error(s) ===")
        return 1


# ---------------------------------------------------------------------------
# Dry-run mode
# ---------------------------------------------------------------------------

def dry_run(backup_dir: Path, args: argparse.Namespace) -> int:
    """Simulate restore — print what would be uploaded, skip checksums."""
    manifest = _load_manifest(backup_dir)
    cfg = _parse_target_env()

    print("=" * 60)
    print("Dry-Run Mode: Simulating Restore")
    print("=" * 60)
    print(f"  Source:      {backup_dir}")
    print(f"  Target:      {cfg['MINIO_ENDPOINT']}")
    print(f"  Bucket:      {cfg['bucket']}")
    print(f"  Objects:     {manifest['object_count']}")
    print(f"  Total size:  {_file_size_str(manifest['total_size_bytes'])}")
    print(f"  Overwrite:   {'yes' if args.overwrite else 'no (skip existing)'}")
    print()

    client = Minio(
        cfg["MINIO_ENDPOINT"],
        access_key=cfg["MINIO_ACCESS_KEY"],
        secret_key=cfg["MINIO_SECRET_KEY"],
        secure=False,
    )

    # Check bucket + connectivity
    try:
        target_exists = client.bucket_exists(cfg["bucket"])
        if not target_exists:
            print(f"  [BUCKET] Would create bucket '{cfg['bucket']}'")
    except S3Error as exc:
        print(f"  [BUCKET] Cannot check bucket: {exc}")

    to_upload = 0
    to_skip = 0
    total_bytes = 0
    for i, obj in enumerate(manifest["objects"], 1):
        key = obj["key"]
        data_path = backup_dir / "data" / key
        if not args.overwrite:
            try:
                if target_exists and _check_object(client, cfg["bucket"], key):
                    if args.verbose:
                        print(f"  [{i}/{manifest['object_count']}] {key} — SKIP (exists)")
                    to_skip += 1
                    continue
            except Exception:
                pass  # can't check — assume upload needed
        to_upload += 1
        total_bytes += obj["size"]
        if args.verbose:
            print(f"  [{i}/{manifest['object_count']}] {key} — WOULD UPLOAD ({_file_size_str(obj['size'])})")

    print()
    print(f"  To upload: {to_upload}")
    print(f"  To skip:   {to_skip}")
    print(f"  Estimated: {_file_size_str(total_bytes)}")
    print("=== Dry-Run: OK (no writes performed) ===")
    return 0


def _check_object(client: Minio, bucket: str, key: str) -> bool:
    try:
        client.stat_object(bucket, key)
        return True
    except S3Error:
        return False


# ---------------------------------------------------------------------------
# Restore mode
# ---------------------------------------------------------------------------

def restore(backup_dir: Path, args: argparse.Namespace) -> int:
    """Execute restore."""
    # Confirmation gate
    if os.environ.get("REQUIRE_RESTORE_CONFIRMATION", "").strip() != "yes":
        print("ERROR: REQUIRE_RESTORE_CONFIRMATION must be set to 'yes'")
        print()
        print("This script uploads objects to a MinIO bucket. To proceed, run:")
        print("  REQUIRE_RESTORE_CONFIRMATION=yes python scripts/restore/minio_restore.py ...")
        return 1

    manifest = _load_manifest(backup_dir)
    cfg = _parse_target_env()
    data_dir = backup_dir / "data"

    print("=" * 60)
    print("Restoring MinIO Bucket")
    print("=" * 60)
    print(f"  Source:      {backup_dir}")
    print(f"  Target:      {cfg['MINIO_ENDPOINT']}")
    print(f"  Bucket:      {cfg['bucket']}")
    print(f"  Objects:     {manifest['object_count']}")
    print(f"  Total size:  {_file_size_str(manifest['total_size_bytes'])}")
    print(f"  Overwrite:   {'yes' if args.overwrite else 'no (skip existing)'}")
    print()

    client = Minio(
        cfg["MINIO_ENDPOINT"],
        access_key=cfg["MINIO_ACCESS_KEY"],
        secret_key=cfg["MINIO_SECRET_KEY"],
        secure=False,
    )

    # Ensure bucket exists
    try:
        if not client.bucket_exists(cfg["bucket"]):
            print(f"Creating bucket '{cfg['bucket']}'...")
            client.make_bucket(cfg["bucket"])
    except S3Error as exc:
        print(f"ERROR: cannot ensure bucket '{cfg['bucket']}': {exc}", file=sys.stderr)
        return 1

    uploaded = 0
    skipped = 0
    errors = 0
    total_bytes = 0
    for i, obj in enumerate(manifest["objects"], 1):
        key = obj["key"]
        data_path = data_dir / key
        size = obj["size"]

        # Verify local file integrity
        expected_sha = obj.get("sha256", "")
        if expected_sha and not _verify_object_sha256(data_path, expected_sha):
            print(f"  [{i}/{manifest['object_count']}] {key} — ERROR: local sha256 mismatch, skipping")
            errors += 1
            continue

        # Check if already exists
        if not args.overwrite and _check_object(client, cfg["bucket"], key):
            if args.verbose:
                print(f"  [{i}/{manifest['object_count']}] {key} — SKIP (exists)")
            skipped += 1
            continue

        # Upload
        try:
            print(f"  [{i}/{manifest['object_count']}] {key} — uploading ({_file_size_str(size)})...",
                  end="", flush=True)
            client.fput_object(cfg["bucket"], key, str(data_path))
            print(" OK")
            uploaded += 1
            total_bytes += size
        except S3Error as exc:
            print(f" FAILED: {exc}")
            errors += 1

    # Post-restore verification
    print()
    print("Verifying restored objects...")
    verify_ok = 0
    verify_fail = 0
    for obj in manifest["objects"]:
        key = obj["key"]
        if not _check_object(client, cfg["bucket"], key):
            print(f"  MISSING: {key}")
            verify_fail += 1
        elif obj.get("sha256"):
            # Verify remote sha256
            try:
                resp = client.get_object(cfg["bucket"], key)
                h = hashlib.sha256()
                while True:
                    chunk = resp.read(131_072)
                    if not chunk:
                        break
                    h.update(chunk)
                resp.close()
                resp.release_conn()
                remote_sha = h.hexdigest()
                if remote_sha == obj["sha256"]:
                    verify_ok += 1
                else:
                    print(f"  SHA MISMATCH: {key} (expected {obj['sha256'][:12]}..., got {remote_sha[:12]}...)")
                    verify_fail += 1
            except S3Error:
                verify_fail += 1
        else:
            verify_ok += 1

    print()
    print("=== Restore Summary ===")
    print(f"  Uploaded:    {uploaded}")
    print(f"  Skipped:     {skipped}")
    print(f"  Upload errors: {errors}")
    print(f"  Verified:    {verify_ok}")
    print(f"  Verify fails:  {verify_fail}")
    print(f"  Endpoint:    {cfg['MINIO_ENDPOINT']}")
    print(f"  Bucket:      {cfg['bucket']}")
    print(f"  Access key:  {_redact(cfg['MINIO_ACCESS_KEY'])}")

    if errors == 0 and verify_fail == 0:
        print("=== Status: SUCCESS ===")
        return 0
    else:
        print("=== Status: COMPLETED WITH ISSUES ===")
        return 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Restore MinIO bucket from backup")
    parser.add_argument("backup_dir", type=Path, help="Path to backup directory (contains manifest.json + data/)")
    parser.add_argument("--check", action="store_true", help="Validate backup integrity, no restore")
    parser.add_argument("--dry-run", action="store_true", help="Simulate restore, no writes")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing objects (default: skip)")
    parser.add_argument("--verbose", action="store_true", help="Print per-object status")
    args = parser.parse_args()

    if not args.backup_dir.exists():
        print(f"ERROR: backup directory not found: {args.backup_dir}", file=sys.stderr)
        return 1

    if args.check:
        return check_backup(args.backup_dir, args)
    if args.dry_run:
        return dry_run(args.backup_dir, args)

    return restore(args.backup_dir, args)


if __name__ == "__main__":
    sys.exit(main())
