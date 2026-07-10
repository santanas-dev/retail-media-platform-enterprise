"""Campaign delivery event handler (ADR-016, S-012 Phases 2b + 2c).

Consumes campaign outbox events from NATS (via outbox relay envelope)
and triggers manifest generation for delivery planning.

Layer: packages/services/ — uses domain/delivery.py, no api/auth/fastapi.

Consumers:
  - StubCampaignEventConsumer — fake queue for unit/behavioral tests
  - NatsJetStreamCampaignConsumer (Phase 2c) — real JetStream pull consumer
"""

from __future__ import annotations

import asyncio
import json as json_mod
import logging
from abc import ABC, abstractmethod
from collections import deque
from collections.abc import Awaitable
from typing import Any, Callable

from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine

logger = logging.getLogger("rmp.campaign_event_handler")

# ---------------------------------------------------------------------------
# Event types that trigger delivery planning / manifest generation
# ---------------------------------------------------------------------------

DELIVERY_EVENT_TYPES: frozenset[str] = frozenset({
    "campaign.approved",
    "campaign.updated",
    "campaign.scheduled",
    "campaign.activated",
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
        if result.manifest_count > 0:
            from packages.services.health_state import bump_manifest_success
            bump_manifest_success()
        else:
            from packages.services.health_state import bump_manifest_skipped
            bump_manifest_skipped()
        return True
    except Exception:
        logger.exception(
            "Manifest generation failed for campaign=%s (event=%s)",
            campaign_id,
            envelope.get("event_id", "?"),
        )
        from packages.services.health_state import bump_manifest_failed
        bump_manifest_failed()
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

    def __init__(self, engine: AsyncEngine, *,
                 session_setup: Callable[[AsyncSession], Awaitable[None]] | None = None) -> None:
        self._engine = engine
        self._session_setup = session_setup
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
            if self._session_setup is not None:
                await self._session_setup(session)
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


# ---------------------------------------------------------------------------
# Real JetStream consumer (S-012 Phase 2c)
# ---------------------------------------------------------------------------


class NatsJetStreamCampaignConsumer(CampaignEventConsumer):
    """Real NATS JetStream pull-based campaign event consumer (ADR-002, ADR-012).

    Pull-based: explicit flow control.  Each message is processed through
    the existing handler in its own transaction.  Ack only after DB commit
    succeeds; nak with delay on handler failure; term+ack on malformed
    messages (poison pill — don't retry forever).

    Lifecycle:
        consumer = NatsJetStreamCampaignConsumer(
            nats_url="nats://localhost:4222",
            engine=engine,
            durable="rmp-campaign-consumer",
            subject="campaign.>",
            batch_size=10,
            fetch_timeout=5.0,
        )
        await consumer.connect()
        asyncio.create_task(consumer.run())
        # ... on shutdown:
        await consumer.stop()
        await consumer.disconnect()
    """

    def __init__(
        self,
        nats_url: str,
        engine: AsyncEngine,
        *,
        durable: str = "rmp-campaign-consumer",
        subject: str = "campaign.>",
        stream: str = "RMP",
        batch_size: int = 10,
        fetch_timeout: float = 5.0,
        nak_delay: float = 5.0,
        connect_timeout: float = 5.0,
        session_setup: Callable[[AsyncSession], Awaitable[None]] | None = None,
    ) -> None:
        self._nats_url = nats_url
        self._engine = engine
        self._durable = durable
        self._subject = subject
        self._stream = stream
        self._batch_size = batch_size
        self._fetch_timeout = fetch_timeout
        self._nak_delay = nak_delay
        self._connect_timeout = connect_timeout

        self._nc: object | None = None
        self._js: object | None = None
        self._sub: object | None = None
        self._running: bool = False
        self._session_setup = session_setup

        # Stats (for tests + observability)
        self.acked: int = 0
        self.nakd: int = 0
        self.terminated: int = 0
        self.errors: int = 0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Connect to NATS and create a JetStream pull subscription."""
        from nats.aio.client import Client as NATS

        self._nc = NATS()
        await self._nc.connect(
            servers=[self._nats_url],
            connect_timeout=self._connect_timeout,
        )
        self._js = self._nc.jetstream()

        # Create or bind to pull subscription
        self._sub = await self._js.pull_subscribe(
            subject=self._subject,
            durable=self._durable,
            stream=self._stream,
        )
        logger.info(
            "JetStream pull consumer subscribed: subject=%s, durable=%s, stream=%s",
            self._subject,
            self._durable,
            self._stream,
        )

    async def disconnect(self) -> None:
        """Drain and close the NATS connection."""
        if self._nc is not None:
            await self._nc.drain()
            self._nc = None
            self._js = None
            self._sub = None

    # ------------------------------------------------------------------
    # Loop
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """Pull-based consumer loop — fetch batches, process messages.

        Runs until stop() is called or CancelledError is received.
        Each message is processed in its own transaction.
        """
        if self._sub is None:
            logger.error("Not connected — call connect() before run()")
            return

        self._running = True
        logger.info(
            "Campaign event consumer started (JetStream pull): "
            "durable=%s, batch=%d",
            self._durable,
            self._batch_size,
        )

        try:
            while self._running:
                try:
                    msgs = await self._sub.fetch(
                        batch=self._batch_size,
                        timeout=self._fetch_timeout,
                    )
                except TimeoutError:
                    # fetch() raises built-in TimeoutError when batch
                    # timeout expires with no messages — normal idle
                    continue
                except Exception:
                    logger.exception("Fetch error — retrying in 1s")
                    await asyncio.sleep(1)
                    continue

                for msg in msgs:
                    if not self._running:
                        break
                    await self._process_one(msg)

        except asyncio.CancelledError:
            logger.info("Campaign event consumer cancelled")
        except Exception:
            logger.exception("Campaign event consumer loop crashed")
        finally:
            self._running = False

    async def stop(self) -> None:
        """Signal the consumer loop to stop (graceful shutdown)."""
        self._running = False

    # ------------------------------------------------------------------
    # Internal — message processing
    # ------------------------------------------------------------------

    async def _process_one(self, msg: object) -> None:
        """Process a single NATS message through the handler.

        Ack/nak semantics:
          - Handler success + commit  → ack  (msg.ack())
          - Handler failure            → nak  (msg.nak(delay)) — retryable
          - Malformed envelope         → term (msg.term()) — poison pill, no retry
          - Unhandled exception        → nak  (msg.nak(delay)) — retryable
        """
        try:
            raw_data: bytes = msg.data  # type: ignore[union-attr]
        except Exception:
            logger.warning("Message has no .data — term")
            await self._safe_term(msg)
            self.terminated += 1
            return

        envelope = parse_envelope(raw_data)
        if envelope is None:
            logger.warning("Unparseable envelope — term (poison pill)")
            await self._safe_term(msg)
            self.terminated += 1
            return

        async with AsyncSession(self._engine) as session:
            if self._session_setup is not None:
                await self._session_setup(session)
            try:
                success = await handle_campaign_delivery_event(session, envelope)
                if success:
                    await session.commit()
                    if await self._safe_ack(msg):
                        self.acked += 1
                        from packages.services.health_state import bump_consumer_acked
                        bump_consumer_acked()
                else:
                    await session.rollback()
                    await self._safe_nak(msg)
                    self.nakd += 1
                    from packages.services.health_state import bump_consumer_nakd
                    bump_consumer_nakd()
            except Exception:
                await session.rollback()
                await self._safe_nak(msg)
                self.nakd += 1
                from packages.services.health_state import bump_consumer_nakd
                bump_consumer_nakd()
                logger.exception(
                    "Unhandled error processing event %s",
                    envelope.get("event_id", "?"),
                )

    # ------------------------------------------------------------------
    # Safe JetStream helpers (never crash on ack/nak/term)
    # ------------------------------------------------------------------

    async def _safe_ack(self, msg: object) -> bool:
        """Ack a message. Returns True on success, False on failure."""
        try:
            await msg.ack()  # type: ignore[union-attr]
            return True
        except Exception:
            self.errors += 1
            from packages.services.health_state import bump_consumer_errors
            bump_consumer_errors()
            logger.exception("ack() failed")
            return False

    async def _safe_nak(self, msg: object) -> None:
        try:
            await msg.nak(delay=self._nak_delay)  # type: ignore[union-attr]
        except Exception:
            self.errors += 1
            from packages.services.health_state import bump_consumer_errors
            bump_consumer_errors()
            logger.exception("nak() failed")

    async def _safe_term(self, msg: object) -> None:
        try:
            await msg.term()  # type: ignore[union-attr]
        except Exception:
            self.errors += 1
            from packages.services.health_state import bump_consumer_errors
            bump_consumer_errors()
            logger.exception("term() failed")
