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


class _ComposeLoader(yaml.SafeLoader):
    """Compose tags (!override, !reset) are not plain YAML - teach the loader."""


_ComposeLoader.add_constructor(
    "!override",
    lambda loader, node: loader.construct_sequence(node)
    if isinstance(node, yaml.SequenceNode) else loader.construct_object(node),
)
_ComposeLoader.add_constructor("!reset", lambda loader, node: None)


def load_overlay() -> dict:
    """Parse the stand overlay, preserving Compose merge tags."""
    return yaml.load(OVERLAY.read_text(), Loader=_ComposeLoader)



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
    assert load_overlay()["name"] == ls.PROJECT
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

def test_overlay_publishes_only_ui_api_and_object_ports():
    """Exactly the ports a browser needs: the two UIs, the API, the S3 endpoint.

    MinIO's S3 API is published deliberately - browser upload uses presigned
    URLs and cannot work without a reachable object endpoint. Its console and
    every datastore stay unpublished.
    """
    doc = load_overlay()
    assert set(doc["services"]) == {
        "control-api", "device-gateway", "admin-web", "advertiser-web",
        "minio", "stand-proxy"}
    for infra in ("postgres", "redis", "nats"):
        assert infra not in doc["services"], f"{infra} must not be published by the overlay"
    # The two portals are fronted by stand-proxy, so they publish nothing.
    for fe in ("admin-web", "advertiser-web"):
        assert not (doc["services"][fe].get("ports") or []), \
            f"{fe} must not publish directly; stand-proxy fronts it"


def test_overlay_binds_to_explicit_address_not_all_interfaces():
    doc = load_overlay()
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
    doc = load_overlay()
    for name, spec in doc["services"].items():
        assert "build" not in (spec or {}), name
        for vol in (spec or {}).get("volumes", []) or []:
            assert not str(vol).startswith((".", "/", "~")), (name, vol)


def test_overlay_documents_disposable_and_not_tls_safe():
    text = OVERLAY.read_text().lower()
    assert "disposable" in text and "no backup" in text
    assert "not production-safe tls" in text


# --- FU: MinIO bindings + browser-upload endpoint ----------------------------

def test_minio_api_published_on_bind_address_only():
    doc = load_overlay()
    ports = doc["services"]["minio"]["ports"]
    assert ports == ["${STAND_BIND_ADDR}:9000:9000"], ports


def test_minio_console_9001_is_not_published():
    doc = load_overlay()
    for svc, spec in doc["services"].items():
        for mapping in (spec or {}).get("ports", []) or []:
            assert not str(mapping).endswith(":9001") and ":9001:" not in str(mapping), \
                f"MinIO console must not be published ({svc}: {mapping})"


@pytest.mark.parametrize("infra", ["postgres", "redis", "nats"])
def test_datastores_are_never_published(infra):
    overlay = load_overlay()
    pilot = yaml.safe_load(PILOT.read_text())
    assert infra not in overlay["services"], f"{infra} must not be published by the overlay"
    assert not (pilot["services"][infra] or {}).get("ports"), \
        f"{infra} must not publish host ports"


BIND = "192.168.110.81"


def _stand_env(**over):
    env = {
        "MINIO_PUBLIC_ENDPOINT": f"{BIND}:9000",
        "CORS_ALLOWED_ORIGINS": f"http://{BIND}:3000,http://{BIND}:3001",
    }
    env.update(over)
    return env


def test_valid_stand_env_has_no_problems():
    assert ls.validate_stand_env(_stand_env(), BIND) == []


@pytest.mark.parametrize("endpoint", [
    "",                              # unset
    "localhost:9000",                # host-internal
    "127.0.0.1:9000",                # host-internal
    "minio:9000",                    # container-internal
    f"http://{BIND}:9000",           # scheme: MinIO SDK raises on it
    f"https://{BIND}:9000",          # scheme
    f"{BIND}:9000/bucket",           # path: MinIO SDK raises on it
])
def test_unreachable_or_invalid_minio_endpoint_rejected(endpoint):
    problems = ls.validate_stand_env(_stand_env(MINIO_PUBLIC_ENDPOINT=endpoint), BIND)
    assert problems, f"{endpoint!r} should be rejected"


def test_minio_endpoint_scheme_is_rejected_with_sdk_reason():
    problems = ls.validate_stand_env(
        _stand_env(MINIO_PUBLIC_ENDPOINT=f"http://{BIND}:9000"), BIND)
    assert any("scheme" in p for p in problems), problems


