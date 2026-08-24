#!/usr/bin/env python3
"""Read-only pilot host preflight (PILOT-DEPLOYMENT-READINESS-001D).

Fail-closed preflight for the pilot Docker host.  Performs NO deployment: it
never runs ``compose up``, migrations, restore, seed, or any application
service, and never pulls an image (registry checks use manifest inspection).

Verdict / exit codes:
    0  GO                 — every check passed
    2  NEEDS_OWNER_INPUT  — no failures, but owner-supplied facts are missing
    1  FAIL               — at least one check failed

Requirement values the repository does not document (CPU/RAM/disk thresholds,
Docker versions, DNS/TLS/backup/monitoring facts) are read from a requirements
JSON supplied by the owner (see infra/deploy/host-requirements.example.json).
A missing value yields MISSING (owner input), never an invented threshold.

Usage:
    python scripts/deploy/pilot_host_preflight.py [--json] [--requirements PATH]
        [--env PATH] [--lock PATH] [--compose PATH] [--skip-registry]
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import socket
import stat
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_COMPOSE = REPO_ROOT / "infra" / "compose" / "docker-compose.pilot.yml"
DEFAULT_ENV = REPO_ROOT / "infra" / "deploy" / ".env.pilot"
DEFAULT_LOCK = REPO_ROOT / "infra" / "deploy" / "images.lock.json"
DEFAULT_REQUIREMENTS = REPO_ROOT / "infra" / "deploy" / "host-requirements.json"

# --- Facts derived from the repository (NOT configurable, NOT invented) ------

# PROJECT_STATE / IMAGE-REGISTRY-001: single-arch linux/amd64.
SUPPORTED_OS = "linux"
SUPPORTED_ARCH = {"x86_64", "amd64"}

# Host ports published by infra/compose/docker-compose.pilot.yml.
REQUIRED_PORTS = [8000, 8001, 3000, 3001]

# Services packaged in the image lock (validate-image-lock.py DEFAULT_SERVICES).
PILOT_SERVICES = [
    "control-api",
    "device-gateway",
    "orchestrator-worker",
    "admin-web",
    "advertiser-web",
]

# Private GHCR namespace (IMAGE-REGISTRY-001-PRIVATE-REMEDIATION).
REGISTRY_NAMESPACE = "ghcr.io/santanas-dev/rmp-pilot"

# Compose project name + declared volumes (docker-compose.pilot.yml).
COMPOSE_PROJECT = "rmp-pilot"
PILOT_VOLUMES = ["pg_data", "minio_data", "nats_jetstream"]

# Outbound endpoints the pilot must reach to obtain images.
OUTBOUND_HOSTS = ["github.com", "ghcr.io"]

# Env var names required by the pilot compose (names only — values never read
# into the report).
REQUIRED_ENV_NAMES = [
    "ENVIRONMENT", "RMP_VERSION", "RMP_GIT_SHA", "RMP_BUILD_TIME", "RMP_SCHEMA_HEAD",
    "POSTGRES_OWNER_USER", "POSTGRES_OWNER_PASSWORD", "POSTGRES_APP_USER",
    "POSTGRES_APP_PASSWORD", "POSTGRES_DB", "DATABASE_URL", "MIGRATION_DATABASE_URL",
    "JWT_SECRET", "JWT_AUDIENCE", "MANIFEST_SIGNING_KEY",
    "MINIO_ROOT_USER", "MINIO_ROOT_PASSWORD", "MINIO_INTERNAL_ENDPOINT",
    "MINIO_PUBLIC_ENDPOINT", "MINIO_ACCESS_KEY", "MINIO_SECRET_KEY",
    "CREATIVE_STORAGE_BUCKET", "CONTRACT_STORAGE_BUCKET",
    "CORS_ALLOWED_ORIGINS", "CORS_ALLOW_CREDENTIALS", "METRICS_AUTH_TOKEN",
    "SEED_DEV_CREDENTIALS", "LICENSE_DEV_INGEST_ENABLED", "BACKUP_DIR",
    "CONTROL_API_IMAGE", "DEVICE_GATEWAY_IMAGE", "ORCHESTRATOR_WORKER_IMAGE",
    "ADMIN_WEB_IMAGE", "ADVERTISER_WEB_IMAGE",
]

# Env file permission ceiling: no group/other access.
_FORBIDDEN_ENV_MODE = stat.S_IRWXG | stat.S_IRWXO

PASS, FAIL, MISSING, SKIP = "PASS", "FAIL", "MISSING", "SKIP"

# --- Redaction ---------------------------------------------------------------

_SECRET_PATTERNS = [
    re.compile(r"(?i)\b(gh[pousr]_[A-Za-z0-9]{20,})"),
    re.compile(r"(?i)\b(github_pat_[A-Za-z0-9_]{20,})"),
    re.compile(r"(?i)(password|passwd|secret|token|api[_-]?key|access[_-]?key)"
               r"(\s*[=:]\s*)(\S+)"),
    re.compile(r"(?i)(://[^:/@\s]+:)([^@/\s]+)(@)"),
    re.compile(r"\b(eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,})"),
    re.compile(r"(?i)-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]


def redact(text: Any) -> Any:
    """Mask anything that looks like a credential.  Applied to every detail."""
    if not isinstance(text, str):
        return text
    out = text
    out = _SECRET_PATTERNS[0].sub("<redacted-token>", out)
    out = _SECRET_PATTERNS[1].sub("<redacted-token>", out)
    out = _SECRET_PATTERNS[2].sub(r"\1\2<redacted>", out)
    out = _SECRET_PATTERNS[3].sub(r"\1<redacted>\3", out)
    out = _SECRET_PATTERNS[4].sub("<redacted-jwt>", out)
    out = _SECRET_PATTERNS[5].sub("<redacted-private-key>", out)
    return out


@dataclass
class Check:
    id: str
    category: str
    status: str
    detail: str = ""

    def to_dict(self) -> dict:
        return {"id": self.id, "category": self.category,
                "status": self.status, "detail": redact(self.detail)}


@dataclass
class Report:
    checks: list[Check] = field(default_factory=list)

    def add(self, id: str, category: str, status: str, detail: str = "") -> None:
        self.checks.append(Check(id, category, status, detail))

    @property
    def failures(self) -> list[Check]:
        return [c for c in self.checks if c.status == FAIL]

    @property
    def missing(self) -> list[Check]:
        return [c for c in self.checks if c.status == MISSING]

    def verdict(self) -> str:
        if self.failures:
            return "FAIL"
        if self.missing:
            return "NEEDS_OWNER_INPUT"
        return "GO"

    def exit_code(self) -> int:
        return {"GO": 0, "FAIL": 1, "NEEDS_OWNER_INPUT": 2}[self.verdict()]


def _run(cmd: list[str], timeout: int = 20) -> tuple[int, str, str]:
    """Run a read-only command.  Never raises."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except FileNotFoundError:
        return 127, "", f"{cmd[0]}: not found"
    except subprocess.TimeoutExpired:
        return 124, "", f"{cmd[0]}: timeout after {timeout}s"
    except Exception as e:  # pragma: no cover - defensive
        return 1, "", str(e)


