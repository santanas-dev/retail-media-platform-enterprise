"""Transactional outbox relay worker.

ADR-011 §3: polls outbox_events, publishes to NATS JetStream,
marks published/failed/dead_letter.  No business table mutation.

Phase S-012 Phase 1: relay foundation only — no campaign manifest
generation or orchestrator business logic.
"""

from __future__ import annotations

import asyncio
import json as json_mod
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from packages.domain.models import OutboxEvent
from packages.domain.repository import (
    fetch_pending_events,
    mark_event_failed,
    mark_event_published,
)
from packages.services.nats_publisher import NatsPublisher

logger = logging.getLogger("rmp.outbox_relay")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class OutboxRelay:
    """Polls outbox_events and publishes to NATS JetStream.

    Single-worker pattern (ADR-011 §3).  Uses async SQLAlchemy engine
    and injected NATS publisher for testability.

    Lifecycle:
        relay = OutboxRelay(publisher, engine)
        await relay.run()          # continuous loop
        # or
        await relay.run_once()     # single batch (for tests/cron)
    """

    def __init__(
        self,
        publisher: NatsPublisher,
        engine: AsyncEngine,
        *,
        poll_interval: float = 0.5,
        batch_size: int = 100,
        max_attempts: int = 7,
    ) -> None:
        self._publisher = publisher
        self._engine = engine
        self._poll_interval = poll_interval
        self._batch_size = batch_size
        self._max_attempts = max_attempts

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """Run relay continuously until cancelled."""
        logger.info(
            "Outbox relay started: interval=%.1fs, batch=%d, max_attempts=%d",
            self._poll_interval,
            self._batch_size,
            self._max_attempts,
        )
        while True:
            try:
                count = await self.run_once()
                if count > 0:
                    logger.debug("Processed %d outbox events", count)
            except Exception:
                logger.exception("Outbox relay iteration failed")
            await asyncio.sleep(self._poll_interval)

    async def run_once(self) -> int:
        """Poll and process one batch of pending events.

        Returns:
            Number of events processed.
        """
        processed = 0
        async with AsyncSession(self._engine) as session:
            events = await fetch_pending_events(session, limit=self._batch_size)

            for event in events:
                try:
                    await self._process_event(session, event)
                    processed += 1
                except Exception:
                    logger.exception(
                        "Failed to process outbox event %s (type=%s)",
                        event.id,
                        event.event_type,
                    )
                    try:
                        await mark_event_failed(
                            session,
                            event.id,
                            last_error="relay processing error",
                            max_attempts=self._max_attempts,
                        )
                    except Exception:
                        logger.exception(
                            "Failed to mark event %s as failed", event.id,
                        )

            await session.commit()
        return processed

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _process_event(
        self,
        session: AsyncSession,
        event: OutboxEvent,
    ) -> None:
        """Process a single outbox event: publish → mark published/failed.

        Uses event_id as Nats-Msg-Id for JetStream deduplication
        (ADR-011 §3).  Payload is JSON-encoded event envelope.
        """
        subject = event.event_type
        envelope = json_mod.dumps({
            "event_id": event.id,
            "event_type": event.event_type,
            "event_version": event.event_version,
            "aggregate_type": event.aggregate_type,
            "aggregate_id": event.aggregate_id,
            "payload": event.payload_json,
            "headers": event.headers_json,
            "created_at": event.created_at.isoformat(),
        }).encode("utf-8")

        result = await self._publisher.publish(
            subject=subject,
            payload=envelope,
            msg_id=event.id,
        )

        if result.success:
            await mark_event_published(session, event.id)
            from packages.services.health_state import bump_relay_published
            bump_relay_published()
        else:
            await mark_event_failed(
                session,
                event.id,
                last_error=result.error or "publish failed",
                max_attempts=self._max_attempts,
            )
            from packages.services.health_state import bump_relay_failed
            bump_relay_failed(result.error)