def test_minio_endpoint_must_match_bind_address():
    problems = ls.validate_stand_env(
        _stand_env(MINIO_PUBLIC_ENDPOINT="10.0.0.9:9000"), BIND)
    assert any("bind address" in p for p in problems)


@pytest.mark.parametrize("cors", [
    "", f"http://{BIND}:3000", f"http://{BIND}:3001", "http://localhost:3000",
])
def test_incomplete_cors_rejected(cors):
    problems = ls.validate_stand_env(_stand_env(CORS_ALLOWED_ORIGINS=cors), BIND)
    assert any("CORS" in p for p in problems)


def test_wildcard_cors_rejected():
    problems = ls.validate_stand_env(_stand_env(CORS_ALLOWED_ORIGINS="*"), BIND)
    assert any("wildcard" in p for p in problems)


def test_start_refuses_invalid_stand_env(tmp_path, monkeypatch):
    monkeypatch.setattr(ls, "read_env", lambda: _stand_env(MINIO_PUBLIC_ENDPOINT="minio:9000"))
    with pytest.raises(SystemExit):
        ls.cmd_start(_Args(bind=BIND))


# --- FU: bootstrap-admin tool -------------------------------------------------

BOOTSTRAP = REPO_ROOT / "scripts" / "deploy" / "local_stand_bootstrap_admin.py"


def _load_bootstrap():
    spec = importlib.util.spec_from_file_location("local_stand_bootstrap_admin", BOOTSTRAP)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


ba = _load_bootstrap()


def test_bcrypt_contract_matches_product_seed():
    seed = (REPO_ROOT / "apps" / "control-api" / "seed.py").read_text()
    assert "rounds=12" in seed, "product seed no longer uses 12 rounds"
    assert ba.BCRYPT_ROUNDS == 12
    assert ba.HASH_ALGORITHM == "bcrypt"
    assert ba.CREDENTIAL_TYPE == "local_break_glass"
    assert ba.DEFAULT_USERNAME == "break_glass_admin"


def test_refuses_without_explicit_local_stand_flag():
    with pytest.raises(SystemExit):
        ba.assert_local_stand(False)


def test_refuses_when_deploy_record_is_not_the_stand(tmp_path, monkeypatch):
    rec = tmp_path / "deploy-record.json"
    rec.write_text(json.dumps({"stand": "pilot", "project": "rmp-pilot"}))
    monkeypatch.setattr(ba, "RECORD", rec)
    with pytest.raises(SystemExit):
        ba.assert_local_stand(True)


def test_refuses_when_project_not_running(tmp_path, monkeypatch):
    monkeypatch.setattr(ba, "RECORD", tmp_path / "absent.json")
    monkeypatch.setattr(ba, "run", lambda cmd, **kw: _P(0, ""))   # empty ps output
    with pytest.raises(SystemExit):
        ba.assert_local_stand(True)


def test_accepts_when_record_and_project_are_the_stand(tmp_path, monkeypatch):
    rec = tmp_path / "deploy-record.json"
    rec.write_text(json.dumps({"stand": ba.STAND_KIND, "project": ba.PROJECT}))
    monkeypatch.setattr(ba, "RECORD", rec)
    monkeypatch.setattr(ba, "run", lambda cmd, **kw: _P(0, '{"Name":"x"}'))
    ba.assert_local_stand(True)          # must not raise


def test_password_never_passed_on_a_command_line(monkeypatch):
    captured = {}

    def fake_compose(*args, stdin=None, check=True):
        captured["args"] = args
        captured["stdin"] = stdin
        return _P(0, "$2b$12$" + "x" * 53)

    monkeypatch.setattr(ba, "compose", fake_compose)
    secret = "correct horse battery staple"
    ba.hash_password(secret)
    assert secret not in " ".join(captured["args"]), "plaintext leaked into argv"
    assert captured["stdin"].strip() == secret, "password must travel on stdin"


def test_hash_failure_is_fail_closed(monkeypatch):
    monkeypatch.setattr(ba, "compose", lambda *a, **k: _P(0, "not-a-hash"))
    with pytest.raises(SystemExit):
        ba.hash_password("whatever")