def _version_tuple(text: str) -> tuple[int, ...]:
    nums = re.findall(r"\d+", text or "")
    return tuple(int(n) for n in nums[:3]) or (0,)


# --- Checks ------------------------------------------------------------------

def check_platform(rep: Report) -> None:
    system = platform.system().lower()
    arch = platform.machine().lower()
    if system != SUPPORTED_OS:
        rep.add("platform.os", "platform", FAIL,
                f"OS '{system}' unsupported; pilot images are {SUPPORTED_OS}/amd64 single-arch")
    else:
        rep.add("platform.os", "platform", PASS, f"OS={system}")
    if arch not in SUPPORTED_ARCH:
        rep.add("platform.arch", "platform", FAIL,
                f"architecture '{arch}' unsupported; images are linux/amd64 only "
                f"(no arm64/multi-arch published)")
    else:
        rep.add("platform.arch", "platform", PASS, f"arch={arch}")


def check_docker(rep: Report, req: dict) -> None:
    if shutil.which("docker") is None:
        rep.add("docker.engine", "docker", FAIL, "docker binary not found on PATH")
        rep.add("docker.compose", "docker", FAIL, "docker not present; compose plugin unavailable")
        rep.add("docker.daemon", "docker", FAIL, "docker not present; daemon unreachable")
        rep.add("docker.access", "docker", FAIL, "docker not present; user access unverifiable")
        return

    rc, out, err = _run(["docker", "version", "--format", "{{.Server.Version}}"])
    if rc != 0 or not out:
        rep.add("docker.engine", "docker", FAIL,
                f"docker engine version unavailable: {err or out or 'no output'}")
        rep.add("docker.daemon", "docker", FAIL, "docker daemon did not respond")
        rep.add("docker.access", "docker", FAIL, "cannot query daemon; access unverifiable")
    else:
        engine = out
        min_engine = req.get("min_docker_engine_version")
        if min_engine in (None, ""):
            rep.add("docker.engine", "docker", MISSING,
                    f"engine={engine}; min_docker_engine_version not supplied by owner "
                    f"(repository documents no minimum)")
        elif _version_tuple(engine) < _version_tuple(str(min_engine)):
            rep.add("docker.engine", "docker", FAIL,
                    f"engine={engine} below required {min_engine}")
        else:
            rep.add("docker.engine", "docker", PASS, f"engine={engine} (>= {min_engine})")

        rc2, _, err2 = _run(["docker", "info", "--format", "{{.ServerVersion}}"])
        if rc2 == 0:
            rep.add("docker.daemon", "docker", PASS, "daemon responded to docker info")
            rep.add("docker.access", "docker", PASS,
                    "current user can reach the docker socket without elevation")
        else:
            rep.add("docker.daemon", "docker", FAIL, f"daemon unreachable: {err2}")
            rep.add("docker.access", "docker", FAIL,
                    f"docker socket not accessible to current user: {err2}")

    rc3, out3, err3 = _run(["docker", "compose", "version", "--short"])
    if rc3 != 0 or not out3:
        rep.add("docker.compose", "docker", FAIL,
                f"docker compose plugin unavailable: {err3 or 'no output'}")
    else:
        min_compose = req.get("min_compose_version")
        if min_compose in (None, ""):
            rep.add("docker.compose", "docker", MISSING,
                    f"compose={out3}; min_compose_version not supplied by owner")
        elif _version_tuple(out3) < _version_tuple(str(min_compose)):
            rep.add("docker.compose", "docker", FAIL,
                    f"compose={out3} below required {min_compose}")
        else:
            rep.add("docker.compose", "docker", PASS, f"compose={out3} (>= {min_compose})")


