"""
Retail Media Platform — Phase 3.2b Security Helpers Tests.

Tests: config, password, token, JWT, sanitization helpers.
No database required.
"""

import asyncio
import os
import sys
import time
import unittest

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import jwt as pyjwt

from packages.security import config as sec_config
from packages.security import password as sec_password
from packages.security import tokens as sec_tokens
from packages.security import jwt as sec_jwt
from packages.security import sanitize as sec_sanitize


# ---------------------------------------------------------------------------
# Config Tests
# ---------------------------------------------------------------------------


class TestSecurityConfig(unittest.TestCase):
    """SecurityConfig loading and validation."""

    def setUp(self):
        # Reset singleton before each test
        sec_config.reset_security_config()
        # Save original env
        self._orig_env = dict(os.environ)
        # S-065: pre-populate metrics token for production tests
        os.environ["METRICS_AUTH_TOKEN"] = "ci-metrics-token-at-least-32-characters-long"

    def tearDown(self):
        sec_config.reset_security_config()
        os.environ.clear()
        os.environ.update(self._orig_env)

    def test_dev_mode_defaults(self):
        """Dev mode allows weak secret."""
        os.environ["ENVIRONMENT"] = "dev"
        os.environ["JWT_SECRET"] = "test"
        cfg = sec_config.SecurityConfig()
        self.assertTrue(cfg.dev_mode)
        self.assertEqual(cfg.jwt_access_token_ttl_minutes, 15)
        self.assertEqual(cfg.jwt_clock_skew_seconds, 30)
        self.assertEqual(cfg.refresh_session_ttl_hours, 8)

    def test_dev_mode_no_secret(self):
        """Dev mode without JWT_SECRET uses safe fallback."""
        os.environ["ENVIRONMENT"] = "dev"
        os.environ.pop("JWT_SECRET", None)
        cfg = sec_config.SecurityConfig()
        self.assertIn("dev-secret", cfg.jwt_secret)

    def test_production_requires_strong_secret(self):
        """Production mode raises on weak JWT_SECRET."""
        os.environ["ENVIRONMENT"] = "production"
        os.environ["JWT_SECRET"] = "short"
        os.environ["CORS_ALLOWED_ORIGINS"] = "https://example.com"
        os.environ["MANIFEST_SIGNING_KEY"] = "ci-manifest-key-at-least-32-chars-xx"
        with self.assertRaises(ValueError):
            sec_config.SecurityConfig()

    def test_production_rejects_weak_words(self):
        """Production mode rejects common weak JWT_SECRET values."""
        os.environ["ENVIRONMENT"] = "production"
        os.environ["JWT_SECRET"] = "secret"
        os.environ["CORS_ALLOWED_ORIGINS"] = "https://example.com"
        os.environ["MANIFEST_SIGNING_KEY"] = "ci-manifest-key-at-least-32-chars-xx"
        with self.assertRaises(ValueError):
            sec_config.SecurityConfig()

    def test_production_accepts_strong_secret(self):
        """Production mode accepts JWT_SECRET >= 32 chars."""
        os.environ["ENVIRONMENT"] = "production"
        os.environ["JWT_SECRET"] = "a" * 32
        os.environ["CORS_ALLOWED_ORIGINS"] = "https://example.com"
        os.environ["MANIFEST_SIGNING_KEY"] = "ci-manifest-key-at-least-32-chars-xx"
        cfg = sec_config.SecurityConfig()
        self.assertFalse(cfg.dev_mode)
        self.assertEqual(cfg.jwt_secret, "a" * 32)

    def test_config_repr_no_secrets(self):
        """__repr__ does not expose JWT secret."""
        os.environ["ENVIRONMENT"] = "dev"
        os.environ["JWT_SECRET"] = "super-secret-value"
        cfg = sec_config.SecurityConfig()
        r = repr(cfg)
        self.assertNotIn("super-secret-value", r)
        self.assertIn("***", r)

    # ── S-021a: manifest signing config ──

    def test_production_requires_manifest_signing_key(self):
        """Production without MANIFEST_SIGNING_KEY raises ValueError."""
        os.environ["ENVIRONMENT"] = "production"
        os.environ["JWT_SECRET"] = "a" * 32
        os.environ["CORS_ALLOWED_ORIGINS"] = "https://example.com"
        os.environ.pop("MANIFEST_SIGNING_KEY", None)
        with self.assertRaises(ValueError) as ctx:
            sec_config.SecurityConfig()
        self.assertIn("MANIFEST_SIGNING_KEY", str(ctx.exception))

    def test_production_rejects_short_manifest_key(self):
        """Production rejects MANIFEST_SIGNING_KEY < 32 chars."""
        os.environ["ENVIRONMENT"] = "production"
        os.environ["JWT_SECRET"] = "a" * 32
        os.environ["CORS_ALLOWED_ORIGINS"] = "https://example.com"
        os.environ["MANIFEST_SIGNING_KEY"] = "short-key"
        with self.assertRaises(ValueError) as ctx:
            sec_config.SecurityConfig()
        self.assertIn("at least 32", str(ctx.exception))

    def test_production_rejects_weak_manifest_key(self):
        """Production rejects common weak MANIFEST_SIGNING_KEY values."""
        os.environ["ENVIRONMENT"] = "production"
        os.environ["JWT_SECRET"] = "a" * 32
        os.environ["CORS_ALLOWED_ORIGINS"] = "https://example.com"
        os.environ["MANIFEST_SIGNING_KEY"] = "test"
        with self.assertRaises(ValueError):
            sec_config.SecurityConfig()

    def test_production_accepts_strong_manifest_key(self):
        """Production accepts MANIFEST_SIGNING_KEY >= 32 chars."""
        os.environ["ENVIRONMENT"] = "production"
        os.environ["JWT_SECRET"] = "a" * 32
        os.environ["CORS_ALLOWED_ORIGINS"] = "https://example.com"
        os.environ["MANIFEST_SIGNING_KEY"] = "b" * 32
        cfg = sec_config.SecurityConfig()
        self.assertFalse(cfg.dev_mode)
        self.assertEqual(cfg.manifest_signing_key, "b" * 32)

    def test_dev_allows_empty_manifest_key(self):
        """Dev mode with no MANIFEST_SIGNING_KEY — empty key, no error."""
        os.environ["ENVIRONMENT"] = "dev"
        os.environ["JWT_SECRET"] = "test"
        os.environ.pop("MANIFEST_SIGNING_KEY", None)
        cfg = sec_config.SecurityConfig()
        self.assertEqual(cfg.manifest_signing_key, "")

    def test_dev_accepts_strong_manifest_key(self):
        """Dev mode with strong MANIFEST_SIGNING_KEY loads correctly."""
        os.environ["ENVIRONMENT"] = "dev"
        os.environ["JWT_SECRET"] = "test"
        os.environ["MANIFEST_SIGNING_KEY"] = "c" * 32
        cfg = sec_config.SecurityConfig()
        self.assertEqual(cfg.manifest_signing_key, "c" * 32)

    def test_default_values(self):
        """Default config values match ADR-006."""
        os.environ["ENVIRONMENT"] = "dev"
        os.environ["JWT_SECRET"] = "test"
        cfg = sec_config.SecurityConfig()
        self.assertEqual(cfg.login_rate_limit_max_attempts, 5)
        self.assertEqual(cfg.login_rate_limit_window_minutes, 15)
        self.assertEqual(cfg.max_sessions_per_user, 5)
        self.assertEqual(cfg.password_bcrypt_rounds, 12)
        self.assertEqual(cfg.password_min_length, 8)

    # ── S-035g: CORS PATCH in default methods ──

    def test_default_cors_methods_includes_patch(self):
        """Default cors_allowed_methods includes PATCH (S-035g)."""
        os.environ["ENVIRONMENT"] = "dev"
        os.environ["JWT_SECRET"] = "test"
        cfg = sec_config.SecurityConfig()
        methods = cfg.cors_allowed_methods
        expected = {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"}
        self.assertTrue(
            expected.issubset(set(methods)),
            f"Expected {expected} ⊆ {set(methods)}",
        )
        self.assertIn("PATCH", methods, "PATCH must be in default CORS methods")

    def test_singleton_returns_same_instance(self):
        """get_security_config returns the same instance."""
        os.environ["ENVIRONMENT"] = "dev"
        os.environ["JWT_SECRET"] = "test"
        c1 = sec_config.get_security_config()
        c2 = sec_config.get_security_config()
        self.assertIs(c1, c2)

    # ── S-017 P2: MinIO credential validation ──

    def test_dev_allows_default_minio_credentials(self):
        """Dev mode: minioadmin/minioadmin is accepted."""
        os.environ["ENVIRONMENT"] = "dev"
        os.environ["JWT_SECRET"] = "test"
        os.environ["MINIO_ACCESS_KEY"] = "minioadmin"
        os.environ["MINIO_SECRET_KEY"] = "minioadmin"
        cfg = sec_config.SecurityConfig()
        self.assertTrue(cfg.dev_mode)
        self.assertEqual(cfg.minio_access_key, "minioadmin")
        self.assertEqual(cfg.minio_secret_key, "minioadmin")

    def test_production_rejects_default_minio_access_key(self):
        """Production mode rejects minioadmin access key."""
        os.environ["ENVIRONMENT"] = "production"
        os.environ["JWT_SECRET"] = "a" * 32
        os.environ["CORS_ALLOWED_ORIGINS"] = "https://example.com"
        os.environ["MINIO_ACCESS_KEY"] = "minioadmin"
        os.environ["MINIO_SECRET_KEY"] = "strong-secret-key-123"
        with self.assertRaises(ValueError) as ctx:
            sec_config.SecurityConfig()
        self.assertIn("MINIO_ACCESS_KEY", str(ctx.exception))

    def test_production_rejects_default_minio_secret_key(self):
        """Production mode rejects minioadmin secret key."""
        os.environ["ENVIRONMENT"] = "production"
        os.environ["JWT_SECRET"] = "a" * 32
        os.environ["CORS_ALLOWED_ORIGINS"] = "https://example.com"
        os.environ["MINIO_ACCESS_KEY"] = "strong-access-key-123"
        os.environ["MINIO_SECRET_KEY"] = "minioadmin"
        with self.assertRaises(ValueError) as ctx:
            sec_config.SecurityConfig()
        self.assertIn("MINIO_SECRET_KEY", str(ctx.exception))

    def test_production_accepts_non_default_minio_credentials(self):
        """Production mode accepts non-default MinIO credentials."""
        os.environ["ENVIRONMENT"] = "production"
        os.environ["JWT_SECRET"] = "a" * 32
        os.environ["CORS_ALLOWED_ORIGINS"] = "https://example.com"
        os.environ["MANIFEST_SIGNING_KEY"] = "ci-manifest-key-at-least-32-chars-xx"
        os.environ["MINIO_ACCESS_KEY"] = "prod-access-key-123"
        os.environ["MINIO_SECRET_KEY"] = "prod-secret-key-456"
        cfg = sec_config.SecurityConfig()
        self.assertFalse(cfg.dev_mode)
        self.assertEqual(cfg.minio_access_key, "prod-access-key-123")
        self.assertEqual(cfg.minio_secret_key, "prod-secret-key-456")


# ---------------------------------------------------------------------------
# Password Tests
# ---------------------------------------------------------------------------


class TestPasswordHelpers(unittest.TestCase):
    """bcrypt password hashing and verification."""

    def setUp(self):
        sec_config.reset_security_config()
        self._orig_env = dict(os.environ)
        os.environ["ENVIRONMENT"] = "dev"
        os.environ["JWT_SECRET"] = "test"

    def tearDown(self):
        sec_config.reset_security_config()
        os.environ.clear()
        os.environ.update(self._orig_env)

    def test_hash_roundtrip(self):
        """hash + verify roundtrip works."""
        plain = "correct-horse-battery-staple"
        hashed = sec_password.hash_password(plain)
        self.assertTrue(hashed.startswith("$2"))  # bcrypt prefix ($2a$, $2b$, $2y$)
        self.assertTrue(sec_password.verify_password(plain, hashed))

    def test_wrong_password_fails(self):
        """verifying wrong password returns False."""
        hashed = sec_password.hash_password("right-password")
        self.assertFalse(sec_password.verify_password("wrong-password", hashed))

    def test_empty_password_rejected(self):
        """hash_password rejects empty password."""
        with self.assertRaises(ValueError):
            sec_password.hash_password("")

    def test_short_password_rejected(self):
        """hash_password rejects too-short password."""
        with self.assertRaises(ValueError):
            sec_password.hash_password("short")  # 5 chars < 8

    def test_empty_verify_returns_false(self):
        """verify_password with empty args returns False."""
        hashed = sec_password.hash_password("valid-pwd")
        self.assertFalse(sec_password.verify_password("", hashed))
        self.assertFalse(sec_password.verify_password("valid-pwd", ""))

    def test_malformed_hash_returns_false(self):
        """verify_password with malformed hash returns False (doesn't crash)."""
        self.assertFalse(sec_password.verify_password("anything", "not-a-hash"))

    def test_unique_salts(self):
        """Each hash produces different output (salt)."""
        h1 = sec_password.hash_password("same-password")
        h2 = sec_password.hash_password("same-password")
        self.assertNotEqual(h1, h2)
        # Both verify correctly
        self.assertTrue(sec_password.verify_password("same-password", h1))
        self.assertTrue(sec_password.verify_password("same-password", h2))


# ---------------------------------------------------------------------------
# Token Tests
# ---------------------------------------------------------------------------


class TestTokenHelpers(unittest.TestCase):
    """Token generation, hashing, and verification."""

    def setUp(self):
        sec_config.reset_security_config()
        self._orig_env = dict(os.environ)
        os.environ["ENVIRONMENT"] = "dev"
        os.environ["JWT_SECRET"] = "test"

    def tearDown(self):
        sec_config.reset_security_config()
        os.environ.clear()
        os.environ.update(self._orig_env)

    def test_generate_token_is_random(self):
        """Consecutive token generations produce different values."""
        t1 = sec_tokens.generate_token()
        t2 = sec_tokens.generate_token()
        self.assertNotEqual(t1, t2)
        # Default: 32 bytes → 64 hex chars
        self.assertEqual(len(t1), 64)

    def test_generate_token_custom_length(self):
        """Custom byte length produces correct output length."""
        t = sec_tokens.generate_token(16)
        self.assertEqual(len(t), 32)  # 16 bytes → 32 hex chars

    def test_hash_token_deterministic(self):
        """Hashing same token produces same hash."""
        token = "test-token-value"
        h1 = sec_tokens.hash_token(token)
        h2 = sec_tokens.hash_token(token)
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 64)  # SHA-256 → 64 hex chars

    def test_hash_token_different_for_different_inputs(self):
        """Different tokens produce different hashes."""
        h1 = sec_tokens.hash_token("token-a")
        h2 = sec_tokens.hash_token("token-b")
        self.assertNotEqual(h1, h2)

    def test_constant_time_compare(self):
        """constant_time_compare returns correct results."""
        self.assertTrue(sec_tokens.constant_time_compare("abc", "abc"))
        self.assertFalse(sec_tokens.constant_time_compare("abc", "abd"))

    def test_verify_token_hash_roundtrip(self):
        """verify_token_hash works correctly."""
        raw = sec_tokens.generate_token()
        hashed = sec_tokens.hash_token(raw)
        self.assertTrue(sec_tokens.verify_token_hash(raw, hashed))
        self.assertFalse(sec_tokens.verify_token_hash("wrong-token", hashed))


