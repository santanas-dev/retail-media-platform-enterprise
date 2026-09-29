"""RF-05 — the pilot compose boots under ENVIRONMENT=pilot.

P0-1…P0-4 of the 2026-09-27 review: the pilot compose was only ever run with
ENVIRONMENT=dev, where the production validator is skipped, so services that
lacked CORS / JWT_AUDIENCE / METRICS_AUTH_TOKEN / MANIFEST_SIGNING_KEY and a
db-migrate that never created the app role all looked green.

These tests build each backend service's environment exactly as the pilot
compose hands it over (``${VAR}`` resolved from strong synthetic values) and
run the real config code in a clean subprocess — no host env leaks in.
The live proof is ``scripts/ci/verify-pilot-run.sh --images-from-env`` (CI job
``pilot-compose-smoke``).
"""

from __future__ import annotations

import importlib.util
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
PILOT_COMPOSE = REPO_ROOT / "infra" / "compose" / "docker-compose.pilot.yml"
ENV_EXAMPLE = REPO_ROOT / "infra" / "deploy" / ".env.pilot.example"
BACKEND_SERVICES = ("control-api", "device-gateway", "orchestrator-worker")

# ${VAR} or ${VAR:-default}; group 2 is the default, if any.
_VAR = re.compile(r"\$\{([A-Z0-9_]+)(?::-([^}]*))?\}")

# Strong, non-default values of the kind validate-pilot-env.py accepts.
SYNTHETIC_ENV = {
    "ENVIRONMENT": "pilot",
    "RMP_VERSION": "v0.0.0-rf05",
    "RMP_GIT_SHA": "0" * 40,
    "RMP_BUILD_TIME": "2026-09-29T00:00:00Z",
    "RMP_SCHEMA_HEAD": "037",
    "POSTGRES_OWNER_USER": "retail_media_owner",
    "POSTGRES_OWNER_PASSWORD": "a" * 48,
    "POSTGRES_APP_USER": "retail_media_app",
    "POSTGRES_APP_PASSWORD": "b" * 48,
    "POSTGRES_DB": "retail_media_platform",
    "DATABASE_URL": "postgresql+asyncpg://retail_media_app:" + "b" * 48 + "@postgres:5432/retail_media_platform",
    "MIGRATION_DATABASE_URL": "postgresql+asyncpg://retail_media_owner:" + "a" * 48 + "@postgres:5432/retail_media_platform",
    "JWT_SECRET": "c" * 64,
    "JWT_AUDIENCE": "rmp-control-api",
    "MANIFEST_SIGNING_KEY": "d" * 64,
    "METRICS_AUTH_TOKEN": "e" * 64,
    "MINIO_ROOT_USER": "f" * 32,
    "MINIO_ROOT_PASSWORD": "g" * 48,
    "MINIO_INTERNAL_ENDPOINT": "minio:9000",
    "MINIO_PUBLIC_ENDPOINT": "media.pilot.example",
    "MINIO_ACCESS_KEY": "h" * 32,
    "MINIO_SECRET_KEY": "i" * 48,
    "CREATIVE_STORAGE_BUCKET": "retail-media-creatives",
    "CONTRACT_STORAGE_BUCKET": "retail-media-contracts",
    "CORS_ALLOWED_ORIGINS": "https://admin.pilot.example,https://ads.pilot.example",
    "CORS_ALLOW_CREDENTIALS": "true",
}


def _services() -> dict:
    return yaml.safe_load(PILOT_COMPOSE.read_text())["services"]


def _service_env(service: str, **overrides: str) -> dict[str, str]:
    """The service's container environment as compose would resolve it."""
    raw = _services()[service].get("environment") or {}
    env: dict[str, str] = {}
    for key, value in raw.items():
        text = str(value)
        missing = [v for v, default in _VAR.findall(text) if v not in SYNTHETIC_ENV and not default]
        assert not missing, f"{service}.{key}: no synthetic value for {missing}"
        env[key] = _VAR.sub(lambda m: SYNTHETIC_ENV.get(m.group(1), m.group(2)), text)
    env.update(overrides)
    return env


def _run_in(env: dict[str, str], code: str) -> subprocess.CompletedProcess:
    clean = {"PATH": os.environ.get("PATH", ""), "PYTHONPATH": str(REPO_ROOT), **env}
    return subprocess.run(
        [sys.executable, "-c", code], env=clean, cwd=REPO_ROOT,
        capture_output=True, text=True, timeout=60,
    )


