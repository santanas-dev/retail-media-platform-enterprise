"""
Retail Media Platform — Orchestrator Worker.

Phase S-012/S-013/S-014: Outbox relay worker + campaign event consumer +
health HTTP server + JetStream provisioning + graceful shutdown.

Runs continuous outbox relay loop when NATS_URL and DATABASE_URL are configured.
Handles SIGTERM/SIGINT for graceful shutdown.
"""

import asyncio
import os
import signal
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from packages.observability import setup_logging

SERVICE_NAME = "orchestrator-worker"
logger = setup_logging(SERVICE_NAME)

# ---------------------------------------------------------------------------
# Shutdown coordination
# ---------------------------------------------------------------------------

_shutdown_event = asyncio.Event()
_relay_ref: object | None = None  # OutboxRelay instance for stop()
_consumer_ref: object | None = None  # CampaignEventConsumer for stop()
_publisher_ref: object | None = None  # NatsJetStreamPublisher for disconnect()


def _handle_signal(sig_name: str) -> None:
    """Set shutdown event so the async main loop can exit cleanly."""
    logger.info("Received %s — initiating graceful shutdown", sig_name)
    _shutdown_event.set()


# ---------------------------------------------------------------------------
# Health HTTP server (sync — reads from thread-safe HealthState singleton)
# ---------------------------------------------------------------------------


async def health_http_server():
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import json as json_mod
    import threading

    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            from packages.services.health_state import get_health_state

            if self.path == "/health/live":
                body = json_mod.dumps({"status": "ok", "service": SERVICE_NAME}).encode()
                code = 200
            elif self.path == "/health/ready":
                state = get_health_state()
                payload = state.to_dict()
                body = json_mod.dumps(payload).encode()
                code = 200 if payload["status"] == "ok" else 503
            else:
                self.send_response(404)
                self.end_headers()
                return

            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt, *args):
            pass

    port = int(os.environ.get("ORCHESTRATOR_PORT", "8003"))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info("Health HTTP server on port %s", port)
    return server


# ---------------------------------------------------------------------------
# Provisioning
# ---------------------------------------------------------------------------


async def _run_provisioning(nats_url: str) -> bool:
    """Provision NATS JetStream if NATS_AUTO_PROVISION=true.

    Returns True if provisioning succeeded (or was not needed).

    Raises RuntimeError if:
      - NATS_AUTO_PROVISION=true but provisioning fails.
      - NATS_AUTO_PROVISION is unset/false and the stream does NOT exist.
    """
    auto_provision = (
        os.environ.get("NATS_AUTO_PROVISION", "").strip().lower() == "true"
    )

    from packages.services.jetstream_provisioning import (
        provision_campaign_delivery,
        check_stream_exists,
    )

    stream = os.environ.get("CAMPAIGN_CONSUMER_STREAM", "RMP")
    durable = os.environ.get("CAMPAIGN_CONSUMER_DURABLE", "rmp-campaign-consumer")
    subject = os.environ.get("CAMPAIGN_CONSUMER_SUBJECT", "campaign.>")

    if auto_provision:
        logger.info(
            "NATS_AUTO_PROVISION=true — provisioning stream=%s durable=%s",
            stream, durable,
        )
        try:
            result = await provision_campaign_delivery(
                nats_url,
                stream=stream,
                subjects=[subject],
                durable=durable,
            )
            logger.info(
                "Provisioning complete: stream=%s durable=%s",
                result["stream"], result["durable"],
            )
            return True
        except Exception as exc:
            raise RuntimeError(
                f"NATS auto-provisioning failed: {exc}. "
                f"Check that NATS is running with JetStream enabled "
                f"(nats-server -js) and credentials are correct."
            ) from exc

    # Auto-provision is off — verify stream exists
    exists = await check_stream_exists(nats_url, stream=stream)
    if not exists:
        raise RuntimeError(
            f"JetStream stream '{stream}' not found at {nats_url}. "
            f"Run provisioning first: set NATS_AUTO_PROVISION=true, or run "
            f"provision_campaign_delivery() from jetstream_provisioning.py. "
            f"See docs/runbook/delivery-runtime.md."
        )

    logger.info("JetStream stream '%s' found — skipping provisioning.", stream)
    return True


# ---------------------------------------------------------------------------
# Outbox relay
# ---------------------------------------------------------------------------