# ---------------------------------------------------------------------------
# JWT Tests
# ---------------------------------------------------------------------------


class TestJWTHelpers(unittest.TestCase):
    """JWT create and verify helpers."""

    def setUp(self):
        sec_config.reset_security_config()
        self._orig_env = dict(os.environ)
        os.environ["ENVIRONMENT"] = "dev"
        os.environ["JWT_SECRET"] = "test-jwt-secret-for-unit-tests"

    def tearDown(self):
        sec_config.reset_security_config()
        os.environ.clear()
        os.environ.update(self._orig_env)

    def test_create_and_verify_roundtrip(self):
        """Create token → verify roundtrip restores claims."""
        sub = "00000000-0000-0000-0000-000000000001"
        token = sec_jwt.create_access_token(sub, "local_advertiser")
        claims = sec_jwt.verify_access_token(token)
        self.assertEqual(claims["sub"], sub)
        self.assertEqual(claims["auth_provider"], "local_advertiser")
        self.assertEqual(claims["aud"], "rmp-control-api")
        self.assertIn("jti", claims)
        self.assertIn("iat", claims)
        self.assertIn("exp", claims)

    def test_audience_missing_fails(self):
        """Token without aud claim is rejected."""
        cfg = sec_config.get_security_config()
        now = int(time.time())
        token = pyjwt.encode(
            {"sub": "u-1", "auth_provider": "ad", "jti": "x",
             "iat": now, "exp": now + 900, "iss": cfg.jwt_issuer},
            cfg.jwt_secret, algorithm="HS256",
        )
        with self.assertRaises(pyjwt.MissingRequiredClaimError):
            sec_jwt.verify_access_token(token)

    def test_wrong_audience_fails(self):
        """Token with wrong audience is rejected."""
        cfg = sec_config.get_security_config()
        now = int(time.time())
        token = pyjwt.encode(
            {"sub": "u-1", "auth_provider": "ad", "jti": "x",
             "iat": now, "exp": now + 900,
             "iss": cfg.jwt_issuer, "aud": "wrong-service"},
            cfg.jwt_secret, algorithm="HS256",
        )
        with self.assertRaises(pyjwt.InvalidAudienceError):
            sec_jwt.verify_access_token(token)

    def test_expired_token_rejected(self):
        """Expired token raises ExpiredSignatureError."""
        cfg = sec_config.get_security_config()
        now = int(time.time())
        claims = {
            "sub": "u-1",
            "auth_provider": "ad",
            "jti": "test-jti",
            "iat": now - 3600,
            "exp": now - 1800,
            "iss": cfg.jwt_issuer,
            "aud": cfg.jwt_audience,
        }
        token = pyjwt.encode(claims, cfg.jwt_secret, algorithm=cfg.jwt_algorithm)
        old_skew = cfg.jwt_clock_skew_seconds
        cfg.jwt_clock_skew_seconds = 0
        try:
            with self.assertRaises(pyjwt.ExpiredSignatureError):
                sec_jwt.verify_access_token(token)
        finally:
            cfg.jwt_clock_skew_seconds = old_skew

    def test_tampered_token_rejected(self):
        """Modified token raises InvalidTokenError.

        Tampering method: flip a character in the middle of the JWT string.
        This corrupts the signature bytes regardless of base64url padding
        behaviour and is robust across PyJWT versions (token[:-2]+'xx'
        produces valid base64url under PyJWT ≥2.14 on Python ≥3.12).
        """
        token = sec_jwt.create_access_token("u-1", "local_advertiser")
        mid = len(token) // 2
        flipped = "Z" if token[mid] != "Z" else "Y"
        tampered = token[:mid] + flipped + token[mid + 1 :]
        with self.assertRaises(pyjwt.InvalidTokenError):
            sec_jwt.verify_access_token(tampered)

    def test_wrong_secret_rejected(self):
        """Token signed with different secret raises InvalidTokenError."""
        token = sec_jwt.create_access_token("u-1", "ad")
        # Change secret and try to verify
        old = os.environ["JWT_SECRET"]
        os.environ["JWT_SECRET"] = "different-secret-value-here"
        sec_config.reset_security_config()
        with self.assertRaises(pyjwt.InvalidTokenError):
            sec_jwt.verify_access_token(token)
        # Restore
        os.environ["JWT_SECRET"] = old
        sec_config.reset_security_config()

    def test_alg_none_rejected(self):
        """Token with alg=none is rejected."""
        token = pyjwt.encode(
            {"sub": "u-1", "auth_provider": "ad", "jti": "x",
             "iat": int(time.time()), "exp": int(time.time()) + 900,
             "iss": "rmp-control-api", "aud": "rmp-control-api"},
            key="",
            algorithm="none",
        )
        with self.assertRaises(pyjwt.InvalidTokenError):
            sec_jwt.verify_access_token(token)

    def test_required_claims_enforced(self):
        """Token missing required claims is rejected."""
        token = pyjwt.encode(
            {"sub": "u-1"},  # missing auth_provider, jti, iat, exp, iss, aud
            os.environ["JWT_SECRET"],
            algorithm="HS256",
        )
        with self.assertRaises(pyjwt.MissingRequiredClaimError):
            sec_jwt.verify_access_token(token)

    def test_clock_skew_respected(self):
        """Token just beyond TTL but within skew window is accepted."""
        cfg = sec_config.get_security_config()
        now = int(time.time())
        claims = {
            "sub": "u-1",
            "auth_provider": "ad",
            "jti": "test-jti-skew",
            "iat": now - 120,
            "exp": now - 15,
            "iss": cfg.jwt_issuer,
            "aud": cfg.jwt_audience,
        }
        token = pyjwt.encode(claims, cfg.jwt_secret, algorithm=cfg.jwt_algorithm)
        claims_decoded = sec_jwt.verify_access_token(token)
        self.assertEqual(claims_decoded["sub"], "u-1")

    def test_beyond_skew_rejected(self):
        """Token expired beyond skew window is rejected."""
        cfg = sec_config.get_security_config()
        now = int(time.time())
        claims = {
            "sub": "u-1",
            "auth_provider": "ad",
            "jti": "test-jti-beyond-skew",
            "iat": now - 200,
            "exp": now - 60,
            "iss": cfg.jwt_issuer,
            "aud": cfg.jwt_audience,
        }
        token = pyjwt.encode(claims, cfg.jwt_secret, algorithm=cfg.jwt_algorithm)
        with self.assertRaises(pyjwt.ExpiredSignatureError):
            sec_jwt.verify_access_token(token)


