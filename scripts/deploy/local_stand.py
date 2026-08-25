#!/usr/bin/env python3
"""Lifecycle tool for the local DEV/QA stand (LOCAL-DEV-STAND-001).

The stand runs the published, digest-pinned private image bundle on a single
Docker host for MANUAL checking. It is explicitly disposable:

  * data may be lost, there is no backup and none is required;
  * it is reachable over plain HTTP on a trusted LAN - this is NOT
    production-safe TLS;
  * it is NOT the pilot and NOT production. Deployed production SHA is never
    changed by this tool.

Commands:
    preflight            run the read-only host preflight
    start                start the stand (provisions the app DB role, migrates)
    stop                 stop containers, keep volumes
    status               containers, health, version identity
    logs                 container logs
    update               switch to a new verified lock, roll back on failure
    reset --confirm NAME destroy ONLY this project's containers and volumes

Every docker command is scoped to the fixed project name below. The tool never
runs a system-wide prune and never touches resources outside the project.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# --- fixed identity ----------------------------------------------------------

PROJECT = "rmp-local-stand"          # exact, unique, never derived from input
STAND_KIND = "local-dev-stand"

ROOT = Path(__file__).resolve().parents[2]
PILOT_COMPOSE = ROOT / "infra" / "compose" / "docker-compose.pilot.yml"
STAND_COMPOSE = ROOT / "infra" / "compose" / "docker-compose.local-stand.yml"
STATE_DIR = ROOT / "state"
ENV_FILE = ROOT / "infra" / "deploy" / ".env.stand"

LOCK_CURRENT = STATE_DIR / "images.lock.json"
LOCK_PREVIOUS = STATE_DIR / "images.lock.previous.json"
RECORD_CURRENT = STATE_DIR / "deploy-record.json"
RECORD_PREVIOUS = STATE_DIR / "deploy-record.previous.json"

SERVICES = ["control-api", "device-gateway", "orchestrator-worker",
            "admin-web", "advertiser-web"]

IMAGE_ENV = {
    "control-api": "CONTROL_API_IMAGE",
    "device-gateway": "DEVICE_GATEWAY_IMAGE",
    "orchestrator-worker": "ORCHESTRATOR_WORKER_IMAGE",
    "admin-web": "ADMIN_WEB_IMAGE",
    "advertiser-web": "ADVERTISER_WEB_IMAGE",
}

APP_ROLE = "retail_media_app"
OWNER_ROLE = "retail_media_owner"
DB_NAME = "retail_media_platform"

_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(1)


def run(cmd: list[str], check: bool = True, capture: bool = False,
        stdin: str | None = None, timeout: int = 600):
    if capture:
        p = subprocess.run(cmd, capture_output=True, text=True,
                           input=stdin, timeout=timeout)
    else:
        p = subprocess.run(cmd, text=True, input=stdin, timeout=timeout)
    if check and p.returncode != 0:
        err = (p.stderr or "").strip() if capture else ""
        fail(f"command failed ({p.returncode}): {' '.join(cmd)}\n{err}")
    return p


def compose(*args: str, **kw):
    """Every compose invocation is pinned to PROJECT and both compose files."""
    cmd = ["docker", "compose", "-p", PROJECT,
           "-f", str(PILOT_COMPOSE), "-f", str(STAND_COMPOSE),
           "--env-file", str(ENV_FILE), *args]
    return run(cmd, **kw)


# --- lock handling -----------------------------------------------------------

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def verify_lock(lock_path: Path, sums_path: Path | None) -> dict:
    """A lock is only accepted if it is digest-only and, when a SHA256SUMS file
    is supplied, matches the published checksum for that exact filename."""
    if not lock_path.exists():
        fail(f"lock not found: {lock_path}")
    try:
        lock = json.loads(lock_path.read_text())
    except json.JSONDecodeError as e:
        fail(f"lock is not valid JSON: {e}")

    images = lock.get("images") or []
    if len(images) != len(SERVICES):
        fail(f"lock must contain exactly {len(SERVICES)} images, got {len(images)}")
    seen = set()
    for img in images:
        svc, digest, repo = img.get("service"), img.get("image_digest", ""), img.get("repository", "")
        if svc not in SERVICES:
            fail(f"unexpected service in lock: {svc}")
        if not _DIGEST_RE.match(str(digest)):
            fail(f"{svc}: image_digest is not digest-only: {digest!r}")
        if ":latest" in repo or repo.rsplit(":", 1)[-1] in ("latest", "dev", "main", "master"):
            fail(f"{svc}: mutable tag in repository {repo!r}")
        seen.add(svc)
    if seen != set(SERVICES):
        fail(f"lock service set mismatch: missing {sorted(set(SERVICES) - seen)}")

    actual = sha256_file(lock_path)
    if sums_path is not None:
        if not sums_path.exists():
            fail(f"SHA256SUMS not found: {sums_path}")
        expected = None
        for line in sums_path.read_text().splitlines():
            parts = line.split()
            if len(parts) == 2 and parts[1].lstrip("*") == lock_path.name:
                expected = parts[0]
        if expected is None:
            fail(f"SHA256SUMS has no entry for {lock_path.name}")
        if expected != actual:
            fail(f"lock checksum mismatch: expected {expected}, got {actual}")
        print(f"  lock checksum verified against SHA256SUMS: {actual[:16]}...")
    else:
        print(f"  lock checksum (unverified, no SHA256SUMS supplied): {actual[:16]}...")

    lock["_checksum"] = actual
    return lock


def image_refs(lock: dict) -> dict[str, str]:
    registry = lock.get("registry") or "ghcr.io/santanas-dev/rmp-pilot"
    refs = {}
    for img in lock["images"]:
        repo = img.get("repository") or f"{registry}/{img['service']}"
        refs[IMAGE_ENV[img["service"]]] = f"{repo}@{img['image_digest']}"
    return refs


# --- env ---------------------------------------------------------------------

def read_env() -> dict[str, str]:
    if not ENV_FILE.exists():
        fail(f"env file missing: {ENV_FILE} (create it on the host, mode 0600)")
    env = {}
    for raw in ENV_FILE.read_text().splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()
    return env


def version_identity(lock: dict) -> dict[str, str]:
    """Version identity the deployed images must report.

    The images read RMP_VERSION/RMP_GIT_SHA from the environment, so switching
    the lock without switching these leaves /version advertising the previous
    release - which is exactly what the identity check is meant to catch, and
    what made the first successful pull still fail verification.
    """
    rel = lock.get("release") or {}
    identity = {}
    version = rel.get("version") or rel.get("tag")
    if version:
        identity["RMP_VERSION"] = version
    if rel.get("git_sha"):
        identity["RMP_GIT_SHA"] = rel["git_sha"]
    return identity


def write_env_images(refs: dict[str, str]) -> None:
    """Rewrite only the given keys; every other value is left untouched."""
    lines = ENV_FILE.read_text().splitlines()
    out, seen = [], set()
    for line in lines:
        key = line.partition("=")[0].strip()
        if key in refs:
            out.append(f"{key}={refs[key]}")
            seen.add(key)
        else:
            out.append(line)
    for k, v in refs.items():
        if k not in seen:
            out.append(f"{k}={v}")
    ENV_FILE.write_text("\n".join(out) + "\n")
    ENV_FILE.chmod(0o600)


def validate_stand_env(env: dict, bind: str) -> list[str]:
    """Stand-specific env rules on top of validate-pilot-env.py.

    Browser-side upload uses presigned URLs, so the object endpoint the browser
    is handed must be the address the browser can actually reach, and the API
    must allow the two stand origins. Getting either wrong makes creative and
    contract upload fail in the browser while every backend check still passes.
    """
    problems: list[str] = []

    endpoint = env.get("MINIO_PUBLIC_ENDPOINT", "")
    if not endpoint:
        problems.append("MINIO_PUBLIC_ENDPOINT is empty")
    else:
        # The MinIO SDK parses this as host[:port] and rejects a scheme or path
        # outright ("path in endpoint is not allowed"), which surfaces as a 500
        # on every presigned-URL request. Observed on the stand.
        if endpoint.startswith(("http://", "https://")):
            problems.append(
                f"MINIO_PUBLIC_ENDPOINT ({endpoint}) must NOT include a scheme - "
                f"the MinIO SDK rejects it; use host:port and set MINIO_SECURE")
        if "/" in endpoint:
            problems.append(
                f"MINIO_PUBLIC_ENDPOINT ({endpoint}) must not contain a path")
        host = endpoint.split(":", 1)[0]
        if host != bind:
            problems.append(
                f"MINIO_PUBLIC_ENDPOINT ({endpoint}) must point at the published "
                f"bind address {bind}:9000, otherwise browser upload cannot reach it")
        if host in ("localhost", "127.0.0.1", "minio"):
            problems.append(
                f"MINIO_PUBLIC_ENDPOINT ({endpoint}) is host-internal; the browser "
                f"cannot resolve it")

    cors = env.get("CORS_ALLOWED_ORIGINS", "")
    required = {f"http://{bind}:3000", f"http://{bind}:3001"}
    present = {o.strip() for o in cors.split(",") if o.strip()}
    missing = required - present
    if missing:
        problems.append(f"CORS_ALLOWED_ORIGINS missing stand origins: {sorted(missing)}")
    if "*" in present:
        problems.append("CORS_ALLOWED_ORIGINS must not contain a wildcard")

    return problems


# --- deploy record -----------------------------------------------------------

def write_record(lock: dict) -> dict:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    rel = lock.get("release") or {}
    record = {
        "stand": STAND_KIND,
        "project": PROJECT,
        "disposable": True,
        "backup": "none - test data may be lost",
        "source_sha": rel.get("git_sha"),
        "release_tag": rel.get("tag") or rel.get("version"),
        "lock_checksum": lock.get("_checksum"),
        "image_digests": {i["service"]: i["image_digest"] for i in lock["images"]},
        "deployed_at": _now(),
        "note": "LOCAL DEV/QA STAND. Not the pilot, not production. "
                "Deployed production SHA is unchanged (UNKNOWN/NOT TRACKED).",
    }
    RECORD_CURRENT.write_text(json.dumps(record, indent=2) + "\n")
    return record


def save_previous() -> None:
    """Preserve the current lock + record before an update, for rollback."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if LOCK_CURRENT.exists():
        shutil.copy2(LOCK_CURRENT, LOCK_PREVIOUS)
    if RECORD_CURRENT.exists():
        shutil.copy2(RECORD_CURRENT, RECORD_PREVIOUS)


