"""Deterministic tests for the pilot host preflight tool (001D, SCOPE D).

Every test drives ``scripts/deploy/pilot_host_preflight.py`` against fixtures
and stubbed host probes — no real host state, no network, no docker, no deploy.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import stat
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL = REPO_ROOT / "scripts" / "deploy" / "pilot_host_preflight.py"
REAL_COMPOSE = REPO_ROOT / "infra" / "compose" / "docker-compose.pilot.yml"


def _load_module():
    spec = importlib.util.spec_from_file_location("pilot_host_preflight", TOOL)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    # Register before exec: @dataclass resolves annotations via sys.modules.
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


pf = _load_module()

GOOD_SHA = "a" * 40
GOOD_DIGEST = "sha256:" + "b" * 64
STRONG = "S" * 40  # >= _MIN_SECRET_LEN


def _valid_lock() -> dict:
    return {
        "release": {"version": "v0.11.1-pilot-packaging", "git_sha": GOOD_SHA},
        "checksum": "c" * 64,
        "images": [
            {
                "service": svc,
                "repository": f"{pf.REGISTRY_NAMESPACE}/{svc}",
                "version": "v0.11.1-pilot-packaging",
                "git_sha": GOOD_SHA,
                "image_digest": GOOD_DIGEST,
                "source_tag": "v0.11.1-pilot-packaging",
            }
            for svc in pf.PILOT_SERVICES
        ],
    }


def _valid_env_text() -> str:
    values = {
        "ENVIRONMENT": "pilot",
        "RMP_VERSION": "v0.11.1-pilot-packaging",
        "RMP_GIT_SHA": GOOD_SHA,
        "RMP_BUILD_TIME": "2026-08-24T00:00:00Z",
        "RMP_SCHEMA_HEAD": "034",
        "POSTGRES_OWNER_USER": "rmp_owner",
        "POSTGRES_OWNER_PASSWORD": STRONG,
        "POSTGRES_APP_USER": "retail_media_app",
        "POSTGRES_APP_PASSWORD": STRONG,
        "POSTGRES_DB": "retail_media",
        "DATABASE_URL": f"postgresql+asyncpg://retail_media_app:{STRONG}@postgres:5432/retail_media",
        "MIGRATION_DATABASE_URL": f"postgresql+asyncpg://rmp_owner:{STRONG}@postgres:5432/retail_media",
        "JWT_SECRET": STRONG,
        "JWT_AUDIENCE": "rmp-pilot",
        "MANIFEST_SIGNING_KEY": STRONG,
        "MINIO_ROOT_USER": "rmpminioroot",
        "MINIO_ROOT_PASSWORD": STRONG,
        "MINIO_INTERNAL_ENDPOINT": "http://minio:9000",
        "MINIO_PUBLIC_ENDPOINT": "https://files.pilot.corp.lan",
        "MINIO_ACCESS_KEY": STRONG,
        "MINIO_SECRET_KEY": STRONG,
        "CREATIVE_STORAGE_BUCKET": "creatives",
        "CONTRACT_STORAGE_BUCKET": "contracts",
        "CORS_ALLOWED_ORIGINS": "https://admin.pilot.corp.lan",
        "CORS_ALLOW_CREDENTIALS": "true",
        "METRICS_AUTH_TOKEN": "M" * 24,
        "SEED_DEV_CREDENTIALS": "false",
        "LICENSE_DEV_INGEST_ENABLED": "false",
        "BACKUP_DIR": "/srv/rmp/backup",
        "CONTROL_API_IMAGE": f"{pf.REGISTRY_NAMESPACE}/control-api@{GOOD_DIGEST}",
        "DEVICE_GATEWAY_IMAGE": f"{pf.REGISTRY_NAMESPACE}/device-gateway@{GOOD_DIGEST}",
        "ORCHESTRATOR_WORKER_IMAGE": f"{pf.REGISTRY_NAMESPACE}/orchestrator-worker@{GOOD_DIGEST}",
        "ADMIN_WEB_IMAGE": f"{pf.REGISTRY_NAMESPACE}/admin-web@{GOOD_DIGEST}",
        "ADVERTISER_WEB_IMAGE": f"{pf.REGISTRY_NAMESPACE}/advertiser-web@{GOOD_DIGEST}",
    }
    assert set(values) == set(pf.REQUIRED_ENV_NAMES), "fixture must cover required names"
    return "\n".join(f"{k}={v}" for k, v in values.items()) + "\n"


def _requirements(data_root: Path, backup: Path) -> dict:
    return {
        "min_cpu_cores": 2,
        "min_memory_gb": 4,
        "min_disk_free_gb": 1,
        "min_backup_disk_free_gb": 1,
        "min_docker_engine_version": "24.0.0",
        "min_compose_version": "2.20.0",
        "persistent_data_root": str(data_root),
        "backup_destination": str(backup),
        "dns_names": {
            "admin_web": "admin.pilot.corp.lan",
            "advertiser_web": "adv.pilot.corp.lan",
            "control_api": "api.pilot.corp.lan",
            "device_gateway": "gw.pilot.corp.lan",
        },
        "tls": {"termination": "nginx on host", "certificate_owner": "infra team"},
        "monitoring_destination": "self-hosted prometheus",
        "secret_storage_mechanism": "host env file, 0600",
        "maintenance_window": "Sun 02:00-04:00 UTC",
        "rollback_operator": "on-call infra",
    }


@pytest.fixture
def host(tmp_path, monkeypatch):
    """A fully satisfied fixture host.  Individual tests degrade one aspect."""
    data_root = tmp_path / "data"
    backup = tmp_path / "backup"
    data_root.mkdir()
    backup.mkdir()

    env_file = tmp_path / ".env.pilot"
    env_file.write_text(_valid_env_text())
    env_file.chmod(0o600)

    lock_file = tmp_path / "images.lock.json"
    lock_file.write_text(json.dumps(_valid_lock()))

    req_file = tmp_path / "host-requirements.json"
    req_file.write_text(json.dumps(_requirements(data_root, backup)))

    compose_file = tmp_path / "docker-compose.pilot.yml"
    compose_file.write_text(REAL_COMPOSE.read_text())

    monkeypatch.setattr(pf.platform, "system", lambda: "Linux")
    monkeypatch.setattr(pf.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(pf.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(pf.os, "cpu_count", lambda: 8)
    monkeypatch.setattr(pf, "_mem_total_gb", lambda: 16.0)
    monkeypatch.setattr(pf, "_port_state", lambda port: (True, "free"))

    def fake_getaddrinfo(hostname, *a, **k):
        return [(2, 1, 6, "", ("192.0.2.1", 443))]

    class _Sock:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(pf.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(pf.socket, "create_connection", lambda *a, **k: _Sock())

    real_run = pf._run

    def fake_run(cmd, timeout=20):
        exe = cmd[0]
        if exe == sys.executable:          # real validators, real files
            return real_run(cmd, timeout)
        if exe == "docker":
            if cmd[1:3] == ["version", "--format"]:
                return 0, "26.1.0", ""
            if cmd[1:3] == ["compose", "version"]:
                return 0, "2.29.0", ""
            if cmd[1] == "info":
                return 0, "26.1.0", ""
            if cmd[1] == "compose":
                return 0, "", ""           # config
            if cmd[1] == "ps":
                return 0, "", ""
            if cmd[1] == "volume":
                return 0, "", ""
            if cmd[1] == "manifest":
                return 0, '{"schemaVersion":2}', ""
            return 0, "", ""
        if exe == "timedatectl":
            return 0, "yes", ""
        if exe == "git":
            return 1, "", "not tracked"     # env file not tracked
        return 127, "", f"{exe}: not found"

    monkeypatch.setattr(pf, "_run", fake_run)

    return argparse.Namespace(
        json=False,
        requirements=str(req_file),
        env=str(env_file),
        lock=str(lock_file),
        compose=str(compose_file),
        skip_registry=True,
    )


def _statuses(rep) -> dict[str, str]:
    return {c.id: c.status for c in rep.checks}


# --- 1. clean fixture -> GO --------------------------------------------------

def test_clean_fixture_yields_go(host):
    rep = pf.build_report(host)
    assert rep.verdict() == "GO", [
        (c.id, c.status, c.detail) for c in rep.checks if c.status in (pf.FAIL, pf.MISSING)
    ]
    assert rep.exit_code() == 0


# --- 2. missing owner input -> NEEDS_OWNER_INPUT -----------------------------

def test_missing_owner_input_yields_needs_owner_input(host, tmp_path):
    host.requirements = str(tmp_path / "absent-requirements.json")
    rep = pf.build_report(host)
    assert rep.verdict() == "NEEDS_OWNER_INPUT"
    assert rep.exit_code() == 2
    assert not rep.failures, [(c.id, c.detail) for c in rep.failures]
    assert _statuses(rep)["owner.requirements_file"] == pf.MISSING


def test_needs_owner_input_never_masks_a_failure(host, tmp_path, monkeypatch):
    host.requirements = str(tmp_path / "absent-requirements.json")
    monkeypatch.setattr(pf.platform, "machine", lambda: "aarch64")
    rep = pf.build_report(host)
    assert rep.verdict() == "FAIL"   # FAIL outranks MISSING
    assert rep.exit_code() == 1


# --- 3. missing Docker / Compose ---------------------------------------------

def test_missing_docker_fails(host, monkeypatch):
    monkeypatch.setattr(pf.shutil, "which", lambda name: None if name == "docker" else "/usr/bin/x")
    rep = pf.build_report(host)
    st = _statuses(rep)
    assert st["docker.engine"] == pf.FAIL
    assert st["docker.daemon"] == pf.FAIL
    assert st["docker.access"] == pf.FAIL
    assert rep.verdict() == "FAIL"


def test_missing_compose_plugin_fails(host, monkeypatch):
    real = pf._run

    def no_compose(cmd, timeout=20):
        if cmd[0] == "docker" and cmd[1:3] == ["compose", "version"]:
            return 1, "", "docker: 'compose' is not a docker command"
        return real(cmd, timeout)

    monkeypatch.setattr(pf, "_run", no_compose)
    rep = pf.build_report(host)
    assert _statuses(rep)["docker.compose"] == pf.FAIL
    assert rep.verdict() == "FAIL"


def test_docker_daemon_down_fails_access_and_daemon(host, monkeypatch):
    real = pf._run

    def daemon_down(cmd, timeout=20):
        if cmd[0] == "docker" and cmd[1] == "info":
            return 1, "", "Cannot connect to the Docker daemon"
        return real(cmd, timeout)

    monkeypatch.setattr(pf, "_run", daemon_down)
    rep = pf.build_report(host)
    st = _statuses(rep)
    assert st["docker.daemon"] == pf.FAIL
    assert st["docker.access"] == pf.FAIL


# --- 4. unsupported architecture ---------------------------------------------

def test_unsupported_architecture_fails(host, monkeypatch):
    monkeypatch.setattr(pf.platform, "machine", lambda: "aarch64")
    rep = pf.build_report(host)
    st = _statuses(rep)
    assert st["platform.arch"] == pf.FAIL
    assert rep.verdict() == "FAIL"
    detail = next(c.detail for c in rep.checks if c.id == "platform.arch")
    assert "amd64" in detail


def test_unsupported_os_fails(host, monkeypatch):
    monkeypatch.setattr(pf.platform, "system", lambda: "Darwin")
    rep = pf.build_report(host)
    assert _statuses(rep)["platform.os"] == pf.FAIL


# --- 5. insufficient disk ----------------------------------------------------

def test_insufficient_disk_fails(host, monkeypatch):
    class _Usage:
        free = 1 * (1024 ** 3)  # 1 GiB

    monkeypatch.setattr(pf.shutil, "disk_usage", lambda p: _Usage())
    req = json.loads(Path(host.requirements).read_text())
    req["min_disk_free_gb"] = 500
    Path(host.requirements).write_text(json.dumps(req))
    rep = pf.build_report(host)
    assert _statuses(rep)["resources.disk"] == pf.FAIL
    assert rep.verdict() == "FAIL"


def test_insufficient_memory_fails(host, monkeypatch):
    monkeypatch.setattr(pf, "_mem_total_gb", lambda: 1.0)
    rep = pf.build_report(host)
    assert _statuses(rep)["resources.memory"] == pf.FAIL


def test_insufficient_cpu_fails(host, monkeypatch):
    monkeypatch.setattr(pf.os, "cpu_count", lambda: 1)
    rep = pf.build_report(host)
    assert _statuses(rep)["resources.cpu"] == pf.FAIL


# --- 6. occupied required port -----------------------------------------------

def test_occupied_required_port_fails(host, monkeypatch):
    monkeypatch.setattr(
        pf, "_port_state",
        lambda port: (False, "occupied (Address already in use)") if port == 8000 else (True, "free"),
    )
    monkeypatch.setattr(pf, "_port_owner", lambda port: "docker container 'other' (foreign)")
    rep = pf.build_report(host)
    st = _statuses(rep)
    assert st["ports.8000"] == pf.FAIL
    assert st["ports.8001"] == pf.PASS
    assert rep.verdict() == "FAIL"
    detail = next(c.detail for c in rep.checks if c.id == "ports.8000")
    assert "classified as" in detail


def test_all_required_ports_are_checked(host):
    rep = pf.build_report(host)
    for port in (8000, 8001, 3000, 3001):
        assert f"ports.{port}" in _statuses(rep)


# --- 7. placeholder image digest ---------------------------------------------

def test_placeholder_image_digest_fails(host):
    lock = _valid_lock()
    lock["images"][0]["image_digest"] = "sha256:REPLACE_WITH_REAL_DIGEST"
    Path(host.lock).write_text(json.dumps(lock))
    rep = pf.build_report(host)
    st = _statuses(rep)
    assert st["lock.valid"] == pf.FAIL
    assert st["lock.digests"] == pf.FAIL
    assert rep.verdict() == "FAIL"


def test_shipped_example_lock_is_rejected(host):
    example = REPO_ROOT / "infra" / "deploy" / "images.lock.example.json"
    host.lock = str(example)
    rep = pf.build_report(host)
    assert _statuses(rep)["lock.valid"] == pf.FAIL


# --- 8. mutable / latest image ------------------------------------------------

def test_mutable_latest_repository_fails(host):
    lock = _valid_lock()
    lock["images"][1]["repository"] = f"{pf.REGISTRY_NAMESPACE}/device-gateway:latest"
    Path(host.lock).write_text(json.dumps(lock))
    rep = pf.build_report(host)
    assert _statuses(rep)["lock.valid"] == pf.FAIL


def test_mutable_tag_in_compose_fails(host, tmp_path):
    import yaml
    doc = yaml.safe_load(REAL_COMPOSE.read_text())
    doc["services"]["redis"]["image"] = "redis:latest"
    bad = tmp_path / "compose-latest.yml"
    bad.write_text(yaml.safe_dump(doc))
    host.compose = str(bad)
    rep = pf.build_report(host)
    assert _statuses(rep)["compose.safety"] == pf.FAIL


def test_build_directive_in_compose_fails(host, tmp_path):
    import yaml
    doc = yaml.safe_load(REAL_COMPOSE.read_text())
    doc["services"]["control-api"]["build"] = {"context": "."}
    bad = tmp_path / "compose-build.yml"
    bad.write_text(yaml.safe_dump(doc))
    host.compose = str(bad)
    rep = pf.build_report(host)
    assert _statuses(rep)["compose.safety"] == pf.FAIL


def test_source_bind_mount_in_compose_fails(host, tmp_path):
    import yaml
    doc = yaml.safe_load(REAL_COMPOSE.read_text())
    doc["services"]["control-api"]["volumes"] = ["./apps:/app/apps"]
    bad = tmp_path / "compose-mount.yml"
    bad.write_text(yaml.safe_dump(doc))
    host.compose = str(bad)
    rep = pf.build_report(host)
    assert _statuses(rep)["compose.safety"] == pf.FAIL


def test_dev_ingest_flag_in_compose_fails(host, tmp_path):
    import yaml
    doc = yaml.safe_load(REAL_COMPOSE.read_text())
    doc["services"]["control-api"]["environment"]["LICENSE_DEV_INGEST_ENABLED"] = "true"
    bad = tmp_path / "compose-ingest.yml"
    bad.write_text(yaml.safe_dump(doc))
    host.compose = str(bad)
    rep = pf.build_report(host)
    assert _statuses(rep)["compose.safety"] == pf.FAIL


def test_real_pilot_compose_is_safe(host):
    rep = pf.build_report(host)
    assert _statuses(rep)["compose.safety"] == pf.PASS


# --- 9. service-set mismatch --------------------------------------------------

def test_service_set_mismatch_fails(host):
    lock = _valid_lock()
    lock["images"] = lock["images"][:-1]          # drop advertiser-web
    Path(host.lock).write_text(json.dumps(lock))
    rep = pf.build_report(host)
    st = _statuses(rep)
    assert st["lock.valid"] == pf.FAIL
    assert st["lock.digests"] == pf.FAIL


def test_unknown_service_in_lock_fails(host):
    lock = _valid_lock()
    lock["images"][0]["service"] = "not-a-pilot-service"
    Path(host.lock).write_text(json.dumps(lock))
    rep = pf.build_report(host)
    assert _statuses(rep)["lock.valid"] == pf.FAIL


# --- 10. weak / dev secret ----------------------------------------------------

def test_weak_secret_fails(host):
    text = _valid_env_text().replace(f"JWT_SECRET={STRONG}", "JWT_SECRET=changeme")
    Path(host.env).write_text(text)
    rep = pf.build_report(host)
    assert _statuses(rep)["env.no_weak_secrets"] == pf.FAIL
    assert rep.verdict() == "FAIL"


def test_dev_credential_fails(host):
    text = _valid_env_text().replace(
        f"MINIO_ROOT_PASSWORD={STRONG}", "MINIO_ROOT_PASSWORD=minioadmin")
    Path(host.env).write_text(text)
    rep = pf.build_report(host)
    assert _statuses(rep)["env.no_weak_secrets"] == pf.FAIL


def test_missing_required_env_name_fails(host):
    lines = [ln for ln in _valid_env_text().splitlines() if not ln.startswith("JWT_AUDIENCE=")]
    Path(host.env).write_text("\n".join(lines) + "\n")
    rep = pf.build_report(host)
    assert _statuses(rep)["env.required_names"] == pf.FAIL
    detail = next(c.detail for c in rep.checks if c.id == "env.required_names")
    assert "JWT_AUDIENCE" in detail


def test_env_values_are_never_printed(host):
    rep = pf.build_report(host)
    blob = json.dumps([c.to_dict() for c in rep.checks])
    assert STRONG not in blob, "a secret value leaked into the report"


# --- 11. unsafe env permissions ----------------------------------------------

def test_unsafe_env_permissions_fails(host):
    Path(host.env).chmod(0o644)
    rep = pf.build_report(host)
    assert _statuses(rep)["env.permissions"] == pf.FAIL
    assert rep.verdict() == "FAIL"


def test_group_readable_env_fails(host):
    Path(host.env).chmod(0o640)
    rep = pf.build_report(host)
    assert _statuses(rep)["env.permissions"] == pf.FAIL


def test_owner_only_env_passes(host):
    Path(host.env).chmod(0o400)
    rep = pf.build_report(host)
    assert _statuses(rep)["env.permissions"] == pf.PASS


def test_tracked_env_file_fails(host, monkeypatch):
    real = pf._run

    def tracked(cmd, timeout=20):
        if cmd[0] == "git":
            return 0, "infra/deploy/.env.pilot", ""
        return real(cmd, timeout)

    monkeypatch.setattr(pf, "_run", tracked)
    rep = pf.build_report(host)
    assert _statuses(rep)["env.not_tracked"] == pf.FAIL


# --- 12. missing backup destination -------------------------------------------

def test_missing_backup_destination_is_owner_input(host):
    req = json.loads(Path(host.requirements).read_text())
    req["backup_destination"] = None
    Path(host.requirements).write_text(json.dumps(req))
    rep = pf.build_report(host)
    assert _statuses(rep)["storage.backup_destination"] == pf.MISSING
    assert rep.verdict() == "NEEDS_OWNER_INPUT"


def test_nonexistent_backup_destination_fails(host, tmp_path):
    req = json.loads(Path(host.requirements).read_text())
    req["backup_destination"] = str(tmp_path / "does-not-exist")
    Path(host.requirements).write_text(json.dumps(req))
    rep = pf.build_report(host)
    assert _statuses(rep)["storage.backup_destination"] == pf.FAIL
    assert rep.verdict() == "FAIL"


def test_nonexistent_data_root_fails(host, tmp_path):
    req = json.loads(Path(host.requirements).read_text())
    req["persistent_data_root"] = str(tmp_path / "no-such-root")
    Path(host.requirements).write_text(json.dumps(req))
    rep = pf.build_report(host)
    assert _statuses(rep)["resources.disk"] == pf.FAIL


# --- 13. report redaction ------------------------------------------------------

@pytest.mark.parametrize("raw,forbidden", [
    ("token=ghp_abcdefghijklmnopqrstuvwxyz0123456789", "ghp_abcdefghijklmnopqrstuvwxyz"),
    ("github_pat_11ABCDEFG0123456789_abcdefghijklmnop", "github_pat_11ABCDEFG0123456789"),
    ("postgresql://user:sup3rs3cretvalue@db:5432/x", "sup3rs3cretvalue"),
    ("password=hunter2hunter2", "hunter2hunter2"),
    ("METRICS_AUTH_TOKEN: abcdef123456xyz", "abcdef123456xyz"),
])
def test_redaction_masks_credentials(raw, forbidden):
    assert forbidden not in pf.redact(raw)


def test_redaction_masks_private_key_header():
    assert "PRIVATE KEY" not in pf.redact("-----BEGIN RSA PRIVATE KEY-----")


def test_redaction_applied_in_check_serialization():
    c = pf.Check("x", "y", pf.FAIL, "password=supersecretvalue123")
    assert "supersecretvalue123" not in json.dumps(c.to_dict())


def test_redaction_applied_in_human_render():
    rep = pf.Report()
    rep.add("x", "y", pf.FAIL, "postgresql://u:leakedpassword99@h/db")
    assert "leakedpassword99" not in pf.render_human(rep)


def test_json_output_is_valid_and_redacted(host, capsys):
    host.json = True
    pf.main([
        "--json", "--skip-registry",
        "--requirements", host.requirements,
        "--env", host.env, "--lock", host.lock, "--compose", host.compose,
    ])
    payload = json.loads(capsys.readouterr().out)
    assert payload["verdict"] in ("GO", "NEEDS_OWNER_INPUT", "FAIL")
    assert payload["deployment_performed"] is False
    assert STRONG not in json.dumps(payload)


# --- 14. existing deployment collision -----------------------------------------

def test_existing_container_collision_fails(host, monkeypatch):
    real = pf._run

    def with_containers(cmd, timeout=20):
        if cmd[0] == "docker" and cmd[1] == "ps":
            return 0, "rmp-pilot-control-api-1 running", ""
        return real(cmd, timeout)

    monkeypatch.setattr(pf, "_run", with_containers)
    rep = pf.build_report(host)
    assert _statuses(rep)["collision.containers"] == pf.FAIL
    assert rep.verdict() == "FAIL"


def test_existing_volume_collision_fails(host, monkeypatch):
    real = pf._run

    def with_volumes(cmd, timeout=20):
        if cmd[0] == "docker" and cmd[1] == "volume":
            return 0, "rmp-pilot_pg_data\nother_volume", ""
        return real(cmd, timeout)

    monkeypatch.setattr(pf, "_run", with_volumes)
    rep = pf.build_report(host)
    assert _statuses(rep)["collision.volumes"] == pf.FAIL
    detail = next(c.detail for c in rep.checks if c.id == "collision.volumes")
    assert "rmp-pilot_pg_data" in detail


# --- exit-code contract ---------------------------------------------------------

def test_exit_codes_are_distinct():
    go, need, fail = pf.Report(), pf.Report(), pf.Report()
    go.add("a", "c", pf.PASS)
    need.add("a", "c", pf.PASS)
    need.add("b", "c", pf.MISSING)
    fail.add("a", "c", pf.FAIL)
    fail.add("b", "c", pf.MISSING)
    assert (go.exit_code(), need.exit_code(), fail.exit_code()) == (0, 2, 1)
    assert (go.verdict(), need.verdict(), fail.verdict()) == (
        "GO", "NEEDS_OWNER_INPUT", "FAIL")


def _command_literals() -> list[list[str]]:
    """Every list-of-strings literal in the tool — i.e. every command it can run.

    Inspects the AST rather than the raw text so that prose in docstrings (which
    legitimately names 'compose up', 'restore', ...) cannot mask a real call.
    """
    import ast

    cmds: list[list[str]] = []
    for node in ast.walk(ast.parse(TOOL.read_text())):
        if isinstance(node, ast.List):
            # Keep the constant elements even when the list mixes in str()/f-strings,
            # so commands built with interpolated paths are still inspected.
            parts = [e.value for e in node.elts
                     if isinstance(e, ast.Constant) and isinstance(e.value, str)]
            if parts:
                cmds.append(parts)
    return cmds


def test_tool_never_invokes_deployment_verbs():
    forbidden = {"up", "pull", "run", "start", "restart", "exec", "rm", "down",
                 "upgrade", "restore", "create"}
    for cmd in _command_literals():
        if cmd and cmd[0] in ("docker", "alembic"):
            overlap = forbidden.intersection(cmd)
            assert not overlap, f"preflight must not run a deployment verb: {cmd} ({overlap})"


def test_tool_only_uses_readonly_docker_subcommands():
    allowed = {"version", "info", "compose", "ps", "volume", "manifest", "inspect"}
    for cmd in _command_literals():
        if cmd and cmd[0] == "docker":
            assert cmd[1] in allowed, f"non-read-only docker subcommand: {cmd}"
    # the only compose subcommand permitted is `config`
    for cmd in _command_literals():
        if len(cmd) > 2 and cmd[0] == "docker" and cmd[1] == "compose":
            assert "up" not in cmd and "down" not in cmd, f"compose lifecycle verb: {cmd}"


# --- 15. staging layout regression (001D-FU1) ---------------------------------
#
# pilot_host_preflight.py derives REPO_ROOT as parents[2] of its own path.  The
# runbook originally documented a FLAT scp, which put the tool at
# <stage>/pilot_host_preflight.py -> REPO_ROOT resolved outside the staging tree,
# the pilot compose was not found, and the run ended in a FALSE FAIL.
# scripts/deploy/stage_preflight.py is now the single source of the layout.

STAGER = REPO_ROOT / "scripts" / "deploy" / "stage_preflight.py"


def _load_stager():
    spec = importlib.util.spec_from_file_location("stage_preflight", STAGER)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


sp = _load_stager()


def test_staging_layout_is_repository_relative():
    assert "scripts/deploy/pilot_host_preflight.py" in sp.STAGE_FILES
    assert "infra/compose/docker-compose.pilot.yml" in sp.STAGE_FILES
    for rel in sp.STAGE_FILES:
        assert "/" in rel, f"{rel} would be staged flat, breaking REPO_ROOT"
        assert (REPO_ROOT / rel).exists(), f"staged file missing from repo: {rel}"


def test_entrypoint_depth_makes_stage_root_the_repo_root():
    # parents[2] of <stage>/scripts/deploy/tool.py must be <stage>
    assert Path(sp.ENTRYPOINT).parts[:2] == ("scripts", "deploy")
    assert len(Path(sp.ENTRYPOINT).parts) == 3


def test_stage_preserves_paths_and_compose_is_found(tmp_path):
    dest = tmp_path / "stage"
    sp.stage(dest)
    tool = dest / sp.ENTRYPOINT
    compose = dest / "infra/compose/docker-compose.pilot.yml"
    assert tool.exists() and compose.exists()
    # the resolution rule the tool itself uses
    assert tool.resolve().parents[2] == dest.resolve()
    assert (tool.resolve().parents[2] / "infra/compose/docker-compose.pilot.yml").exists()


def test_staged_tree_yields_compose_safety_pass_not_false_fail(host, tmp_path, monkeypatch):
    """The documented staging layout must find compose and PASS the safety check."""
    dest = tmp_path / "stage"
    sp.stage(dest)
    host.compose = str(dest / "infra/compose/docker-compose.pilot.yml")
    rep = pf.build_report(host)
    st = _statuses(rep)
    assert st["compose.safety"] == pf.PASS
    assert st["compose.config"] != pf.FAIL
    assert not any(c.id.startswith("compose") and c.status == pf.FAIL for c in rep.checks)


def test_flat_layout_would_lose_compose(tmp_path):
    """Documents the defect the stager prevents: flat copy breaks REPO_ROOT."""
    flat = tmp_path / "flat"
    flat.mkdir()
    shutil_copy = __import__("shutil").copy2
    shutil_copy(REPO_ROOT / sp.ENTRYPOINT, flat / "pilot_host_preflight.py")
    staged_tool = flat / "pilot_host_preflight.py"
    derived_root = staged_tool.resolve().parents[2]
    assert not (derived_root / "infra/compose/docker-compose.pilot.yml").exists(), (
        "flat layout unexpectedly resolved compose; the regression guard is meaningless"
    )


def test_stage_rejects_missing_requirements(tmp_path):
    with pytest.raises(FileNotFoundError):
        sp.stage(tmp_path / "s", requirements=tmp_path / "nope.json")


def test_stage_includes_requirements_at_expected_path(tmp_path):
    req = tmp_path / "req.json"
    req.write_text("{}")
    dest = tmp_path / "stage"
    sp.stage(dest, requirements=req)
    assert (dest / sp.REQUIREMENTS_TARGET).exists()


def test_stager_never_executes_the_preflight():
    import ast as _ast
    src = STAGER.read_text()
    for node in _ast.walk(_ast.parse(src)):
        if isinstance(node, _ast.List):
            parts = [e.value for e in node.elts
                     if isinstance(e, _ast.Constant) and isinstance(e.value, str)]
            if parts and parts[0] in ("docker", "alembic"):
                raise AssertionError(f"stager must not run {parts}")
    assert "compose up" not in src.replace("no compose up", "")
