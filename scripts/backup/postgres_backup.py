#!/usr/bin/env python3
"""
PostgreSQL backup script for Retail Media Platform.

Reads DATABASE_URL or individual PG* env vars. Runs pg_dump in custom format.
Writes timestamped backup file to BACKUP_DIR. Supports retention (keep last N
or older than D days). Prints safe summary — no secrets in output.

Usage:
    DATABASE_URL=postgresql://... python scripts/backup/postgres_backup.py
    DATABASE_URL=... BACKUP_DIR=/backups KEEP_LAST=5 python scripts/backup/postgres_backup.py
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


def parse_db_url(url: str) -> dict[str, str]:
    """Parse DATABASE_URL into pg_dump-compatible env vars."""
    parsed = urlparse(url)
    if parsed.scheme not in ("postgres", "postgresql", "postgresql+asyncpg"):
        raise ValueError(f"Unsupported scheme: {parsed.scheme}")
    host = parsed.hostname or "localhost"
    port = str(parsed.port) if parsed.port else "5432"
    dbname = parsed.path.lstrip("/") if parsed.path else ""
    user = parsed.username or ""
    password = parsed.password or ""
    return {
        "PGHOST": host,
        "PGPORT": port,
        "PGDATABASE": dbname,
        "PGUSER": user,
        "PGPASSWORD": password,
    }


def run_pg_dump(pg_env: dict[str, str], output_path: Path) -> subprocess.CompletedProcess:
    """Run pg_dump in custom format. Returns CompletedProcess."""
    env = os.environ.copy()
    env.update(pg_env)
    return subprocess.run(
        ["pg_dump", "-Fc", "--no-owner", "--no-acl", "-f", str(output_path)],
        env=env,
        capture_output=True,
        text=True,
    )


def clean_old_backups(backup_dir: Path, keep_last: int | None, older_than_days: int | None) -> list[Path]:
    """Remove old backups according to retention policy. Returns list of removed files."""
    backups = sorted(
        backup_dir.glob("rmp_backup_*.dump"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not backups:
        return []

    removed: list[Path] = []

    # Keep last N
    if keep_last is not None and keep_last > 0:
        for old in backups[keep_last:]:
            old.unlink()
            removed.append(old)

    # Remove older than D days
    if older_than_days is not None and older_than_days > 0:
        cutoff = datetime.now(timezone.utc).timestamp() - (older_than_days * 86400)
        for b in backups:
            if b.exists() and b.stat().st_mtime < cutoff:
                b.unlink()
                if b not in removed:
                    removed.append(b)

    return removed


def redact_url(database_url: str) -> str:
    """Redact password from DATABASE_URL for safe logging."""
    return re.sub(r":([^:@/]+)@", r":***@", database_url)


def main() -> int:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        # Build from individual PG vars
        user = os.environ.get("PGUSER", "")
        password = os.environ.get("PGPASSWORD", "")
        host = os.environ.get("PGHOST", "localhost")
        port = os.environ.get("PGPORT", "5432")
        dbname = os.environ.get("PGDATABASE", "retail_media_platform")
        if password:
            database_url = f"postgresql://{user}:***@{host}:{port}/{dbname}"
        else:
            database_url = f"postgresql://{user}@{host}:{port}/{dbname}"

    backup_dir = Path(os.environ.get("BACKUP_DIR", str(Path.cwd() / "backups")))
    backup_dir.mkdir(parents=True, exist_ok=True)

    keep_last = None
    if os.environ.get("KEEP_LAST"):
        keep_last = int(os.environ["KEEP_LAST"])

    older_than_days = None
    if os.environ.get("KEEP_OLDER_THAN_DAYS"):
        older_than_days = int(os.environ["KEEP_OLDER_THAN_DAYS"])

    # Parse connection
    full_url = os.environ.get("DATABASE_URL", "")
    if not full_url:
        print("ERROR: DATABASE_URL is not set", file=sys.stderr)
        return 1

    try:
        pg_env = parse_db_url(full_url)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    # Generate filename
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    db_name = pg_env["PGDATABASE"]
    filename = f"rmp_backup_{db_name}_{timestamp}.dump"
    output_path = backup_dir / filename

    # Run pg_dump
    result = run_pg_dump(pg_env, output_path)

    if result.returncode != 0:
        # Don't print stderr verbatim — may contain connection details
        print(
            f"ERROR: pg_dump failed with exit code {result.returncode}. "
            "Check pg_dump availability and database connectivity.",
            file=sys.stderr,
        )
        # Clean up partial file
        if output_path.exists():
            output_path.unlink()
        return 1

    if not output_path.exists() or output_path.stat().st_size == 0:
        print("ERROR: Backup file is empty or missing.", file=sys.stderr)
        return 1

    file_size = output_path.stat().st_size
    size_str = f"{file_size / 1024:.1f} KB" if file_size < 1024 * 1024 else f"{file_size / (1024*1024):.1f} MB"

    # Retention cleanup
    removed = clean_old_backups(backup_dir, keep_last, older_than_days)

    # Safe summary
    print("=== Backup Summary ===")
    print(f"  File:     {output_path}")
    print(f"  Size:     {size_str}")
    print(f"  Database: {db_name}")
    print(f"  Time:     {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"  URL:      {redact_url(database_url)}")

    if keep_last is not None:
        print(f"  Retention: keep last {keep_last}")
    if older_than_days is not None:
        print(f"  Retention: older than {older_than_days} days")

    if removed:
        print(f"  Cleaned:  {len(removed)} old backup(s) removed")
    else:
        print("  Cleaned:  0 old backups removed")
    print("=== Status: SUCCESS ===")

    return 0


if __name__ == "__main__":
    sys.exit(main())
