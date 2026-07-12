"""
Restore drill integration test.

Proves the full path: backup -> restore -> verify integrity.
Creates test data in source DB, backs up, restores to target, verifies.

Requires:
  - RUN_BACKUP_RESTORE_TESTS=1
  - PostgreSQL with seed data + migrations
  - pg_dump / pg_restore on PATH
  - Target DB must exist and be empty

Usage:
  RUN_BACKUP_RESTORE_TESTS=1 python -m pytest tests/integration/test_backup_restore.py -v

Skips silently when env is not set.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

REQUIRE_ENV = os.environ.get("RUN_BACKUP_RESTORE_TESTS", "") == "1"
SKIP_REASON = "RUN_BACKUP_RESTORE_TESTS=1 not set."

pytestmark = pytest.mark.skipif(not REQUIRE_ENV, reason=SKIP_REASON)

# Read defaults from docker-compose to avoid hardcoding secrets.


def _read_compose_db_password() -> str:
    """Read POSTGRES_PASSWORD from docker-compose.phase1.yml."""
    compose_path = Path("infra/compose/docker-compose.phase1.yml")
    if not compose_path.exists():
        return "retail_media_owner_pass"
    text = compose_path.read_text()
    match = re.search(r"POSTGRES_PASSWORD:\s*(\S+)", text)
    return match.group(1) if match else "retail_media_owner_pass"


def _get_source_db_url() -> str:
    """Build source DB URL from env or compose defaults."""
    if os.environ.get("BACKUP_RESTORE_SOURCE_DB_URL"):
        return os.environ["BACKUP_RESTORE_SOURCE_DB_URL"]
    pw = _read_compose_db_password()
    host = os.environ.get("PGHOST", "localhost")
    port = os.environ.get("PGPORT", "5432")
    user = os.environ.get("PGUSER", "retail_media_owner")
    db = os.environ.get("PGDATABASE", "retail_media_platform")
    url = "postgresql://" + user + ":" + pw + "@" + host + ":" + port + "/" + db
    return url


def _get_target_db_url() -> str:
    """Build target DB URL from env or compose defaults."""
    if os.environ.get("BACKUP_RESTORE_TARGET_DB_URL"):
        return os.environ["BACKUP_RESTORE_TARGET_DB_URL"]
    pw = _read_compose_db_password()
    host = os.environ.get("PGHOST", "localhost")
    port = os.environ.get("PGPORT", "5432")
    user = os.environ.get("PGUSER", "retail_media_owner")
    url = "postgresql://" + user + ":" + pw + "@" + host + ":" + port + "/rmp_restore_target"
    return url


def _pg_env(url: str) -> dict[str, str]:
    """Split a postgresql:// URL into env dict for subprocess."""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    pw = parsed.password or ""
    return {
        "PGHOST": parsed.hostname or "localhost",
        "PGPORT": str(parsed.port or 5432),
        "PGUSER": parsed.username or "",
        "PGPASSWORD": pw,
        "PGDATABASE": parsed.path.lstrip("/") or "postgres",
    }


def _run_psql(db_url: str, query: str) -> subprocess.CompletedProcess:
    """Run a query via psql."""
    pg = _pg_env(db_url)
    env = os.environ.copy()
    env["PGPASSWORD"] = pg["PGPASSWORD"]
    return subprocess.run(
        ["psql", "-h", pg["PGHOST"], "-p", pg["PGPORT"],
         "-U", pg["PGUSER"], "-d", pg["PGDATABASE"],
         "-c", query, "-t"],
        capture_output=True, text=True, timeout=30, env=env,
    )


def _get_table_names(db_url: str) -> list[str]:
    """Return sorted list of table names in public schema."""
    proc = _run_psql(
        db_url,
        "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;",
    )
    if proc.returncode != 0:
        return []
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def _get_row_counts(db_url: str) -> dict[str, int]:
    """Return {table_name: approximate_row_count} for all public tables."""
    proc = _run_psql(
        db_url,
        "SELECT relname, n_live_tup FROM pg_stat_user_tables ORDER BY relname;",
    )
    if proc.returncode != 0:
        return {}
    counts: dict[str, int] = {}
    for line in proc.stdout.splitlines():
        parts = line.strip().split("|")
        if len(parts) >= 2:
            name = parts[0].strip()
            try:
                counts[name] = int(parts[1].strip())
            except ValueError:
                pass
    return counts


def _create_target_db():
    """Create the target database if not exists."""
    pg = _pg_env(_get_source_db_url())
    # Connect to 'postgres' to create target DB
    env = os.environ.copy()
    env["PGPASSWORD"] = pg["PGPASSWORD"]
    subprocess.run(
        ["psql", "-h", pg["PGHOST"], "-p", pg["PGPORT"],
         "-U", pg["PGUSER"], "-d", "postgres",
         "-c", "CREATE DATABASE rmp_restore_target OWNER retail_media_owner;"],
        capture_output=True, text=True, timeout=30, env=env,
    )


def _drop_target_tables():
    """Drop all tables in target DB."""
    proc = _run_psql(
        _get_target_db_url(),
        "DROP SCHEMA public CASCADE; CREATE SCHEMA public;",
    )


@pytest.fixture(scope="module")
def backup_dir():
    """Create temporary directory for backup files. Cleaned up after all tests."""
    with tempfile.TemporaryDirectory(prefix="rmp_backup_drill_") as d:
        yield Path(d)


