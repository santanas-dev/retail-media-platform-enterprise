"""Deterministic tests for the local DEV/QA stand tooling (LOCAL-DEV-STAND-001).

No docker, no network, no host mutation: compose invocations are captured and
asserted on. The stand must stay scoped to its exact project, digest-only, and
must never prune system-wide.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL = REPO_ROOT / "scripts" / "deploy" / "local_stand.py"
OVERLAY = REPO_ROOT / "infra" / "compose" / "docker-compose.local-stand.yml"
PILOT = REPO_ROOT / "infra" / "compose" / "docker-compose.pilot.yml"


def _load():
    spec = importlib.util.spec_from_file_location("local_stand", TOOL)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


ls = _load()

SERVICES = ls.SERVICES
GOOD_SHA = "9" * 40


def _lock(digest_suffix: str = "b" * 64, services=None, registry=None) -> dict:
    services = services or SERVICES
    reg = registry or "ghcr.io/santanas-dev/rmp-pilot"
    return {
        "release": {"tag": "v0.11.1-pilot-packaging",
                    "version": "v0.11.1-pilot-packaging",
                    "git_sha": GOOD_SHA},
        "registry": reg,
        "images": [{"service": s, "repository": f"{reg}/{s}",
                    "image_digest": f"sha256:{digest_suffix}"} for s in services],
    }


def _write(tmp_path: Path, lock: dict, name="images.lock.json") -> Path:
    p = tmp_path / name
    p.write_text(json.dumps(lock))
    return p


# --- project scope -----------------------------------------------------------

def test_project_name_is_fixed_and_unique():
    assert ls.PROJECT == "rmp-local-stand"
    assert yaml.safe_load(OVERLAY.read_text())["name"] == ls.PROJECT
    # must not collide with the pilot project or the CI verify project
    assert ls.PROJECT != yaml.safe_load(PILOT.read_text())["name"]
    assert not ls.PROJECT.startswith("rmp-verify")


def test_every_compose_call_is_scoped_to_the_project(monkeypatch):
    seen = []
    monkeypatch.setattr(ls, "run", lambda cmd, **kw: seen.append(cmd) or _P(0))
    ls.compose("ps")
    cmd = seen[0]
    assert cmd[:2] == ["docker", "compose"]
    assert "-p" in cmd and cmd[cmd.index("-p") + 1] == ls.PROJECT
    assert str(ls.PILOT_COMPOSE) in cmd and str(ls.STAND_COMPOSE) in cmd


class _P:
    def __init__(self, rc, out="", err=""):
        self.returncode, self.stdout, self.stderr = rc, out, err


# --- safety: no system-wide destruction --------------------------------------

def test_tool_never_prunes_system_wide():
    src = TOOL.read_text()
    for forbidden in ("system prune", "docker system", "volume prune",
                      "image prune", "network prune", "container prune"):
        assert forbidden not in src, f"tool must not reference '{forbidden}'"


def test_only_reset_uses_down_v(monkeypatch):
    """`down -v` destroys data; it must appear only in reset, never in stop."""
    seen = []
    monkeypatch.setattr(ls, "run", lambda cmd, **kw: seen.append(cmd) or _P(0))
    ls.cmd_stop(_Args())
    flat = [" ".join(c) for c in seen]
    assert not any("down" in f for f in flat), flat
    assert any("stop" in f for f in flat)


class _Args:
    def __init__(self, **kw):
        self.confirm = kw.get("confirm")
        self.bind = kw.get("bind", "127.0.0.1")
        self.lock = kw.get("lock")
        self.sha256sums = kw.get("sha256sums")
        self.allow_unverified = kw.get("allow_unverified", False)
        self.skip_registry = kw.get("skip_registry", True)
        self.service = kw.get("service", [])
        self.tail = kw.get("tail", 10)
        self.follow = False


def test_reset_requires_exact_project_name(monkeypatch):
    seen = []
    monkeypatch.setattr(ls, "run", lambda cmd, **kw: seen.append(cmd) or _P(0))
    for bad in ("", "rmp-local", "rmp-local-stand ", "RMP-LOCAL-STAND", "yes"):
        with pytest.raises(SystemExit):
            ls.cmd_reset(_Args(confirm=bad))
    assert seen == [], "no docker command may run for a rejected reset"


def test_reset_with_exact_name_is_scoped(monkeypatch):
    seen = []
    monkeypatch.setattr(ls, "run", lambda cmd, **kw: seen.append(cmd) or _P(0))
    assert ls.cmd_reset(_Args(confirm=ls.PROJECT)) == 0
    cmd = seen[0]
    assert "down" in cmd and "-v" in cmd
    assert cmd[cmd.index("-p") + 1] == ls.PROJECT


# --- lock verification: digest-only ------------------------------------------

def test_valid_lock_accepted(tmp_path):
    lock = ls.verify_lock(_write(tmp_path, _lock()), None)
    assert len(lock["images"]) == len(SERVICES)


@pytest.mark.parametrize("digest", [
    "REPLACE_WITH_REAL_DIGEST", "sha256:short", "latest", "", "sha256:" + "Z" * 64,
])
def test_non_digest_refs_rejected(tmp_path, digest):
    lock = _lock()
    lock["images"][0]["image_digest"] = digest
    with pytest.raises(SystemExit):
        ls.verify_lock(_write(tmp_path, lock), None)


def test_mutable_tag_repository_rejected(tmp_path):
    lock = _lock()
    lock["images"][1]["repository"] = "ghcr.io/santanas-dev/rmp-pilot/device-gateway:latest"
    with pytest.raises(SystemExit):
        ls.verify_lock(_write(tmp_path, lock), None)


def test_service_set_mismatch_rejected(tmp_path):
    with pytest.raises(SystemExit):
        ls.verify_lock(_write(tmp_path, _lock(services=SERVICES[:-1])), None)


def test_unknown_service_rejected(tmp_path):
    lock = _lock()
    lock["images"][0]["service"] = "not-a-service"
    with pytest.raises(SystemExit):
        ls.verify_lock(_write(tmp_path, lock), None)


# --- lock verification: published checksum -----------------------------------

def test_checksum_match_accepted(tmp_path):
    p = _write(tmp_path, _lock())
    sums = tmp_path / "SHA256SUMS"
    sums.write_text(f"{ls.sha256_file(p)}  {p.name}\n")
    assert ls.verify_lock(p, sums)["_checksum"] == ls.sha256_file(p)


def test_checksum_mismatch_rejected(tmp_path):
    p = _write(tmp_path, _lock())
    sums = tmp_path / "SHA256SUMS"
    sums.write_text(f"{'0' * 64}  {p.name}\n")
    with pytest.raises(SystemExit):
        ls.verify_lock(p, sums)


def test_checksum_entry_missing_rejected(tmp_path):
    p = _write(tmp_path, _lock())
    sums = tmp_path / "SHA256SUMS"
    sums.write_text(f"{'0' * 64}  some-other-file.json\n")
    with pytest.raises(SystemExit):
        ls.verify_lock(p, sums)


def test_update_requires_sha256sums(tmp_path, monkeypatch):
    monkeypatch.setattr(ls, "read_env", lambda: {"POSTGRES_APP_PASSWORD": "x"})
    with pytest.raises(SystemExit):
        ls.cmd_update(_Args(lock=str(_write(tmp_path, _lock())), sha256sums=None))


# --- image refs --------------------------------------------------------------

def test_image_refs_are_digest_pinned(tmp_path):
    refs = ls.image_refs(ls.verify_lock(_write(tmp_path, _lock()), None))
    assert set(refs) == set(ls.IMAGE_ENV.values())
    for ref in refs.values():
        assert "@sha256:" in ref and ":latest" not in ref


def test_env_rewrite_touches_only_image_lines(tmp_path, monkeypatch):
    env = tmp_path / ".env.stand"
    env.write_text("JWT_SECRET=keepme\nCONTROL_API_IMAGE=old\nPOSTGRES_DB=rmp\n")
    env.chmod(0o600)
    monkeypatch.setattr(ls, "ENV_FILE", env)
    ls.write_env_images({"CONTROL_API_IMAGE": "new@sha256:" + "a" * 64})
    text = env.read_text()
    assert "JWT_SECRET=keepme" in text and "POSTGRES_DB=rmp" in text
    assert "CONTROL_API_IMAGE=new@sha256:" in text and "=old" not in text
    assert (env.stat().st_mode & 0o077) == 0, "env must stay owner-only"


# --- deploy record -----------------------------------------------------------

def test_deploy_record_fields(tmp_path, monkeypatch):
    monkeypatch.setattr(ls, "STATE_DIR", tmp_path)
    monkeypatch.setattr(ls, "RECORD_CURRENT", tmp_path / "deploy-record.json")
    lock = ls.verify_lock(_write(tmp_path, _lock()), None)
    rec = ls.write_record(lock)
    for key in ("source_sha", "lock_checksum", "image_digests", "deployed_at"):
        assert rec.get(key), key
    assert rec["source_sha"] == GOOD_SHA
    assert set(rec["image_digests"]) == set(SERVICES)
    assert rec["disposable"] is True
    assert "not production" in rec["note"].lower()


def test_save_previous_preserves_rollback_target(tmp_path, monkeypatch):
    monkeypatch.setattr(ls, "STATE_DIR", tmp_path)
    cur_lock, prev_lock = tmp_path / "images.lock.json", tmp_path / "images.lock.previous.json"
    cur_rec, prev_rec = tmp_path / "deploy-record.json", tmp_path / "deploy-record.previous.json"
    monkeypatch.setattr(ls, "LOCK_CURRENT", cur_lock)
    monkeypatch.setattr(ls, "LOCK_PREVIOUS", prev_lock)
    monkeypatch.setattr(ls, "RECORD_CURRENT", cur_rec)
    monkeypatch.setattr(ls, "RECORD_PREVIOUS", prev_rec)
    cur_lock.write_text('{"v":1}')
    cur_rec.write_text('{"r":1}')
    ls.save_previous()
    assert prev_lock.read_text() == '{"v":1}' and prev_rec.read_text() == '{"r":1}'


# --- update / rollback -------------------------------------------------------

def _update_harness(tmp_path, monkeypatch, healthy: bool):
    monkeypatch.setattr(ls, "STATE_DIR", tmp_path)
    monkeypatch.setattr(ls, "LOCK_CURRENT", tmp_path / "images.lock.json")
    monkeypatch.setattr(ls, "LOCK_PREVIOUS", tmp_path / "images.lock.previous.json")
    monkeypatch.setattr(ls, "RECORD_CURRENT", tmp_path / "deploy-record.json")
    monkeypatch.setattr(ls, "RECORD_PREVIOUS", tmp_path / "deploy-record.previous.json")
    env = tmp_path / ".env.stand"
    env.write_text("POSTGRES_APP_PASSWORD=x\n")
    env.chmod(0o600)
    monkeypatch.setattr(ls, "ENV_FILE", env)
    monkeypatch.setattr(ls, "read_env", lambda: {"POSTGRES_APP_PASSWORD": "x"})
    monkeypatch.setattr(ls, "_bring_up", lambda e: None)
    # First call = the new lock's health. Any later call is the rollback, which
    # runs the previously working images and is therefore expected to come up.
    calls = {"n": 0}

    def _health(timeout_s=300):
        calls["n"] += 1
        if calls["n"] == 1:
            return (healthy, [] if healthy else ["control-api"])
        return (True, [])

    monkeypatch.setattr(ls, "wait_healthy", _health)
    monkeypatch.setattr(ls, "verify_identity", lambda b, t, s: [])

    old = _lock(digest_suffix="a" * 64)
    (tmp_path / "images.lock.json").write_text(json.dumps(old))
    ls.write_record(ls.verify_lock(tmp_path / "images.lock.json", None))

    new = _lock(digest_suffix="c" * 64)
    new_path = tmp_path / "new.lock.json"
    new_path.write_text(json.dumps(new))
    sums = tmp_path / "SHA256SUMS"
    sums.write_text(f"{ls.sha256_file(new_path)}  {new_path.name}\n")
    return new_path, sums


def test_update_success_records_new_lock(tmp_path, monkeypatch):
    new_path, sums = _update_harness(tmp_path, monkeypatch, healthy=True)
    rc = ls.cmd_update(_Args(lock=str(new_path), sha256sums=str(sums)))
    assert rc == 0
    rec = json.loads((tmp_path / "deploy-record.json").read_text())
    assert all(d.endswith("c" * 64) for d in rec["image_digests"].values())
    assert (tmp_path / "images.lock.previous.json").exists(), "rollback target kept"


def test_failed_update_rolls_back_to_previous_lock(tmp_path, monkeypatch):
    new_path, sums = _update_harness(tmp_path, monkeypatch, healthy=False)
    rc = ls.cmd_update(_Args(lock=str(new_path), sha256sums=str(sums)))
    assert rc == 1, "a failed update must not report success"
    restored = json.loads((tmp_path / "images.lock.json").read_text())
    assert all(i["image_digest"].endswith("a" * 64) for i in restored["images"]), \
        "stand must be back on the previous lock"
    rec = json.loads((tmp_path / "deploy-record.json").read_text())
    assert all(d.endswith("a" * 64) for d in rec["image_digests"].values()), \
        "deploy record must reflect the rolled-back lock"


def test_rollback_restores_image_env(tmp_path, monkeypatch):
    new_path, sums = _update_harness(tmp_path, monkeypatch, healthy=False)
    ls.cmd_update(_Args(lock=str(new_path), sha256sums=str(sums)))
    text = (tmp_path / ".env.stand").read_text()
    assert "a" * 64 in text and "c" * 64 not in text


# --- overlay safety ----------------------------------------------------------

def test_overlay_publishes_only_ui_api_ports():
    doc = yaml.safe_load(OVERLAY.read_text())
    published = {s: spec.get("ports", []) for s, spec in doc["services"].items()}
    assert set(published) == {"control-api", "device-gateway", "admin-web", "advertiser-web"}
    for infra in ("postgres", "redis", "minio", "nats"):
        assert infra not in doc["services"], f"{infra} must not be published by the overlay"


def test_overlay_binds_to_explicit_address_not_all_interfaces():
    doc = yaml.safe_load(OVERLAY.read_text())
    for svc in ("control-api", "admin-web", "advertiser-web"):
        for mapping in doc["services"][svc]["ports"]:
            assert mapping.startswith("${STAND_BIND_ADDR}:"), (svc, mapping)
    for mapping in doc["services"]["device-gateway"]["ports"]:
        assert mapping.startswith("127.0.0.1:"), "device-gateway must stay host-only"


def test_pilot_compose_does_not_publish_infrastructure():
    doc = yaml.safe_load(PILOT.read_text())
    for infra in ("postgres", "redis", "minio", "nats"):
        assert not (doc["services"][infra] or {}).get("ports"), \
            f"{infra} must not publish host ports"


def test_overlay_adds_no_build_or_bind_mounts():
    doc = yaml.safe_load(OVERLAY.read_text())
    for name, spec in doc["services"].items():
        assert "build" not in (spec or {}), name
        for vol in (spec or {}).get("volumes", []) or []:
            assert not str(vol).startswith((".", "/", "~")), (name, vol)


def test_overlay_documents_disposable_and_not_tls_safe():
    text = OVERLAY.read_text().lower()
    assert "disposable" in text and "no backup" in text
    assert "not production-safe tls" in text
