"""LOCAL-STAND-COOKIE-001 — the local-stand refresh-cookie exception.

A disposable local DEV/QA stand runs as staging on plain HTTP over a private
LAN. Browsers drop a Secure cookie there, so the session cannot survive a
reload. These tests pin the exception to exactly that case and prove it stays
closed everywhere else.
"""

from __future__ import annotations

import importlib
import os

import pytest

import packages.security.config as cfgmod


STAND_ORIGINS = "http://192.168.110.81:3000,http://192.168.110.81:3001"


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch):
    """Full isolation: env changes go through monkeypatch and the module is
    reloaded afterwards, so these tests cannot leak configuration into the rest
    of the suite (they did before this fixture took ownership of _build)."""
    for key in ("ENVIRONMENT", "LOCAL_STAND_MODE", "REFRESH_TOKEN_COOKIE_SECURE",
                "SEED_DEV_CREDENTIALS", "CORS_ALLOWED_ORIGINS", "JWT_SECRET",
                "JWT_AUDIENCE", "MANIFEST_SIGNING_KEY", "PYTEST_CURRENT_TEST"):
        monkeypatch.delenv(key, raising=False)
    # strong values so only the cookie gate can fail the build
    monkeypatch.setenv("JWT_SECRET", "s" * 40)
    monkeypatch.setenv("JWT_AUDIENCE", "rmp-control-api")
    monkeypatch.setenv("MANIFEST_SIGNING_KEY", "m" * 40)
    monkeypatch.setenv("METRICS_AUTH_TOKEN", "t" * 40)

    def build(**env):
        for k, v in env.items():
            if v is None:
                monkeypatch.delenv(k, raising=False)
            else:
                monkeypatch.setenv(k, v)
        importlib.reload(cfgmod)
        return cfgmod.SecurityConfig()

    global _build
    _build = build
    yield
    # restore the module for every other test in the session
    importlib.reload(cfgmod)


def _build(**env):  # replaced per-test by the isolated_env fixture
    raise RuntimeError("_build is provided by the _isolated_env fixture")


def _stand_env(**over):
    env = {
        "ENVIRONMENT": "staging",
        "LOCAL_STAND_MODE": "true",
        "REFRESH_TOKEN_COOKIE_SECURE": "false",
        "SEED_DEV_CREDENTIALS": "false",
        "CORS_ALLOWED_ORIGINS": STAND_ORIGINS,
    }
    env.update(over)
    return env


# --- the exception itself ----------------------------------------------------

def test_local_stand_may_disable_secure():
    cfg = _build(**_stand_env())
    assert cfg.refresh_token_cookie_secure is False
    assert cfg.local_stand_mode is True


def test_httponly_and_samesite_are_not_weakened():
    """The exception covers Secure only - nothing else may be relaxed."""
    cfg = _build(**_stand_env())
    assert cfg.refresh_token_cookie_samesite == "strict"
    assert cfg.refresh_token_cookie_name == "refresh_token"
    assert cfg.refresh_token_cookie_path == "/api/v1/auth"


def test_default_is_secure_everywhere():
    cfg = _build(ENVIRONMENT="staging", CORS_ALLOWED_ORIGINS=STAND_ORIGINS,
                 METRICS_AUTH_TOKEN="t" * 40)
    assert cfg.refresh_token_cookie_secure is True
    assert cfg.local_stand_mode is False


# --- negative matrix: every gate must be load-bearing ------------------------

@pytest.mark.parametrize("override,reason", [
    ({"ENVIRONMENT": "production"}, "ENVIRONMENT"),
    ({"LOCAL_STAND_MODE": "false"}, "LOCAL_STAND_MODE"),
    ({"LOCAL_STAND_MODE": None}, "LOCAL_STAND_MODE"),
    ({"SEED_DEV_CREDENTIALS": "true"}, "SEED_DEV_CREDENTIALS"),
    ({"CORS_ALLOWED_ORIGINS": "*"}, "wildcard"),
    ({"CORS_ALLOWED_ORIGINS": "https://rmp.example.com"}, "private"),
    ({"CORS_ALLOWED_ORIGINS": "http://8.8.8.8:3000"}, "private"),
    ({"CORS_ALLOWED_ORIGINS": None}, "CORS_ALLOWED_ORIGINS"),
])
def test_insecure_cookie_rejected_when_a_gate_fails(override, reason):
    with pytest.raises(ValueError) as excinfo:
        _build(**_stand_env(**override))
    assert reason.lower() in str(excinfo.value).lower(), str(excinfo.value)