async def _start_relay() -> bool:
    """Start the outbox relay if NATS and DB are configured.

    Returns:
        True if relay was started.
        False if running in skeleton mode (no NATS_URL configured).

    Raises:
        RuntimeError: if NATS_URL is configured but a real publisher
            cannot be established (nats-py missing or connect failure).
            Only bypassed by explicit OUTBOX_RELAY_ALLOW_STUB=true.
    """
    nats_url = os.environ.get("NATS_URL", "").strip()
    db_url = os.environ.get("DATABASE_URL", "").strip()

    if not nats_url or not db_url:
        logger.info(
            "Outbox relay NOT started — NATS_URL=%s, DATABASE_URL=%s. "
            "Running in skeleton mode (health server only).",
            "set" if nats_url else "not set",
            "set" if db_url else "not set",
        )
        return False

    allow_stub = os.environ.get("OUTBOX_RELAY_ALLOW_STUB", "").strip().lower() == "true"

    from packages.domain.database import create_engine
    from packages.services.outbox_relay import OutboxRelay

    # --- Resolve publisher ---

    try:
        from packages.services.nats_publisher import NatsJetStreamPublisher  # noqa: F401
    except ImportError:
        if allow_stub:
            logger.warning(
                "nats-py not installed — falling back to StubNatsPublisher "
                "(OUTBOX_RELAY_ALLOW_STUB=true). Messages will NOT be delivered."
            )
            return await _start_relay_with_stub(
                db_url, nats_url,
            )
        raise RuntimeError(
            "NATS_URL is configured but nats-py is not installed. "
            "Install nats-py for JetStream publishing, "
            "or set OUTBOX_RELAY_ALLOW_STUB=true to use stub (dev/test only)."
        )

    from packages.services.nats_publisher import NatsJetStreamPublisher

    publisher = NatsJetStreamPublisher(
        nats_url,
        timeout=float(os.environ.get("NATS_TIMEOUT", "5.0")),
    )
    try:
        await publisher.connect()
        logger.info("Connected to NATS JetStream at %s", nats_url)
        from packages.services.health_state import set_nats_connected, set_publisher_ready
        set_nats_connected(True)
        set_publisher_ready(True)
        global _publisher_ref
        _publisher_ref = publisher
    except Exception as exc:
        from packages.services.health_state import set_nats_connected
        set_nats_connected(False)
        if allow_stub:
            logger.error(
                "NATS connection failed: %s. Falling back to StubNatsPublisher "
                "(OUTBOX_RELAY_ALLOW_STUB=true). Messages will NOT be delivered.",
                exc,
            )
            return await _start_relay_with_stub(
                db_url, nats_url,
            )
        raise RuntimeError(
            f"NATS_URL is configured but connection failed: {exc}. "
            "Set OUTBOX_RELAY_ALLOW_STUB=true to use stub (dev/test only)."
        ) from exc

    return await _start_relay_loop(db_url, publisher)


async def _start_relay_loop(db_url: str, publisher) -> bool:
    """Start the outbox relay loop with the given publisher."""
    from packages.domain.database import create_engine
    from packages.services.outbox_relay import OutboxRelay
    from packages.services.health_state import set_relay_running, set_db_ok

    engine = create_engine(db_url)

    # Real DB connectivity check
    try:
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        set_db_ok(True)
        logger.info("Database connectivity verified")
    except Exception as exc:
        set_db_ok(False)
        logger.error("Database connectivity check failed: %s", exc)
        raise RuntimeError(
            f"Database unreachable at {db_url}: {exc}. "
            f"Check DATABASE_URL and PostgreSQL availability."
        ) from exc

    poll_interval = float(os.environ.get("RELAY_POLL_INTERVAL", "0.5"))
    batch_size = int(os.environ.get("RELAY_BATCH_SIZE", "100"))

    relay = OutboxRelay(
        publisher=publisher,
        engine=engine,
        poll_interval=poll_interval,
        batch_size=batch_size,
    )
    logger.info(
        "Outbox relay started: poll=%.1fs, batch=%d, publisher=%s",
        poll_interval,
        batch_size,
        type(publisher).__name__,
    )

    set_relay_running(True)
    asyncio.create_task(relay.run())
    global _relay_ref
    _relay_ref = relay
    return True


async def _start_relay_with_stub(db_url: str, nats_url: str) -> bool:
    """Start relay with StubNatsPublisher (explicit dev/test override)."""
    from packages.services.nats_publisher import StubNatsPublisher

    publisher = StubNatsPublisher()
    logger.warning(
        "Using StubNatsPublisher — NATS messages will NOT be delivered. "
        "Install nats-py for real JetStream publishing."
    )
    return await _start_relay_loop(db_url, publisher)


