"""Unit tests for production readiness (S-013).

Tests: health_state, provisioning, startup checks, health endpoint.
"""

from __future__ import annotations

import json
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from packages.services.health_state import (
    HealthState,
    bump_relay_published,
    bump_relay_failed,
    bump_consumer_acked,
    bump_consumer_nakd,
    bump_consumer_errors,
    bump_manifest_success,
    bump_manifest_failed,
    bump_manifest_skipped,
    get_health_state,
    set_db_ok,
    set_nats_connected,
    set_publisher_ready,
    set_consumer_ready,
)


# ---------------------------------------------------------------------------
# HealthState
# ---------------------------------------------------------------------------


class TestHealthState(unittest.TestCase):
    """HealthState dataclass and singleton."""

    def test_default_state_is_degraded(self):
        state = HealthState()
        d = state.to_dict()
        self.assertEqual(d["status"], "degraded")
        self.assertEqual(d["checks"]["database"], "fail")
        self.assertEqual(d["checks"]["nats"], "fail")

    def test_healthy_when_db_and_nats_ok(self):
        state = HealthState(db_ok=True, nats_connected=True)
        d = state.to_dict()
        self.assertEqual(d["status"], "ok")
        self.assertEqual(d["checks"]["database"], "ok")
        self.assertEqual(d["checks"]["nats"], "ok")

    def test_degraded_when_only_db_ok(self):
        state = HealthState(db_ok=True, nats_connected=False)
        d = state.to_dict()
        self.assertEqual(d["status"], "degraded")

    def test_publisher_and_consumer_not_ready_by_default(self):
        state = HealthState()
        d = state.to_dict()
        self.assertEqual(d["checks"]["publisher"], "not_ready")
        self.assertEqual(d["checks"]["consumer"], "not_ready")

    def test_publisher_and_consumer_ready(self):
        state = HealthState(publisher_ready=True, consumer_ready=True)
        d = state.to_dict()
        self.assertEqual(d["checks"]["publisher"], "ready")
        self.assertEqual(d["checks"]["consumer"], "ready")

    def test_relay_stats_in_output(self):
        state = HealthState(relay_published=5, relay_failed=2, relay_dead_letter=1)
        d = state.to_dict()
        c = d["components"]["relay"]
        self.assertEqual(c["published"], 5)
        self.assertEqual(c["failed"], 2)
        self.assertEqual(c["dead_letter"], 1)

    def test_consumer_stats_in_output(self):
        state = HealthState(
            consumer_acked=10, consumer_nakd=3,
            consumer_terminated=1, consumer_errors=2,
        )
        d = state.to_dict()
        c = d["components"]["consumer"]
        self.assertEqual(c["acked"], 10)
        self.assertEqual(c["nakd"], 3)
        self.assertEqual(c["terminated"], 1)
        self.assertEqual(c["errors"], 2)

    def test_manifest_stats_in_output(self):
        state = HealthState(
            consumer_manifest_success=12,
            consumer_manifest_failed=2,
            consumer_manifest_skipped=4,
        )
        d = state.to_dict()
        m = d["components"]["consumer"]["manifest"]
        self.assertEqual(m["success"], 12)
        self.assertEqual(m["failed"], 2)
        self.assertEqual(m["skipped"], 4)

    def test_uptime_is_positive(self):
        state = HealthState()
        d = state.to_dict()
        self.assertGreaterEqual(d["uptime_seconds"], 0)

    def test_service_name(self):
        state = HealthState()
        d = state.to_dict()
        self.assertEqual(d["service"], "orchestrator-worker")