def _mem_total_gb() -> float | None:
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                return int(line.split()[1]) / (1024 * 1024)
    except Exception:
        return None
    return None


def check_resources(rep: Report, req: dict) -> None:
    cores = os.cpu_count() or 0
    min_cores = req.get("min_cpu_cores")
    if min_cores in (None, ""):
        rep.add("resources.cpu", "resources", MISSING,
                f"detected {cores} cores; min_cpu_cores not supplied by owner")
    elif cores < int(min_cores):
        rep.add("resources.cpu", "resources", FAIL,
                f"{cores} cores below required {min_cores}")
    else:
        rep.add("resources.cpu", "resources", PASS, f"{cores} cores (>= {min_cores})")

    mem = _mem_total_gb()
    min_mem = req.get("min_memory_gb")
    if mem is None:
        rep.add("resources.memory", "resources", FAIL, "cannot read /proc/meminfo")
    elif min_mem in (None, ""):
        rep.add("resources.memory", "resources", MISSING,
                f"detected {mem:.1f} GiB; min_memory_gb not supplied by owner")
    elif mem < float(min_mem):
        rep.add("resources.memory", "resources", FAIL,
                f"{mem:.1f} GiB below required {min_mem} GiB")
    else:
        rep.add("resources.memory", "resources", PASS, f"{mem:.1f} GiB (>= {min_mem})")

    data_root = req.get("persistent_data_root")
    min_disk = req.get("min_disk_free_gb")
    if data_root in (None, ""):
        rep.add("resources.disk", "resources", MISSING,
                "persistent_data_root not supplied by owner; cannot measure free space "
                "for docker volumes")
    else:
        p = Path(str(data_root))
        if not p.exists():
            rep.add("resources.disk", "resources", FAIL,
                    f"persistent_data_root '{data_root}' does not exist")
        else:
            free_gb = shutil.disk_usage(p).free / (1024 ** 3)
            if min_disk in (None, ""):
                rep.add("resources.disk", "resources", MISSING,
                        f"{free_gb:.1f} GiB free at {data_root}; min_disk_free_gb "
                        f"not supplied by owner")
            elif free_gb < float(min_disk):
                rep.add("resources.disk", "resources", FAIL,
                        f"{free_gb:.1f} GiB free at {data_root} below required {min_disk} GiB")
            else:
                rep.add("resources.disk", "resources", PASS,
                        f"{free_gb:.1f} GiB free at {data_root} (>= {min_disk})")
            if not os.access(p, os.W_OK):
                rep.add("resources.filesystem", "resources", FAIL,
                        f"persistent_data_root '{data_root}' is not writable")
            else:
                rep.add("resources.filesystem", "resources", PASS,
                        f"persistent_data_root '{data_root}' writable")


