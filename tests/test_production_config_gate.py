"""
S-030 — Production Config Gate tests.

Verifies that ENVIRONMENT=production rejects:
- missing/weak JWT_SECRET
- missing/weak MANIFEST_SIGNING_KEY
- default MinIO credentials
- SEED_DEV_CREDENTIALS enabled
- wildcard CORS
- localhost CORS origins
- localhost DATABASE_URL
- dev default database passwords

And that dev/test mode still accepts dev defaults.
"""
import os
import pytest

# Singleton reset before each test
from packages.security.config import reset_security_config, SecurityConfig


@pytest.fixture(autouse=True)
def reset_config():
    """Reset the SecurityConfig singleton between tests."""
    reset_security_config()
    yield
    reset_security_config()


def _prod_config(**overrides) -> SecurityConfig:
    """Create a SecurityConfig with production-mode env + strong defaults,
    then apply overrides via monkeypatching os.environ."""
    # Strong production defaults
    env = {
        "ENVIRONMENT": "production",
        "JWT_SECRET": "a-strong-production-jwt-secret-at-least-32-chars!!",
        "MANIFEST_SIGNING_KEY": "a-strong-production-manifest-key-32c!!",
        "MINIO_ACCESS_KEY": "prod-minio-access-key-strong",
        "MINIO_SECRET_KEY": "prod-minio-secret-key-strong-unique",
        "CORS_ALLOWED_ORIGINS": "https://portal.example.com,https://admin.example.com",
        "DATABASE_URL": "postgresql+asyncpg://rmp_user:strong-prod-pass@db.internal:5432/rmp_prod",
        "SEED_DEV_CREDENTIALS": "",
    }
    env.update(overrides)
    # Sentinel: empty string means "delete this key from environment"
    # (used for testing missing/absent env vars in production)
    with _set_env(env):
        return SecurityConfig()


class _set_env:
    """Context manager to temporarily set environment variables."""

    def __init__(self, overrides: dict):
        self.overrides = overrides
        self.saved = {}

    def __enter__(self):
        for k, v in self.overrides.items():
            self.saved[k] = os.environ.get(k, "__NOT_SET__")
            if v == "":
                # Delete key — simulate absent env var
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def __exit__(self, *args):
        for k, saved in self.saved.items():
            if saved == "__NOT_SET__":
                os.environ.pop(k, None)
            else:
                os.environ[k] = saved


# ═══════════════════════════════════════════════
# Happy path — production accepts strong config
# ═══════════════════════════════════════════════


def test_production_accepts_strong_config():
    """Full production config with strong values must not raise."""
    cfg = _prod_config()
    assert not cfg.dev_mode
    assert cfg.jwt_secret == "a-strong-production-jwt-secret-at-least-32-chars!!"
    assert cfg.manifest_signing_key == "a-strong-production-manifest-key-32c!!"
    assert cfg.cors_allowed_origins == [
        "https://portal.example.com",
        "https://admin.example.com",
    ]


# ═══════════════════════════════════════════════
# JWT_SECRET
# ═══════════════════════════════════════════════


def test_production_rejects_missing_jwt_secret():
    with pytest.raises(ValueError, match="JWT_SECRET must be set"):
        _prod_config(JWT_SECRET="")


def test_production_rejects_short_jwt_secret():
    with pytest.raises(ValueError, match="at least 32"):
        _prod_config(JWT_SECRET="short")


# ═══════════════════════════════════════════════
# MANIFEST_SIGNING_KEY
# ═══════════════════════════════════════════════


def test_production_rejects_missing_manifest_key():
    with pytest.raises(ValueError, match="MANIFEST_SIGNING_KEY must be set"):
        _prod_config(MANIFEST_SIGNING_KEY="")


def test_production_rejects_short_manifest_key():
    with pytest.raises(ValueError, match="MANIFEST_SIGNING_KEY must be at least 32"):
        _prod_config(MANIFEST_SIGNING_KEY="short-key")


# ═══════════════════════════════════════════════
# MinIO
# ═══════════════════════════════════════════════


def test_production_rejects_default_minio_access_key():
    with pytest.raises(ValueError, match="MINIO_ACCESS_KEY must not be 'minioadmin'"):
        _prod_config(MINIO_ACCESS_KEY="minioadmin")


def test_production_rejects_default_minio_secret_key():
    with pytest.raises(ValueError, match="MINIO_SECRET_KEY must not be 'minioadmin'"):
        _prod_config(MINIO_SECRET_KEY="minioadmin")


# ═══════════════════════════════════════════════
# SEED_DEV_CREDENTIALS
# ═══════════════════════════════════════════════


def test_production_rejects_seed_dev_credentials_true():
    with pytest.raises(ValueError, match="SEED_DEV_CREDENTIALS must not be enabled"):
        _prod_config(SEED_DEV_CREDENTIALS="true")


