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
             patch.object(mod, "_engine", object()):
            mock_check.return_value = (True, None)
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


if __name__ == "__main__":
    unittest.main()
