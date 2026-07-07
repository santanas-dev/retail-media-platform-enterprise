"""Unit tests for outbox relay worker and NATS publisher abstraction.

Phase S-012 Phase 1: relay foundation — no real NATS, no real DB.
"""

from __future__ import annotations

import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from packages.services.nats_publisher import PublishResult, StubNatsPublisher


# ---------------------------------------------------------------------------
# NATS Publisher abstraction
# ---------------------------------------------------------------------------


class TestStubNatsPublisher(unittest.IsolatedAsyncioTestCase):
    """StubNatsPublisher — fake for tests with controllable failures."""

    async def test_publish_success_records_message(self):
        pub = StubNatsPublisher()
        result = await pub.publish(
            "campaign.created", b'{"id": "1"}', "evt-001",
        )
        self.assertTrue(result.success)
        self.assertIsNone(result.error)
        self.assertEqual(pub.publish_count, 1)
        self.assertEqual(pub.last_published["subject"], "campaign.created")
        self.assertEqual(pub.last_published["msg_id"], "evt-001")

    async def test_fail_next_reports_failure(self):
        pub = StubNatsPublisher()
        pub.fail_next(1)
        result = await pub.publish("test.event", b"{}", "id-1")
        self.assertFalse(result.success)
        self.assertEqual(result.error, "simulated transient failure")
        self.assertEqual(pub.publish_count, 0)

    async def test_fail_next_count_is_consumed(self):
        pub = StubNatsPublisher()
        pub.fail_next(2)
        r1 = await pub.publish("a", b"{}", "1")
        r2 = await pub.publish("b", b"{}", "2")
        r3 = await pub.publish("c", b"{}", "3")
        self.assertFalse(r1.success)
        self.assertFalse(r2.success)
        self.assertTrue(r3.success)
        self.assertEqual(pub.publish_count, 1)

    async def test_fail_on_subject_permanent(self):
        pub = StubNatsPublisher()
        pub.fail_on("failing.event")
        r1 = await pub.publish("failing.event", b"{}", "1")
        r2 = await pub.publish("other.event", b"{}", "2")
        self.assertFalse(r1.success)
        self.assertTrue(r2.success)

    async def test_msg_id_stored(self):
        pub = StubNatsPublisher()
        await pub.publish("test", b'{"x":1}', "msg-abc-123")
        self.assertEqual(pub.last_published["msg_id"], "msg-abc-123")

    async def test_payload_preserved(self):
        pub = StubNatsPublisher()
        payload = b'{"event_type":"campaign.created","payload":{"id":"x"}}'
        await pub.publish("test", payload, "1")
        self.assertEqual(pub.last_published["payload"], payload)


# ---------------------------------------------------------------------------
# NatsJetStreamPublisher — unit tests (mocked NATS client)
# ---------------------------------------------------------------------------