# --- failure diagnostics -----------------------------------------------------

# Secret-shaped values are stripped before anything is written: an env value is
# only ever reported as present/absent, never printed.
# Names that LOOK secret-shaped but are booleans/labels worth seeing: hiding
# REFRESH_TOKEN_COOKIE_SECURE would redact the very flag a cookie-gate failure
# needs. Matched first so the generic rule below cannot swallow them.
_NON_SECRET_KEYS = (
    "REFRESH_TOKEN_COOKIE_SECURE",
    "REFRESH_TOKEN_COOKIE_SAMESITE",
    "REFRESH_TOKEN_COOKIE_NAME",
    "REFRESH_TOKEN_COOKIE_PATH",
    "LOCAL_STAND_MODE",
    "SEED_DEV_CREDENTIALS",
    "METRICS_AUTH_TOKEN_REQUIRED",
)
_NON_SECRET_RE = re.compile(
    r"(?i)^(?:" + "|".join(_NON_SECRET_KEYS) + r")\s*[=:]")

_SECRET_RE = re.compile(
    r"(?i)((?:password|secret|token|key|dsn)[\w-]*\s*[=:]\s*)(\S+)")
_URL_PW_RE = re.compile(r"(://[^:/@\s]+:)([^@/\s]+)(@)")

# Env names whose PRESENCE (not value) matters for the local-stand cookie gate.
_GATE_KEYS = ("LOCAL_STAND_MODE", "REFRESH_TOKEN_COOKIE_SECURE",
              "ENVIRONMENT", "SEED_DEV_CREDENTIALS", "CORS_ALLOWED_ORIGINS")