_BOOT_CONFIG = (
    "from packages.security.config import get_security_config\n"
    "cfg = get_security_config()\n"
    "print('dev_mode', cfg.dev_mode)\n"
)


@pytest.mark.parametrize("service", BACKEND_SERVICES)
def test_security_config_boots_under_pilot(service):
    """P0-2 / P0-4 (+ control-api MANIFEST_SIGNING_KEY): no ValueError at import."""
    result = _run_in(_service_env(service), _BOOT_CONFIG)
    assert result.returncode == 0, f"{service}: {result.stderr.strip().splitlines()[-1:]}"
    assert "dev_mode False" in result.stdout, "pilot must be validated as production"


def test_device_token_issued_by_control_api_verifies_at_device_gateway():
    """P0-3: control-api issues device tokens; device-gateway must accept them."""
    device_id = str(uuid.uuid4())
    issued = _run_in(
        _service_env("control-api"),
        "from packages.security.jwt import create_access_token\n"
        f"print(create_access_token('{device_id}', 'device'))\n",
    )
    assert issued.returncode == 0, issued.stderr
    token = issued.stdout.strip().splitlines()[-1]

    verified = _run_in(
        _service_env("device-gateway"),
        "from packages.security.jwt import verify_access_token\n"
        f"c = verify_access_token('{token}')\n"
        "print(c['sub'], c['auth_provider'])\n",
    )
    assert verified.returncode == 0, verified.stderr.strip().splitlines()[-1:]
    assert verified.stdout.split() == [device_id, "device"]


def test_production_validator_requires_jwt_audience():
    """P0-3: an empty audience must fail at boot, not as 401 on every request."""
    env = _service_env("control-api")
    env.pop("JWT_AUDIENCE")
    result = _run_in(env, _BOOT_CONFIG)
    assert result.returncode != 0
    assert "JWT_AUDIENCE" in result.stderr


def test_db_migrate_creates_app_role_before_granting():
    """P0-1: nothing else creates retail_media_app in the pilot stack."""
    svc = _services()["db-migrate"]
    command = svc["command"]
    assert "create-app-role.py" in command
    assert command.index("create-app-role.py") < command.index("grant-app-role.py")
    env = svc["environment"]
    # grant-app-role.py grants to retail_media_app, so that is the only sane default.
    assert env.get("POSTGRES_APP_USER") == "${POSTGRES_APP_USER:-retail_media_app}"
    assert env.get("POSTGRES_APP_PASSWORD") == "${POSTGRES_APP_PASSWORD}"


def test_every_compose_variable_is_documented_in_env_example():
    example_keys = {
        line.split("=", 1)[0]
        for line in ENV_EXAMPLE.read_text().splitlines()
        if line and not line.startswith("#") and "=" in line
    }
    used = {name for name, _ in _VAR.findall(yaml.safe_dump(_services()))}
    image_vars = {v for v in used if v.endswith("_IMAGE")}
    assert used - image_vars - example_keys == set()


def test_no_literal_secrets_in_pilot_compose():
    """Owner condition RF-05: secrets only via env, never literal in compose."""
    secret_keys = ("PASSWORD", "SECRET", "TOKEN", "_KEY", "DATABASE_URL")
    for name, svc in _services().items():
        for key, value in (svc.get("environment") or {}).items():
            if any(s in key for s in secret_keys):
                m = _VAR.fullmatch(str(value))
                assert m and m.group(2) is None, f"{name}.{key} must be a plain ${{VAR}} reference (no default)"


# --- P2-I11: readiness enforces the DB role in every strict environment -------

_MAIN_PY = REPO_ROOT / "apps" / "control-api" / "main.py"