def check_clock(rep: Report) -> None:
    rc, out, _ = _run(["timedatectl", "show", "-p", "NTPSynchronized", "--value"])
    if rc == 0 and out:
        if out.strip().lower() in ("yes", "true", "1"):
            rep.add("clock.sync", "clock", PASS, "timedatectl reports NTPSynchronized=yes")
        else:
            rep.add("clock.sync", "clock", FAIL,
                    f"time synchronization not active (NTPSynchronized={out.strip()})")
        return
    for probe in (["chronyc", "tracking"], ["ntpq", "-p"]):
        rc2, out2, _ = _run(probe, timeout=10)
        if rc2 == 0 and out2:
            rep.add("clock.sync", "clock", PASS, f"{probe[0]} reports an active time source")
            return
    rep.add("clock.sync", "clock", MISSING,
            "no observable time-sync service (timedatectl/chronyc/ntpq absent); "
            "owner must confirm host clock discipline")


def _port_state(port: int) -> tuple[bool, str]:
    """Return (free, detail).  Bind test is read-only and released immediately."""
    for family, addr in ((socket.AF_INET, ("0.0.0.0", port)),):
        s = socket.socket(family, socket.SOCK_STREAM)
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(addr)
            return True, "free"
        except OSError as e:
            return False, f"occupied ({e.strerror})"
        finally:
            s.close()
    return False, "unknown"


def check_ports(rep: Report) -> None:
    for port in REQUIRED_PORTS:
        free, detail = _port_state(port)
        if free:
            rep.add(f"ports.{port}", "ports", PASS, f"host port {port} {detail}")
        else:
            owner = _port_owner(port)
            rep.add(f"ports.{port}", "ports", FAIL,
                    f"host port {port} {detail}; classified as: {owner}")


def _port_owner(port: int) -> str:
    """Classify what holds a port, without changing anything."""
    rc, out, _ = _run(["docker", "ps", "--format", "{{.Names}} {{.Ports}}"], timeout=15)
    if rc == 0 and out:
        for line in out.splitlines():
            if f":{port}->" in line:
                name = line.split()[0]
                if name.startswith(COMPOSE_PROJECT):
                    return f"existing pilot container '{name}' (deployment collision)"
                return f"docker container '{name}' (foreign)"
    rc2, out2, _ = _run(["ss", "-ltnp", f"sport = :{port}"], timeout=10)
    if rc2 == 0 and out2 and str(port) in out2:
        return "non-docker listener (see ss output on host)"
    return "unidentified listener"


def check_network(rep: Report) -> None:
    for host in OUTBOUND_HOSTS:
        try:
            socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
            rep.add(f"dns.{host}", "network", PASS, f"{host} resolves")
        except Exception as e:
            rep.add(f"dns.{host}", "network", FAIL, f"{host} does not resolve: {e}")
            continue
        try:
            with socket.create_connection((host, 443), timeout=10):
                rep.add(f"https.{host}", "network", PASS, f"outbound HTTPS to {host}:443 open")
        except Exception as e:
            rep.add(f"https.{host}", "network", FAIL,
                    f"outbound HTTPS to {host}:443 blocked: {e}")