def _sanitize(text: str) -> str:
    """Redact secret values, but keep the diagnostic flags readable."""
    lines = []
    for line in (text or "").splitlines():
        if _NON_SECRET_RE.match(line.strip()):
            lines.append(line)          # a boolean/label, not a credential
            continue
        out = _SECRET_RE.sub(r"\1<redacted>", line)
        lines.append(_URL_PW_RE.sub(r"\1<redacted>\3", out))
    return "\n".join(lines)


def collect_diagnostics(dest: Path) -> Path:
    """Capture why an update failed - BEFORE anything is torn down.

    A rollback removes the failed containers, taking their logs with them, so
    this must run first or the evidence is gone. Everything written here is
    sanitized; no secret value is recorded.
    """
    dest.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report = dest / f"update-failure-{stamp}.txt"
    chunks: list[str] = [f"=== local-stand update failure {stamp} ==="]

    def _add(title: str, body: str) -> None:
        chunks.append(f"\n--- {title} ---\n{_sanitize(body).strip()}")

    p = compose("config", capture=True, check=False)
    _add("resolved compose config (sanitized)", p.stdout or p.stderr)

    p = compose("ps", "-a", capture=True, check=False)
    _add("compose ps -a", p.stdout or p.stderr)

    p = run(["docker", "ps", "-a", "--filter",
             f"label=com.docker.compose.project={PROJECT}",
             "--format", "{{.Names}}|{{.State}}|{{.Status}}"],
            capture=True, check=False)
    rows = [r for r in (p.stdout or "").splitlines() if r.strip()]
    _add("container states", "\n".join(rows))

    for row in rows:
        name = row.split("|", 1)[0]
        insp = run(["docker", "inspect", "--format",
                    "state={{.State.Status}} exit={{.State.ExitCode}} "
                    "health={{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}} "
                    "image={{.Image}}", name], capture=True, check=False)
        state = (insp.stdout or "").strip()
        _add(f"inspect {name}", state)

        if "exit=0" not in state or "health=unhealthy" in state:
            logs = run(["docker", "logs", "--tail", "120", name],
                       capture=True, check=False)
            _add(f"logs {name} (sanitized, last 120)",
                 (logs.stdout or "") + (logs.stderr or ""))

        env = run(["docker", "inspect", "--format",
                   "{{range .Config.Env}}{{println .}}{{end}}", name],
                  capture=True, check=False)
        present = []
        for line in (env.stdout or "").splitlines():
            key = line.split("=", 1)[0]
            if key in _GATE_KEYS:
                # ENVIRONMENT and the two flags are not secrets; the rest is
                # reported as presence only.
                if key in ("ENVIRONMENT", "LOCAL_STAND_MODE",
                           "REFRESH_TOKEN_COOKIE_SECURE", "SEED_DEV_CREDENTIALS"):
                    present.append(line)
                else:
                    present.append(f"{key}=<set>")
        _add(f"gate env {name}", "\n".join(present) or "(none of the gate keys set)")

    report.write_text("\n".join(chunks) + "\n")
    report.chmod(0o600)
    return report


