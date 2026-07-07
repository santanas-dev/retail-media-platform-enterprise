"""Unit tests for outbox relay worker and NATS publisher abstraction.

Phase S-012 Phase 1: relay foundation — no real NATS, no real DB.
"""

from __future__ import annotations

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


if __name__ == "__main__":
    unittest.main()
