"""
Retail Media Platform — Phase 2.2 Health Endpoint Tests.

Tests: liveness independence, readiness DB check, error sanitisation.
"""

import importlib.util
import os
import re
import sys
import unittest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient

# Project root
ROOT = os.path.join(os.path.dirname(__file__), "..")
MAIN_PY = os.path.join(ROOT, "apps", "control-api", "main.py")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_APP = None
_MODULE = None


def _load_module():
    """Load apps/control-api/main.py via importlib (hyphens in dir name)."""
    global _APP, _MODULE
    if _MODULE is None:
        spec = importlib.util.spec_from_file_location("control_api_main", MAIN_PY)
        _MODULE = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_MODULE)
        _APP = _MODULE.app
    return _MODULE


def _get_app():
    _load_module()
    return _APP


def _read_main_src() -> str:
    with open(MAIN_PY) as f:
        return f.read()


# ---------------------------------------------------------------------------
# Live endpoint — no DB dependency
# ---------------------------------------------------------------------------

class TestHealthLive(unittest.TestCase):
    """Liveness probe must never depend on database."""

    def test_live_returns_200(self):
        client = TestClient(_get_app())
        resp = client.get("/health/live")
        self.assertEqual(resp.status_code, 200)

    def test_live_body(self):
        client = TestClient(_get_app())
        resp = client.get("/health/live")
        data = resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["service"], "control-api")

    def test_live_handler_no_db_references(self):
        """/health/live handler source must not reference DB/engine."""
        src = _read_main_src()
        # Extract the health_live function body
        m = re.search(r"async def health_live\(\):(.+?)(?=\n(?:@app\.|async def |# ---))", src, re.DOTALL)
        self.assertIsNotNone(m, "Cannot find health_live function")
        body = m.group(1).lower()
        self.assertNotIn("engine", body)
        self.assertNotIn("check_db", body)
        self.assertNotIn("database", body)


# ---------------------------------------------------------------------------
# Readiness — DB health check
# ---------------------------------------------------------------------------

class TestHealthReady(unittest.TestCase):
    """Readiness probe must check database and sanitise errors."""

    def test_ready_handler_calls_db_check(self):
        """/health/ready handler source references check_db_health."""
        src = _read_main_src()
        self.assertIn("check_db_health", src)

    def test_ready_no_engine_returns_503(self):
        """When engine is None, return 503 degraded."""
        mod = _load_module()
        with patch.object(mod, "_engine", None):
            client = TestClient(_get_app())
            resp = client.get("/health/ready")
            self.assertEqual(resp.status_code, 503)
            data = resp.json()
            self.assertEqual(data["status"], "degraded")
            self.assertEqual(data["checks"]["database"], "unhealthy")

    def test_ready_db_ok_returns_200(self):
        """When DB is healthy, return 200 ok."""
        mod = _load_module()
        with patch.object(mod, "check_db_health", new_callable=AsyncMock) as mock_check, \
             patch.object(mod, "check_db_role_safety", new_callable=AsyncMock) as mock_role, \
             patch.object(mod, "_engine", object()):
            mock_check.return_value = (True, None)
            mock_role.return_value = (True, {"db_role": "ok", "db_role_details": "ok"})
            client = TestClient(_get_app())
            resp = client.get("/health/ready")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["status"], "ok")
            self.assertEqual(data["checks"]["database"], "ok")
            self.assertNotIn("db_error", data)

    def test_ready_db_unavailable_returns_503(self):
        """When DB is down, return 503 degraded."""
        mod = _load_module()
        with patch.object(mod, "check_db_health", new_callable=AsyncMock) as mock_check, \
             patch.object(mod, "_engine", object()):
            mock_check.return_value = (False, "connection_failed")
            client = TestClient(_get_app())
            resp = client.get("/health/ready")
            self.assertEqual(resp.status_code, 503)
            data = resp.json()
            self.assertEqual(data["status"], "degraded")
            self.assertEqual(data["checks"]["database"], "unhealthy")

    def test_ready_db_unavailable_message_sanitised(self):
        """Error response must NOT expose connection string or raw exception."""
        mod = _load_module()
        with patch.object(mod, "check_db_health", new_callable=AsyncMock) as mock_check, \
             patch.object(mod, "_engine", object()):
            mock_check.return_value = (False, "connection_failed")
            client = TestClient(_get_app())
            resp = client.get("/health/ready")
            data = resp.json()
            # Generic sanitised message
            self.assertEqual(data.get("db_error"), "database_unavailable")
            # Must not leak connection details
            body = str(data).lower()
            self.assertNotIn("postgresql", body)
            self.assertNotIn("asyncpg", body)
            self.assertNotIn("retail_media_dev", body)
            self.assertNotIn("5432", body)
            self.assertNotIn("password", body)