# --- health ------------------------------------------------------------------

def _http_json(url: str, timeout: int = 5):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode())


def wait_healthy(timeout_s: int = 300) -> tuple[bool, list[str]]:
    """Wait until every container with a healthcheck reports healthy.

    State-based: it polls docker's own health state and never sleeps past a
    real failure to make a red run look green.
    """
    deadline = time.time() + timeout_s
    unhealthy: list[str] = []
    while time.time() < deadline:
        p = compose("ps", "--format", "json", capture=True, check=False)
        rows = []
        for line in (p.stdout or "").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            rows.extend(obj if isinstance(obj, list) else [obj])
        if rows:
            unhealthy = [r.get("Name", "?") for r in rows
                         if r.get("Health") not in ("healthy", "", None)
                         or r.get("State") not in ("running", "exited")]
            if not unhealthy:
                return True, []
        time.sleep(3)
    return False, unhealthy


def verify_identity(bind: str, tag: str, sha: str) -> list[str]:
    """Check /version and build-info against the deployed lock. No retry masking."""
    problems = []
    checks = [
        (f"http://{bind}:8000/version", "control-api", True),
        ("http://127.0.0.1:8001/version", "device-gateway", False),
        (f"http://{bind}:3000/build-info.json", "admin-web", True),
        (f"http://{bind}:3001/build-info.json", "advertiser-web", True),
    ]
    for url, name, check_tag in checks:
        try:
            d = _http_json(url)
        except Exception as e:
            problems.append(f"{name}: {url} unreachable ({e})")
            continue
        if d.get("git_sha") != sha:
            problems.append(f"{name}: git_sha={d.get('git_sha')} expected {sha}")
        if check_tag and d.get("version") != tag:
            problems.append(f"{name}: version={d.get('version')} expected {tag}")
    return problems


