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

# RM-STAB-020 (P1-7): every outbox event type is published under its own
# subject (subject = event_type); a subject no stream captures fails the
# relay's publish and the event ends in dead_letter.  Two streams:
#
# * RMP — campaign events only, read by the campaign consumer (its durable has
#   no server-side filter).  Kept separate so high-volume PoP traffic can never
#   evict an unacked campaign event under the limits/DiscardOld policy.
# * RMP_EVENTS — every other outbox family.  No consumer yet: a bounded
#   buffer for future readers (7 days / 1 GiB, oldest discarded).
CAMPAIGN_STREAM_SUBJECTS: tuple[str, ...] = ("campaign.>",)

EVENTS_STREAM = "RMP_EVENTS"
EVENTS_STREAM_SUBJECTS: tuple[str, ...] = (
    "delivery.>",
    "pop.>",
    "emergency.>",
    "creative_asset.>",
)
EVENTS_STREAM_CONFIG: dict = {
    "retention": "limits",
    "max_msgs": -1,
    "max_bytes": 1024 * 1024 * 1024,  # 1 GiB
    "max_age": 7 * 24 * 3600,  # seconds — 7 days
    "discard": "old",
    "storage": "file",
    "num_replicas": 1,
}

# Everything the relay may publish — the union of both streams.
OUTBOX_STREAM_SUBJECTS: tuple[str, ...] = CAMPAIGN_STREAM_SUBJECTS + EVENTS_STREAM_SUBJECTS

DEFAULT_CONSUMER_CONFIG: dict = {
    "ack_policy": "explicit",
    "ack_wait": 30,  # seconds — handler must ack within 30s
    # Server-side unlimited: the consumer itself counts deliveries and
    # dead-letters (RM-STAB-020).  Changing this would recreate the durable.
    "max_deliver": -1,
    "max_ack_pending": 100,
}


# ---------------------------------------------------------------------------
# Provisioning helpers
# ---------------------------------------------------------------------------


async def _ensure_stream(
    js, name: str, subjects: list[str], config: dict | None = None,
) -> None:
    """Create or update a JetStream stream.  Idempotent — safe to re-run."""
    config = DEFAULT_STREAM_CONFIG if config is None else config
    try:
        await js.add_stream(
            name=name,
            subjects=subjects,
            **config,
        )
        logger.info("JetStream stream created: %s (subjects=%s)", name, subjects)
    except Exception:
        # Stream exists — update it
        try:
            await js.update_stream(
                name=name,
                subjects=subjects,
                **config,
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
        subjects: Subjects the stream captures.  Default: CAMPAIGN_STREAM_SUBJECTS.
        durable: Durable consumer name.
        connect_timeout: NATS connect timeout in seconds.

    Returns:
        Dict with keys: stream, consumer, subjects, durable — for logging.

    Raises:
        RuntimeError: if NATS is unreachable or provisioning fails.
    """
    if subjects is None:
        subjects = list(CAMPAIGN_STREAM_SUBJECTS)

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


async def provision_outbox_event_stream(
    nats_url: str,
    *,
    connect_timeout: float = 5.0,
) -> dict:
    """Create or update RMP_EVENTS (non-campaign outbox subjects).  Idempotent.

    Raises:
        RuntimeError: if NATS is unreachable or provisioning fails.
    """
    from nats.aio.client import Client as NATS

    try:
        nc = NATS()
        await nc.connect(servers=[nats_url], connect_timeout=connect_timeout)
    except Exception as exc:
        raise RuntimeError(f"NATS unreachable at {nats_url}: {exc}.") from exc

    try:
        js = nc.jetstream()
        await _ensure_stream(js, EVENTS_STREAM, list(EVENTS_STREAM_SUBJECTS), EVENTS_STREAM_CONFIG)
    finally:
        await nc.drain()

    logger.info("Outbox event stream provisioned: stream=%s subjects=%s",
                EVENTS_STREAM, list(EVENTS_STREAM_SUBJECTS))
    return {"stream": EVENTS_STREAM, "subjects": list(EVENTS_STREAM_SUBJECTS)}


async def missing_stream_subjects(
    nats_url: str,
    expected: dict[str, tuple[str, ...]],
    connect_timeout: float = 5.0,
) -> list[str]:
    """Problems with the provisioned streams; empty list when every expected
    stream exists and captures at least its expected subjects.

    Used when auto-provisioning is off, so a stream created by an older
    runbook (``campaign.>`` only) is reported instead of silently leaving
    P1-7 in place.  The worker raises; ``main()`` logs it and starts anyway.
    """
    from nats.aio.client import Client as NATS

    try:
        nc = NATS()
        await nc.connect(servers=[nats_url], connect_timeout=connect_timeout)
    except Exception as exc:
        return [f"NATS unreachable at {nats_url}: {exc}"]

    problems: list[str] = []
    try:
        js = nc.jetstream()
        for stream, subjects in expected.items():
            try:
                info = await js.stream_info(stream)
            except Exception:
                problems.append(f"stream {stream} not found")
                continue
            have = set(info.config.subjects or [])
            for subject in subjects:
                if subject not in have:
                    problems.append(f"stream {stream} does not capture {subject}")
    finally:
        await nc.drain()
    return problems
