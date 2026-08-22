"""Version identity tests (PILOT-DEPLOYMENT-READINESS-001B, SCOPE D).

Covers:
- fields present;
- SHA/version validated;
- no secrets in payload;
- missing build metadata fail-closed in pilot/production;
- dev has honest fallback (dev/unknown), never production-looking.
"""

import pytest

from packages.version import (
    VERSION_FIELDS,
    build_version_payload,
    environment_name,
    is_strict_environment,
)


def _set_env(monkeypatch, **kwargs):
    for k in ("RMP_VERSION", "RMP_GIT_SHA", "RMP_BUILD_TIME", "RMP_SCHEMA_HEAD", "ENVIRONMENT", "PYTEST_CURRENT_TEST"):
        monkeypatch.delenv(k, raising=False)
    for k, v in kwargs.items():
        monkeypatch.setenv(k, v)


class TestFieldsPresent:
    def test_all_fields_present(self, monkeypatch):
        _set_env(
            monkeypatch,
            RMP_VERSION="v0.11.0-pilot-control-plane",
            RMP_GIT_SHA="e13020768c7cc1c2358ff03713baf32fc6ae409c",
            RMP_BUILD_TIME="2026-08-22T00:00:00Z",
            RMP_SCHEMA_HEAD="034",
            ENVIRONMENT="pilot",
        )
        payload = build_version_payload("control-api")
        for field in VERSION_FIELDS:
            assert field in payload, f"missing field {field}"

    def test_service_and_values_reflected(self, monkeypatch):
        _set_env(
            monkeypatch,
            RMP_VERSION="v1.2.3",
            RMP_GIT_SHA="a" * 40,
            RMP_BUILD_TIME="2026-01-01T00:00:00Z",
            ENVIRONMENT="pilot",
        )
        payload = build_version_payload("device-gateway")
        assert payload["service"] == "device-gateway"
        assert payload["version"] == "v1.2.3"
        assert payload["git_sha"] == "a" * 40
        assert payload["environment"] == "pilot"

    def test_schema_head_optional_and_none_when_unset(self, monkeypatch):
        _set_env(
            monkeypatch,
            RMP_VERSION="v1",
            RMP_GIT_SHA="a" * 40,
            RMP_BUILD_TIME="t",
            ENVIRONMENT="pilot",
        )
        payload = build_version_payload("control-api")
        assert payload["schema_head"] is None


class TestNoSecrets:
    def test_payload_has_no_secret_like_values(self, monkeypatch):
        # Set unrelated secret-bearing env vars: the version payload must NOT
        # reflect any of them — only the RMP_* identity fields.
        _set_env(
            monkeypatch,
            RMP_VERSION="v0.11.0-pilot-control-plane",
            RMP_GIT_SHA="e13020768c7cc1c2358ff03713baf32fc6ae409c",
            RMP_BUILD_TIME="2026-08-22T00:00:00Z",
            ENVIRONMENT="pilot",
            DATABASE_URL="postgresql://user:dbsecret@host/db",
            JWT_SECRET="x" * 64,
            MINIO_SECRET_KEY="minioadmin",
        )
        payload = build_version_payload("control-api")
        blob = str(payload)
        for forbidden in ("dbsecret", "minioadmin", "JWT_SECRET", "DATABASE_URL"):
            assert forbidden not in blob, f"secret leaked: {forbidden}"

    def test_payload_only_contains_version_fields(self, monkeypatch):
        _set_env(
            monkeypatch,
            RMP_VERSION="v1",
            RMP_GIT_SHA="a" * 40,
            RMP_BUILD_TIME="t",
            ENVIRONMENT="pilot",
            JWT_SECRET="x" * 64,
            DATABASE_URL="postgresql://u:pw@h/db",
        )
        payload = build_version_payload("control-api")
        assert set(payload.keys()) == set(VERSION_FIELDS)
        # No env dump: the payload must not contain any key that isn't a
        # declared version field.
        for key in payload:
            assert key in VERSION_FIELDS


class TestStrictFailClosed:
    @pytest.mark.parametrize("env", ["pilot", "production", "staging"])
    def test_missing_metadata_raises_in_strict(self, monkeypatch, env):
        _set_env(monkeypatch, ENVIRONMENT=env)  # no RMP_VERSION/SHA/TIME
        with pytest.raises(RuntimeError, match="build metadata missing"):
            build_version_payload("control-api")

    def test_partial_metadata_raises_in_pilot(self, monkeypatch):
        _set_env(
            monkeypatch,
            ENVIRONMENT="pilot",
            RMP_VERSION="v1",
            # RMP_GIT_SHA and RMP_BUILD_TIME missing
        )
        with pytest.raises(RuntimeError):
            build_version_payload("control-api")

    def test_strict_env_detection(self):
        assert is_strict_environment() is False  # default dev/test


class TestDevFallback:
    @pytest.mark.parametrize("env", ["dev", "development", "local", "test", ""])
    def test_dev_fallback_never_production(self, monkeypatch, env):
        _set_env(monkeypatch, ENVIRONMENT=env)
        payload = build_version_payload("control-api")
        assert payload["version"] == "dev"
        assert payload["git_sha"] == "unknown"
        assert payload["build_time"] == "unknown"
        assert payload["environment"] in ("dev", "development", "local", "test", "")

    def test_dev_does_not_raise_on_missing(self, monkeypatch):
        _set_env(monkeypatch, ENVIRONMENT="dev")
        payload = build_version_payload("control-api")
        assert payload["version"] == "dev"


class TestSHAValidation:
    @pytest.mark.parametrize("sha", [
        "e13020768c7cc1c2358ff03713baf32fc6ae409c",  # 40 hex
        "e130207",  # short form accepted as injected value
    ])
    def test_sha_accepted_in_strict(self, monkeypatch, sha):
        _set_env(
            monkeypatch,
            ENVIRONMENT="pilot",
            RMP_VERSION="v1",
            RMP_GIT_SHA=sha,
            RMP_BUILD_TIME="t",
        )
        payload = build_version_payload("control-api")
        assert payload["git_sha"] == sha