# ---------------------------------------------------------------------------
# Campaign event consumer
# ---------------------------------------------------------------------------


async def _start_consumer(db_url: str) -> bool:
    """Start the campaign event consumer if CAMPAIGN_CONSUMER_ENABLED=true.

    Consumer selection:
      - NATS_URL set + CAMPAIGN_CONSUMER_ALLOW_STUB != true →
          NatsJetStreamCampaignConsumer (real JetStream pull).
          Fails fast if nats-py missing or NATS unreachable.
      - CAMPAIGN_CONSUMER_ALLOW_STUB=true or no NATS_URL →
          StubCampaignEventConsumer (test/skeleton mode).

    Returns True if consumer was started, False if disabled.
    """
    enabled = os.environ.get("CAMPAIGN_CONSUMER_ENABLED", "").strip().lower()
    if enabled != "true":
        logger.info(
            "Campaign event consumer NOT started — "
            "CAMPAIGN_CONSUMER_ENABLED=%s (set 'true' to enable)",
            enabled or "not set",
        )
        return False

    from packages.domain.database import create_engine

    engine = create_engine(db_url)
    nats_url = os.environ.get("NATS_URL", "").strip()
    allow_stub = (
        os.environ.get("CAMPAIGN_CONSUMER_ALLOW_STUB", "").strip().lower()
        == "true"
    )

    if nats_url and not allow_stub:
        return await _start_real_consumer(nats_url, engine)

    return await _start_stub_consumer(engine)


async def _start_real_consumer(nats_url: str, engine) -> bool:
    """Start NatsJetStreamCampaignConsumer with real NATS JetStream.

    Raises RuntimeError if nats-py missing or connect fails,
    unless CAMPAIGN_CONSUMER_ALLOW_STUB=true.
    """
    from packages.services.campaign_event_handler import (
        NatsJetStreamCampaignConsumer,
    )
    from packages.services.health_state import set_consumer_ready, set_consumer_running

    try:
        from nats.aio.client import Client as NATS  # noqa: F401
    except ImportError:
        allow_stub = (
            os.environ.get("CAMPAIGN_CONSUMER_ALLOW_STUB", "")
            .strip()
            .lower()
            == "true"
        )
        if allow_stub:
            logger.warning(
                "nats-py not installed — falling back to "
                "StubCampaignEventConsumer "
                "(CAMPAIGN_CONSUMER_ALLOW_STUB=true). "
                "Campaign events will NOT be consumed from NATS."
            )
            return await _start_stub_consumer(engine)
        raise RuntimeError(
            "NATS_URL is configured but nats-py is not installed. "
            "Install nats-py for JetStream consumption, "
            "or set CAMPAIGN_CONSUMER_ALLOW_STUB=true for stub (dev/test only)."
        )

    consumer = NatsJetStreamCampaignConsumer(
        nats_url=nats_url,
        engine=engine,
        durable=os.environ.get(
            "CAMPAIGN_CONSUMER_DURABLE", "rmp-campaign-consumer",
        ),
        subject=os.environ.get("CAMPAIGN_CONSUMER_SUBJECT", "campaign.>"),
        stream=os.environ.get("CAMPAIGN_CONSUMER_STREAM", "RMP"),
        batch_size=int(os.environ.get("CAMPAIGN_CONSUMER_BATCH_SIZE", "10")),
        fetch_timeout=float(
            os.environ.get("CAMPAIGN_CONSUMER_FETCH_TIMEOUT", "5.0"),
        ),
    )

    try:
        await consumer.connect()
        set_consumer_ready(True)
        logger.info(
            "Connected to NATS JetStream for campaign consumer: "
            "url=%s, durable=%s",
            nats_url,
            consumer._durable,
        )
    except Exception as exc:
        allow_stub = (
            os.environ.get("CAMPAIGN_CONSUMER_ALLOW_STUB", "")
            .strip()
            .lower()
            == "true"
        )
        if allow_stub:
            logger.error(
                "NATS connection failed: %s. Falling back to "
                "StubCampaignEventConsumer "
                "(CAMPAIGN_CONSUMER_ALLOW_STUB=true). "
                "Campaign events will NOT be consumed from NATS.",
                exc,
            )
            return await _start_stub_consumer(engine)
        raise RuntimeError(
            f"NATS_URL is configured but connection failed: {exc}. "
            "Set CAMPAIGN_CONSUMER_ALLOW_STUB=true for stub (dev/test only)."
        ) from exc

    logger.info("Campaign event consumer started (JetStream pull)")
    set_consumer_running(True)
    asyncio.create_task(consumer.run())
    global _consumer_ref
    _consumer_ref = consumer
    return True