# --- database ----------------------------------------------------------------

def provision_app_role(env: dict) -> None:
    """Create the NOBYPASSRLS app role.

    Known gap carried by the v0.11.1 bundle (IMAGE-REGISTRY-001): the pilot
    compose does not create retail_media_app, because init-db.sql is dev-only
    and pilot forbids source bind mounts. create-app-role.py is staged for the
    next patch release; until then the role is provisioned here, exactly as
    scripts/ci/verify-pilot-run.sh does for the CI run proof.
    """
    app_pw = env.get("POSTGRES_APP_PASSWORD")
    owner = env.get("POSTGRES_OWNER_USER", OWNER_ROLE)
    db = env.get("POSTGRES_DB", DB_NAME)
    if not app_pw:
        fail("POSTGRES_APP_PASSWORD missing from env file")

    exists = compose("exec", "-T", "postgres", "psql", "-U", owner, "-d", db,
                     "-tAc", f"SELECT 1 FROM pg_roles WHERE rolname='{APP_ROLE}'",
                     capture=True, check=False)
    if (exists.stdout or "").strip() == "1":
        print(f"  app role {APP_ROLE} already present")
        return

    sql = (
        f"CREATE ROLE {APP_ROLE} LOGIN PASSWORD '{app_pw}' "
        f"NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;\n"
        f"GRANT CONNECT ON DATABASE {db} TO {APP_ROLE};\n"
        f"GRANT USAGE ON SCHEMA public TO {APP_ROLE};\n"
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {APP_ROLE};\n"
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        f"GRANT USAGE, SELECT ON SEQUENCES TO {APP_ROLE};\n"
    )
    compose("exec", "-T", "postgres", "psql", "-U", owner, "-d", db,
            "-v", "ON_ERROR_STOP=1", stdin=sql, capture=True)
    print(f"  app role {APP_ROLE} provisioned (NOBYPASSRLS)")


def check_nobypassrls(env: dict) -> bool:
    owner = env.get("POSTGRES_OWNER_USER", OWNER_ROLE)
    db = env.get("POSTGRES_DB", DB_NAME)
    p = compose("exec", "-T", "postgres", "psql", "-U", owner, "-d", db, "-tAc",
                f"SELECT rolbypassrls FROM pg_roles WHERE rolname='{APP_ROLE}'",
                capture=True, check=False)
    return (p.stdout or "").strip().lower() in ("f", "false")


# --- commands ----------------------------------------------------------------

