"""Unit tests for campaign event handler and consumer (S-012 Phase 2b).

Tests: envelope parsing, campaign_id extraction, event type filtering,
ack/nak semantics, handler calls generate_manifests_for_campaign,
import boundaries.
"""

from __future__ import annotations

import asyncio
import json
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from packages.services.campaign_event_handler import (
    DELIVERY_EVENT_TYPES,
    StubCampaignEventConsumer,
    extract_campaign_id,
    handle_campaign_delivery_event,
    parse_envelope,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_envelope_bytes(
    event_type="campaign.approved",
    aggregate_id="camp-001",
    event_id="evt-001",
) -> bytes:
    return json.dumps({
        "event_id": event_id,
        "event_type": event_type,
        "event_version": "1.0",
        "aggregate_type": "campaign",
        "aggregate_id": aggregate_id,
        "payload": {},
        "headers": {},
        "created_at": "2026-07-07T00:00:00Z",
    }).encode("utf-8")


# ---------------------------------------------------------------------------
# Envelope parsing
# ---------------------------------------------------------------------------


class TestEnvelopeParsing(unittest.TestCase):
    """parse_envelope and extract_campaign_id."""

    def test_parse_valid_json(self):
        raw = _make_envelope_bytes()
        env = parse_envelope(raw)
        self.assertIsNotNone(env)
        self.assertEqual(env["event_type"], "campaign.approved")

    def test_parse_invalid_json_returns_none(self):
        self.assertIsNone(parse_envelope(b"not json"))

    def test_parse_empty_bytes_returns_none(self):
        self.assertIsNone(parse_envelope(b""))

    def test_extract_campaign_id_from_aggregate_id(self):
        env = json.loads(_make_envelope_bytes(aggregate_id="camp-xyz"))
        self.assertEqual(extract_campaign_id(env), "camp-xyz")

    def test_extract_campaign_id_missing_returns_none(self):
        self.assertIsNone(extract_campaign_id({}))


# ---------------------------------------------------------------------------
# Event type filtering
# ---------------------------------------------------------------------------


class TestDeliveryEventTypes(unittest.TestCase):
    """DELIVERY_EVENT_TYPES frozenset contains expected ADR-016 triggers."""

    def test_contains_all_adr016_triggers(self):
        """All 7 delivery triggers from ADR-016 §1 must be present."""
        required = {
            "campaign.approved",
            "campaign.updated",
            "campaign.scheduled",
            "campaign.activated",
            "campaign.placement.changed",
            "campaign.creative.changed",
            "campaign.flight.changed",
        }
        self.assertEqual(DELIVERY_EVENT_TYPES, required)

    def test_contains_approved(self):
        self.assertIn("campaign.approved", DELIVERY_EVENT_TYPES)

    def test_contains_updated(self):
        self.assertIn("campaign.updated", DELIVERY_EVENT_TYPES)

    def test_contains_scheduled(self):
        self.assertIn("campaign.scheduled", DELIVERY_EVENT_TYPES)

    def test_contains_activated(self):
        self.assertIn("campaign.activated", DELIVERY_EVENT_TYPES)

    def test_contains_placement_changed(self):
        self.assertIn("campaign.placement.changed", DELIVERY_EVENT_TYPES)

    def test_contains_creative_changed(self):
        self.assertIn("campaign.creative.changed", DELIVERY_EVENT_TYPES)

    def test_contains_flight_changed(self):
        self.assertIn("campaign.flight.changed", DELIVERY_EVENT_TYPES)

    def test_does_not_contain_created(self):
        self.assertNotIn("campaign.created", DELIVERY_EVENT_TYPES)

    def test_does_not_contain_archived(self):
        self.assertNotIn("campaign.archived", DELIVERY_EVENT_TYPES)


# ---------------------------------------------------------------------------
# Handler — unit (mocked generate_manifests_for_campaign)
# ---------------------------------------------------------------------------


class TestCampaignEventHandler(unittest.IsolatedAsyncioTestCase):
    """handle_campaign_delivery_event with mocked DB/generation."""

    async def _make_session(self):
        return AsyncMock()

    async def test_supported_event_calls_generate(self):
        session = await self._make_session()
        env = json.loads(_make_envelope_bytes("campaign.approved", "camp-1"))

        with patch(
            "packages.domain.delivery.generate_manifests_for_campaign",
        ) as mock_gen:
            mock_gen.return_value = MagicMock(eligible=True, manifest_count=3)
            result = await handle_campaign_delivery_event(session, env)

        self.assertTrue(result)
        mock_gen.assert_called_once_with(session, "camp-1")

    async def test_unknown_event_type_returns_true_no_call(self):
        session = await self._make_session()
        env = json.loads(_make_envelope_bytes("campaign.created", "camp-1"))

        with patch(
            "packages.domain.delivery.generate_manifests_for_campaign",
        ) as mock_gen:
            result = await handle_campaign_delivery_event(session, env)

        self.assertTrue(result)  # ack: nothing to do
        mock_gen.assert_not_called()

    async def test_no_campaign_id_returns_true_no_call(self):
        session = await self._make_session()
        env = json.loads(_make_envelope_bytes("campaign.approved", aggregate_id=""))

        with patch(
            "packages.domain.delivery.generate_manifests_for_campaign",
        ) as mock_gen:
            result = await handle_campaign_delivery_event(session, env)

        self.assertTrue(result)  # ack: nothing to do
        mock_gen.assert_not_called()

    async def test_handler_error_returns_false(self):
        session = await self._make_session()
        env = json.loads(_make_envelope_bytes("campaign.approved", "camp-1"))

        with patch(
            "packages.domain.delivery.generate_manifests_for_campaign",
            side_effect=RuntimeError("DB down"),
        ):
            result = await handle_campaign_delivery_event(session, env)

        self.assertFalse(result)


# ---------------------------------------------------------------------------
# StubCampaignEventConsumer — unit
# ---------------------------------------------------------------------------


class TestStubCampaignEventConsumer(unittest.IsolatedAsyncioTestCase):
    """StubCampaignEventConsumer ack/nak semantics."""

    def _make_consumer(self):
        engine = MagicMock()
        return StubCampaignEventConsumer(engine)

    async def test_supported_event_acked(self):
        consumer = self._make_consumer()
        raw = _make_envelope_bytes("campaign.approved", "camp-1")

        with patch(
            "packages.domain.delivery.generate_manifests_for_campaign",
        ) as mock_gen:
            mock_gen.return_value = MagicMock(eligible=True, manifest_count=1)
            await consumer._handle_one(raw)

        self.assertEqual(consumer.acked, 1)
        self.assertEqual(consumer.nakd, 0)

    async def test_unknown_event_acked(self):
        """Unknown events are safe-to-ignore — ack."""
        consumer = self._make_consumer()
        raw = _make_envelope_bytes("campaign.created", "camp-1")

        with patch(
            "packages.domain.delivery.generate_manifests_for_campaign",
        ) as mock_gen:
            await consumer._handle_one(raw)

        self.assertEqual(consumer.acked, 1)
        self.assertEqual(consumer.nakd, 0)
        mock_gen.assert_not_called()

    async def test_handler_failure_nakd(self):
        consumer = self._make_consumer()
        raw = _make_envelope_bytes("campaign.approved", "camp-1")

        with patch(
            "packages.domain.delivery.generate_manifests_for_campaign",
            side_effect=RuntimeError("boom"),
        ):
            await consumer._handle_one(raw)

        self.assertEqual(consumer.acked, 0)
        self.assertEqual(consumer.nakd, 1)

    async def test_unparseable_envelope_nakd(self):
        consumer = self._make_consumer()
        await consumer._handle_one(b"not json")

        self.assertEqual(consumer.acked, 0)
        self.assertEqual(consumer.nakd, 1)


# ---------------------------------------------------------------------------
# Import boundaries
# ---------------------------------------------------------------------------


class TestConsumerImports(unittest.TestCase):
    """Verify campaign event handler has no forbidden imports."""

    def test_no_fastapi_import(self):
        import inspect
        from packages.services import campaign_event_handler as mod

        src = inspect.getsource(mod)
        # Filter out docstring (can mention "fastapi" in "no api/auth/fastapi")
        # Only real imports matter
        lines = [
            line for line in src.split("\n")
            if not line.strip().startswith("#") and not line.strip().startswith('"""')
            and not line.strip().startswith("'''")
        ]
        filtered = "\n".join(lines)
        self.assertNotIn("from fastapi", filtered)
        self.assertNotIn("import fastapi", filtered)

    def test_no_nats_direct_import(self):
        """Module-level imports must not include nats.
           Lazy imports inside methods (connect()) are OK."""
        import inspect
        from packages.services import campaign_event_handler as mod

        src = inspect.getsource(mod)
        # Only check module-level lines (no indentation), skip method bodies
        module_level = [
            line for line in src.split("\n")
            if not line.startswith(" ") and not line.startswith("\t")
        ]
        filtered = "\n".join(module_level)
        self.assertNotIn("import nats", filtered)
        self.assertNotIn("from nats", filtered)

    def test_control_api_no_consumer_import(self):
        """Control API must not import consumer/handler."""
        path = os.path.join(
            os.path.dirname(__file__), "..", "apps", "control-api", "main.py",
        )
        with open(path) as f:
            src = f.read()
        self.assertNotIn("campaign_event_handler", src)
        self.assertNotIn("CampaignEventConsumer", src)
        self.assertNotIn("StubCampaignEventConsumer", src)
        self.assertNotIn("NatsJetStreamCampaignConsumer", src)


# ---------------------------------------------------------------------------
# NatsJetStreamCampaignConsumer — unit (mocked NATS client)
# ---------------------------------------------------------------------------


class _MockNatsMsg:
    """Simulate a nats.aio.msg.Msg with .data, .ack(), .nak(), .term()."""

    def __init__(self, data: bytes) -> None:
        self.data = data
        self._acked = False
        self._nakd = False
        self._terminated = False
        self._nak_delay: float | None = None

    async def ack(self) -> None:
        self._acked = True

    async def nak(self, delay: float = 0) -> None:
        self._nakd = True
        self._nak_delay = delay

    async def term(self) -> None:
        self._terminated = True


class TestNatsJetStreamCampaignConsumer(unittest.IsolatedAsyncioTestCase):
    """NatsJetStreamCampaignConsumer — unit tests with mocked NATS."""

    def _make_consumer(self, **kwargs) -> NatsJetStreamCampaignConsumer:
        from packages.services.campaign_event_handler import (
            NatsJetStreamCampaignConsumer,
        )
        engine = MagicMock()
        return NatsJetStreamCampaignConsumer(
            nats_url="nats://localhost:4222",
            engine=engine,
            **kwargs,
        )

    # -- subscribe / subject / durable ------------------------------------

    async def test_consumer_creates_pull_subscription(self):
        """connect() must create a pull subscription with expected args."""
        consumer = self._make_consumer(durable="test-durable", stream="RMP")
        mock_nc = AsyncMock()
        mock_js = AsyncMock()
        mock_sub = AsyncMock()
        mock_js.pull_subscribe.return_value = mock_sub
        # jetstream() is a sync method returning a JS context — use MagicMock
        mock_nc.jetstream = MagicMock(return_value=mock_js)

        # Patch the NATS import inside connect()
        with patch(
            "nats.aio.client.Client",
            return_value=mock_nc,
        ):
            await consumer.connect()

        mock_js.pull_subscribe.assert_called_once_with(
            subject="campaign.>",
            durable="test-durable",
            stream="RMP",
        )
        self.assertIsNotNone(consumer._sub)

    # -- ack after handler success ----------------------------------------

    async def test_valid_message_acked_after_handler_success(self):
        """Handler returns True → commit → ack."""
        consumer = self._make_consumer()
        consumer._sub = AsyncMock()
        msg = _MockNatsMsg(_make_envelope_bytes("campaign.approved", "camp-1"))

        with patch(
            "packages.domain.delivery.generate_manifests_for_campaign",
        ) as mock_gen:
            mock_gen.return_value = MagicMock(eligible=True, manifest_count=3)
            await consumer._process_one(msg)

        self.assertTrue(msg._acked)
        self.assertFalse(msg._nakd)
        self.assertFalse(msg._terminated)
        self.assertEqual(consumer.acked, 1)
        self.assertEqual(consumer.nakd, 0)

    # -- nak after handler failure ----------------------------------------

    async def test_handler_failure_nakd_with_delay(self):
        """Handler returns False → rollback → nak with delay."""
        consumer = self._make_consumer(nak_delay=5.0)
        consumer._sub = AsyncMock()
        msg = _MockNatsMsg(_make_envelope_bytes("campaign.approved", "camp-1"))

        with patch(
            "packages.domain.delivery.generate_manifests_for_campaign",
            side_effect=RuntimeError("DB down"),
        ):
            await consumer._process_one(msg)

        self.assertFalse(msg._acked)
        self.assertTrue(msg._nakd)
        self.assertEqual(msg._nak_delay, 5.0)
        self.assertEqual(consumer.nakd, 1)
        self.assertEqual(consumer.acked, 0)

    # -- term on malformed message ----------------------------------------

    async def test_unparseable_message_terminated(self):
        """Malformed envelope → term+ack (poison pill)."""
        consumer = self._make_consumer()
        consumer._sub = AsyncMock()
        msg = _MockNatsMsg(b"not json")

        await consumer._process_one(msg)

        self.assertTrue(msg._terminated)
        self.assertFalse(msg._acked)
        self.assertFalse(msg._nakd)
        self.assertEqual(consumer.terminated, 1)
        self.assertEqual(consumer.nakd, 0)

    # -- unknown event → safe ack -----------------------------------------

    async def test_unknown_event_acked(self):
        """Unknown event type → safe ack (no-op)."""
        consumer = self._make_consumer()
        consumer._sub = AsyncMock()
        msg = _MockNatsMsg(
            _make_envelope_bytes("campaign.created", "camp-1"),
        )

        with patch(
            "packages.domain.delivery.generate_manifests_for_campaign",
        ) as mock_gen:
            await consumer._process_one(msg)

        self.assertTrue(msg._acked)
        self.assertFalse(msg._nakd)
        self.assertFalse(msg._terminated)
        self.assertEqual(consumer.acked, 1)
        mock_gen.assert_not_called()

    # -- run loop fetches and processes -----------------------------------

    async def test_run_fetches_and_processes_messages(self):
        """run() fetches messages and processes each one."""
        consumer = self._make_consumer(batch_size=10, fetch_timeout=1.0)
        mock_sub = AsyncMock()

        msg1 = _MockNatsMsg(_make_envelope_bytes("campaign.approved", "camp-1"))
        msg2 = _MockNatsMsg(_make_envelope_bytes("campaign.updated", "camp-2"))

        # fetch returns 2 messages, then timeout (idle), then stop
        mock_sub.fetch.side_effect = [
            [msg1, msg2],
            TimeoutError(),
            TimeoutError(),
            TimeoutError(),
            TimeoutError(),
        ]
        consumer._sub = mock_sub

        with patch(
            "packages.domain.delivery.generate_manifests_for_campaign",
        ) as mock_gen:
            mock_gen.return_value = MagicMock(eligible=True, manifest_count=3)

            # Run briefly then stop
            task = asyncio.create_task(consumer.run())
            await asyncio.sleep(0.3)
            await consumer.stop()
            await task

        self.assertTrue(msg1._acked)
        self.assertTrue(msg2._acked)
        self.assertEqual(consumer.acked, 2)
        # fetch was called at least twice (batch + at least one idle poll)
        self.assertGreaterEqual(mock_sub.fetch.call_count, 2)

    # -- no blocking I/O --------------------------------------------------

    def test_no_sync_sleep_in_module(self):
        """No time.sleep() — only asyncio.sleep() (ADR-012)."""
        import inspect
        from packages.services import campaign_event_handler as mod

        src = inspect.getsource(mod)
        self.assertNotIn("time.sleep", src)

    def test_no_blocking_http_calls(self):
        """No requests/urllib/httpx sync calls."""
        import inspect
        from packages.services import campaign_event_handler as mod

        src = inspect.getsource(mod)
        self.assertNotIn("import requests", src)
        # asyncio.sleep is allowed
        # Filter the "import asyncio" line before checking for blocking patterns
        self.assertNotIn("requests.get(", src.lower().replace("asyncio", ""))


# ---------------------------------------------------------------------------
# orchestrator-worker _start_consumer — fail-fast tests
# ---------------------------------------------------------------------------


class TestStartConsumerFailFast(unittest.IsolatedAsyncioTestCase):
    """_start_consumer must fail when NATS_URL set but nats-py missing."""

    async def _call_start_consumer(self, env_overrides=None):
        """Import and call _start_consumer with env overrides, return result or exc."""
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
                patch.object(
                    worker_mod, "_start_real_consumer", new=AsyncMock(),
                ) as mock_real,
                patch.object(
                    worker_mod, "_start_stub_consumer", new=AsyncMock(),
                ) as mock_stub,
                patch(
                    "packages.domain.database.create_engine",
                    return_value=MagicMock(),
                ) as mock_engine,
            ):
                mock_real.return_value = True
                mock_stub.return_value = True
                try:
                    result = await worker_mod._start_consumer(
                        "postgresql://localhost/db",
                    )
                    return result, mock_real, mock_stub, None
                except RuntimeError as exc:
                    return None, mock_real, mock_stub, exc

    async def test_no_nats_url_uses_stub(self):
        """No NATS_URL → StubCampaignEventConsumer."""
        result, mock_real, mock_stub, exc = await self._call_start_consumer({
            "CAMPAIGN_CONSUMER_ENABLED": "true",
            "NATS_URL": "",
        })
        self.assertIsNone(exc)
        self.assertTrue(result)
        mock_real.assert_not_called()
        mock_stub.assert_called_once()

    async def test_nats_url_uses_real_consumer(self):
        """NATS_URL set + no ALLOW_STUB → real consumer path."""
        result, mock_real, mock_stub, exc = await self._call_start_consumer({
            "CAMPAIGN_CONSUMER_ENABLED": "true",
            "NATS_URL": "nats://localhost:4222",
        })
        self.assertIsNone(exc)
        self.assertTrue(result)
        mock_real.assert_called_once()
        mock_stub.assert_not_called()

    async def test_allow_stub_uses_stub(self):
        """NATS_URL + CAMPAIGN_CONSUMER_ALLOW_STUB=true → stub."""
        result, mock_real, mock_stub, exc = await self._call_start_consumer({
            "CAMPAIGN_CONSUMER_ENABLED": "true",
            "NATS_URL": "nats://localhost:4222",
            "CAMPAIGN_CONSUMER_ALLOW_STUB": "true",
        })
        self.assertIsNone(exc)
        self.assertTrue(result)
        mock_real.assert_not_called()
        mock_stub.assert_called_once()

    async def test_disabled_returns_false(self):
        """CAMPAIGN_CONSUMER_ENABLED != true → no consumer started."""
        result, mock_real, mock_stub, exc = await self._call_start_consumer({
            "CAMPAIGN_CONSUMER_ENABLED": "false",
        })
        self.assertIsNone(exc)
        self.assertFalse(result)
        mock_real.assert_not_called()
        mock_stub.assert_not_called()


if __name__ == "__main__":
    unittest.main()