def test_production_rejects_seed_dev_credentials_1():
    with pytest.raises(ValueError, match="SEED_DEV_CREDENTIALS must not be enabled"):
        _prod_config(SEED_DEV_CREDENTIALS="1")


def test_production_rejects_seed_dev_credentials_yes():
    with pytest.raises(ValueError, match="SEED_DEV_CREDENTIALS must not be enabled"):
        _prod_config(SEED_DEV_CREDENTIALS="yes")


def test_production_accepts_seed_dev_credentials_disabled():
    """Empty or false SEED_DEV_CREDENTIALS is fine."""
    cfg = _prod_config(SEED_DEV_CREDENTIALS="false")
    assert not cfg.dev_mode
    cfg2 = _prod_config(SEED_DEV_CREDENTIALS="")
    assert not cfg2.dev_mode


# ═══════════════════════════════════════════════
# CORS
# ═══════════════════════════════════════════════


def test_production_rejects_cors_localhost():
    with pytest.raises(ValueError, match="CORS origin.*localhost"):
        _prod_config(CORS_ALLOWED_ORIGINS="http://localhost:3000")


def test_production_rejects_cors_127():
    with pytest.raises(ValueError, match="CORS origin.*127\\.0\\.0\\.1"):
        _prod_config(CORS_ALLOWED_ORIGINS="http://127.0.0.1:3000")


def test_production_rejects_cors_wildcard():
    with pytest.raises(ValueError, match="CORS wildcard"):
        _prod_config(CORS_ALLOWED_ORIGINS="*")


def test_production_rejects_cors_wildcard_with_other_origins():
    with pytest.raises(ValueError, match="CORS wildcard"):
        _prod_config(
            CORS_ALLOWED_ORIGINS="https://portal.example.com,*"
        )


# ═══════════════════════════════════════════════
# DATABASE_URL
# ═══════════════════════════════════════════════


def test_production_rejects_localhost_db_url():
    with pytest.raises(ValueError, match="DATABASE_URL refers to a localhost"):
        _prod_config(
            DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/mydb"
        )


def test_production_rejects_127_db_url():
    with pytest.raises(ValueError, match="DATABASE_URL refers to a localhost"):
        _prod_config(
            DATABASE_URL="postgresql+asyncpg://user:pass@127.0.0.1:5432/mydb"
        )


def test_production_rejects_dev_password_retail_media_owner():
    with pytest.raises(ValueError, match="DATABASE_URL contains a known dev password"):
        _prod_config(
            DATABASE_URL="postgresql+asyncpg://retail_media_owner:retail_media_owner_pass@db.internal:5432/rmp"
        )


def test_production_rejects_dev_password_retail_media_app():
    with pytest.raises(ValueError, match="DATABASE_URL contains a known dev password"):
        _prod_config(
            DATABASE_URL="postgresql+asyncpg://some_user:retail_media_app@db.internal:5432/rmp"
        )


def test_production_accepts_remote_db_url():
    """Production DB URL with remote host and strong password must pass."""
    cfg = _prod_config(
        DATABASE_URL="postgresql+asyncpg://rmp_user:strong-unique-prod-pw@db-prod.internal:5432/rmp_prod"
    )
    assert not cfg.dev_mode


def test_production_skips_db_validation_when_empty():
    """If DATABASE_URL is not set, skip validation (service without DB)."""
    cfg = _prod_config(DATABASE_URL="")
    assert not cfg.dev_mode


# ═══════════════════════════════════════════════
# Dev mode — still works with defaults
# ═══════════════════════════════════════════════


def test_dev_mode_accepts_minimal_config():
    """Dev mode must still accept dev defaults without failing."""
    with _set_env({"ENVIRONMENT": "dev"}):
        cfg = SecurityConfig()
        assert cfg.dev_mode
        assert cfg.jwt_secret  # auto-set to dev default


def test_dev_mode_accepts_localhost_cors():
    """Dev mode must accept localhost CORS origins."""
    with _set_env({
        "ENVIRONMENT": "dev",
        "CORS_ALLOWED_ORIGINS": "http://localhost:3000,http://127.0.0.1:3000",
    }):
        cfg = SecurityConfig()
        assert "http://localhost:3000" in cfg.cors_allowed_origins


def test_dev_mode_accepts_dev_database_url():
    """Dev mode must accept localhost DATABASE_URL."""
    with _set_env({
        "ENVIRONMENT": "dev",
        "DATABASE_URL": "postgresql+asyncpg://retail_media_owner:retail_media_owner_pass@localhost:5432/retail_media_platform",
        "JWT_SECRET": "at-least-32-chars-for-ci-testing-ok!",
    }):
        cfg = SecurityConfig()
        assert cfg.dev_mode