def cmd_preflight(args) -> int:
    tool = ROOT / "scripts" / "deploy" / "pilot_host_preflight.py"
    if not tool.exists():
        fail(f"preflight tool missing: {tool}")
    cmd = [sys.executable, str(tool), "--compose", str(PILOT_COMPOSE)]
    if ENV_FILE.exists():
        cmd += ["--env", str(ENV_FILE)]
    if LOCK_CURRENT.exists():
        cmd += ["--lock", str(LOCK_CURRENT)]
    req = ROOT / "infra" / "deploy" / "host-requirements.json"
    if req.exists():
        cmd += ["--requirements", str(req)]
    if args.skip_registry:
        cmd.append("--skip-registry")
    return subprocess.run(cmd).returncode


def _bring_up(env: dict) -> None:
    print("=== starting postgres ===")
    compose("up", "-d", "postgres")
    deadline = time.time() + 180
    status = "missing"
    while time.time() < deadline:
        p = run(["docker", "inspect", "--format", "{{.State.Health.Status}}",
                 f"{PROJECT}-postgres-1"], capture=True, check=False)
        status = (p.stdout or "").strip()
        if status == "healthy":
            break
        time.sleep(2)
    if status != "healthy":
        fail(f"postgres not healthy (status={status})")
    provision_app_role(env)

    print("=== starting the stand ===")
    compose("up", "-d")

    print("=== waiting for db-migrate ===")
    deadline = time.time() + 420
    state = "missing"
    while time.time() < deadline:
        p = run(["docker", "inspect", "--format", "{{.State.Status}}",
                 f"{PROJECT}-db-migrate-1"], capture=True, check=False)
        state = (p.stdout or "").strip()
        if state == "exited":
            break
        time.sleep(3)
    p = run(["docker", "inspect", "--format", "{{.State.ExitCode}}",
             f"{PROJECT}-db-migrate-1"], capture=True, check=False)
    code = (p.stdout or "").strip()
    if code != "0":
        compose("logs", "db-migrate", check=False)
        fail(f"db-migrate exit code={code}")
    print("  db-migrate completed (exit 0)")


def cmd_start(args) -> int:
    env = read_env()
    env_problems = validate_stand_env(env, args.bind)
    if env_problems:
        fail("stand env invalid: " + "; ".join(env_problems))
    if not LOCK_CURRENT.exists():
        fail(f"no lock deployed yet: {LOCK_CURRENT} (use 'update --lock ...')")
    lock = verify_lock(LOCK_CURRENT, None)
    write_env_images({**image_refs(lock), **version_identity(lock)})
    _bring_up(env)

    ok, unhealthy = wait_healthy()
    if not ok:
        fail(f"services did not become healthy: {', '.join(unhealthy)}")
    print("  all services healthy")

    rel = lock.get("release") or {}
    problems = verify_identity(args.bind, rel.get("tag") or rel.get("version"),
                               rel.get("git_sha"))
    if problems:
        fail("version identity mismatch: " + "; ".join(problems))
    print("  version identity OK")
    if not check_nobypassrls(env):
        fail(f"{APP_ROLE} does not have NOBYPASSRLS")
    print(f"  {APP_ROLE} NOBYPASSRLS confirmed")

    record = write_record(lock)
    print(f"\nstand up: source_sha={record['source_sha']} "
          f"lock={record['lock_checksum'][:16]}...")
    return 0


def cmd_stop(args) -> int:
    compose("stop")
    print(f"{PROJECT} stopped (volumes kept)")
    return 0


def cmd_status(args) -> int:
    compose("ps", check=False)
    if RECORD_CURRENT.exists():
        rec = json.loads(RECORD_CURRENT.read_text())
        print(f"\nsource_sha  : {rec.get('source_sha')}")
        print(f"release_tag : {rec.get('release_tag')}")
        print(f"lock        : {rec.get('lock_checksum')}")
        print(f"deployed_at : {rec.get('deployed_at')}")
        print(f"disposable  : {rec.get('disposable')} (backup: {rec.get('backup')})")
    else:
        print("\nno deploy record yet")
    return 0


def cmd_logs(args) -> int:
    extra = ["--tail", str(args.tail)]
    if args.follow:
        extra.append("-f")
    compose("logs", *extra, *(args.service or []), check=False)
    return 0


