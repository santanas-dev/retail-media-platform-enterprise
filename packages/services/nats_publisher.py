"""NATS publisher abstraction for outbox relay.

ADR-012: no blocking I/O — all implementations use async-native clients.
ADR-011 §3: Nats-Msg-Id = event_id for JetStream deduplication.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class PublishResult:
    """Result of a NATS publish attempt."""

    success: bool
    error: str | None = None


class NatsPublisher(ABC):
    """Async NATS publisher — injectable interface for relay + tests."""

    @abstractmethod
    async def publish(
        self,
        subject: str,
        payload: bytes,
        msg_id: str,
    ) -> PublishResult:
        """Publish a message to NATS JetStream.

        Args:
            subject: NATS subject (derived from event_type).
            payload: JSON-encoded message body.
            msg_id: Nats-Msg-Id header for deduplication (ADR-011 §3).

        Returns:
            PublishResult with success=True on ack, False on failure.
        """
        ...


class StubNatsPublisher(NatsPublisher):
    """Fake NATS publisher for tests — records published messages.

    Supports configurable failure injection:
    - fail_next(n): fail the next n publishes
    - fail_on(subject): permanently fail publishes to a subject
    """

    def __init__(self) -> None:
        self.published: list[dict[str, object]] = []
        self._fail_next_count: int = 0
        self._fail_subjects: set[str] = set()

    async def publish(
        self,
        subject: str,
        payload: bytes,
        msg_id: str,
    ) -> PublishResult:
        if self._fail_next_count > 0:
            self._fail_next_count -= 1
            return PublishResult(
                success=False,
                error="simulated transient failure",
            )
        if subject in self._fail_subjects:
            return PublishResult(
                success=False,
                error=f"simulated failure on subject {subject}",
            )
        self.published.append({
            "subject": subject,
            "payload": payload,
            "msg_id": msg_id,
        })
        return PublishResult(success=True)

    def fail_next(self, count: int = 1) -> None:
        """Fail the next `count` publish attempts."""
        self._fail_next_count = count

    def fail_on(self, subject: str) -> None:
        """Permanently fail publishes to this subject."""
        self._fail_subjects.add(subject)

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------

    @property
    def publish_count(self) -> int:
        return len(self.published)

    @property
    def last_published(self) -> dict[str, object] | None:
        return self.published[-1] if self.published else None
