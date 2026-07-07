"""Campaign delivery event handler (ADR-016, Phase S-012 Phase 2b).

Consumes campaign outbox events from NATS (via outbox relay envelope)
and triggers manifest generation for delivery planning.

Layer: packages/services/ — uses domain/delivery.py, no api/auth/fastapi.
"""

from __future__ import annotations

import asyncio
import json as json_mod
import logging
from abc import ABC, abstractmethod
from collections import deque
from typing import Any, Callable

from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine

logger = logging.getLogger("rmp.campaign_event_handler")

# ---------------------------------------------------------------------------
# Event types that trigger delivery planning / manifest generation
# ---------------------------------------------------------------------------

DELIVERY_EVENT_TYPES: frozenset[str] = frozenset({
    "campaign.approved",
    "campaign.updated",
    "campaign.placement.changed",
    "campaign.creative.changed",
    "campaign.flight.changed",
})


# ---------------------------------------------------------------------------
# Event envelope parsing
# ---------------------------------------------------------------------------


def parse_envelope(raw: bytes) -> dict[str, Any] | None:
    """Decode a relay-published outbox event envelope.

    Returns None if the envelope is unparseable.
    """
    try:
        return json_mod.loads(raw)
    except (json_mod.JSONDecodeError, TypeError, UnicodeDecodeError):
        logger.warning("Failed to parse outbox event envelope")
        return None


def extract_campaign_id(envelope: dict[str, Any]) -> str | None:
    """Extract campaign_id from the envelope's aggregate_id field."""
    return envelope.get("aggregate_id") or None


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------


async def handle_campaign_delivery_event(
    session: AsyncSession,
    envelope: dict[str, Any],
) -> bool:
    """Process a campaign outbox event and trigger manifest generation.

    Args:
        session: Active async SQLAlchemy session (caller owns transaction).
        envelope: Parsed outbox event envelope.

    Returns:
        True if processing succeeded (manifest generation called), False on error.
        Unknown/ineligible events return True (ack — nothing to process).
    """
    event_type = envelope.get("event_type", "")
    campaign_id = extract_campaign_id(envelope)

    if not campaign_id:
        logger.debug(
            "Skipping event %s — no aggregate_id",
            envelope.get("event_id", "?"),
        )
        return True  # ack: nothing to do

    if event_type not in DELIVERY_EVENT_TYPES:
        logger.debug(
            "Skipping event %s (type=%s, campaign=%s) — not a delivery trigger",
            envelope.get("event_id", "?"),
            event_type,
            campaign_id,
        )
        return True  # ack: nothing to do

    logger.info(
        "Handling delivery event %s (type=%s, campaign=%s)",
        envelope.get("event_id", "?"),
        event_type,
        campaign_id,
    )

    from packages.domain.delivery import generate_manifests_for_campaign

    try:
        result = await generate_manifests_for_campaign(session, campaign_id)
        logger.info(
            "Manifest generation done: campaign=%s, eligible=%s, manifests=%d",
            campaign_id,
            result.eligible,
            result.manifest_count,
        )
        return True
    except Exception:
        logger.exception(
            "Manifest generation failed for campaign=%s (event=%s)",
            campaign_id,
            envelope.get("event_id", "?"),
        )
        return False


# ---------------------------------------------------------------------------
# Consumer abstraction
# ---------------------------------------------------------------------------


class CampaignEventConsumer(ABC):
    """Async consumer for campaign outbox events.

    Testable via StubCampaignEventConsumer — no real NATS required for unit tests.
    """

    @abstractmethod
    async def run(self) -> None:
        """Run consumer loop until cancelled."""
        ...


class StubCampaignEventConsumer(CampaignEventConsumer):
    """Fake consumer for tests — inject messages via inject_message().

    Each injected message is processed synchronously within the consumer
    loop with its own transaction.  Ack is automatic after successful
    handler return; nak/log-skip on failure.
    """

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine
        self._queue: deque[bytes] = deque()
        self._acked: int = 0
        self._nakd: int = 0
        self._running: bool = False

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------

    def inject_message(self, raw_envelope: bytes) -> None:
        """Inject a raw outbox event envelope for the consumer to process."""
        self._queue.append(raw_envelope)

    @property
    def acked(self) -> int:
        return self._acked

    @property
    def nakd(self) -> int:
        return self._nakd

    # ------------------------------------------------------------------
    # Loop
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """Process injected messages in a loop until cancelled."""
        self._running = True
        logger.info("Campaign event consumer started (stub)")

        try:
            while self._running:
                while self._queue:
                    raw = self._queue.popleft()
                    await self._handle_one(raw)
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            logger.info("Campaign event consumer cancelled")
        finally:
            self._running = False

    async def stop(self) -> None:
        """Signal the consumer loop to stop."""
        self._running = False

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _handle_one(self, raw: bytes) -> None:
        envelope = parse_envelope(raw)
        if envelope is None:
            self._nakd += 1
            return

        async with AsyncSession(self._engine) as session:
            try:
                success = await handle_campaign_delivery_event(session, envelope)
                if success:
                    await session.commit()
                    self._acked += 1
                else:
                    await session.rollback()
                    self._nakd += 1
            except Exception:
                await session.rollback()
                self._nakd += 1
                logger.exception("Unhandled consumer error")