def cmd_update(args) -> int:
    env = read_env()
    new_lock_path = Path(args.lock).resolve()
    sums = Path(args.sha256sums).resolve() if args.sha256sums else None
    if sums is None and not args.allow_unverified:
        fail("update requires --sha256sums from the published release "
             "(or --allow-unverified, which is not recommended)")

    print("=== verifying new lock ===")
    new_lock = verify_lock(new_lock_path, sums)

    print("=== saving current deploy record for rollback ===")
    save_previous()
    had_previous = LOCK_PREVIOUS.exists()

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(new_lock_path, LOCK_CURRENT)
    write_env_images({**image_refs(new_lock), **version_identity(new_lock)})

    print("=== applying update ===")
    try:
        _bring_up(env)
        ok, unhealthy = wait_healthy()
        if not ok:
            raise RuntimeError(f"unhealthy: {', '.join(unhealthy)}")
        rel = new_lock.get("release") or {}
        problems = verify_identity(args.bind, rel.get("tag") or rel.get("version"),
                                   rel.get("git_sha"))
        if problems:
            raise RuntimeError("; ".join(problems))
    except (RuntimeError, SystemExit) as e:
        print(f"\nUPDATE FAILED: {e}", file=sys.stderr)
        # Evidence first: rollback deletes the failed containers and their logs.
        try:
            report = collect_diagnostics(STATE_DIR / "diagnostics")
            print(f"diagnostics written: {report}", file=sys.stderr)
        except Exception as diag_err:            # never mask the real failure
            print(f"diagnostics collection failed: {diag_err}", file=sys.stderr)
        if not had_previous:
            fail("no previous lock to roll back to; stand left stopped")
        print("=== rolling back to previous lock ===")
        shutil.copy2(LOCK_PREVIOUS, LOCK_CURRENT)
        prev = verify_lock(LOCK_CURRENT, None)
        write_env_images({**image_refs(prev), **version_identity(prev)})
        _bring_up(env)
        ok, unhealthy = wait_healthy()
        if RECORD_PREVIOUS.exists():
            shutil.copy2(RECORD_PREVIOUS, RECORD_CURRENT)
        if not ok:
            fail(f"rollback also unhealthy: {', '.join(unhealthy)}")
        print("rolled back to the previous lock; stand healthy")
        return 1

    write_record(new_lock)
    print("update applied and verified")
    return 0


def cmd_reset(args) -> int:
    if args.confirm != PROJECT:
        fail(f"reset requires --confirm {PROJECT} (got {args.confirm!r})")
    # Scoped to this project only. No system-wide prune, ever.
    compose("down", "-v", "--remove-orphans", check=False)
    print(f"{PROJECT} reset: containers and volumes for this project removed")
    print("note: images, other projects and system resources were not touched")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--bind", default=os.environ.get("STAND_BIND_ADDR", "127.0.0.1"),
                   help="host address the stand publishes on (for verification URLs)")
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("preflight"); sp.add_argument("--skip-registry", action="store_true")
    sp.set_defaults(func=cmd_preflight)

    sub.add_parser("start").set_defaults(func=cmd_start)
    sub.add_parser("stop").set_defaults(func=cmd_stop)
    sub.add_parser("status").set_defaults(func=cmd_status)

    sl = sub.add_parser("logs")
    sl.add_argument("service", nargs="*")
    sl.add_argument("--tail", default=200)
    sl.add_argument("-f", "--follow", action="store_true")
    sl.set_defaults(func=cmd_logs)

    su = sub.add_parser("update")
    su.add_argument("--lock", required=True)
    su.add_argument("--sha256sums")
    su.add_argument("--allow-unverified", action="store_true")
    su.set_defaults(func=cmd_update)

    sr = sub.add_parser("reset")
    sr.add_argument("--confirm", required=True,
                    help=f"must be exactly {PROJECT}")
    sr.set_defaults(func=cmd_reset)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
