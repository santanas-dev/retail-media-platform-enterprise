#!/usr/bin/env python3
"""
PostgreSQL restore script for Retail Media Platform.

Restores a pg_dump custom-format backup to a target database.
Requires explicit confirmation via REQUIRE_RESTORE_CONFIRMATION env var.
Supports validate-only/check mode.

Usage:
    DATABASE_URL=postgresql://...  \
    REQUIRE_RESTORE_CONFIRMATION=yes \
    python scripts/restore/postgres_restore.py /path/to/backup.dump

    # Check mode (validate backup file only, no restore)
    DATABASE_URL=postgresql://... python scripts/restore/postgres_restore.py /path.dump --check

    # Dry-run
    python scripts/restore/postgres_restore.py /path.dump --dry-run
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


def parse_db_url(url: str) -> dict[str, str]:
    """Parse DATABASE_URL into pg_env dict (PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE)."""
    parsed = urlparse(url)
    if not parsed.hostname:
        raise ValueError(f"Invalid DATABASE_URL: no hostname in {url}")
    return {
        "PGHOST": parsed.hostname,
        "PGPORT": str(parsed.port or 5432),
        "PGUSER": parsed.username or "",
        "PGPASSWORD": parsed.password or "",
        "PGDATABASE": (parsed.path or "/").lstrip("/") or "retail_media_platform",
    }


def redact_url(url: str) -> str:
    """Redact password from database URL."""
    return re.sub(r":([^/:]+)@", ":****@", url)


def pg_restore_list(backup_path: Path) -> subprocess.CompletedProcess:
    """Run pg_restore --list to validate backup structure without restoring."""
    return subprocess.run(
        ["pg_restore", "--list", str(backup_path)],
        capture_output=True,
        text=True,
        timeout=60,
    )


def pg_restore_run(
    backup_path: Path, pg_env: dict[str, str], extra_args: list[str] | None = None
) -> subprocess.CompletedProcess:
    """Run pg_restore with --clean --if-exists to the target database."""
    args = [
        "pg_restore",
        "--host", pg_env["PGHOST"],
        "--port", pg_env["PGPORT"],
        "--username", pg_env["PGUSER"],
        "--dbname", pg_env["PGDATABASE"],
        "--clean",
        "--if-exists",
        "--no-owner",
        "--no-privileges",
        "--single-transaction",
    ]
    if extra_args:
        args.extend(extra_args)
    args.append(str(backup_path))

    env = os.environ.copy()
    env["PGPASSWORD"] = pg_env["PGPASSWORD"]

    return subprocess.run(args, capture_output=True, text=True, timeout=300, env=env)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Restore PostgreSQL backup to target database."
    )
    parser.add_argument(
        "backup_file", type=str,
        help="Path to the pg_dump custom-format backup file",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Validate-only mode: check backup structure without restoring",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print what would be restored without executing",
    )
    args = parser.parse_args()

    backup_path = Path(args.backup_file)
    if not backup_path.exists():
        print(f"ERROR: Backup file not found: {backup_path}", file=sys.stderr)
        return 1
    if backup_path.stat().st_size == 0:
        print(f"ERROR: Backup file is empty: {backup_path}", file=sys.stderr)
        return 1

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL is not set", file=sys.stderr)
        return 1

    try:
        pg_env = parse_db_url(database_url)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    safe_url = redact_url(database_url)

    # Check mode
    if args.check:
        print("=== Check Mode ===")
        print(f"  Backup:     {backup_path}")
        print(f"  Size:       {backup_path.stat().st_size / 1024:.1f} KB")
        print(f"  Target URL: {safe_url}")
        print()

        result = pg_restore_list(backup_path)
        if result.returncode != 0:
            print(
                f"ERROR: pg_restore --list failed (exit {result.returncode})",
                file=sys.stderr,
            )
            return 1

        lines = result.stdout.strip().splitlines()
        print(f"  Objects in backup: {len(lines)}")
        print("  First 10 objects:")
        for line in lines[:10]:
            print(f"    {line}")
        if len(lines) > 10:
            print(f"    ... ({len(lines) - 10} more)")
        print("=== Check Mode: VALID ===")
        return 0

    # Dry-run mode
    if args.dry_run:
        print("=== Dry Run ===")
        print(f"  Would restore: {backup_path}")
        print(f"  Size:          {backup_path.stat().st_size / 1024:.1f} KB")
        print(f"  To:            {safe_url}")
        print(f"  Database:      {pg_env['PGDATABASE']}")
        print("  (Not executed — use without --dry-run to perform actual restore)")
        return 0

    # Safety gate
    confirmation = os.environ.get("REQUIRE_RESTORE_CONFIRMATION", "")
    if confirmation.strip().upper() not in ("YES", "1", "TRUE"):
        print(
            "ERROR: Restore requires explicit confirmation. "
            "Set REQUIRE_RESTORE_CONFIRMATION=yes to proceed.",
            file=sys.stderr,
        )
        return 1

    # Actual restore
    print("=== Restore ===")
    print(f"  Backup:     {backup_path}")
    print(f"  Size:       {backup_path.stat().st_size / 1024:.1f} KB")
    print(f"  Target:     {safe_url}")
    print(f"  Database:   {pg_env['PGDATABASE']}")
    print(f"  Time:       {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print()

    result = pg_restore_run(backup_path, pg_env)

    if result.returncode != 0:
        print(
            f"ERROR: pg_restore failed (exit {result.returncode})",
            file=sys.stderr,
        )
        return 1

    print("=== Restore: SUCCESS ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
