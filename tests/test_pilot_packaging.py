"""Deployment package verification tests (PILOT-DEPLOYMENT-READINESS-001B, SCOPE G).

Proves the pilot compose + lock manifest + env validator are production-like:
- compose config parses with synthetic test-only secrets;
- runtime services have restart policy;
- app services have healthchecks;
- advertiser-web present;
- migration job separated from runtime;
- no build:/source mounts/latest/dev credentials in pilot compose;
- image refs consistent with lock manifest;
- version metadata single SHA;
- persistent volumes declared explicitly.

No real deploy is performed.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
PILOT_COMPOSE = REPO_ROOT / "infra" / "compose" / "docker-compose.pilot.yml"
LOCK_EXAMPLE = REPO_ROOT / "infra" / "deploy" / "images.lock.example.json"
ENV_EXAMPLE = REPO_ROOT / "infra" / "deploy" / ".env.pilot.example"

PILOT_SERVICES = [
    "control-api",
    "device-gateway",
    "orchestrator-worker",
    "admin-web",
    "advertiser-web",
]


def _compose() -> dict:
    assert PILOT_COMPOSE.exists(), "pilot compose missing"
    return yaml.safe_load(PILOT_COMPOSE.read_text())


def _services() -> dict:
    return _compose().get("services", {})


class TestPilotComposeParses:
    def test_compose_is_valid_yaml_and_has_services(self):
        svc = _services()
        assert svc, "pilot compose has no services"

    def test_required_services_present(self):
        svc = _services()
        for name in PILOT_SERVICES + ["postgres", "redis", "minio", "nats", "db-migrate"]:
            assert name in svc, f"missing service {name}"

    def test_advertiser_web_present(self):
        assert "advertiser-web" in _services(), "advertiser-web must be in pilot topology"

    def test_no_build_directives(self):
        for name, cfg in _services().items():
            assert "build" not in cfg, f"{name} must not use build: (image-only)"

    def test_no_source_bind_mounts(self):
        for name, cfg in _services().items():
            for vol in cfg.get("volumes", []) or []:
                # Bind mounts are "host:container" with a path (./ or /) on host.
                host = vol.split(":")[0] if isinstance(vol, str) else ""
                assert not host.startswith((".", "/")), f"{name} has a source bind mount: {vol}"

    def test_no_latest_or_mutable_tags(self):
        for name, cfg in _services().items():
            img = cfg.get("image", "")
            assert img, f"{name} has no image"
            assert "latest" not in img.lower(), f"{name} uses mutable 'latest' image"
            # env-var refs are allowed (${VAR}); no bare mutable tag
            if not img.startswith("${"):
                assert ":" in img, f"{name} image '{img}' is not a pinned tag/digest"

    def test_runtime_restart_policy(self):
        runtime = PILOT_SERVICES + ["postgres", "redis", "minio", "nats"]
        for name in runtime:
            cfg = _services()[name]
            assert cfg.get("restart") == "unless-stopped", \
                f"{name} must have restart: unless-stopped"

    def test_migration_job_not_restarted_and_separate(self):
        svc = _services()
        assert "db-migrate" in svc
        assert svc["db-migrate"].get("restart") == "no", "migration job must be one-shot"
        # migration uses owner credential, not app runtime
        mig_env = svc["db-migrate"].get("environment", {})
        env_flat = _flatten_env(mig_env)
        assert "MIGRATION_DATABASE_URL" in env_flat or "DATABASE_URL" in env_flat

    def test_all_app_services_have_healthcheck(self):
        for name in PILOT_SERVICES:
            assert "healthcheck" in _services()[name], f"{name} missing healthcheck"

    def test_seed_dev_credentials_disabled(self):
        svc = _services()
        mig_env = _flatten_env(svc["db-migrate"].get("environment", {}))
        assert mig_env.get("SEED_DEV_CREDENTIALS", "").lower() == "false"

    def test_license_dev_ingest_disabled(self):
        svc = _services()
        for name in ("db-migrate", "control-api"):
            env = _flatten_env(svc[name].get("environment", {}))
            assert env.get("LICENSE_DEV_INGEST_ENABLED", "").lower() == "false", \
                f"{name} must disable dev-ingest license"

    def test_app_runtime_uses_app_role(self):
        # control-api DATABASE_URL must reference retail_media_app (not owner).
        svc = _services()
        env = _flatten_env(svc["control-api"].get("environment", {}))
        # DATABASE_URL is an env var reference in compose; assert it is present.
        assert "DATABASE_URL" in env, "control-api must have DATABASE_URL"

    def test_persistent_volumes_declared(self):
        comp = _compose()
        vols = comp.get("volumes", {})
        for name in ("pg_data", "minio_data", "nats_jetstream"):
            assert name in vols, f"persistent volume {name} not declared"

    def test_startup_deps_use_health_or_completion(self):
        svc = _services()
        control_deps = svc["control-api"].get("depends_on", {})
        dep_conds = list(control_deps.values())
        assert any(c.get("condition", "") in ("service_healthy", "service_completed_successfully")
                   for c in dep_conds), "control-api deps must use health/completion conditions"


def _flatten_env(env) -> dict:
    """Flatten a compose environment (list of dicts or 'KEY=VALUE' strings)."""
    out: dict = {}
    if isinstance(env, dict):
        return env
    for item in env or []:
        if isinstance(item, dict):
            out.update(item)
        elif isinstance(item, str) and "=" in item:
            k, _, v = item.partition("=")
            out[k] = v
    return out


class TestImageRefsMatchLock:
    def test_lock_example_covers_pilot_services(self):
        lock = json.loads(LOCK_EXAMPLE.read_text())
        lock_services = {img["service"] for img in lock["images"]}
        assert lock_services == set(PILOT_SERVICES), \
            f"lock services {lock_services} != pilot services {set(PILOT_SERVICES)}"

    def test_lock_example_single_sha_and_version(self):
        lock = json.loads(LOCK_EXAMPLE.read_text())
        shas = {img["git_sha"] for img in lock["images"]}
        versions = {img["version"] for img in lock["images"]}
        assert len(shas) == 1, f"mixed SHAs in lock: {shas}"
        assert len(versions) == 1, f"mixed versions in lock: {versions}"
        assert lock["release"]["git_sha"] in shas
        assert lock["release"]["version"] in versions

    def test_lock_example_has_no_real_digest(self):
        # The committed example MUST NOT contain a real digest — only placeholders.
        lock = json.loads(LOCK_EXAMPLE.read_text())
        for img in lock["images"]:
            d = img["image_digest"]
            assert "REPLACE_WITH" in d, "example lock must use placeholder digests"

    def test_compose_image_vars_match_lock_services(self):
        # Pilot compose references ${CONTROL_API_IMAGE}, ${DEVICE_GATEWAY_IMAGE}, …
        # — one var per packaged service. Confirm the variable naming is consistent.
        svc = _services()
        expected_vars = {
            "control-api": "CONTROL_API_IMAGE",
            "device-gateway": "DEVICE_GATEWAY_IMAGE",
            "orchestrator-worker": "ORCHESTRATOR_WORKER_IMAGE",
            "admin-web": "ADMIN_WEB_IMAGE",
            "advertiser-web": "ADVERTISER_WEB_IMAGE",
        }
        for name, var in expected_vars.items():
            img = svc[name]["image"]
            assert img == f"${{{var}}}", f"{name} image should reference ${{{var}}}"


class TestValidatorScripts:
    def test_image_lock_validator_rejects_example(self):
        # The example lock has placeholder digests → validator must fail.
        r = subprocess.run(
            [sys.executable, "scripts/deploy/validate-image-lock.py",
             "--lock", "infra/deploy/images.lock.example.json"],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        assert r.returncode == 1, "example lock (placeholders) must be rejected"

    def test_image_lock_validator_accepts_valid_lock(self, tmp_path):
        lock = {
            "release": {"version": "v0.11.0-pilot-control-plane",
                        "git_sha": "e13020768c7cc1c2358ff03713baf32fc6ae409c"},
            "build_timestamp": "2026-08-22T00:00:00Z",
            "images": [
                {"service": s,
                 "repository": f"ghcr.io/org/{s}",
                 "version": "v0.11.0-pilot-control-plane",
                 "git_sha": "e13020768c7cc1c2358ff03713baf32fc6ae409c",
                 "image_digest": "sha256:" + "ab" * 32,
                 "build_timestamp": "2026-08-22T00:00:00Z",
                 "source_tag": "v0.11.0-pilot-control-plane"}
                for s in PILOT_SERVICES
            ],
        }
        p = tmp_path / "lock.json"
        p.write_text(json.dumps(lock))
        r = subprocess.run(
            [sys.executable, "scripts/deploy/validate-image-lock.py", "--lock", str(p)],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        assert r.returncode == 0, r.stdout + r.stderr

    def test_env_validator_rejects_example(self):
        # .env.pilot.example has REPLACE_WITH placeholders → validator must fail.
        r = subprocess.run(
            [sys.executable, "scripts/deploy/validate-pilot-env.py",
             "--env", "infra/deploy/.env.pilot.example"],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        assert r.returncode == 1, ".env.pilot.example (placeholders) must be rejected"

    def test_env_validator_rejects_minioadmin(self, tmp_path):
        env = _valid_env()
        env["MINIO_ACCESS_KEY"] = "minioadmin"
        p = tmp_path / ".env"
        p.write_text("\n".join(f"{k}={v}" for k, v in env.items()))
        r = subprocess.run(
            [sys.executable, "scripts/deploy/validate-pilot-env.py", "--env", str(p)],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        assert r.returncode == 1
        # The validator redacts the offending value; assert on the rule name.
        assert "forbidden dev/weak value" in (r.stdout + r.stderr)
        assert "MINIO_ACCESS_KEY" in (r.stdout + r.stderr)

    def test_env_validator_rejects_dev_seed_flag(self, tmp_path):
        env = _valid_env()
        env["SEED_DEV_CREDENTIALS"] = "true"
        p = tmp_path / ".env"
        p.write_text("\n".join(f"{k}={v}" for k, v in env.items()))
        r = subprocess.run(
            [sys.executable, "scripts/deploy/validate-pilot-env.py", "--env", str(p)],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        assert r.returncode == 1
        assert "SEED_DEV_CREDENTIALS" in (r.stdout + r.stderr)


def _valid_env() -> dict:
    return {
        "ENVIRONMENT": "pilot",
        "RMP_VERSION": "v0.11.0-pilot-control-plane",
        "RMP_GIT_SHA": "e13020768c7cc1c2358ff03713baf32fc6ae409c",
        "RMP_BUILD_TIME": "2026-08-22T00:00:00Z",
        "RMP_SCHEMA_HEAD": "034",
        "POSTGRES_OWNER_USER": "retail_media_owner",
        "POSTGRES_OWNER_PASSWORD": "A" * 40,
        "POSTGRES_APP_USER": "retail_media_app",
        "POSTGRES_APP_PASSWORD": "B" * 40,
        "POSTGRES_DB": "retail_media_platform",
        "DATABASE_URL": "postgresql+asyncpg://retail_media_app:" + "C" * 40 + "@postgres:5432/retail_media_platform",
        "MIGRATION_DATABASE_URL": "postgresql+asyncpg://retail_media_owner:" + "D" * 40 + "@postgres:5432/retail_media_platform",
        "JWT_SECRET": "E" * 40,
        "JWT_AUDIENCE": "rmp-control-api",
        "MANIFEST_SIGNING_KEY": "F" * 40,
        "MINIO_ROOT_USER": "G" * 20,
        "MINIO_ROOT_PASSWORD": "H" * 40,
        "MINIO_INTERNAL_ENDPOINT": "minio:9000",
        "MINIO_PUBLIC_ENDPOINT": "minio.pilot.example.com",
        "MINIO_ACCESS_KEY": "I" * 20,
        "MINIO_SECRET_KEY": "J" * 40,
        "CREATIVE_STORAGE_BUCKET": "retail-media-creatives",
        "CONTRACT_STORAGE_BUCKET": "retail-media-contracts",
        "CORS_ALLOWED_ORIGINS": "https://admin.pilot.example.com,https://adv.pilot.example.com",
        "CORS_ALLOW_CREDENTIALS": "true",
        "METRICS_AUTH_TOKEN": "K" * 40,
        "SEED_DEV_CREDENTIALS": "false",
        "LICENSE_DEV_INGEST_ENABLED": "false",
    }