def check_compose(rep: Report, compose: Path, env: Path) -> None:
    if not compose.exists():
        rep.add("compose.config", "compose", FAIL, f"pilot compose missing: {compose}")
        return
    if not env.exists():
        rep.add("compose.config", "compose", MISSING,
                f"env file {env.name} absent on this host; compose config not validated")
    else:
        rc, _, err = _run(["docker", "compose", "-f", str(compose),
                           "--env-file", str(env), "config"], timeout=60)
        if rc == 0:
            rep.add("compose.config", "compose", PASS, "pilot compose config validates")
        else:
            rep.add("compose.config", "compose", FAIL,
                    f"pilot compose config failed: {err[:400]}")

    try:
        import yaml  # noqa: PLC0415
        doc = yaml.safe_load(compose.read_text()) or {}
    except Exception as e:
        rep.add("compose.safety", "compose", FAIL, f"cannot parse pilot compose: {e}")
        return

    services = doc.get("services", {}) or {}
    problems: list[str] = []
    for name, spec in services.items():
        spec = spec or {}
        if "build" in spec:
            problems.append(f"{name}: build: present (images must come from the lock)")
        for vol in spec.get("volumes", []) or []:
            target = vol if isinstance(vol, str) else str(vol)
            src = target.split(":", 1)[0]
            if src.startswith((".", "/", "~", "$")):
                problems.append(f"{name}: source bind mount '{target}'")
        image = str(spec.get("image", ""))
        if image.endswith(":latest") or re.search(r":(latest|dev|develop|main|master)$", image):
            problems.append(f"{name}: mutable image tag '{image}'")
        envmap = spec.get("environment", {}) or {}
        items = envmap.items() if isinstance(envmap, dict) else (
            (e.split("=", 1)[0], e.split("=", 1)[-1]) for e in envmap)
        for k, v in items:
            v = "" if v is None else str(v)
            if k == "SEED_DEV_CREDENTIALS" and v.lower() not in ("false", "0", "no"):
                problems.append(f"{name}: SEED_DEV_CREDENTIALS not disabled")
            if k == "LICENSE_DEV_INGEST_ENABLED" and v.lower() not in ("false", "0", "no"):
                problems.append(f"{name}: LICENSE_DEV_INGEST_ENABLED not disabled")
            if v.lower() in ("minioadmin", "retail_media_owner_pass", "retail_media_app_pass",
                             "dev-secret-do-not-use-in-production"):
                problems.append(f"{name}: dev credential literal in {k}")

    if problems:
        rep.add("compose.safety", "compose", FAIL, "; ".join(problems))
    else:
        rep.add("compose.safety", "compose", PASS,
                "no build:/bind mounts/mutable tags/dev credentials/dev ingest in pilot compose")


def check_image_lock(rep: Report, lock: Path) -> None:
    if not lock.exists():
        rep.add("lock.present", "images", MISSING,
                f"image lock {lock.name} not present on this host (owner supplies the "
                f"release lock from the GitHub Release)")
        return
    rep.add("lock.present", "images", PASS, f"image lock present: {lock.name}")

    validator = REPO_ROOT / "scripts" / "deploy" / "validate-image-lock.py"
    rc, out, err = _run([sys.executable, str(validator), "--lock", str(lock),
                         "--services", ",".join(PILOT_SERVICES)], timeout=60)
    if rc == 0:
        rep.add("lock.valid", "images", PASS,
                "validate-image-lock.py: digests immutable, service set exact")
    else:
        rep.add("lock.valid", "images", FAIL,
                f"validate-image-lock.py rejected the lock: {(out + err)[:400]}")

    try:
        doc = json.loads(lock.read_text())
    except Exception as e:
        rep.add("lock.digests", "images", FAIL, f"lock is not valid JSON: {e}")
        return

    images = doc.get("images", []) or []
    digest_only = [i for i in images
                   if re.fullmatch(r"sha256:[0-9a-f]{64}", str(i.get("image_digest", "")))]
    if len(images) != len(PILOT_SERVICES) or len(digest_only) != len(PILOT_SERVICES):
        rep.add("lock.digests", "images", FAIL,
                f"expected {len(PILOT_SERVICES)} digest-only refs, "
                f"got {len(digest_only)} valid of {len(images)}")
    else:
        rep.add("lock.digests", "images", PASS,
                f"all {len(PILOT_SERVICES)} image references are digest-only")

    checksum = doc.get("checksum") or doc.get("sha256")
    if checksum:
        rep.add("lock.checksum", "images", PASS, f"lock records a checksum ({str(checksum)[:16]}…)")
    else:
        rep.add("lock.checksum", "images", MISSING,
                "lock has no embedded checksum field; owner must verify it against "
                "the release SHA256SUMS out of band")