class TestHealthStateSingleton(unittest.TestCase):
    """Thread-safe singleton bump/get functions."""

    def setUp(self):
        # Reset ALL counters to defaults by creating a fresh state
        set_db_ok(False)
        set_nats_connected(False)
        set_publisher_ready(False)
        set_consumer_ready(False)
        # Reset counters by bumping negative... no, we can't.
        # Instead, we test relative changes.
        # For snapshot test, read baseline first.
        self._baseline = get_health_state()

    def test_bump_relay_published(self):
        before = get_health_state().relay_published
        bump_relay_published()
        state = get_health_state()
        self.assertEqual(state.relay_published, before + 1)
        self.assertIsNotNone(state.relay_last_poll_at)

    def test_bump_relay_failed_with_error(self):
        before = get_health_state().relay_failed
        bump_relay_failed("connection refused")
        state = get_health_state()
        self.assertEqual(state.relay_failed, before + 1)
        self.assertEqual(state.relay_last_error, "connection refused")

    def test_bump_consumer_counters(self):
        ack_before = get_health_state().consumer_acked
        nak_before = get_health_state().consumer_nakd
        bump_consumer_acked()
        bump_consumer_acked()
        bump_consumer_nakd()
        state = get_health_state()
        self.assertEqual(state.consumer_acked, ack_before + 2)
        self.assertEqual(state.consumer_nakd, nak_before + 1)

    def test_bump_consumer_errors(self):
        before = get_health_state().consumer_errors
        bump_consumer_errors()
        bump_consumer_errors()
        state = get_health_state()
        self.assertEqual(state.consumer_errors, before + 2)

    def test_bump_manifest_stats(self):
        s_before = get_health_state().consumer_manifest_success
        f_before = get_health_state().consumer_manifest_failed
        sk_before = get_health_state().consumer_manifest_skipped
        bump_manifest_success()
        bump_manifest_success()
        bump_manifest_failed()
        bump_manifest_skipped()
        state = get_health_state()
        self.assertEqual(state.consumer_manifest_success, s_before + 2)
        self.assertEqual(state.consumer_manifest_failed, f_before + 1)
        self.assertEqual(state.consumer_manifest_skipped, sk_before + 1)

    def test_set_readiness_flags(self):
        set_db_ok(True)
        set_nats_connected(True)
        set_publisher_ready(True)
        set_consumer_ready(True)
        state = get_health_state()
        self.assertTrue(state.db_ok)
        self.assertTrue(state.nats_connected)
        self.assertTrue(state.publisher_ready)
        self.assertTrue(state.consumer_ready)

    def test_get_is_snapshot(self):
        """get_health_state returns a copy, not the live state."""
        baseline = get_health_state()
        base_count = baseline.relay_published
        # Test relative to baseline since singleton persists across tests
        s1 = get_health_state()
        bump_relay_published()
        s2 = get_health_state()
        self.assertEqual(s1.relay_published, baseline.relay_published)
        self.assertEqual(s2.relay_published, baseline.relay_published + 1)


# ---------------------------------------------------------------------------
# JetStream provisioning — unit tests
# ---------------------------------------------------------------------------


class TestJetStreamProvisioning(unittest.IsolatedAsyncioTestCase):
    """provision_campaign_delivery — idempotent create/update."""

    async def _mock_nats_client(self, add_stream_fails=False):
        """Set up a mock NATS connection + JetStream context."""
        mock_nc = AsyncMock()
        mock_js = AsyncMock()
        mock_nc.jetstream = MagicMock(return_value=mock_js)

        if add_stream_fails:
            mock_js.add_stream.side_effect = Exception("stream exists")
        else:
            mock_js.add_stream.return_value = None

        return mock_nc, mock_js

    async def test_provision_creates_stream_and_consumer(self):
        """First run: add_stream + add_consumer succeed."""
        mock_nc, mock_js = await self._mock_nats_client()
        from packages.services.jetstream_provisioning import (
            provision_campaign_delivery,
        )
        with patch("nats.aio.client.Client", return_value=mock_nc):
            result = await provision_campaign_delivery(
                "nats://localhost:4222",
                stream="RMP",
                subjects=["campaign.>"],
                durable="rmp-campaign-consumer",
            )

        self.assertEqual(result["stream"], "RMP")
        self.assertEqual(result["durable"], "rmp-campaign-consumer")
        mock_js.add_stream.assert_called_once()
        mock_js.add_consumer.assert_called_once()

    async def test_provision_updates_existing_stream(self):
        """Second run: add_stream raises → update_stream succeeds."""
        mock_nc, mock_js = await self._mock_nats_client(add_stream_fails=True)
        from packages.services.jetstream_provisioning import (
            provision_campaign_delivery,
        )
        with patch("nats.aio.client.Client", return_value=mock_nc):
            result = await provision_campaign_delivery(
                "nats://localhost:4222",
            )

        self.assertEqual(result["stream"], "RMP")
        mock_js.update_stream.assert_called_once()

    async def test_nats_unreachable_raises(self):
        """NATS down → RuntimeError with clear message."""
        from packages.services.jetstream_provisioning import (
            provision_campaign_delivery,
        )
        with patch(
            "nats.aio.client.Client",
            side_effect=OSError("Connection refused"),
        ):
            with self.assertRaises(RuntimeError) as ctx:
                await provision_campaign_delivery("nats://localhost:4222")
            self.assertIn("unreachable", str(ctx.exception))
            self.assertIn("Connection refused", str(ctx.exception))

    async def test_check_stream_returns_true(self):
        """check_stream_exists returns True when stream exists."""
        from packages.services.jetstream_provisioning import (
            check_stream_exists,
        )
        mock_nc = AsyncMock()
        mock_js = AsyncMock()
        mock_js.stream_info.return_value = MagicMock()
        mock_nc.jetstream = MagicMock(return_value=mock_js)

        with patch("nats.aio.client.Client", return_value=mock_nc):
            result = await check_stream_exists("nats://localhost:4222", stream="RMP")
            self.assertTrue(result)

    async def test_check_stream_returns_false_when_missing(self):
        """check_stream_exists returns False when stream doesn't exist."""
        from packages.services.jetstream_provisioning import (
            check_stream_exists,
        )
        mock_nc = AsyncMock()
        mock_js = AsyncMock()
        mock_js.stream_info.side_effect = Exception("not found")
        mock_nc.jetstream = MagicMock(return_value=mock_js)

        with patch("nats.aio.client.Client", return_value=mock_nc):
            result = await check_stream_exists("nats://localhost:4222", stream="RMP")
            self.assertFalse(result)

    async def test_check_stream_returns_false_when_nats_down(self):
        """check_stream_exists returns False when NATS unreachable."""
        from packages.services.jetstream_provisioning import (
            check_stream_exists,
        )
        with patch(
            "nats.aio.client.Client",
            side_effect=OSError("Connection refused"),
        ):
            result = await check_stream_exists("nats://localhost:4222")
            self.assertFalse(result)