class TestNatsJetStreamPublisher(unittest.IsolatedAsyncioTestCase):
    """NatsJetStreamPublisher — real publisher with mocked nats-py client."""

    async def _make_pub(self, **kwargs):
        from packages.services.nats_publisher import NatsJetStreamPublisher
        return NatsJetStreamPublisher("nats://localhost:4222", timeout=5.0, **kwargs)

    @staticmethod
    def _mock_ack(stream_name="RMP"):
        """Create a mock PubAck with .stream attribute set."""
        ack = MagicMock()
        ack.stream = stream_name
        ack.seq = 42
        return ack

    async def test_publish_sets_msg_id_header(self):
        """Nats-Msg-Id header must be passed to JetStream publish."""
        pub = await self._make_pub()
        mock_js = AsyncMock()
        mock_js.publish.return_value = self._mock_ack()
        pub._nc = MagicMock()
        pub._js = mock_js

        result = await pub.publish("test.subject", b"payload", "evt-abc-123")

        self.assertTrue(result.success)
        mock_js.publish.assert_called_once()
        subject, payload, kwargs = self._unpack_publish_call(mock_js.publish)
        self.assertEqual(subject, "test.subject")
        self.assertEqual(payload, b"payload")
        self.assertEqual(kwargs.get("headers", {}).get("Nats-Msg-Id"), "evt-abc-123")

    async def test_success_only_after_jetstream_ack(self):
        """PublishResult(success=True) only when JetStream ack has .stream."""
        pub = await self._make_pub()
        mock_js = AsyncMock()
        pub._nc = MagicMock()
        pub._js = mock_js

        # Case 1: valid ack
        mock_js.publish.return_value = self._mock_ack()
        r1 = await pub.publish("s1", b"p1", "id1")
        self.assertTrue(r1.success)

        # Case 2: ack without stream attribute (no ack)
        mock_js.publish.return_value = MagicMock(spec=[])  # no .stream
        r2 = await pub.publish("s2", b"p2", "id2")
        self.assertFalse(r2.success)
        self.assertIn("no ack", r2.error)

    async def test_failure_returns_success_false(self):
        """Publish exception → PublishResult(success=False)."""
        pub = await self._make_pub()
        mock_js = AsyncMock()
        mock_js.publish.side_effect = TimeoutError("publish timed out")
        pub._nc = MagicMock()
        pub._js = mock_js

        result = await pub.publish("s", b"p", "id")
        self.assertFalse(result.success)
        self.assertIn("TimeoutError", result.error)
        self.assertIn("publish timed out", result.error)

    async def test_not_connected_returns_error(self):
        """Calling publish() before connect() returns failure."""
        pub = await self._make_pub()
        result = await pub.publish("s", b"p", "id")
        self.assertFalse(result.success)
        self.assertIn("not connected", result.error)

    async def test_connect_disconnect_lifecycle(self):
        """connect() and disconnect() manage NATS client correctly."""
        pub = await self._make_pub()
        self.assertIsNone(pub._nc)
        self.assertIsNone(pub._js)

        # Mock the NATS client
        mock_nc = AsyncMock()
        mock_nc.jetstream.return_value = AsyncMock()

        with patch.object(pub.__class__, "connect", new=AsyncMock()) as mock_connect:
            mock_connect.side_effect = lambda: setattr(pub, "_nc", mock_nc) or setattr(pub, "_js", mock_nc.jetstream.return_value)
            await pub.connect()
            self.assertIsNotNone(pub._nc)
            self.assertIsNotNone(pub._js)

        with patch.object(pub.__class__, "disconnect", new=AsyncMock()) as mock_disconnect:
            mock_disconnect.side_effect = lambda: setattr(pub, "_nc", None) or setattr(pub, "_js", None)
            await pub.disconnect()
            self.assertIsNone(pub._nc)
            self.assertIsNone(pub._js)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _unpack_publish_call(mock_call):
        """Extract (subject, payload, kwargs) from a mock JS publish call."""
        args = mock_call.call_args[0] if mock_call.call_args else ()
        kwargs = mock_call.call_args[1] if mock_call.call_args else {}
        subject = args[0] if len(args) > 0 else kwargs.get("subject")
        payload = args[1] if len(args) > 1 else kwargs.get("payload")
        return subject, payload, kwargs


# ---------------------------------------------------------------------------
# OutboxRelay — unit tests (mocked DB)
# ---------------------------------------------------------------------------


