"""NATS JetStream provisioning — idempotent stream/consumer creation (S-013).

Safe to run multiple times: creates or updates existing streams/consumers.
No FastAPI or web framework imports.  Uses nats-py async client
(ADR-012: no blocking I/O).

Usage:
    from packages.services.jetstream_provisioning import (
        provision_campaign_delivery,
    )

    await provision_campaign_delivery(
        nats_url="nats://localhost:4222",
        stream="RMP",
        subjects=["campaign.>"],
        durable="rmp-campaign-consumer",
    )

On failure (NATS unreachable, auth error): raises RuntimeError with
a clear message.  Does NOT silently degrade.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("rmp.jetstream_provisioning")

# ---------------------------------------------------------------------------
# Stream defaults
# ---------------------------------------------------------------------------

DEFAULT_STREAM_CONFIG: dict = {
    "retention": "limits",
    "max_msgs": 1_000_000,
    "max_bytes": 256 * 1024 * 1024,  # 256 MB
    "max_age": 0,  # never expire
    "storage": "file",
    "num_replicas": 1,
}

DEFAULT_CONSUMER_CONFIG: dict = {
    "ack_policy": "explicit",
    "ack_wait": 30,  # seconds — handler must ack within 30s
    "max_deliver": -1,  # unlimited redeliveries (nak returns for retry)
    "max_ack_pending": 100,
}


# ---------------------------------------------------------------------------
# Provisioning helpers
# ---------------------------------------------------------------------------


async def _ensure_stream(js, name: str, subjects: list[str]) -> None:
    """Create or update a JetStream stream.  Idempotent — safe to re-run."""
    try:
        await js.add_stream(
            name=name,
            subjects=subjects,
            **DEFAULT_STREAM_CONFIG,
        )
        logger.info("JetStream stream created: %s (subjects=%s)", name, subjects)
    except Exception:
        # Stream exists — update it
        try:
            await js.update_stream(
                name=name,
                subjects=subjects,
                **DEFAULT_STREAM_CONFIG,
            )
            logger.info("JetStream stream updated: %s (subjects=%s)", name, subjects)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to create or update JetStream stream '{name}': {exc}"
            ) from exc


async def _ensure_consumer(
    js,
    stream: str,
    durable: str,
    filter_subject: str = "",
) -> None:
    """Create or update a JetStream pull consumer.  Idempotent."""
    config: dict = {**DEFAULT_CONSUMER_CONFIG}
    if filter_subject:
        config["filter_subject"] = filter_subject

    try:
        await js.add_consumer(
            stream=stream,
            durable_name=durable,
            **config,
        )
        logger.info(
            "JetStream consumer created: stream=%s durable=%s",
            stream, durable,
        )
    except Exception:
        # Consumer exists — delete and recreate (nats-py lacks update_consumer)
        try:
            await js.delete_consumer(stream=stream, consumer=durable)
            await js.add_consumer(
                stream=stream,
                durable_name=durable,
                **config,
            )
            logger.info(
                "JetStream consumer recreated: stream=%s durable=%s",
                stream, durable,
            )
        except Exception as exc:
            raise RuntimeError(
                f"Failed to create or update JetStream consumer "
                f"'{durable}' on stream '{stream}': {exc}"
            ) from exc


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def provision_campaign_delivery(
    nats_url: str,
    *,
    stream: str = "RMP",
    subjects: list[str] | None = None,
    durable: str = "rmp-campaign-consumer",
    connect_timeout: float = 5.0,
) -> dict:
    """Provision JetStream for campaign delivery events.

    Creates (or updates) the stream and pull consumer for campaign
    outbox-event delivery.  Idempotent — safe to run at every startup.

    Args:
        nats_url: NATS server URL (e.g. 'nats://localhost:4222').
        stream: JetStream stream name.
        subjects: Subjects the stream captures.  Default: ['campaign.>'].
        durable: Durable consumer name.
        connect_timeout: NATS connect timeout in seconds.

    Returns:
        Dict with keys: stream, consumer, subjects, durable — for logging.

    Raises:
        RuntimeError: if NATS is unreachable or provisioning fails.
    """
    if subjects is None:
        subjects = ["campaign.>"]

    from nats.aio.client import Client as NATS

    try:
        nc = NATS()
        await nc.connect(
            servers=[nats_url],
            connect_timeout=connect_timeout,
        )
    except Exception as exc:
        raise RuntimeError(
            f"NATS unreachable at {nats_url}: {exc}. "
            f"Start NATS with JetStream enabled (nats-server -js)."
        ) from exc

    try:
        js = nc.jetstream()
        await _ensure_stream(js, stream, subjects)
        await _ensure_consumer(js, stream, durable)
    finally:
        await nc.drain()

    logger.info(
        "Campaign delivery provisioning complete: "
        "stream=%s subjects=%s durable=%s",
        stream, subjects, durable,
    )

    return {
        "stream": stream,
        "subjects": subjects,
        "durable": durable,
    }


async def check_stream_exists(
    nats_url: str,
    stream: str = "RMP",
    connect_timeout: float = 5.0,
) -> bool:
    """Check whether a JetStream stream exists.

    Returns True if the stream is found, False otherwise.
    Does NOT raise on connection error — returns False.
    """
    try:
        from nats.aio.client import Client as NATS
        nc = NATS()
        await nc.connect(
            servers=[nats_url],
            connect_timeout=connect_timeout,
        )
        try:
            js = nc.jetstream()
            await js.stream_info(stream)
            return True
        except Exception:
            return False
        finally:
            await nc.drain()
    except Exception:
        return False