def test_prompt_requires_a_tty(monkeypatch):
    monkeypatch.setattr(ba.sys.stdin, "isatty", lambda: False)
    with pytest.raises(SystemExit):
        ba.prompt_password()


def _tty(monkeypatch, first, second=None):
    monkeypatch.setattr(ba.sys.stdin, "isatty", lambda: True)
    answers = iter([first, second if second is not None else first])
    monkeypatch.setattr(ba.getpass, "getpass", lambda prompt="": next(answers))


def test_mismatched_passwords_rejected(monkeypatch):
    _tty(monkeypatch, "averylongpassword1", "averylongpassword2")
    with pytest.raises(SystemExit):
        ba.prompt_password()


def test_short_password_rejected(monkeypatch):
    _tty(monkeypatch, "short")
    with pytest.raises(SystemExit):
        ba.prompt_password()


@pytest.mark.parametrize("pw", sorted(ba.FORBIDDEN_PASSWORDS))
def test_known_dev_passwords_rejected(monkeypatch, pw):
    _tty(monkeypatch, pw + "xxxxxxxxxxxx" if len(pw) < 12 else pw)
    if len(pw) >= ba.MIN_PASSWORD_LEN:
        with pytest.raises(SystemExit):
            ba.prompt_password()


def test_accepts_a_strong_password(monkeypatch):
    _tty(monkeypatch, "a-perfectly-fine-stand-password")
    assert ba.prompt_password() == "a-perfectly-fine-stand-password"


def _bootstrap_harness(monkeypatch, existing: bool):
    calls = []

    def fake_psql(env, sql, tuples_only=True):
        calls.append(sql)
        if sql.startswith("SELECT id FROM users"):
            return "11111111-1111-1111-1111-111111111111"
        if sql.startswith("SELECT 1 FROM local_credentials"):
            return "1" if existing else ""
        if sql.startswith("SELECT status"):
            return "active|bcrypt"
        return ""

    monkeypatch.setattr(ba, "_psql", fake_psql)
    return calls


def test_creates_credential_when_absent(monkeypatch):
    calls = _bootstrap_harness(monkeypatch, existing=False)
    assert ba.bootstrap({}, "break_glass_admin", "$2b$12$hash") == "created"
    assert any(c.startswith("INSERT INTO local_credentials") for c in calls)
    assert not any(c.startswith("UPDATE local_credentials") for c in calls)


def test_rotates_credential_when_present(monkeypatch):
    calls = _bootstrap_harness(monkeypatch, existing=True)
    assert ba.bootstrap({}, "break_glass_admin", "$2b$12$hash") == "rotated"
    assert any(c.startswith("UPDATE local_credentials") for c in calls)
    assert not any(c.startswith("INSERT INTO local_credentials") for c in calls)


def test_bootstrap_is_idempotent_end_state(monkeypatch):
    """Running twice converges on the same active bcrypt credential."""
    for existing in (False, True):
        calls = _bootstrap_harness(monkeypatch, existing=existing)
        ba.bootstrap({}, "break_glass_admin", "$2b$12$hash")
        applied = [c for c in calls if c.startswith(("INSERT", "UPDATE"))]
        assert len(applied) == 1
        assert "status='active'" in applied[0] or "'active'" in applied[0]
        assert "bcrypt" in applied[0]


def test_missing_user_is_fail_closed(monkeypatch):
    monkeypatch.setattr(ba, "_psql", lambda env, sql, tuples_only=True: "")
    with pytest.raises(SystemExit):
        ba.bootstrap({}, "nobody", "$2b$12$hash")


def test_verification_failure_is_fail_closed(monkeypatch):
    def fake_psql(env, sql, tuples_only=True):
        if sql.startswith("SELECT id FROM users"):
            return "uid"
        if sql.startswith("SELECT 1 FROM local_credentials"):
            return ""
        if sql.startswith("SELECT status"):
            return "disabled|bcrypt"
        return ""
    monkeypatch.setattr(ba, "_psql", fake_psql)
    with pytest.raises(SystemExit):
        ba.bootstrap({}, "break_glass_admin", "$2b$12$hash")


def test_tool_does_not_persist_plaintext():
    src = BOOTSTRAP.read_text()
    assert "write_text(password" not in src and "open(" not in src.replace("read_text", "")
    assert "getpass" in src
    assert "del password" in src