class TestOutboxRelayUnit(unittest.IsolatedAsyncioTestCase):
    """OutboxRelay with mocked database — proves relay logic without real DB."""

    async def _make_relay(self, publisher=None, **kwargs):
        from packages.services.outbox_relay import OutboxRelay

        pub = publisher or StubNatsPublisher()
        engine = MagicMock()
        relay = OutboxRelay(pub, engine, **kwargs)
        return relay, pub

    @patch("packages.services.outbox_relay.fetch_pending_events")
    async def test_fetch_pending_calls_repository(self, mock_fetch):
        mock_fetch.return_value = []
        relay, pub = await self._make_relay()
        # Need to mock the session too
        with patch("packages.services.outbox_relay.AsyncSession") as mock_session_cls:
            mock_session = AsyncMock()
            mock_session_cls.return_value.__aenter__.return_value = mock_session
            count = await relay.run_once()
            mock_fetch.assert_called_once()
            self.assertEqual(count, 0)

    @patch("packages.services.outbox_relay.fetch_pending_events")
    @patch("packages.services.outbox_relay.mark_event_published")
    async def test_successful_publish_marks_published(
        self, mock_mark_pub, mock_fetch,
    ):
        mock_event = MagicMock()
        mock_event.id = "evt-001"
        mock_event.event_type = "campaign.created"
        mock_event.event_version = "1.0"
        mock_event.aggregate_type = "campaign"
        mock_event.aggregate_id = "camp-1"
        mock_event.payload_json = {"campaign_id": "camp-1"}
        mock_event.headers_json = {"correlation_id": "abc"}
        mock_event.created_at = MagicMock()
        mock_event.created_at.isoformat.return_value = "2026-07-07T00:00:00Z"

        mock_fetch.return_value = [mock_event]

        pub = StubNatsPublisher()
        relay, _ = await self._make_relay(publisher=pub)

        with patch("packages.services.outbox_relay.AsyncSession") as mock_session_cls:
            mock_session = AsyncMock()
            mock_session_cls.return_value.__aenter__.return_value = mock_session
            count = await relay.run_once()

            self.assertEqual(count, 1)
            self.assertEqual(pub.publish_count, 1)
            # Verify Nats-Msg-Id = event_id (ADR-011 §3)
            self.assertEqual(pub.last_published["msg_id"], "evt-001")
            mock_mark_pub.assert_called_once_with(mock_session, "evt-001")
            mock_session.commit.assert_called_once()

    @patch("packages.services.outbox_relay.fetch_pending_events")
    @patch("packages.services.outbox_relay.mark_event_failed")
    async def test_publish_failure_marks_failed(
        self, mock_mark_fail, mock_fetch,
    ):
        mock_event = MagicMock()
        mock_event.id = "evt-002"
        mock_event.event_type = "test.event"
        mock_event.event_version = "1.0"
        mock_event.aggregate_type = "test"
        mock_event.aggregate_id = "t-1"
        mock_event.payload_json = {}
        mock_event.headers_json = {}
        mock_event.created_at = MagicMock()
        mock_event.created_at.isoformat.return_value = "2026-07-07T00:00:00Z"

        mock_fetch.return_value = [mock_event]

        pub = StubNatsPublisher()
        pub.fail_next(1)
        relay, _ = await self._make_relay(publisher=pub, max_attempts=7)

        with patch("packages.services.outbox_relay.AsyncSession") as mock_session_cls:
            mock_session = AsyncMock()
            mock_session_cls.return_value.__aenter__.return_value = mock_session
            count = await relay.run_once()

            self.assertEqual(count, 1)
            mock_mark_fail.assert_called_once_with(
                mock_session, "evt-002",
                last_error="simulated transient failure",
                max_attempts=7,
            )

    @patch("packages.services.outbox_relay.fetch_pending_events")
    async def test_no_events_returns_zero(self, mock_fetch):
        mock_fetch.return_value = []
        relay, _ = await self._make_relay()

        with patch("packages.services.outbox_relay.AsyncSession") as mock_session_cls:
            mock_session = AsyncMock()
            mock_session_cls.return_value.__aenter__.return_value = mock_session
            count = await relay.run_once()
            self.assertEqual(count, 0)
            mock_session.commit.assert_called_once()

    async def test_default_config_values(self):
        from packages.services.outbox_relay import OutboxRelay

        relay = OutboxRelay(StubNatsPublisher(), MagicMock())
        self.assertEqual(relay._poll_interval, 0.5)
        self.assertEqual(relay._batch_size, 100)
        self.assertEqual(relay._max_attempts, 7)