@pytest.mark.parametrize("origin", ["http://0.0.0.0:3000", "http://[::]:3000"])
def test_unspecified_bind_origin_is_refused(origin):
    """0.0.0.0 is not a destination; it must never carry an insecure cookie."""
    with pytest.raises(ValueError):
        _build(**_stand_env(CORS_ALLOWED_ORIGINS=origin))


def test_pilot_environment_is_gated_outside_pytest(monkeypatch):
    """ENVIRONMENT=pilot must hit the gate in a real deployment.

    Under pytest the product's dev heuristic treats an unknown ENVIRONMENT as
    dev (PYTEST_CURRENT_TEST is set), which never happens on a real host - so
    the heuristic is pinned off for this check.
    """
    importlib.reload(cfgmod)
    for key, val in _stand_env(ENVIRONMENT="pilot").items():
        if val is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, val)
    # dev_mode is a dataclass default_factory, so it is passed explicitly here
    # rather than patched: on a real host the heuristic returns False for an
    # unknown ENVIRONMENT because PYTEST_CURRENT_TEST is absent.
    with pytest.raises(ValueError) as excinfo:
        cfgmod.SecurityConfig(dev_mode=False)
    assert "ENVIRONMENT" in str(excinfo.value)


def test_failure_is_fail_closed_not_silent_downgrade():
    """A bad request must refuse to boot, not quietly re-enable Secure."""
    with pytest.raises(ValueError):
        _build(**_stand_env(ENVIRONMENT="production"))


@pytest.mark.parametrize("origin,ok", [
    ("http://localhost:3000", True),
    ("http://127.0.0.1:3000", True),
    ("http://192.168.110.81:3000", True),
    ("http://10.1.2.3:3000", True),
    ("http://172.16.0.9:3000", True),
    ("https://192.168.110.81:3000", False),   # https is not the HTTP exception
    ("http://8.8.8.8:3000", False),
    ("http://rmp.example.com", False),
    ("http://0.0.0.0:3000", False),   # wildcard, not a destination
    ("http://[::]:3000", False),      # wildcard, not a destination
    ("*", False),
])
def test_private_http_origin_classifier(origin, ok):
    assert cfgmod._is_private_http_origin(origin) is ok


# --- production / pilot must never be affected -------------------------------

def test_production_keeps_secure_even_if_asked_nicely():
    with pytest.raises(ValueError):
        _build(ENVIRONMENT="production", LOCAL_STAND_MODE="true",
               REFRESH_TOKEN_COOKIE_SECURE="false",
               SEED_DEV_CREDENTIALS="false",
               CORS_ALLOWED_ORIGINS=STAND_ORIGINS)


def test_pilot_compose_does_not_set_the_override():
    import yaml
    from pathlib import Path
    pilot = yaml.safe_load(
        (Path(__file__).resolve().parents[1] /
         "infra/compose/docker-compose.pilot.yml").read_text())
    for name, spec in pilot["services"].items():
        env = (spec or {}).get("environment", {}) or {}
        keys = set(env) if isinstance(env, dict) else {
            e.split("=", 1)[0] for e in env}
        assert "REFRESH_TOKEN_COOKIE_SECURE" not in keys, name
        assert "LOCAL_STAND_MODE" not in keys, name


def test_local_stand_overlay_sets_both_flags_explicitly():
    import yaml
    from pathlib import Path

    class _L(yaml.SafeLoader):
        pass

    _L.add_constructor("!override", lambda l, n: l.construct_sequence(n)
                       if isinstance(n, yaml.SequenceNode) else None)
    _L.add_constructor("!reset", lambda l, n: None)
    overlay = yaml.load(
        (Path(__file__).resolve().parents[1] /
         "infra/compose/docker-compose.local-stand.yml").read_text(), Loader=_L)
    env = overlay["services"]["control-api"]["environment"]
    assert env["LOCAL_STAND_MODE"] == "true"
    assert env["REFRESH_TOKEN_COOKIE_SECURE"] == "false"