def _control_api_module():
    spec = importlib.util.spec_from_file_location("control_api_main_rf05", _MAIN_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize("environment,expected_dev", [
    ("pilot", False), (" Pilot ", False), ("staging", False), ("production", False),
    (None, False), ("dev", True), ("DEV", True),
])
def test_readiness_role_check_is_strict_outside_dev(monkeypatch, environment, expected_dev):
    from fastapi.testclient import TestClient

    mod = _control_api_module()
    if environment is None:
        monkeypatch.delenv("ENVIRONMENT", raising=False)
    else:
        monkeypatch.setenv("ENVIRONMENT", environment)
    with patch.object(mod, "check_db_health", new_callable=AsyncMock) as db, \
         patch.object(mod, "check_db_role_safety", new_callable=AsyncMock) as role, \
         patch.object(mod, "_engine", object()):
        db.return_value = (True, None)
        role.return_value = (True, {"db_role": "ok"})
        TestClient(mod.app).get("/health/ready")
    assert role.await_args.kwargs["dev_mode"] is expected_dev


# --- P2-I9: alembic env ---------------------------------------------------------

_ALEMBIC_ENV = REPO_ROOT / "apps" / "control-api" / "alembic" / "env.py"


def _alembic_url(env: dict[str, str]) -> subprocess.CompletedProcess:
    """Run only the URL-resolution prologue of alembic/env.py."""
    return _run_in(env, (
        "import sys, types\n"
        "from alembic.config import Config\n"
        "cfg = Config()\n"
        "ctx = types.SimpleNamespace(config=cfg)\n"
        "import alembic\n"
        "alembic.context = ctx\n"
        "sys.modules['alembic.context'] = ctx\n"
        f"src = open({str(_ALEMBIC_ENV)!r}).read().split('target_metadata =')[0]\n"
        f"exec(compile(src, {str(_ALEMBIC_ENV)!r}, 'exec'), {{'__file__': {str(_ALEMBIC_ENV)!r}}})\n"
        "print(cfg.get_main_option('sqlalchemy.url'))\n"
    ))


def test_alembic_url_with_percent_encoded_password():
    url = "postgresql+asyncpg://owner:p%40ss%25w@postgres:5432/db"
    result = _alembic_url({"ENVIRONMENT": "pilot", "DATABASE_URL": url})
    assert result.returncode == 0, result.stderr.strip().splitlines()[-1:]
    assert result.stdout.strip().splitlines()[-1] == url.replace("+asyncpg", "")


def test_alembic_refuses_localhost_fallback_in_strict_environment():
    result = _alembic_url({"ENVIRONMENT": "pilot"})
    assert result.returncode != 0
    assert "DATABASE_URL" in result.stderr


# --- P1-16: dev compose (phase1) --------------------------------------------------

PHASE1_COMPOSE = REPO_ROOT / "infra" / "compose" / "docker-compose.phase1.yml"


def test_phase1_host_ports_are_unique():
    services = yaml.safe_load(PHASE1_COMPOSE.read_text())["services"]
    seen: dict[str, str] = {}
    for name, svc in services.items():
        for mapping in svc.get("ports") or []:
            host_port = str(mapping).rsplit(":", 1)[0].rsplit(":", 1)[-1]
            assert host_port not in seen, f"host port {host_port}: {seen.get(host_port)} and {name}"
            seen[host_port] = name


def test_phase1_nats_healthcheck_does_not_need_nats_cli():
    probe = yaml.safe_load(PHASE1_COMPOSE.read_text())["services"]["nats"]["healthcheck"]["test"][-1]
    assert "nats server" not in probe
    assert "8222/healthz" in probe


# --- create-app-role.py never prints the password -------------------------------

def test_create_app_role_failure_does_not_print_password():
    """SQLAlchemy errors carry the failed statement; the script must not echo it."""
    password = "LEAK-" + "p" * 24
    code = (
        "import runpy, sys\n"
        "import packages.domain.database as db\n"
        "class Boom:\n"
        "    def begin(self):\n"
        f"        raise RuntimeError(\"[SQL: CREATE ROLE x PASSWORD '{password}']\")\n"
        "    async def dispose(self): pass\n"
        "db.create_engine = lambda *a, **k: Boom()\n"
        "runpy.run_path('infra/compose/create-app-role.py', run_name='__main__')\n"
    )
    result = _run_in({"POSTGRES_APP_PASSWORD": password, "ENVIRONMENT": "dev"}, code)
    assert result.returncode == 1
    assert "create-app-role failed (RuntimeError" in result.stderr
    assert password not in result.stdout + result.stderr


@pytest.mark.parametrize("name", ["Retail", "app-role", "x;drop", ""])
def test_create_app_role_rejects_non_identifier_names(name):
    result = _run_in(
        {"POSTGRES_APP_USER": name or " ", "POSTGRES_APP_PASSWORD": "x" * 24, "ENVIRONMENT": "dev"},
        "import runpy; runpy.run_path('infra/compose/create-app-role.py', run_name='__main__')\n",
    )
    assert result.returncode == 1
    assert "plain lowercase identifier" in result.stderr