def check_registry(rep: Report, lock: Path, skip: bool) -> None:
    if skip:
        rep.add("registry.auth", "registry", SKIP, "--skip-registry requested")
        return
    if shutil.which("docker") is None:
        rep.add("registry.auth", "registry", FAIL, "docker absent; cannot inspect manifests")
        return
    if not lock.exists():
        rep.add("registry.auth", "registry", MISSING,
                "no image lock on host; no digest refs to inspect")
        return
    try:
        images = json.loads(lock.read_text()).get("images", []) or []
    except Exception:
        rep.add("registry.auth", "registry", FAIL, "cannot read lock for registry check")
        return

    ref = None
    for img in images:
        repo, digest = img.get("repository"), img.get("image_digest")
        if repo and digest:
            ref = f"{repo}@{digest}"
            break
    if ref is None:
        rep.add("registry.auth", "registry", FAIL, "lock contains no usable digest reference")
        return

    # Authenticated manifest inspection — no pull.
    rc, _, err = _run(["docker", "manifest", "inspect", ref], timeout=60)
    if rc == 0:
        rep.add("registry.auth", "registry", PASS,
                f"authenticated manifest inspection succeeded for {ref.split('@')[0]}")
    else:
        rep.add("registry.auth", "registry", FAIL,
                f"authenticated manifest inspection failed: {err[:300]}")

    # Anonymous access to the private package must be denied.
    env = {k: v for k, v in os.environ.items() if k != "DOCKER_CONFIG"}
    env["DOCKER_CONFIG"] = "/nonexistent-anonymous-preflight"
    try:
        p = subprocess.run(["docker", "manifest", "inspect", ref],
                           capture_output=True, text=True, timeout=60, env=env)
        if p.returncode != 0:
            rep.add("registry.anonymous_denied", "registry", PASS,
                    "anonymous manifest inspection denied (package is private)")
        else:
            rep.add("registry.anonymous_denied", "registry", FAIL,
                    "anonymous manifest inspection SUCCEEDED — package appears public")
    except Exception as e:
        rep.add("registry.anonymous_denied", "registry", PASS,
                f"anonymous access rejected ({type(e).__name__})")


def check_env_file(rep: Report, env: Path) -> None:
    if not env.exists():
        rep.add("env.present", "env", MISSING,
                f"{env.name} absent; owner installs it on the target host only "
                f"(never committed)")
        return
    rep.add("env.present", "env", PASS, f"{env.name} present on host")

    mode = env.stat().st_mode
    if mode & _FORBIDDEN_ENV_MODE:
        rep.add("env.permissions", "env", FAIL,
                f"{env.name} mode {stat.filemode(mode)} grants group/other access; "
                f"expected owner-only (0600/0400)")
    else:
        rep.add("env.permissions", "env", PASS,
                f"{env.name} mode {stat.filemode(mode)} is owner-only")

    rc, out, _ = _run(["git", "-C", str(REPO_ROOT), "ls-files", "--error-unmatch",
                       str(env.relative_to(REPO_ROOT))] if _within_repo(env) else
                      ["git", "-C", str(REPO_ROOT), "ls-files", "--error-unmatch", str(env)],
                      timeout=15)
    if rc == 0 and out:
        rep.add("env.not_tracked", "env", FAIL,
                f"{env.name} is TRACKED by git — secrets must never be committed")
    else:
        rep.add("env.not_tracked", "env", PASS, f"{env.name} is not tracked by git")

    # Names only — values are never read into the report.
    present: set[str] = set()
    try:
        for raw in env.read_text().splitlines():
            line = raw.strip()
            if line and not line.startswith("#") and "=" in line:
                present.add(line.partition("=")[0].strip())
    except Exception as e:
        rep.add("env.required_names", "env", FAIL, f"cannot read {env.name}: {e}")
        return

    missing = [n for n in REQUIRED_ENV_NAMES if n not in present]
    if missing:
        rep.add("env.required_names", "env", FAIL,
                f"{len(missing)} required variable name(s) absent: {', '.join(sorted(missing))}")
    else:
        rep.add("env.required_names", "env", PASS,
                f"all {len(REQUIRED_ENV_NAMES)} required variable names present "
                f"(values not read)")

    validator = REPO_ROOT / "scripts" / "deploy" / "validate-pilot-env.py"
    rc2, out2, err2 = _run([sys.executable, str(validator), "--env", str(env)], timeout=60)
    if rc2 == 0:
        rep.add("env.no_weak_secrets", "env", PASS,
                "validate-pilot-env.py: no placeholder/dev/weak secrets")
    else:
        summary = [ln.strip() for ln in (out2 + "\n" + err2).splitlines()
                   if "ERROR:" in ln]
        rep.add("env.no_weak_secrets", "env", FAIL,
                f"validate-pilot-env.py rejected the env file: "
                f"{'; '.join(summary)[:400] or 'see validator output'}")