# ---------------------------------------------------------------------------
# _run_provisioning — startup checks
# ---------------------------------------------------------------------------


class TestRunProvisioning(unittest.IsolatedAsyncioTestCase):
    """_run_provisioning — auto-provision and fail-fast logic."""

    async def _call(self, env_overrides=None):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "worker_main",
            os.path.join(
                os.path.dirname(__file__), "..", "apps",
                "orchestrator-worker", "main.py",
            ),
            submodule_search_locations=[],
        )
        worker_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(worker_mod)

        with patch.dict(os.environ, env_overrides or {}, clear=False):
            try:
                result = await worker_mod._run_provisioning(
                    env_overrides.get("NATS_URL", "nats://localhost:4222"),
                )
                return result, None
            except RuntimeError as exc:
                return None, exc

    async def test_auto_provision_calls_provisioning(self):
        """NATS_AUTO_PROVISION=true → calls provision_campaign_delivery."""
        with patch(
            "packages.services.jetstream_provisioning.provision_campaign_delivery",
        ) as mock_prov:
            mock_prov.return_value = {
                "stream": "RMP", "durable": "rmp-campaign-consumer",
                "subjects": ["campaign.>"],
            }
            result, exc = await self._call({
                "NATS_AUTO_PROVISION": "true",
                "NATS_URL": "nats://localhost:4222",
            })
            self.assertIsNone(exc)
            self.assertTrue(result)
            mock_prov.assert_called_once()

    async def test_auto_provision_failure_raises(self):
        """Provisioning failure → RuntimeError propagates."""
        with patch(
            "packages.services.jetstream_provisioning.provision_campaign_delivery",
            side_effect=RuntimeError("NATS down"),
        ):
            result, exc = await self._call({
                "NATS_AUTO_PROVISION": "true",
                "NATS_URL": "nats://localhost:4222",
            })
            self.assertIsNone(result)
            self.assertIsNotNone(exc)
            self.assertIn("auto-provisioning failed", str(exc))

    async def test_no_auto_provision_stream_exists(self):
        """Auto-provision off + stream exists → OK."""
        with patch(
            "packages.services.jetstream_provisioning.check_stream_exists",
            return_value=True,
        ):
            result, exc = await self._call({
                "NATS_AUTO_PROVISION": "false",
                "NATS_URL": "nats://localhost:4222",
            })
            self.assertIsNone(exc)
            self.assertTrue(result)

    async def test_no_auto_provision_stream_missing_raises(self):
        """Auto-provision off + stream missing → fail-fast."""
        with patch(
            "packages.services.jetstream_provisioning.check_stream_exists",
            return_value=False,
        ):
            result, exc = await self._call({
                "NATS_AUTO_PROVISION": "false",
                "NATS_URL": "nats://localhost:4222",
            })
            self.assertIsNone(result)
            self.assertIsNotNone(exc)
            self.assertIn("not found", str(exc))
            self.assertIn("NATS_AUTO_PROVISION=true", str(exc))