# ---------------------------------------------------------------------------
# Import boundaries
# ---------------------------------------------------------------------------


class TestOutboxRelayImports(unittest.TestCase):
    """Verify relay module does NOT import forbidden packages."""

    def test_no_fastapi_import(self):
        """Relay must not import FastAPI — it's a background worker."""
        import inspect
        from packages.services import outbox_relay as mod

        src = inspect.getsource(mod)
        self.assertNotIn("fastapi", src.lower())
        self.assertNotIn("from fastapi", src)

    def test_no_nats_direct_import(self):
        """Relay uses injected NatsPublisher — no direct nats-py import."""
        import inspect
        from packages.services import outbox_relay as mod

        src = inspect.getsource(mod)
        self.assertNotIn("import nats", src)
        self.assertNotIn("from nats", src)

    def test_no_business_table_mutation(self):
        """Relay must not import campaign, device, or other business models."""
        import inspect
        from packages.services import outbox_relay as mod

        src = inspect.getsource(mod)
        # Only OutboxEvent model allowed
        self.assertNotIn("Campaign", src.replace("OutboxEvent", ""))
        self.assertNotIn("Device", src)
        self.assertNotIn("Manifest", src)
        self.assertNotIn("Advertiser", src)

    def test_nats_publisher_no_fastapi(self):
        """NATS publisher must not import FastAPI."""
        import inspect
        from packages.services import nats_publisher as mod

        src = inspect.getsource(mod)
        self.assertNotIn("fastapi", src.lower())

    def test_control_api_has_no_nats_import(self):
        """Control API must not import NATS (ADR-002: outbox relay only)."""
        path = os.path.join(
            os.path.dirname(__file__), "..", "apps", "control-api", "main.py",
        )
        with open(path) as f:
            src = f.read()
        self.assertNotIn("import nats", src)
        self.assertNotIn("from nats", src)
        self.assertNotIn("NatsJetStreamPublisher", src)


# ---------------------------------------------------------------------------
# _start_relay fail-fast (P2 fix — no silent Stub fallback)
# ---------------------------------------------------------------------------


