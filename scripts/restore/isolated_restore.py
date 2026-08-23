#!/usr/bin/env python3
"""Isolated restore orchestrator (PILOT-DEPLOYMENT-READINESS-001C, SCOPE E).

Restores a quiesced backup into a fully separate, disposable environment.

Safety guards (enforced BEFORE any mutation):
  - refuse if source endpoint == target endpoint (DSN/endpoint identity check)
  - refuse if target is non-empty unless --drill flag is explicitly set
  - no wildcard volume/container deletion — cleanup only by exact compose
    project name (handled by the CI wrapper, not this script)
  - manifest + checksums must verify before any restore

Restore order:
  1. verify manifest + checksums
  2. (caller) bring up empty PostgreSQL + MinIO
  3. restore roles/ownership safely (owner credential only)
  4. restore PostgreSQL
  5. restore MinIO objects/metadata
  6. verify alembic head
  7. (caller) start runtime under retail_media_app NOBYPASSRLS
  8. (caller) run verification suite

Never prints secrets.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.backup import backup_manifest  # noqa: E402

POSTGRES_RESTORE = REPO_ROOT / "scripts" / "restore" / "postgres_restore.py"
MINIO_RESTORE = REPO_ROOT / "scripts" / "restore" / "minio_restore.py"


def _identity(dsn: str) -> tuple[str, str]:
    """Normalise a DSN/endpoint into an (host, port) identity for equality checks."""
    if "://" in dsn:
        u = urlparse(dsn)
        return (u.hostname or "", str(u.port or ""))
    return (dsn, "")


def _same_endpoint(a: str, b: str) -> bool:
    """True if two DSN/endpoint strings resolve to the same host:port."""
    return _identity(a) == _identity(b)


def _target_pg_empty(target_env: dict[str, str]) -> bool:
    host = target_env.get("PGHOST", "localhost")
    port = target_env.get("PGPORT", "5432")
    user = target_env.get("PGUSER", "retail_media_owner")
    db = target_env.get("PGDATABASE", "retail_media_platform")
    pw = target_env.get("PGPASSWORD", "")
    env = dict(target_env)
    env["PGPASSWORD"] = pw
    try:
        proc = subprocess.run(
            ["psql", "-h", host, "-p", port, "-U", user, "-d", db,
             "-Atc", "SELECT count(*) FROM pg_tables WHERE schemaname='public';"],
            capture_output=True, text=True, timeout=60, env=env,
        )
        if proc.returncode != 0:
            return False  # can't determine — treat as non-empty (fail-closed)
        return int(proc.stdout.strip()) == 0
    except Exception:
        return False


def guard_source_target_distinct(
    source_dsn: str,
    target_dsn: str,
    source_minio_endpoint: str,
    target_minio_endpoint: str,
) -> list[str]:
    """Return list of violation messages (empty = safe)."""
    problems: list[str] = []
    if source_dsn and target_dsn and _same_endpoint(source_dsn, target_dsn):
        problems.append(
            "source and target PostgreSQL endpoints are identical — refusing to restore"
        )
    if (
        source_minio_endpoint
        and target_minio_endpoint
        and _same_endpoint(source_minio_endpoint, target_minio_endpoint)
    ):
        problems.append(
            "source and target MinIO endpoints are identical — refusing to restore"
        )
    return problems


def guard_nonempty_target(target_is_empty: bool, allow_nonempty: bool) -> list[str]:
    """Refuse restoring into a non-empty target unless the drill flag is set."""
    if allow_nonempty:
        return []
    if not target_is_empty:
        return ["target PostgreSQL is not empty and --drill was not set — refusing to restore"]
    return []


def run_isolated_restore(
    *,
    backup_dir: Path,
    target_env: dict[str, str],
    source_dsn: str,
    source_minio_endpoint: str,
    allow_nonempty_target: bool,
) -> dict[str, str]:
    """Execute an isolated restore. Returns a summary dict (no secrets)."""
    manifest_path = backup_dir / "backup-manifest.json"
    if not manifest_path.exists():
        print(f"ERROR: {manifest_path} not found", file=sys.stderr)
        sys.exit(1)

    manifest = backup_manifest.load_manifest(manifest_path)

    # 1. Verify manifest + checksums against disk
    problems = backup_manifest.verify_manifest_against_disk(manifest, backup_dir)
    if problems:
        for pr in problems:
            print(f"ERROR: manifest verification failed: {pr}", file=sys.stderr)
        sys.exit(1)

    # Safety guard: source != target
    target_dsn = target_env.get("DATABASE_URL", "")
    target_minio_endpoint = target_env.get("MINIO_ENDPOINT", "")
    guard_problems = guard_source_target_distinct(
        source_dsn, target_dsn, source_minio_endpoint, target_minio_endpoint,
    )
    if guard_problems:
        for pr in guard_problems:
            print(f"ERROR: {pr}", file=sys.stderr)
        sys.exit(1)

    # Safety guard: non-empty target
    nonempty_problems = guard_nonempty_target(
        _target_pg_empty(target_env), allow_nonempty_target,
    )
    if nonempty_problems:
        for pr in nonempty_problems:
            print(f"ERROR: {pr}", file=sys.stderr)
        sys.exit(1)

    # 2. restore PostgreSQL (owner credential; roles handled by --no-owner)
    pg_restore_env = dict(target_env)
    pg_restore_env["REQUIRE_RESTORE_CONFIRMATION"] = "yes"
    dump_rel = manifest["postgres"]["dump_file"]
    dump_path = backup_dir / dump_rel
    proc = subprocess.run(
        [sys.executable, str(POSTGRES_RESTORE), str(dump_path)],
        capture_output=True, text=True, timeout=600, env=pg_restore_env,
    )
    if proc.returncode != 0:
        print(f"ERROR: postgres_restore failed:\n{proc.stderr}", file=sys.stderr)
        sys.exit(1)

    # 3. restore MinIO objects per bucket
    for bucket in manifest["minio"]["buckets"]:
        bucket_backup_dir = backup_dir / "minio"
        # minio_restore.py expects a backup dir containing manifest.json + data/
        # (bucket-scoped). Layout is minio/<bucket>/<timestamp>/manifest.json.
        bucket_manifest_dir = None
        for mf in sorted(bucket_backup_dir.glob("**/manifest.json")):
            import json as _json
            with open(mf) as f:
                m = _json.load(f)
            if m.get("bucket") == bucket:
                bucket_manifest_dir = mf.parent
                break
        if bucket_manifest_dir is None:
            print(f"ERROR: no MinIO backup dir for bucket {bucket!r}", file=sys.stderr)
            sys.exit(1)
        minio_env = dict(target_env)
        minio_env["MINIO_BUCKET"] = bucket
        minio_env["REQUIRE_RESTORE_CONFIRMATION"] = "yes"
        minio_env["MINIO_ENDPOINT"] = target_env.get("MINIO_ENDPOINT", "")
        minio_env["MINIO_ACCESS_KEY"] = target_env.get("MINIO_ACCESS_KEY", "")
        minio_env["MINIO_SECRET_KEY"] = target_env.get("MINIO_SECRET_KEY", "")
        proc = subprocess.run(
            [sys.executable, str(MINIO_RESTORE), str(bucket_manifest_dir)],
            capture_output=True, text=True, timeout=600, env=minio_env,
        )
        if proc.returncode != 0:
            print(f"ERROR: minio_restore failed for {bucket}:\n{proc.stderr}", file=sys.stderr)
            sys.exit(1)

    # 4. verify alembic head
    head = _alembic_head(target_env)
    expected_head = manifest["postgres"]["alembic_head"]
    if head != expected_head:
        print(
            f"ERROR: alembic head mismatch — expected {expected_head}, got {head}",
            file=sys.stderr,
        )
        sys.exit(1)

    return {
        "status": "success",
        "alembic_head": head,
        "buckets": ",".join(manifest["minio"]["buckets"].keys()),
        "row_count_tables": str(len(manifest["postgres"]["row_counts"])),
    }


def _alembic_head(target_env: dict[str, str]) -> str:
    host = target_env.get("PGHOST", "localhost")
    port = target_env.get("PGPORT", "5432")
    user = target_env.get("PGUSER", "retail_media_owner")
    db = target_env.get("PGDATABASE", "retail_media_platform")
    pw = target_env.get("PGPASSWORD", "")
    env = dict(target_env)
    env["PGPASSWORD"] = pw
    proc = subprocess.run(
        ["psql", "-h", host, "-p", port, "-U", user, "-d", db,
         "-Atc", "SELECT version_num FROM alembic_version;"],
        capture_output=True, text=True, timeout=60, env=env,
    )
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip().splitlines()[0]


def main() -> int:
    p = argparse.ArgumentParser(description="Isolated restore orchestrator (001C)")
    p.add_argument("backup_dir", type=Path)
    p.add_argument("--source-dsn", default=os.environ.get("SOURCE_DATABASE_URL", ""))
    p.add_argument("--source-minio", default=os.environ.get("SOURCE_MINIO_ENDPOINT", ""))
    p.add_argument("--drill", action="store_true",
                   help="allow restoring into a non-empty target (isolated drill only)")
    args = p.parse_args()

    target_env = dict(os.environ)
    summary = run_isolated_restore(
        backup_dir=args.backup_dir,
        target_env=target_env,
        source_dsn=args.source_dsn,
        source_minio_endpoint=args.source_minio,
        allow_nonempty_target=args.drill,
    )
    print("=== Isolated Restore Summary ===")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    print("=== Status: SUCCESS ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