# --- FU2: pilot compose omits MANIFEST_SIGNING_KEY for control-api -----------
#
# docker-compose.pilot.yml passes MANIFEST_SIGNING_KEY to device-gateway and
# orchestrator-worker but not to control-api. verify-pilot-run.sh runs with
# ENVIRONMENT=dev, where the production validator is skipped, so CI never saw
# it. Under ENVIRONMENT=staging/production control-api refuses to boot. The
# stand runs as staging, so the overlay supplies the variable.

def test_pilot_compose_still_omits_manifest_key_for_control_api():
    """Guards the reason the overlay carries this variable.

    If the pilot compose is fixed, this test fails on purpose: remove the
    workaround from the overlay instead of keeping a silent duplicate.
    """
    pilot = yaml.safe_load(PILOT.read_text())
    env = (pilot["services"]["control-api"] or {}).get("environment", {}) or {}
    keys = set(env) if isinstance(env, dict) else {e.split("=", 1)[0] for e in env}
    assert "MANIFEST_SIGNING_KEY" not in keys, (
        "pilot compose now sets MANIFEST_SIGNING_KEY for control-api - "
        "drop the workaround from docker-compose.local-stand.yml")


def test_overlay_supplies_manifest_key_to_control_api():
    doc = load_overlay()
    env = doc["services"]["control-api"]["environment"]
    assert env["MANIFEST_SIGNING_KEY"] == "${MANIFEST_SIGNING_KEY}"


def test_manifest_key_is_required_by_staging_validator():
    cfg = (REPO_ROOT / "packages" / "security" / "config.py").read_text()
    assert "MANIFEST_SIGNING_KEY must be set in production/staging" in cfg


def test_services_needing_manifest_key_all_receive_it():
    pilot = yaml.safe_load(PILOT.read_text())
    overlay = load_overlay()
    for svc in ("device-gateway", "orchestrator-worker"):
        assert "MANIFEST_SIGNING_KEY" in (pilot["services"][svc]["environment"] or {}), svc
    merged = dict((pilot["services"]["control-api"] or {}).get("environment", {}) or {})
    merged.update(overlay["services"]["control-api"]["environment"])
    assert "MANIFEST_SIGNING_KEY" in merged


# --- FU3: pilot compose omits CORS_ALLOWED_ORIGINS for device-gateway --------
#
# Same class as the MANIFEST_SIGNING_KEY gap: the shared security validator
# requires an explicit CORS list under staging/production, but the pilot compose
# only passes it to control-api. On the real host device-gateway entered a
# restart loop. The stand overlay supplies it.

def test_pilot_compose_still_omits_cors_for_device_gateway():
    """Guards the reason the overlay carries this variable; fails once fixed."""
    pilot = yaml.safe_load(PILOT.read_text())
    env = (pilot["services"]["device-gateway"] or {}).get("environment", {}) or {}
    keys = set(env) if isinstance(env, dict) else {e.split("=", 1)[0] for e in env}
    assert "CORS_ALLOWED_ORIGINS" not in keys, (
        "pilot compose now sets CORS_ALLOWED_ORIGINS for device-gateway - "
        "drop the workaround from docker-compose.local-stand.yml")


def test_overlay_supplies_cors_to_device_gateway():
    doc = load_overlay()
    env = doc["services"]["device-gateway"]["environment"]
    assert env["CORS_ALLOWED_ORIGINS"] == "${CORS_ALLOWED_ORIGINS}"


def test_cors_is_required_by_staging_validator():
    cfg = (REPO_ROOT / "packages" / "security" / "config.py").read_text()
    assert "CORS_ALLOWED_ORIGINS must be set to an explicit list in production" in cfg


def test_every_service_the_validator_gates_gets_its_variables():
    """control-api and device-gateway must end up with both gated variables."""
    pilot = yaml.safe_load(PILOT.read_text())
    overlay = load_overlay()
    for svc in ("control-api", "device-gateway"):
        merged = dict((pilot["services"][svc] or {}).get("environment", {}) or {})
        merged.update((overlay["services"].get(svc) or {}).get("environment", {}) or {})
        assert "MANIFEST_SIGNING_KEY" in merged, svc
        assert "CORS_ALLOWED_ORIGINS" in merged, svc


# --- FU4: Compose concatenates port lists across files ------------------------
#
# Merging two compose files CONCATENATES their `ports` lists. Without !override
# each service ended up with the pilot's 0.0.0.0 mapping AND the stand's
# address-scoped one: the second bind failed with "address already in use", and
# the 0.0.0.0 mapping would have published the stand on every interface. Both
# were observed on the real host.