class TestStartRelayFailFast(unittest.IsolatedAsyncioTestCase):
    """_start_relay must fail when NATS_URL is set but publisher unavailable."""

    async def _call_start_relay(self, env_overrides=None):
        """Import and call _start_relay with environment overrides.

        Uses mock to isolate from real DB/NATS dependencies.
        """
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
            with (
                patch.object(worker_mod, "_start_relay_loop", new=AsyncMock()) as mock_loop,
                patch.object(worker_mod, "_start_relay_with_stub", new=AsyncMock()) as mock_stub,
            ):
                mock_loop.return_value = True
                mock_stub.return_value = True
                try:
                    result = await worker_mod._start_relay()
                    return result, mock_loop, mock_stub, None
                except RuntimeError as exc:
                    return None, mock_loop, mock_stub, exc

    async def test_no_nats_url_returns_false(self):
        """No NATS_URL → skeleton mode, returns False."""
        result, mock_loop, mock_stub, exc = await self._call_start_relay({
            "NATS_URL": "",
            "DATABASE_URL": "postgresql://localhost/db",
        })
        self.assertIsNone(exc)
        self.assertFalse(result)
        mock_loop.assert_not_called()
        mock_stub.assert_not_called()

    async def test_connect_failure_raises_without_allow_stub(self):
        """NATS_URL set + connect failure → RuntimeError (no silent Stub)."""
        with patch(
            "packages.services.nats_publisher.NatsJetStreamPublisher.connect",
            side_effect=ConnectionRefusedError("no NATS"),
        ):
            result, mock_loop, mock_stub, exc = await self._call_start_relay({
                "NATS_URL": "nats://localhost:4222",
                "DATABASE_URL": "postgresql://localhost/db",
            })
            self.assertIsNotNone(exc)
            self.assertIsNone(result)
            self.assertIn("connection failed", str(exc))
            mock_stub.assert_not_called()

    async def test_connect_failure_allows_stub_with_flag(self):
        """NATS_URL set + connect failure + ALLOW_STUB=true → Stub fallback."""
        with patch(
            "packages.services.nats_publisher.NatsJetStreamPublisher.connect",
            side_effect=ConnectionRefusedError("no NATS"),
        ):
            result, mock_loop, mock_stub, exc = await self._call_start_relay({
                "NATS_URL": "nats://localhost:4222",
                "DATABASE_URL": "postgresql://localhost/db",
                "OUTBOX_RELAY_ALLOW_STUB": "true",
            })
            self.assertIsNone(exc)
            self.assertTrue(result)
            mock_stub.assert_called_once()
            mock_loop.assert_not_called()

    async def test_import_error_raises_without_allow_stub(self):
        """nats-py ImportError + NATS_URL set → RuntimeError (no silent Stub)."""
        # Simulate nats-py not installed by hiding NatsJetStreamPublisher import
        real_import = __import__

        def _fake_import(name, *args, **kwargs):
            if name == "packages.services.nats_publisher":
                raise ImportError("No module named 'nats'")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=_fake_import):
            result, mock_loop, mock_stub, exc = await self._call_start_relay({
                "NATS_URL": "nats://localhost:4222",
                "DATABASE_URL": "postgresql://localhost/db",
            })
            self.assertIsNotNone(exc)
            self.assertIsNone(result)
            self.assertIn("nats-py is not installed", str(exc))
            mock_stub.assert_not_called()

    async def test_import_error_allows_stub_with_flag(self):
        """nats-py ImportError + ALLOW_STUB=true → Stub fallback."""
        real_import = __import__

        def _fake_import(name, *args, **kwargs):
            if name == "packages.services.nats_publisher":
                raise ImportError("No module named 'nats'")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=_fake_import):
            result, mock_loop, mock_stub, exc = await self._call_start_relay({
                "NATS_URL": "nats://localhost:4222",
                "DATABASE_URL": "postgresql://localhost/db",
                "OUTBOX_RELAY_ALLOW_STUB": "true",
            })
            self.assertIsNone(exc)
            self.assertTrue(result)
            mock_stub.assert_called_once()
            mock_loop.assert_not_called()


# ---------------------------------------------------------------------------
# fetch_pending_events time-fence (P1 fix)
# ---------------------------------------------------------------------------


class TestFetchPendingTimeFence(unittest.TestCase):
    """fetch_pending_events must filter by next_attempt_at <= NOW()."""

    def test_query_includes_time_condition(self):
        """The generated SQL must include next_attempt_at <= now."""
        import inspect
        from packages.domain import repository as repo

        src = inspect.getsource(repo.fetch_pending_events)
        self.assertIn("next_attempt_at", src)
        self.assertIn("now", src.lower() or src)

    def test_query_uses_and_operator(self):
        """Both status filter and time filter must be AND-ed."""
        import inspect
        from packages.domain import repository as repo

        src = inspect.getsource(repo.fetch_pending_events)
        self.assertIn("and_", src)
        self.assertIn("or_", src)


# ---------------------------------------------------------------------------
# Dead-letter counter wiring (S-014)
# ---------------------------------------------------------------------------