def _within_repo(p: Path) -> bool:
    try:
        p.resolve().relative_to(REPO_ROOT)
        return True
    except ValueError:
        return False


def check_storage(rep: Report, req: dict) -> None:
    dest = req.get("backup_destination")
    if dest in (None, ""):
        rep.add("storage.backup_destination", "storage", MISSING,
                "backup_destination not supplied by owner")
        return
    p = Path(str(dest))
    if not p.exists():
        rep.add("storage.backup_destination", "storage", FAIL,
                f"backup destination '{dest}' does not exist")
        return
    if not os.access(p, os.W_OK):
        rep.add("storage.backup_destination", "storage", FAIL,
                f"backup destination '{dest}' is not writable")
        return
    free_gb = shutil.disk_usage(p).free / (1024 ** 3)
    min_free = req.get("min_backup_disk_free_gb")
    if min_free in (None, ""):
        rep.add("storage.backup_destination", "storage", MISSING,
                f"backup destination '{dest}' writable, {free_gb:.1f} GiB free; "
                f"min_backup_disk_free_gb not supplied by owner")
    elif free_gb < float(min_free):
        rep.add("storage.backup_destination", "storage", FAIL,
                f"backup destination '{dest}' has {free_gb:.1f} GiB free, "
                f"below required {min_free} GiB")
    else:
        rep.add("storage.backup_destination", "storage", PASS,
                f"backup destination '{dest}' writable, {free_gb:.1f} GiB free")


def check_existing_deployment(rep: Report) -> None:
    if shutil.which("docker") is None:
        rep.add("collision.containers", "collision", FAIL,
                "docker absent; cannot detect an existing deployment")
        return
    rc, out, _ = _run(["docker", "ps", "-a", "--filter",
                       f"label=com.docker.compose.project={COMPOSE_PROJECT}",
                       "--format", "{{.Names}} {{.State}}"], timeout=20)
    if rc == 0 and out:
        rep.add("collision.containers", "collision", FAIL,
                f"existing '{COMPOSE_PROJECT}' containers present — deployment collision: "
                f"{'; '.join(out.splitlines())}")
    else:
        rep.add("collision.containers", "collision", PASS,
                f"no existing '{COMPOSE_PROJECT}' containers")

    rc2, out2, _ = _run(["docker", "volume", "ls", "--format", "{{.Name}}"], timeout=20)
    if rc2 == 0:
        existing = [v for v in out2.splitlines()
                    if v.strip() in {f"{COMPOSE_PROJECT}_{v2}" for v2 in PILOT_VOLUMES}]
        if existing:
            rep.add("collision.volumes", "collision", FAIL,
                    f"existing pilot volumes would be reused: {', '.join(existing)}")
        else:
            rep.add("collision.volumes", "collision", PASS,
                    f"no pre-existing {COMPOSE_PROJECT} volumes")
    else:
        rep.add("collision.volumes", "collision", FAIL, "cannot list docker volumes")


