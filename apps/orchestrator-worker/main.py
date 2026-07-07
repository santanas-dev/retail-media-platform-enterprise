"""
Retail Media Platform — Orchestrator Worker.

Phase S-012: Outbox relay worker + health HTTP server.
Runs continuous outbox relay loop when NATS_URL and DATABASE_URL are configured.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from packages.observability import setup_logging

SERVICE_NAME = "orchestrator-worker"
logger = setup_logging(SERVICE_NAME)


# ---------------------------------------------------------------------------
# Health HTTP server
# ---------------------------------------------------------------------------


async def health_http_server():
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import json as json_mod
    import threading

    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path in ("/health/live", "/health/ready"):
                body = json_mod.dumps({
                    "status": "ok",
                    "service": SERVICE_NAME,
                    "checks": {
                        "database": "not_configured",
                        "nats": "not_configured",
                    },
                }).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, fmt, *args):
            pass

    port = int(os.environ.get("ORCHESTRATOR_PORT", "8003"))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info("Health HTTP server on port %s", port)
    return server


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

    # When NATS_URL is configured, we require a real publisher.
    # StubNatsPublisher is NOT an acceptable fallback unless the
    # operator explicitly overrides via OUTBOX_RELAY_ALLOW_STUB=true.
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
    except Exception as exc:
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

    engine = create_engine(db_url)
    logger.info("Database engine created for outbox relay")

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

    asyncio.create_task(relay.run())
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
    """Start the campaign event consumer if configured.

    Gated by CAMPAIGN_CONSUMER_ENABLED=true.  Uses StubCampaignEventConsumer
    for tests — real JetStream consumer is deferred (Phase 2c).

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
    from packages.services.campaign_event_handler import StubCampaignEventConsumer

    engine = create_engine(db_url)
    consumer = StubCampaignEventConsumer(engine)
    logger.info("Campaign event consumer started (stub mode)")
    asyncio.create_task(consumer.run())
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main():
    logger.info("Starting %s", SERVICE_NAME)
    server = await health_http_server()
    await _start_relay()
    await _start_consumer(
        os.environ.get("DATABASE_URL", "").strip(),
    )

    while True:
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