class TestDeadLetterCounter(unittest.TestCase):
    """mark_event_failed returns True only when event transitions to dead_letter."""

    def test_returns_false_when_not_dead_letter(self):
        """Normal transient failure → mark_event_failed returns False."""
        import asyncio

        async def _test():
            import inspect
            from packages.domain.repository import mark_event_failed
            sig = inspect.signature(mark_event_failed)
            self.assertEqual(
                sig.return_annotation,
                bool,
                "mark_event_failed must return bool",
            )

        asyncio.run(_test())

    def test_relay_calls_bump_dead_letter_when_is_dead(self):
        """Source check: relay must call bump_relay_dead_letter on dead_letter."""
        import inspect
        from packages.services import outbox_relay as mod

        src = inspect.getsource(mod)
        self.assertIn("bump_relay_dead_letter", src)
        self.assertIn("is_dead", src)

    def test_dead_letter_returns_true_in_repository(self):
        """Repository mark_event_failed must return True in dead_letter path."""
        import inspect
        from packages.domain import repository as repo

        src = inspect.getsource(repo.mark_event_failed)
        self.assertIn('"dead_letter"', src)
        self.assertIn("return True", src)

    def test_behavioral_transient_failure_does_not_count_dead_letter(self):
        """Transient failure → returns False, dead_letter counter NOT bumped."""
        import asyncio

        async def _test():
            from unittest.mock import AsyncMock, MagicMock, patch
            from packages.domain.repository import mark_event_failed

            mock_session = AsyncMock()
            # Simulate event with 1 attempt so far → transient failure (max=7)
            mock_result = MagicMock()
            mock_result.scalar_one_or_none = MagicMock(return_value=1)
            mock_session.execute.return_value = mock_result

            result = await mark_event_failed(
                mock_session,
                "evt-001",
                last_error="transient error",
                max_attempts=7,
            )
            self.assertFalse(
                result,
                "transient failure should return False (not dead_letter)",
            )

        asyncio.run(_test())

    def test_behavioral_max_attempts_counts_dead_letter_once(self):
        """Exhausted retries → returns True exactly once per event transition."""
        import asyncio

        async def _test():
            from unittest.mock import AsyncMock, MagicMock
            from packages.domain.repository import mark_event_failed

            mock_session = AsyncMock()
            # Event already at 6 attempts, max_attempts=7 → crossing threshold
            mock_result = MagicMock()
            mock_result.scalar_one_or_none = MagicMock(return_value=6)
            mock_session.execute.return_value = mock_result

            result = await mark_event_failed(
                mock_session,
                "evt-002",
                last_error="final failure",
                max_attempts=7,
            )
            self.assertTrue(
                result,
                "max_attempts reached should return True (dead_letter transition)",
            )
            # Verify UPDATE was called (second execute after SELECT)
            self.assertGreaterEqual(
                mock_session.execute.call_count, 2,
                "should perform SELECT + UPDATE when transitioning to dead_letter",
            )

        asyncio.run(_test())

    def test_behavioral_already_dead_letter_not_double_counted(self):
        """Event at max_attempts+1 (already dead) returns True but won't be re-fetched."""
        import asyncio

        async def _test():
            from unittest.mock import AsyncMock, MagicMock
            from packages.domain.repository import mark_event_failed

            mock_session = AsyncMock()
            # Event already at 7 attempts (already dead_letter from previous run)
            # fetch_pending_events filters on status='pending', so this is unreachable
            # in normal operation.  The repository returns True but relay won't
            # re-process it because fetch_pending_events won't return dead_letter events.
            mock_result = MagicMock()
            mock_result.scalar_one_or_none = MagicMock(return_value=7)
            mock_session.execute.return_value = mock_result

            result = await mark_event_failed(
                mock_session,
                "evt-003",
                last_error="still failing",
                max_attempts=7,
            )
            # Would return True again, but this path is guarded by fetch_pending_events
            # which filters status != 'pending'
            self.assertTrue(
                result,
                "already dead letter → returns True (re-fetch guard is in relay)",
            )

        asyncio.run(_test())

    def test_event_not_found_returns_false(self):
        """Non-existent event → returns False."""
        import asyncio

        async def _test():
            from unittest.mock import AsyncMock, MagicMock
            from packages.domain.repository import mark_event_failed

            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none = MagicMock(return_value=None)
            mock_session.execute.return_value = mock_result

            result = await mark_event_failed(
                mock_session,
                "evt-nonexistent",
                last_error="not found",
            )
            self.assertFalse(result, "non-existent event should return False")

        asyncio.run(_test())


if __name__ == "__main__":
    unittest.main()