def check_owner_inputs(rep: Report, req: dict, req_path: Path, supplied: bool) -> None:
    if not supplied:
        rep.add("owner.requirements_file", "owner", MISSING,
                f"no requirements file at {req_path}; copy "
                f"host-requirements.example.json and fill it in")

    dns = req.get("dns_names") or {}
    for key in ("admin_web", "advertiser_web", "control_api", "device_gateway"):
        val = dns.get(key)
        if val in (None, ""):
            rep.add(f"owner.dns.{key}", "owner", MISSING, f"DNS name for {key} not supplied")
        else:
            try:
                socket.getaddrinfo(str(val), 443, proto=socket.IPPROTO_TCP)
                rep.add(f"owner.dns.{key}", "owner", PASS, f"{key} -> {val} resolves")
            except Exception as e:
                rep.add(f"owner.dns.{key}", "owner", FAIL,
                        f"{key} -> {val} does not resolve: {e}")

    tls = req.get("tls") or {}
    for key in ("termination", "certificate_owner"):
        if tls.get(key) in (None, ""):
            rep.add(f"owner.tls.{key}", "owner", MISSING, f"TLS {key} not supplied")
        else:
            rep.add(f"owner.tls.{key}", "owner", PASS, f"TLS {key} = {tls[key]}")

    for key, label in (("monitoring_destination", "monitoring destination"),
                       ("secret_storage_mechanism", "secret storage mechanism"),
                       ("maintenance_window", "maintenance window"),
                       ("rollback_operator", "rollback operator")):
        if req.get(key) in (None, ""):
            rep.add(f"owner.{key}", "owner", MISSING, f"{label} not supplied")
        else:
            rep.add(f"owner.{key}", "owner", PASS, f"{label} = {req[key]}")


# --- Rendering ---------------------------------------------------------------

_ICON = {PASS: "✅", FAIL: "❌", MISSING: "⚠️ ", SKIP: "⏭️ "}


def render_human(rep: Report) -> str:
    lines = ["=== Pilot Host Preflight — PILOT-DEPLOYMENT-READINESS-001D ===",
             "read-only: no deployment, no compose up, no migrations, no image pull", ""]
    by_cat: dict[str, list[Check]] = {}
    for c in rep.checks:
        by_cat.setdefault(c.category, []).append(c)
    for cat, checks in by_cat.items():
        lines.append(f"--- {cat} ---")
        for c in checks:
            lines.append(f"  {_ICON[c.status]} {c.status:8} {c.id:34} {redact(c.detail)}")
        lines.append("")
    counts = {s: sum(1 for c in rep.checks if c.status == s) for s in (PASS, FAIL, MISSING, SKIP)}
    lines.append(f"SUMMARY: {counts[PASS]} pass · {counts[FAIL]} fail · "
                 f"{counts[MISSING]} missing owner input · {counts[SKIP]} skipped")
    lines.append(f"VERDICT: {rep.verdict()}")
    if rep.verdict() != "GO":
        lines.append("")
        lines.append("This host is NOT cleared for deployment. 001E must not start.")
    return "\n".join(lines)


def build_report(args: argparse.Namespace) -> Report:
    rep = Report()
    req_path = Path(args.requirements)
    supplied = req_path.exists()
    req: dict = {}
    if supplied:
        try:
            req = json.loads(req_path.read_text())
        except Exception as e:
            rep.add("owner.requirements_file", "owner", FAIL,
                    f"requirements file is not valid JSON: {e}")
            req = {}
    req = {k: v for k, v in req.items() if not k.startswith("$")}

    check_platform(rep)
    check_docker(rep, req)
    check_resources(rep, req)
    check_clock(rep)
    check_ports(rep)
    check_network(rep)
    check_compose(rep, Path(args.compose), Path(args.env))
    check_image_lock(rep, Path(args.lock))
    check_registry(rep, Path(args.lock), args.skip_registry)
    check_env_file(rep, Path(args.env))
    check_storage(rep, req)
    check_existing_deployment(rep)
    check_owner_inputs(rep, req, req_path, supplied)
    return rep


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", action="store_true", help="emit JSON instead of text")
    parser.add_argument("--requirements", default=str(DEFAULT_REQUIREMENTS))
    parser.add_argument("--env", default=str(DEFAULT_ENV))
    parser.add_argument("--lock", default=str(DEFAULT_LOCK))
    parser.add_argument("--compose", default=str(DEFAULT_COMPOSE))
    parser.add_argument("--skip-registry", action="store_true",
                        help="skip registry manifest inspection (offline preflight)")
    args = parser.parse_args(argv)

    rep = build_report(args)

    if args.json:
        print(json.dumps({
            "task": "PILOT-DEPLOYMENT-READINESS-001D",
            "verdict": rep.verdict(),
            "exit_code": rep.exit_code(),
            "deployment_performed": False,
            "checks": [c.to_dict() for c in rep.checks],
        }, indent=2))
    else:
        print(render_human(rep))
    return rep.exit_code()


if __name__ == "__main__":
    sys.exit(main())
