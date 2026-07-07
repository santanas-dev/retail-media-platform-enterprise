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


class NatsJetStreamPublisher(NatsPublisher):
    """Real async NATS JetStream publisher (ADR-002, ADR-012).

    Uses nats-py async client.  Sets Nats-Msg-Id header for JetStream
    deduplication (ADR-011 §3).

    Lifecycle:
        pub = NatsJetStreamPublisher("nats://localhost:4222", timeout=5.0)
        await pub.connect()
        result = await pub.publish("subject", payload, msg_id="evt-1")
        await pub.disconnect()
    """

    def __init__(
        self,
        url: str,
        *,
        timeout: float = 5.0,
        stream: str | None = None,
        **connect_kwargs,
    ) -> None:
        self._url = url
        self._timeout = timeout
        self._stream = stream
        self._connect_kwargs = connect_kwargs
        self._nc: object | None = None
        self._js: object | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Connect to NATS server and create JetStream context."""
        from nats.aio.client import Client as NATS

        self._nc = NATS()
        await self._nc.connect(
            servers=[self._url],
            connect_timeout=self._timeout,
            **self._connect_kwargs,
        )
        self._js = self._nc.jetstream()

    async def disconnect(self) -> None:
        """Drain and close the NATS connection."""
        if self._nc is not None:
            await self._nc.drain()
            self._nc = None
            self._js = None

    # ------------------------------------------------------------------
    # Publish
    # ------------------------------------------------------------------

    async def publish(
        self,
        subject: str,
        payload: bytes,
        msg_id: str,
    ) -> PublishResult:
        """Publish to NATS JetStream with Nats-Msg-Id dedup header.

        Returns PublishResult(success=True) only after JetStream ack.
        Returns PublishResult(success=False) on any failure.
        """
        if self._js is None:
            return PublishResult(
                success=False,
                error="not connected — call connect() first",
            )

        try:
            ack = await self._js.publish(
                subject,
                payload,
                headers={"Nats-Msg-Id": msg_id},
                stream=self._stream,
                timeout=self._timeout,
            )
            # ack.stream is set on successful JetStream publish
            if ack is not None and getattr(ack, "stream", None):
                return PublishResult(success=True)
            return PublishResult(
                success=False,
                error="JetStream publish returned no ack",
            )
        except Exception as exc:
            return PublishResult(
                success=False,
                error=f"{type(exc).__name__}: {exc}",
            )