# ---------------------------------------------------------------------------
# DB health helper — no real DB
# ---------------------------------------------------------------------------

class TestCheckDbHealth(unittest.TestCase):
    """check_db_health returns safe values without a real database."""

    def test_no_engine_returns_false_no_engine(self):
        import asyncio
        from packages.domain.database import check_db_health
        ok, reason = asyncio.run(check_db_health(None))
        self.assertFalse(ok)
        self.assertEqual(reason, "no_engine")

    def test_no_db_returns_false(self):
        """Without a real PostgreSQL, returns False with sanitised reason."""
        import asyncio
        from packages.domain.database import check_db_health, create_engine

        engine = create_engine(
            "postgresql+asyncpg://nonexistent:nope@localhost:19999/no_db"
        )
        try:
            ok, reason = asyncio.run(check_db_health(engine, timeout=0.5))
            self.assertFalse(ok)
            self.assertIn(reason, {"timeout", "connection_failed"})
        finally:
            asyncio.run(engine.dispose())


# ---------------------------------------------------------------------------
# No old backend dependency
# ---------------------------------------------------------------------------

class TestNoOldBackendDependency(unittest.TestCase):
    """Control-api main.py must not import from old backend."""

    def test_main_no_backend_import(self):
        src = _read_main_src()
        self.assertNotIn("from backend", src)
        self.assertNotIn("import backend", src)


# ---------------------------------------------------------------------------
# DB role safety (Phase 3.5b)
# ---------------------------------------------------------------------------


class TestDbRoleSafety(unittest.TestCase):
    """check_db_role_safety must detect unsafe roles and never leak secrets."""

    def test_ok_when_role_is_safe(self):
        import asyncio
        from packages.domain.database import check_db_role_safety

        mock_engine = _MockEngine([
            (False, False),  # rolsuper=false, rolbypassrls=false
        ])
        ok, info = asyncio.run(check_db_role_safety(mock_engine))
        self.assertTrue(ok)
        self.assertEqual(info["db_role"], "ok")
        self.assertEqual(info["db_role_details"], "non-superuser, NOBYPASSRLS")

    def test_unsafe_when_superuser_in_production(self):
        import asyncio
        from packages.domain.database import check_db_role_safety

        mock_engine = _MockEngine([
            (True, False),  # rolsuper=true
        ])
        ok, info = asyncio.run(
            check_db_role_safety(mock_engine, dev_mode=False)
        )
        self.assertFalse(ok)
        self.assertEqual(info["db_role"], "unsafe")
        self.assertIn("superuser", info["db_role_details"])

    def test_unsafe_when_bypassrls_in_production(self):
        import asyncio
        from packages.domain.database import check_db_role_safety

        mock_engine = _MockEngine([
            (False, True),  # rolbypassrls=true
        ])
        ok, info = asyncio.run(
            check_db_role_safety(mock_engine, dev_mode=False)
        )
        self.assertFalse(ok)
        self.assertEqual(info["db_role"], "unsafe")
        self.assertIn("BYPASSRLS", info["db_role_details"])

    def test_dev_mode_allows_superuser(self):
        import asyncio
        from packages.domain.database import check_db_role_safety

        mock_engine = _MockEngine([
            (True, True),  # both superuser and BYPASSRLS
        ])
        ok, info = asyncio.run(
            check_db_role_safety(mock_engine, dev_mode=True)
        )
        self.assertTrue(ok)
        self.assertEqual(info["db_role"], "ok")
        self.assertIn("dev:", info["db_role_details"])

    def test_no_engine_returns_unhealthy(self):
        import asyncio
        from packages.domain.database import check_db_role_safety

        ok, info = asyncio.run(check_db_role_safety(None))
        self.assertFalse(ok)
        self.assertEqual(info["db_role"], "unhealthy")

    def test_pg_roles_failure_returns_unhealthy(self):
        import asyncio
        from packages.domain.database import check_db_role_safety

        class _FailingEngine:
            def connect(self):
                raise RuntimeError("connection lost")

        ok, info = asyncio.run(check_db_role_safety(_FailingEngine()))
        self.assertFalse(ok)
        self.assertEqual(info["db_role"], "unhealthy")

    def test_response_never_leaks_secrets(self):
        """check_db_role_safety must never return DB URLs or credentials."""
        import asyncio
        from packages.domain.database import check_db_role_safety

        mock_engine = _MockEngine([
            (True, True),
        ])
        _, info = asyncio.run(
            check_db_role_safety(mock_engine, dev_mode=False)
        )
        body = str(info).lower()
        self.assertNotIn("postgresql", body)
        self.assertNotIn("password", body)
        self.assertNotIn("retail_media", body)
        self.assertNotIn("5432", body)


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