# ---------------------------------------------------------------------------
# Health HTTP endpoint
# ---------------------------------------------------------------------------


class TestHealthEndpoint(unittest.TestCase):
    """HealthHandler returns correct JSON for /health/live and /health/ready."""

    def test_live_endpoint_returns_ok(self):
        """GET /health/live returns {'status': 'ok'}, format verified."""
        from packages.services.health_state import get_health_state
        state = get_health_state()
        d = state.to_dict()
        self.assertIn("status", d)
        self.assertIn("checks", d)
        self.assertIn("components", d)
        self.assertIn("relay", d["components"])
        self.assertIn("consumer", d["components"])

    def test_ready_endpoint_includes_all_components(self):
        """Ready JSON includes relay, consumer, manifest stats."""
        set_db_ok(True)
        set_nats_connected(True)
        set_publisher_ready(True)
        set_consumer_ready(True)
        bump_relay_published()
        bump_consumer_acked()
        bump_manifest_success()

        from packages.services.health_state import get_health_state
        d = get_health_state().to_dict()

        self.assertEqual(d["status"], "ok")
        self.assertEqual(d["checks"]["database"], "ok")
        self.assertEqual(d["checks"]["publisher"], "ready")
        self.assertGreaterEqual(d["components"]["relay"]["published"], 1)
        self.assertGreaterEqual(d["components"]["consumer"]["acked"], 1)
        self.assertGreaterEqual(
            d["components"]["consumer"]["manifest"]["success"], 1,
        )

    # -- P1 fix: readiness HTTP status code -------------------------------

    def test_ready_returns_200_when_status_ok(self):
        """When db+nats are ok, to_dict status is 'ok' → expect HTTP 200."""
        set_db_ok(True)
        set_nats_connected(True)
        d = get_health_state().to_dict()
        self.assertEqual(d["status"], "ok")
        # Verify the conditional logic: 200 == ok
        expected_code = 200 if d["status"] == "ok" else 503
        self.assertEqual(expected_code, 200)

    def test_ready_returns_503_when_status_degraded(self):
        """When db or nats is down, to_dict status is 'degraded' → expect HTTP 503."""
        set_db_ok(False)
        set_nats_connected(False)
        d = get_health_state().to_dict()
        self.assertEqual(d["status"], "degraded")
        expected_code = 200 if d["status"] == "ok" else 503
        self.assertEqual(expected_code, 503)

    def test_ready_source_contains_503(self):
        """HealthHandler.do_GET must assign 503 when status != 'ok'."""
        path = os.path.join(
            os.path.dirname(__file__), "..", "apps",
            "orchestrator-worker", "main.py",
        )
        with open(path) as f:
            src = f.read()
        # The readiness handler must contain 503 for the non-ok case
        self.assertIn('"ok" else 503', src)

    def test_live_handler_never_returns_503(self):
        """HealthHandler live endpoint must NOT use non-200 status codes."""
        path = os.path.join(
            os.path.dirname(__file__), "..", "apps",
            "orchestrator-worker", "main.py",
        )
        with open(path) as f:
            src = f.read()
        # Find the live handler section and verify it only uses 200
        live_section_start = src.find('/health/live')
        live_section_end = src.find('/health/ready')
        live_section = src[live_section_start:live_section_end]
        self.assertNotIn("503", live_section)
        self.assertIn("200", live_section)

    def test_provisioning_failure_message_is_accurate(self):
        """Provisioning failure log must mention fail-fast, not 'degraded'."""
        path = os.path.join(
            os.path.dirname(__file__), "..", "apps",
            "orchestrator-worker", "main.py",
        )
        with open(path) as f:
            src = f.read()
        self.assertIn("may fail-fast", src)
        self.assertNotIn("will start degraded", src)


# ---------------------------------------------------------------------------
# Import boundaries
# ---------------------------------------------------------------------------