# ---------------------------------------------------------------------------
# Sanitization Tests
# ---------------------------------------------------------------------------


class TestSanitizeHelpers(unittest.TestCase):
    """Audit detail sanitization."""

    def test_password_masked(self):
        """password field is masked."""
        data = {"username": "test", "password": "secret123"}
        clean = sec_sanitize.sanitize_auth_details(data)
        self.assertEqual(clean["username"], "test")
        self.assertEqual(clean["password"], "***")

    def test_token_masked(self):
        """token fields are masked."""
        data = {"access_token": "eyJhbGciOiJIUzI1NiJ9.xxx"}
        clean = sec_sanitize.sanitize_auth_details(data)
        self.assertEqual(clean["access_token"], "***MASKED***")

    def test_authorization_masked(self):
        """Authorization header is masked."""
        data = {"authorization": "Bearer token-value"}
        clean = sec_sanitize.sanitize_auth_details(data)
        self.assertEqual(clean["authorization"], "***MASKED***")

    def test_cookie_masked(self):
        """Cookie/set-cookie are masked."""
        data = {"set-cookie": "refresh=abc123; HttpOnly"}
        clean = sec_sanitize.sanitize_auth_details(data)
        self.assertEqual(clean["set-cookie"], "***MASKED***")

    def test_nested_dict(self):
        """Nested dicts are sanitized recursively."""
        data = {
            "user": "test",
            "headers": {
                "authorization": "Bearer x",
                "content-type": "application/json",
            },
        }
        clean = sec_sanitize.sanitize_auth_details(data)
        self.assertEqual(clean["headers"]["authorization"], "***MASKED***")
        self.assertEqual(clean["headers"]["content-type"], "application/json")

    def test_list_of_dicts(self):
        """Lists of dicts are sanitized."""
        data = {
            "events": [
                {"name": "login", "password": "p1"},
                {"name": "refresh", "token": "t1"},
            ],
        }
        clean = sec_sanitize.sanitize_auth_details(data)
        self.assertEqual(clean["events"][0]["password"], "***")
        self.assertEqual(clean["events"][1]["token"], "***MASKED***")

    def test_none_returns_empty_dict(self):
        """None input returns empty dict."""
        self.assertEqual(sec_sanitize.sanitize_auth_details(None), {})

    def test_original_not_mutated(self):
        """Sanitization returns a copy — original is untouched."""
        data = {"password": "secret"}
        clean = sec_sanitize.sanitize_auth_details(data)
        self.assertEqual(data["password"], "secret")
        self.assertEqual(clean["password"], "***")

    def test_non_sensitive_preserved(self):
        """Non-sensitive fields are preserved."""
        data = {"username": "test", "action": "login", "ip": "127.0.0.1"}
        clean = sec_sanitize.sanitize_auth_details(data)
        self.assertEqual(clean, data)

    def test_substring_false_positives_not_masked(self):
        """Fields containing sensitive substrings are NOT masked."""
        data = {
            "authorization_id": "auth-123",
            "cookie_preferences": "dark-mode",
            "tokenizer_config": "gpt-4",
            "passwordless_enabled": True,
            "refresh_tokens_count": 5,
        }
        clean = sec_sanitize.sanitize_auth_details(data)
        self.assertEqual(clean["authorization_id"], "auth-123")
        self.assertEqual(clean["cookie_preferences"], "dark-mode")
        self.assertEqual(clean["tokenizer_config"], "gpt-4")
        self.assertEqual(clean["passwordless_enabled"], True)
        self.assertEqual(clean["refresh_tokens_count"], 5)

    def test_underscore_variants_masked(self):
        """Underscore variants of sensitive keys are masked."""
        data = {
            "access_token": "secret-token",
            "set_cookie": "session=abc",
            "api_key": "sk-123",
        }
        clean = sec_sanitize.sanitize_auth_details(data)
        self.assertEqual(clean["access_token"], "***MASKED***")
        self.assertEqual(clean["set_cookie"], "***MASKED***")
        self.assertEqual(clean["api_key"], "***MASKED***")