class _MockEngine:
    """Minimal async engine mock — returns a fixed row from connect()."""

    def __init__(self, rows: list):
        self._rows = rows

    def connect(self):
        return _MockConnection(self._rows)


class _MockConnection:
    def __init__(self, rows: list):
        self._rows = rows

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def execute(self, stmt):
        return _MockResult(self._rows)


class _MockResult:
    def __init__(self, rows: list):
        self._rows = rows

    def fetchone(self):
        return self._rows[0] if self._rows else None


# ---------------------------------------------------------------------------
# CORS tests
# ---------------------------------------------------------------------------


class TestCorsHeaders(unittest.TestCase):
    """CORS middleware returns correct headers for allowed/disallowed origins."""

    def setUp(self):
        from packages.security.config import reset_security_config
        reset_security_config()
        # Set dev mode with explicit origins for testing
        os.environ["ENVIRONMENT"] = "dev"
        os.environ["JWT_SECRET"] = "test-cors-secret-at-least-32-chars!!!"
        os.environ["CORS_ALLOWED_ORIGINS"] = "http://localhost:5173,http://app.example.com"

    def tearDown(self):
        from packages.security.config import reset_security_config
        reset_security_config()
        for key in ("CORS_ALLOWED_ORIGINS", "CORS_ALLOW_CREDENTIALS",
                     "ENVIRONMENT", "JWT_SECRET"):
            os.environ.pop(key, None)

    def test_allowed_origin_gets_cors_headers(self):
        """Request from an allowed origin returns access-control headers."""
        client = TestClient(_get_app())
        resp = client.get(
            "/health/live",
            headers={"Origin": "http://localhost:5173"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.headers.get("access-control-allow-origin"),
            "http://localhost:5173",
        )

    def test_disallowed_origin_no_allow_origin_header(self):
        """Request from a disallowed origin does NOT get allow-origin."""
        client = TestClient(_get_app())
        resp = client.get(
            "/health/live",
            headers={"Origin": "https://evil.example.com"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("access-control-allow-origin", resp.headers)

    def test_preflight_options_returns_cors_headers(self):
        """OPTIONS preflight from allowed origin returns CORS headers."""
        client = TestClient(_get_app())
        resp = client.options(
            "/health/live",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.headers.get("access-control-allow-origin"),
            "http://localhost:5173",
        )
        self.assertIn("GET", resp.headers.get("access-control-allow-methods", ""))

    def test_preflight_disallowed_origin_no_cors(self):
        """OPTIONS from disallowed origin returns 400 (no CORS headers)."""
        client = TestClient(_get_app())
        resp = client.options(
            "/health/live",
            headers={
                "Origin": "https://evil.example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        # Disallowed origin — should not get CORS headers
        self.assertNotIn("access-control-allow-origin", resp.headers)


class TestCorsConfig(unittest.TestCase):
    """CORS configuration validation — dev defaults, production safety."""

    def setUp(self):
        from packages.security.config import reset_security_config
        reset_security_config()

    def tearDown(self):
        from packages.security.config import reset_security_config
        reset_security_config()
        for key in ("CORS_ALLOWED_ORIGINS", "CORS_ALLOW_CREDENTIALS",
                     "ENVIRONMENT", "JWT_SECRET"):
            os.environ.pop(key, None)

    def test_dev_defaults_include_localhost(self):
        """Dev mode without CORS_ALLOWED_ORIGINS defaults to localhost:5173."""
        os.environ["ENVIRONMENT"] = "dev"
        os.environ["JWT_SECRET"] = "test-cors-dev-secret-at-least-32-chars"
        from packages.security.config import SecurityConfig
        cfg = SecurityConfig()
        self.assertTrue(cfg.dev_mode)
        self.assertIn("http://localhost:5173", cfg.cors_allowed_origins)
        self.assertIn("http://127.0.0.1:5173", cfg.cors_allowed_origins)

    def test_no_wildcard_with_credentials_raises(self):
        """Config with ['*'] + credentials=True raises ValueError."""
        os.environ["ENVIRONMENT"] = "dev"
        os.environ["JWT_SECRET"] = "test-cors-wc-secret-at-least-32-chars!!"
        os.environ["CORS_ALLOWED_ORIGINS"] = "*"
        os.environ["CORS_ALLOW_CREDENTIALS"] = "true"
        from packages.security.config import SecurityConfig
        with self.assertRaises(ValueError) as ctx:
            SecurityConfig()
        self.assertIn("allow_credentials", str(ctx.exception).lower())

    def test_production_requires_explicit_origins(self):
        """Production with empty CORS origins raises ValueError."""
        os.environ["ENVIRONMENT"] = "production"
        os.environ["JWT_SECRET"] = "prod-test-secret-at-least-32-characters!!"
        from packages.security.config import SecurityConfig
        with self.assertRaises(ValueError) as ctx:
            SecurityConfig()
        self.assertIn("CORS_ALLOWED_ORIGINS", str(ctx.exception))

    def test_production_explicit_origins_valid(self):
        """Production with explicit origins + credentials is valid."""
        os.environ["ENVIRONMENT"] = "production"
        os.environ["JWT_SECRET"] = "prod-test-secret-at-least-32-characters!!"
        os.environ["MANIFEST_SIGNING_KEY"] = "ci-manifest-key-at-least-32-chars-xx"
        os.environ["CORS_ALLOWED_ORIGINS"] = "https://portal.example.com"
        os.environ["CORS_ALLOW_CREDENTIALS"] = "true"
        from packages.security.config import SecurityConfig
        cfg = SecurityConfig()
        self.assertFalse(cfg.dev_mode)
        self.assertEqual(cfg.cors_allowed_origins, ["https://portal.example.com"])
        self.assertTrue(cfg.cors_allow_credentials)

    def test_production_no_wildcard_with_credentials_raises(self):
        """Production with ['*'] + credentials=True raises ValueError."""
        os.environ["ENVIRONMENT"] = "production"
        os.environ["JWT_SECRET"] = "prod-test-secret-at-least-32-characters!!"
        os.environ["CORS_ALLOWED_ORIGINS"] = "*"
        os.environ["CORS_ALLOW_CREDENTIALS"] = "true"
        from packages.security.config import SecurityConfig
        with self.assertRaises(ValueError) as ctx:
            SecurityConfig()
        self.assertIn("allow_credentials", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()
