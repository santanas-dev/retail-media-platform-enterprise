#!/usr/bin/env python3
"""Quiesced backup orchestrator (PILOT-DEPLOYMENT-READINESS-001C, SCOPE B).

Orchestrates a consistent (quiesced) Layer-1 backup by reusing the existing
per-component tools (postgres_backup.py, minio_backup.py) and producing a
single unified manifest that ties PostgreSQL + MinIO to one logical point.

Quiesce contract:
    1. enter maintenance / stop app writers
    2. wait for in-flight operations to drain
    3. record migration head + deployed candidate SHA
    4. PostgreSQL backup
    5. MinIO backup
    6. assemble unified manifest
    7. only after manifest verification succeed → resume writers

In the pilot drill the source contour runs no app writers (the contour is
provisioned, migrated, seeded, then quiesced-by-construction), so the quiesce
step is a no-op but is still recorded. For a real host, `--quiesce-command`
allows an operator hook (e.g. `docker compose stop control-api …`).

Never prints secrets.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.backup import backup_manifest  # noqa: E402

POSTGRES_BACKUP = REPO_ROOT / "scripts" / "backup" / "postgres_backup.py"
MINIO_BACKUP = REPO_ROOT / "scripts" / "backup" / "minio_backup.py"


def _run(cmd: list[str], env: dict[str, str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=600, env=env)


def _require_env(env: dict[str, str], *keys: str) -> None:
    missing = [k for k in keys if not env.get(k, "").strip()]
    if missing:
        print(f"ERROR: missing required env vars: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)


def _server_version_pg(env: dict[str, str]) -> str:
    """Query server version via psql; return '' if unavailable."""
    host = env.get("PGHOST", "localhost")
    port = env.get("PGPORT", "5432")
    user = env.get("PGUSER", "retail_media_owner")
    db = env.get("PGDATABASE", "retail_media_platform")
    pw = env.get("PGPASSWORD", "")
    sub_env = dict(env)
    sub_env["PGPASSWORD"] = pw
    try:
        proc = _run(
            ["psql", "-h", host, "-p", port, "-U", user, "-d", db,
             "-Atc", "SHOW server_version;"],
            sub_env,
        )
        if proc.returncode == 0:
            return proc.stdout.strip().splitlines()[0]
    except Exception:
        pass
    return ""


def _alembic_head(env: dict[str, str]) -> str:
    host = env.get("PGHOST", "localhost")
    port = env.get("PGPORT", "5432")
    user = env.get("PGUSER", "retail_media_owner")
    db = env.get("PGDATABASE", "retail_media_platform")
    pw = env.get("PGPASSWORD", "")
    sub_env = dict(env)
    sub_env["PGPASSWORD"] = pw
    try:
        proc = _run(
            ["psql", "-h", host, "-p", port, "-U", user, "-d", db,
             "-Atc", "SELECT version_num FROM alembic_version;"],
            sub_env,
        )
        if proc.returncode == 0:
            return proc.stdout.strip().splitlines()[0]
    except Exception:
        pass
    return ""


def _row_counts(env: dict[str, str]) -> dict[str, int]:
    host = env.get("PGHOST", "localhost")
    port = env.get("PGPORT", "5432")
    user = env.get("PGUSER", "retail_media_owner")
    db = env.get("PGDATABASE", "retail_media_platform")
    pw = env.get("PGPASSWORD", "")
    sub_env = dict(env)
    sub_env["PGPASSWORD"] = pw
    counts: dict[str, int] = {}
    for tbl in backup_manifest.CONTROL_TABLES:
        try:
            proc = _run(
                ["psql", "-h", host, "-p", port, "-U", user, "-d", db,
                 "-Atc", f"SELECT count(*) FROM {tbl};"],
                sub_env,
            )
            if proc.returncode == 0:
                counts[tbl] = int(proc.stdout.strip())
        except Exception:
            counts[tbl] = -1
    return counts


def _minio_server_version(env: dict[str, str]) -> str:
    """MinIO server version, injected by the deploy process or probed via mc.

    Prefers an explicit MINIO_SERVER_VERSION env var (build/deploy injects the
    image tag — no runtime introspection needed). Falls back to ``mc admin
    info``, then ''.
    """
    explicit = env.get("MINIO_SERVER_VERSION", "").strip()
    if explicit:
        return explicit
    mc = env.get("MC_BIN", "") or "mc"
    endpoint = env.get("MINIO_ENDPOINT", "localhost:9000")
    access = env.get("MINIO_ACCESS_KEY", "")
    secret = env.get("MINIO_SECRET_KEY", "")
    try:
        sub_env = dict(env)
        sub_env["MC_HOST"] = "http://" + endpoint
        proc = _run(
            [mc, "alias", "set", "backup-src", f"http://{endpoint}", access, secret],
            sub_env,
        )
        if proc.returncode != 0:
            return ""
        proc = _run([mc, "admin", "info", "backup-src", "--json"], sub_env)
        if proc.returncode == 0:
            info = json.loads(proc.stdout)
            return info.get("info", {}).get("version", "")
    except Exception:
        pass
    return ""


def run_quiesced_backup(
    *,
    backup_root: Path,
    source_env: dict[str, str],
    git_sha: str,
    version: str,
    environment: str,
    quiesce_command: str | None,
    resume_command: str | None,
    quiesce_mode: str,
    quiesce_evidence: str,
    encryption_enabled: bool,
    rpo_target_seconds: int,
) -> dict[str, Any]:
    """Execute a quiesced backup. Returns the manifest dict."""
    _require_env(source_env, "DATABASE_URL")

    # 0. Quiescence gate — fail-closed BEFORE any backup artifact is created.
    # In pilot/production, consistency_mode=quiesced without proven quiescence
    # is a lie; refuse up front. dev/drill is quiesced-by-construction.
    problems = backup_manifest.check_quiescence_evidence(
        environment, quiesce_mode, quiesce_evidence,
    )
    if problems:
        for pr in problems:
            print(f"ERROR: {pr}", file=sys.stderr)
        sys.exit(1)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = backup_root / timestamp
    pg_dir = run_dir / "postgres"
    minio_dir = run_dir / "minio"
    run_dir.mkdir(parents=True, exist_ok=True)

    # 1. Quiesce (writers stopped / maintenance entered)
    if quiesce_command:
        proc = subprocess.run(quiesce_command, shell=True, capture_output=True, text=True)
        if proc.returncode != 0:
            print(
                f"ERROR: quiesce command failed (exit {proc.returncode}): {proc.stderr}",
                file=sys.stderr,
            )
            sys.exit(1)
    # (drill: no writers by construction)

    # 2. record head + version
    pg_version = _server_version_pg(source_env)
    head = _alembic_head(source_env)

    # 3. PostgreSQL backup
    pg_env = dict(source_env)
    pg_env["BACKUP_DIR"] = str(pg_dir)
    proc = _run([sys.executable, str(POSTGRES_BACKUP)], pg_env)
    if proc.returncode != 0:
        print(f"ERROR: postgres_backup failed:\n{proc.stderr}", file=sys.stderr)
        sys.exit(1)

    dumps = sorted(pg_dir.glob("*.dump"))
    if len(dumps) != 1:
        print(f"ERROR: expected exactly one .dump, found {len(dumps)}", file=sys.stderr)
        sys.exit(1)
    dump_path = dumps[0]
    dump_sha = backup_manifest.sha256_file(dump_path)

    # 4. MinIO backup
    # 4. MinIO backup — one invocation per bucket (minio_backup.py is
    # single-bucket). Multiple buckets are backed into per-bucket subdirs.
    minio_env = dict(source_env)
    minio_buckets = [
        b.strip() for b in minio_env.get("MINIO_BUCKETS", "").split(",") if b.strip()
    ]
    if not minio_buckets and minio_env.get("MINIO_BUCKET", "").strip():
        minio_buckets = [minio_env["MINIO_BUCKET"].strip()]

    buckets_meta: dict[str, dict[str, Any]] = {}
    for bucket in minio_buckets:
        bucket_dir = minio_dir / bucket
        bucket_dir.mkdir(parents=True, exist_ok=True)
        bucket_env = dict(minio_env)
        bucket_env["MINIO_BUCKET"] = bucket
        bucket_env["BACKUP_DIR"] = str(bucket_dir)
        proc = _run([sys.executable, str(MINIO_BACKUP)], bucket_env)
        if proc.returncode != 0:
            print(f"ERROR: minio_backup failed for {bucket}:\n{proc.stderr}", file=sys.stderr)
            sys.exit(1)
        # Ingest the per-bucket manifest produced by minio_backup.py
        mfs = list(bucket_dir.glob("*/manifest.json"))
        if not mfs:
            print(f"ERROR: minio_backup produced no manifest for {bucket}", file=sys.stderr)
            sys.exit(1)
        with open(mfs[0]) as f:
            m = json.load(f)
        # minio_backup.py writes objects under <bucket_dir>/<timestamp>/data/<key>.
        # Store an explicit data_rel path so disk verification can locate each
        # file without re-deriving the timestamped layout.
        ts_dir = mfs[0].parent
        data_rel_prefix = ts_dir.relative_to(run_dir)
        objects = []
        for o in m.get("objects", []):
            obj = dict(o)
            obj["data_rel"] = str(data_rel_prefix / "data" / o["key"])
            objects.append(obj)
        buckets_meta[bucket] = {
            "object_count": m.get("object_count", 0),
            "total_size_bytes": m.get("total_size_bytes", 0),
            "objects": objects,
        }

    # 5. row counts
    counts = _row_counts(source_env)

    # 6. assemble manifest
    manifest = backup_manifest.build_manifest(
        backup_dir=run_dir,
        git_sha=git_sha,
        version=version,
        alembic_head=head,
        postgres_server_version=pg_version,
        minio_server_version=_minio_server_version(source_env),
        dump_file=dump_path.relative_to(run_dir),
        dump_sha256=dump_sha,
        row_counts=counts,
        buckets=buckets_meta,
        backup_tool_version="001C-1.0.0",
        encryption_enabled=encryption_enabled,
        encryption_status="enabled" if encryption_enabled else "none",
        rpo_target_seconds=rpo_target_seconds,
        environment=environment,
        quiesce_mode=quiesce_mode,
        quiesce_evidence=quiesce_evidence,
    )
    manifest_path = run_dir / "backup-manifest.json"
    backup_manifest.write_manifest(manifest, manifest_path)

    # 7. verify against disk before resuming writers
    problems = backup_manifest.verify_manifest_against_disk(manifest, run_dir)
    if problems:
        for pr in problems:
            print(f"ERROR: manifest verification failed: {pr}", file=sys.stderr)
        sys.exit(1)

    if resume_command:
        subprocess.run(resume_command, shell=True, check=False)

    return manifest


def main() -> int:
    p = argparse.ArgumentParser(description="Quiesced backup orchestrator (001C)")
    p.add_argument("--backup-root", default=os.environ.get("BACKUP_ROOT", "./backups"))
    p.add_argument("--git-sha", default=os.environ.get("RMP_GIT_SHA", "unknown"))
    p.add_argument("--version", default=os.environ.get("RMP_VERSION", "dev"))
    p.add_argument("--environment", default=os.environ.get("ENVIRONMENT", "pilot"))
    p.add_argument("--quiesce-command", default=os.environ.get("QUIESCE_COMMAND", ""))
    p.add_argument("--resume-command", default=os.environ.get("RESUME_COMMAND", ""))
    p.add_argument("--quiesce-mode", default=os.environ.get("QUIESCE_MODE", "writers-stopped"))
    p.add_argument("--quiesce-evidence", default=os.environ.get("QUIESCE_EVIDENCE", ""))
    p.add_argument("--encryption-enabled", action="store_true",
                   default=os.environ.get("BACKUP_ENCRYPTION_ENABLED", "false").lower() == "true")
    p.add_argument("--rpo-target-seconds", type=int,
                   default=int(os.environ.get("RPO_TARGET_SECONDS", "0")))
    args = p.parse_args()

    source_env = dict(os.environ)
    manifest = run_quiesced_backup(
        backup_root=Path(args.backup_root),
        source_env=source_env,
        git_sha=args.git_sha,
        version=args.version,
        environment=args.environment,
        quiesce_command=args.quiesce_command or None,
        resume_command=args.resume_command or None,
        quiesce_mode=args.quiesce_mode,
        quiesce_evidence=args.quiesce_evidence,
        encryption_enabled=args.encryption_enabled,
        rpo_target_seconds=args.rpo_target_seconds,
    )
    print("=== Quiesced Backup Summary ===")
    print(f"  Directory:      {manifest['backup_dir']}")
    print(f"  Alembic head:   {manifest['postgres']['alembic_head']}")
    print(f"  PG version:     {manifest['postgres']['server_version']}")
    print(f"  Dump SHA-256:   {manifest['postgres']['dump_sha256'][:16]}…")
    print(f"  Row counts:     {len(manifest['postgres']['row_counts'])} tables")
    print(f"  MinIO buckets:  {len(manifest['minio']['buckets'])}")
    print(f"  Consistency:    {manifest['consistency_mode']}")
    print("=== Status: SUCCESS ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