async def _start_stub_consumer(engine) -> bool:
    """Start StubCampaignEventConsumer (test/skeleton mode)."""
    from packages.services.campaign_event_handler import (
        StubCampaignEventConsumer,
    )

    consumer = StubCampaignEventConsumer(engine)
    logger.info("Campaign event consumer started (stub mode)")
    asyncio.create_task(consumer.run())
    return True


# ---------------------------------------------------------------------------
# Observability summary logger
# ---------------------------------------------------------------------------


async def _observability_reporter(interval: float = 60.0) -> None:
    """Periodically log health state summary for ops visibility."""
    from packages.services.health_state import get_health_state

    while True:
        await asyncio.sleep(interval)
        state = get_health_state()
        logger.info(
            "Health summary: db=%s nats=%s publisher=%s consumer=%s "
            "relay(pub=%d fail=%d dlq=%d) "
            "consumer(ack=%d nak=%d term=%d err=%d) "
            "manifest(ok=%d fail=%d skip=%d)",
            "ok" if state.db_ok else "fail",
            "ok" if state.nats_connected else "fail",
            "ready" if state.publisher_ready else "no",
            "ready" if state.consumer_ready else "no",
            state.relay_published,
            state.relay_failed,
            state.relay_dead_letter,
            state.consumer_acked,
            state.consumer_nakd,
            state.consumer_terminated,
            state.consumer_errors,
            state.consumer_manifest_success,
            state.consumer_manifest_failed,
            state.consumer_manifest_skipped,
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main():
    logger.info("Starting %s", SERVICE_NAME)
    server = await health_http_server()

    # Register signal handlers
    loop = asyncio.get_running_loop()
    for sig_name, sig in [("SIGTERM", signal.SIGTERM), ("SIGINT", signal.SIGINT)]:
        try:
            loop.add_signal_handler(sig, lambda n=sig_name: _handle_signal(n))
        except NotImplementedError:
            logger.warning("Signal handler not supported on this platform")

    nats_url = os.environ.get("NATS_URL", "").strip()
    db_url = os.environ.get("DATABASE_URL", "").strip()
    consumer_enabled = (
        os.environ.get("CAMPAIGN_CONSUMER_ENABLED", "").strip().lower()
        == "true"
    )

    # --- Provisioning ---
    if nats_url and consumer_enabled:
        try:
            await _run_provisioning(nats_url)
        except RuntimeError:
            logger.exception(
                "Provisioning failed — worker will attempt to start "
                "relay/consumer (may fail-fast if NATS is unreachable)"
            )

    # --- Start relay ---
    await _start_relay()

    # --- Start consumer ---
    if consumer_enabled:
        await _start_consumer(db_url)

    # --- Observability reporter ---
    asyncio.create_task(_observability_reporter())

    logger.info("%s running — health :8003", SERVICE_NAME)

    # --- Wait for shutdown signal ---
    await _shutdown_event.wait()

    # --- Graceful shutdown ---
    logger.info("Shutting down orchestrator-worker")
    from packages.services.health_state import set_shutting_down
    set_shutting_down()

    # Stop relay
    if _relay_ref is not None:
        _relay_ref.stop()  # type: ignore[union-attr]
        logger.info("Relay stopped")

    # Stop consumer
    if _consumer_ref is not None:
        await _consumer_ref.stop()  # type: ignore[union-attr]
        logger.info("Consumer stopped")

    # Drain NATS publisher
    if _publisher_ref is not None:
        try:
            await _publisher_ref.disconnect()  # type: ignore[union-attr]
            logger.info("NATS publisher disconnected")
        except Exception:
            logger.exception("Error disconnecting NATS publisher")

    # Drain NATS consumer
    if _consumer_ref is not None:
        try:
            await _consumer_ref.disconnect()  # type: ignore[union-attr]
            logger.info("NATS consumer disconnected")
        except Exception:
            logger.exception("Error disconnecting NATS consumer")

    # Allow pending log flushes
    await asyncio.sleep(0.5)
    logger.info("Shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
