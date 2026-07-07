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

    Returns True if relay was started, False if running in skeleton mode.
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

    from packages.domain.database import create_engine
    from packages.services.nats_publisher import StubNatsPublisher
    from packages.services.outbox_relay import OutboxRelay

    # TODO: use real NatsJetStreamPublisher when nats-py dependency is added
    publisher = StubNatsPublisher()
    logger.warning(
        "Using StubNatsPublisher — NATS messages will NOT be delivered. "
        "Install nats-py and use NatsJetStreamPublisher for production."
    )

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
        "Outbox relay started: poll=%.1fs, batch=%d, nats=%s",
        poll_interval, batch_size, nats_url,
    )

    asyncio.create_task(relay.run())
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main():
    logger.info("Starting %s", SERVICE_NAME)
    server = await health_http_server()
    await _start_relay()

    while True:
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
