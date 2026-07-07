"""Unit tests for campaign event handler and consumer (S-012 Phase 2b).

Tests: envelope parsing, campaign_id extraction, event type filtering,
ack/nak semantics, handler calls generate_manifests_for_campaign,
import boundaries.
"""

from __future__ import annotations

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
        import inspect
        from packages.services import campaign_event_handler as mod

        src = inspect.getsource(mod)
        self.assertNotIn("import nats", src)
        self.assertNotIn("from nats", src)

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


if __name__ == "__main__":
    unittest.main()