def _overlay_raw() -> str:
    return OVERLAY.read_text()


def test_overlay_overrides_ports_it_redefines():
    """Any service whose ports the pilot also defines must use !override."""
    pilot = yaml.safe_load(PILOT.read_text())
    raw = _overlay_raw()
    for svc in ("control-api", "device-gateway", "admin-web", "advertiser-web"):
        assert (pilot["services"][svc] or {}).get("ports"), \
            f"{svc}: pilot no longer defines ports - revisit the override"
        block = raw.split(f"\n  {svc}:", 1)[1].split("\n  ", 1)[0] if f"\n  {svc}:" in raw else ""
        # locate this service's own ports declaration
        start = raw.index(f"\n  {svc}:")
        nxt = raw.find("\n  ", start + len(f"\n  {svc}:"))
        while nxt != -1 and raw[nxt:nxt + 4] == "\n   ":
            nxt = raw.find("\n  ", nxt + 1)
        section = raw[start:] if nxt == -1 else raw[start:nxt]
        assert "ports: !override" in section, (
            f"{svc}: ports must use !override or Compose will concatenate the "
            f"pilot list and the bind will collide")


def test_minio_needs_no_override():
    """minio publishes nothing in the pilot file, so a plain list is correct."""
    pilot = yaml.safe_load(PILOT.read_text())
    assert not (pilot["services"]["minio"] or {}).get("ports")


def _merged_ports() -> dict:
    """Merge the two files the way Compose does: concatenate port lists."""
    class _L(yaml.SafeLoader):
        pass

    def _override(loader, node):
        seq = loader.construct_sequence(node)
        return {"__override__": seq}

    _L.add_constructor("!override", _override)
    pilot = yaml.safe_load(PILOT.read_text())
    overlay = yaml.load(_overlay_raw(), Loader=_L)

    merged = {}
    for svc, spec in overlay["services"].items():
        base = list((pilot["services"].get(svc) or {}).get("ports", []) or [])
        own = (spec or {}).get("ports")
        if isinstance(own, dict) and "__override__" in own:
            merged[svc] = list(own["__override__"])
        else:
            merged[svc] = base + list(own or [])
    return merged


def test_no_service_ends_up_with_duplicate_published_ports():
    for svc, ports in _merged_ports().items():
        published = [str(p).split(":")[-2] for p in ports if str(p).count(":") >= 2]
        assert len(published) == len(set(published)), \
            f"{svc}: duplicate published port after merge -> {ports}"


def test_no_service_publishes_on_all_interfaces():
    for svc, ports in _merged_ports().items():
        for mapping in ports:
            assert str(mapping).count(":") >= 2, \
                f"{svc}: '{mapping}' has no host address - it would bind 0.0.0.0"
            host = str(mapping).rsplit(":", 2)[0]
            assert host not in ("", "0.0.0.0", "::"), \
                f"{svc}: '{mapping}' publishes on every interface"


# --- FU5: frontend healthchecks resolve localhost to IPv6 ---------------------
#
# /etc/hosts in these images maps localhost to both 127.0.0.1 and ::1. wget
# tries IPv6 first, nginx listens on IPv4 only, so the pilot probe reported
# "connection refused" while the site served fine from the LAN.

@pytest.mark.parametrize("svc,port", [("admin-web", 3000), ("advertiser-web", 3001)])
def test_overlay_healthcheck_avoids_localhost_ambiguity(svc, port):
    doc = load_overlay()
    test = doc["services"][svc]["healthcheck"]["test"]
    probe = test[-1] if isinstance(test, list) else str(test)
    assert f"127.0.0.1:{port}" in probe, f"{svc}: probe must pin IPv4"
    assert "localhost" not in probe, (
        f"{svc}: localhost resolves to ::1 first; nginx listens on IPv4 only")


def test_pilot_healthchecks_still_use_localhost():
    """Guards the reason the overlay overrides them; fails once pilot is fixed."""
    pilot = yaml.safe_load(PILOT.read_text())
    for svc in ("admin-web", "advertiser-web"):
        probe = pilot["services"][svc]["healthcheck"]["test"][-1]
        assert "localhost" in probe, (
            f"pilot {svc} healthcheck no longer uses localhost - "
            f"drop the override from docker-compose.local-stand.yml")