# ---------------------------------------------------------------------------
# S-008 hardening: prove admin flag reset after scope resolution
# ---------------------------------------------------------------------------


class TestScopeAdminReset:
    """Prove app.rmp_is_admin does not leak after resolve_scope_context.

    Uses a self-contained DB engine (not shared fixtures) to test the
    exact behavior of resolve_scope_context in isolation.

    Requires: real PostgreSQL. Run via behavioral-postgres-tests CI job.
    Skipped in unit test suite (no guaranteed DB).
    """

    @staticmethod
    def _make_session():
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, \
            create_async_engine

        import os
        url = os.environ.get(
            "DATABASE_URL",
            "postgresql+asyncpg://retail_media:retail_media_dev"
            "@localhost:5432/retail_media_platform",
        )
        engine = create_async_engine(url, echo=False)
        return async_sessionmaker(engine, class_=AsyncSession,
                                  expire_on_commit=False)

    @pytest.fixture(autouse=True)
    def _require_db(self):
        """Skip in unit suite — requires real PostgreSQL."""
        import socket
        try:
            s = socket.create_connection(("localhost", 5432), timeout=1)
            s.close()
        except OSError:
            pytest.skip(
                "PostgreSQL not available — "
                "run via behavioral-postgres-tests CI job"
            )

    def test_non_admin_resets_admin_flag(self):
        """After scope resolution for non-admin, raw DB sees admin=false."""
        from packages.domain.scopes import resolve_scope_context
        from sqlalchemy import text

        sf = self._make_session()

        async def _test():
            async with sf() as session:
                async with session.begin():
                    ctx = await resolve_scope_context(
                        session, "00000000-0000-0000-0000-0000000000ff",
                    )
                    row = await session.execute(
                        text("SELECT current_setting('app.rmp_is_admin', true)")
                    )
                    val = row.scalar()
                return ctx, val

        ctx, flag = asyncio.run(_test())
        assert ctx.is_admin is False, "test user should not be admin"
        assert flag == "false", (
            f"Admin flag should be reset to false after scope resolution, "
            f"got {flag}"
        )

    def test_admin_resets_flag_before_return(self):
        """Even admin scope resolution resets flag; set_rls_context re-sets it."""
        from packages.domain.scopes import resolve_scope_context
        from sqlalchemy import text

        sf = self._make_session()

        async def _test():
            async with sf() as session:
                async with session.begin():
                    ctx = await resolve_scope_context(
                        session, "00000000-0000-0000-0000-000000000150",
                    )
                    row = await session.execute(
                        text("SELECT current_setting('app.rmp_is_admin', true)")
                    )
                    val = row.scalar()
                return ctx, val

        ctx, flag = asyncio.run(_test())
        # Seed admin user IS admin
        assert ctx.is_admin is True, "seed superadmin should be admin"
        # But the DB flag must be false — scope resolution resets it
        assert flag == "false", (
            f"Admin flag must be false after scope resolution (set_rls_context "
            f"will re-set it), got {flag}"
        )


if __name__ == "__main__":
    unittest.main()