def _find_dump(backup_dir: Path) -> Path:
    """Find the single .dump file in backup_dir. Fails if not exactly one."""
    files = sorted(backup_dir.glob("*.dump"))
    if not files:
        raise FileNotFoundError("No .dump files found in " + str(backup_dir))
    if len(files) > 1:
        raise RuntimeError("Multiple .dump files in " + str(backup_dir) + ": " + str(files))
    return files[0]


class TestBackupRestoreDrill:
    """End-to-end restore drill: backup, restore, verify."""

    def test_1_backup_creates_file(self, backup_dir):
        """Backup the source DB - must produce a .dump file > 0 bytes."""
        env = os.environ.copy()
        env["DATABASE_URL"] = _get_source_db_url()
        env["BACKUP_DIR"] = str(backup_dir)

        proc = subprocess.run(
            [sys.executable, "scripts/backup/postgres_backup.py"],
            capture_output=True, text=True, timeout=120, env=env,
        )

        assert proc.returncode == 0, "Backup failed: " + proc.stderr
        assert "SUCCESS" in proc.stdout, "No SUCCESS in output: " + proc.stdout

        dump_path = _find_dump(backup_dir)
        assert dump_path.stat().st_size > 0, "Backup file is empty"

    def test_2_backup_check_mode(self, backup_dir):
        """Verify the backup file is valid with pg_restore --list."""
        dump_path = _find_dump(backup_dir)
        env = os.environ.copy()
        env["DATABASE_URL"] = _get_source_db_url()

        proc = subprocess.run(
            [sys.executable, "scripts/restore/postgres_restore.py",
             str(dump_path), "--check"],
            capture_output=True, text=True, timeout=120, env=env,
        )

        assert proc.returncode == 0, "Check failed: " + proc.stderr
        assert "VALID" in proc.stdout, "No VALID in output: " + proc.stdout
        assert "Objects in backup:" in proc.stdout, "No object count: " + proc.stdout

    def test_3_restore_to_target(self, backup_dir):
        """Restore the backup to target DB and verify integrity."""
        dump_path = _find_dump(backup_dir)
        file_size_kb = dump_path.stat().st_size / 1024

        source_url = _get_source_db_url()
        target_url = _get_target_db_url()

        _create_target_db()
        _drop_target_tables()

        source_tables = _get_table_names(source_url)
        source_counts = _get_row_counts(source_url)
        assert len(source_tables) > 0, "Source DB has no tables"

        env = os.environ.copy()
        env["DATABASE_URL"] = target_url
        env["REQUIRE_RESTORE_CONFIRMATION"] = "yes"

        proc = subprocess.run(
            [sys.executable, "scripts/restore/postgres_restore.py",
             str(dump_path)],
            capture_output=True, text=True, timeout=300, env=env,
        )

        assert proc.returncode == 0, "Restore failed: " + proc.stderr
        assert "SUCCESS" in proc.stdout, "No SUCCESS in output: " + proc.stdout

        target_tables = _get_table_names(target_url)
        target_counts = _get_row_counts(target_url)

        source_set = set(source_tables)
        target_set = set(target_tables)
        missing = source_set - target_set
        extra = target_set - source_set

        assert not missing, "Tables missing in target: " + str(missing)
        assert not extra, "Unexpected tables in target: " + str(extra)

        key_tables = ["campaigns", "creative_assets", "advertiser_organizations",
                      "local_credentials", "permissions"]
        mismatched = []
        for tbl in key_tables:
            src = source_counts.get(tbl, 0)
            tgt = target_counts.get(tbl, 0)
            if src != tgt:
                mismatched.append(tbl + ": source=" + str(src) + " target=" + str(tgt))

        assert not mismatched, "Row count mismatches: " + str(mismatched)

        result = _run_psql(
            target_url,
            "SELECT name FROM campaigns LIMIT 1;",
        )
        assert result.returncode == 0, "Query failed: " + result.stderr
        assert len(result.stdout.strip()) > 0, \
            "Expected non-empty campaign name in target"

        print("\n=== Restore Drill Results ===")
        print("  Backup size:  " + str(round(file_size_kb, 1)) + " KB")
        print("  Source tables: " + str(len(source_tables)))
        print("  Target tables: " + str(len(target_tables)))
        counts_str = ", ".join(t + "=" + str(target_counts.get(t, 0)) for t in key_tables)
        print("  Key row counts match: " + counts_str)
        print("  Status: PASS")

    def test_4_restore_requires_confirmation(self, backup_dir):
        """Restore must fail without REQUIRE_RESTORE_CONFIRMATION."""
        dump_path = _find_dump(backup_dir)

        env = os.environ.copy()
        env["DATABASE_URL"] = _get_target_db_url()

        proc = subprocess.run(
            [sys.executable, "scripts/restore/postgres_restore.py",
             str(dump_path)],
            capture_output=True, text=True, timeout=60, env=env,
        )

        assert proc.returncode != 0, "Restore should have failed without confirmation"
        assert "confirmation" in proc.stderr.lower(), \
            "Expected confirmation error, got: " + proc.stderr

    def test_5_dry_run_noop(self, backup_dir):
        """Dry-run must not execute the restore."""
        dump_path = _find_dump(backup_dir)

        env = os.environ.copy()
        env["DATABASE_URL"] = _get_target_db_url()

        proc = subprocess.run(
            [sys.executable, "scripts/restore/postgres_restore.py",
             str(dump_path), "--dry-run"],
            capture_output=True, text=True, timeout=60, env=env,
        )

        assert proc.returncode == 0, "Dry run failed: " + proc.stderr
        assert "Not executed" in proc.stdout or "Would restore" in proc.stdout, \
            "Unexpected dry-run output: " + proc.stdout