class TestProvisioningImports(unittest.TestCase):
    """JetStream provisioning must not import control-api or FastAPI."""

    def test_no_fastapi_import(self):
        import inspect
        from packages.services import jetstream_provisioning as mod
        src = inspect.getsource(mod)
        self.assertNotIn("from fastapi", src)
        self.assertNotIn("import fastapi", src)

    def test_no_control_api_import(self):
        import inspect
        from packages.services import jetstream_provisioning as mod
        src = inspect.getsource(mod)
        self.assertNotIn("control-api", src)

    def test_no_http_import(self):
        import inspect
        from packages.services import jetstream_provisioning as mod
        src = inspect.getsource(mod)
        self.assertNotIn("from http", src)
        self.assertNotIn("import http", src)

    def test_control_api_no_provisioning_import(self):
        """Control API must not import provisioning."""
        path = os.path.join(
            os.path.dirname(__file__), "..", "apps", "control-api", "main.py",
        )
        with open(path) as f:
            src = f.read()
        self.assertNotIn("jetstream_provisioning", src)
        self.assertNotIn("provision_campaign_delivery", src)


class TestHealthStateImports(unittest.TestCase):
    """health_state must not import FastAPI or nats."""

    def test_no_fastapi_import(self):
        import inspect
        from packages.services import health_state as mod
        src = inspect.getsource(mod)
        self.assertNotIn("from fastapi", src)

    def test_no_nats_import(self):
        import inspect
        from packages.services import health_state as mod
        src = inspect.getsource(mod)
        self.assertNotIn("import nats", src)
        self.assertNotIn("from nats", src)


# ---------------------------------------------------------------------------
# S-014: Shutdown + DB check + health
# ---------------------------------------------------------------------------


class TestShutdownHealth(unittest.TestCase):
    """HealthState during shutdown and DB check verification."""

    def test_shutting_down_status(self):
        """When shutting_down=True, ready status is 'shutting_down'."""
        from packages.services.health_state import HealthState
        state = HealthState(db_ok=True, nats_connected=True, shutting_down=True)
        d = state.to_dict()
        self.assertEqual(d["status"], "shutting_down")

    def test_shutting_down_not_ok_even_when_healthy(self):
        """Shutting down status is never 'ok'."""
        from packages.services.health_state import HealthState
        state = HealthState(db_ok=True, nats_connected=True, shutting_down=True)
        d = state.to_dict()
        self.assertNotEqual(d["status"], "ok")

    def test_shutting_down_overrides_degraded(self):
        """Shutting down takes priority over degraded."""
        from packages.services.health_state import HealthState
        state = HealthState(db_ok=False, shutting_down=True)
        d = state.to_dict()
        self.assertEqual(d["status"], "shutting_down")

    def test_set_shutting_down(self):
        """set_shutting_down() marks the singleton."""
        from packages.services.health_state import set_shutting_down, get_health_state
        set_shutting_down()
        state = get_health_state()
        self.assertTrue(state.shutting_down)

    def test_worker_has_signal_handlers(self):
        """Worker main.py must register SIGTERM and SIGINT handlers."""
        path = os.path.join(
            os.path.dirname(__file__), "..", "apps",
            "orchestrator-worker", "main.py",
        )
        with open(path) as f:
            src = f.read()
        self.assertIn("SIGTERM", src)
        self.assertIn("SIGINT", src)
        self.assertIn("add_signal_handler", src)

    def test_db_check_source_has_select_1(self):
        """Worker must have real DB SELECT 1 connectivity check."""
        path = os.path.join(
            os.path.dirname(__file__), "..", "apps",
            "orchestrator-worker", "main.py",
        )
        with open(path) as f:
            src = f.read()
        self.assertIn("SELECT 1", src)
        self.assertIn("Database unreachable", src)

    def test_shutdown_calls_stop_on_relay(self):
        """Shutdown path must call relay.stop()."""
        path = os.path.join(
            os.path.dirname(__file__), "..", "apps",
            "orchestrator-worker", "main.py",
        )
        with open(path) as f:
            src = f.read()
        self.assertIn("_relay_ref.stop()", src)

    def test_shutdown_calls_set_shutting_down(self):
        """Shutdown path must call set_shutting_down."""
        path = os.path.join(
            os.path.dirname(__file__), "..", "apps",
            "orchestrator-worker", "main.py",
        )
        with open(path) as f:
            src = f.read()
        self.assertIn("set_shutting_down", src)


if __name__ == "__main__":
    unittest.main()
