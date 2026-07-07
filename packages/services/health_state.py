"""Health state singleton for orchestrator-worker readiness (S-013).

Thread-safe: the async relay/consumer loops update state via set_* methods;
the sync health HTTP handler reads via to_dict().  A simple threading.Lock
guards writes so the handler never sees a partial update.

No FastAPI/Starlette dependency — works with the existing http.server.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field


@dataclass
class HealthState:
    """Readiness snapshot for orchestrator-worker.

    Updated by relay/consumer loops; read by health HTTP endpoint.
    """

    # --- Infrastructure readiness ---
    db_ok: bool = False
    nats_connected: bool = False

    # --- Component readiness ---
    publisher_ready: bool = False
    consumer_ready: bool = False

    # --- Relay observability ---
    relay_running: bool = False
    relay_published: int = 0
    relay_failed: int = 0
    relay_dead_letter: int = 0
    relay_last_poll_at: float | None = None
    relay_last_error: str | None = None

    # --- Consumer observability ---
    consumer_running: bool = False
    consumer_acked: int = 0
    consumer_nakd: int = 0
    consumer_terminated: int = 0
    consumer_errors: int = 0
    consumer_manifest_success: int = 0
    consumer_manifest_failed: int = 0
    consumer_manifest_skipped: int = 0

    # --- Service metadata ---
    service: str = "orchestrator-worker"
    started_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        """Return a JSON-serializable readiness snapshot."""
        return {
            "status": "ok" if (self.db_ok and self.nats_connected) else "degraded",
            "service": self.service,
            "uptime_seconds": round(time.time() - self.started_at, 1),
            "checks": {
                "database": "ok" if self.db_ok else "fail",
                "nats": "ok" if self.nats_connected else "fail",
                "publisher": "ready" if self.publisher_ready else "not_ready",
                "consumer": "ready" if self.consumer_ready else "not_ready",
            },
            "components": {
                "relay": {
                    "running": self.relay_running,
                    "published": self.relay_published,
                    "failed": self.relay_failed,
                    "dead_letter": self.relay_dead_letter,
                    "last_poll_at": self.relay_last_poll_at,
                    "last_error": self.relay_last_error,
                },
                "consumer": {
                    "running": self.consumer_running,
                    "acked": self.consumer_acked,
                    "nakd": self.consumer_nakd,
                    "terminated": self.consumer_terminated,
                    "errors": self.consumer_errors,
                    "manifest": {
                        "success": self.consumer_manifest_success,
                        "failed": self.consumer_manifest_failed,
                        "skipped": self.consumer_manifest_skipped,
                    },
                },
            },
        }


# ---------------------------------------------------------------------------
# Thread-safe singleton
# ---------------------------------------------------------------------------

_state = HealthState()
_lock = threading.Lock()


def get_health_state() -> HealthState:
    """Return current health state (read-only snapshot for HTTP handler)."""
    with _lock:
        return HealthState(
            db_ok=_state.db_ok,
            nats_connected=_state.nats_connected,
            publisher_ready=_state.publisher_ready,
            consumer_ready=_state.consumer_ready,
            relay_running=_state.relay_running,
            relay_published=_state.relay_published,
            relay_failed=_state.relay_failed,
            relay_dead_letter=_state.relay_dead_letter,
            relay_last_poll_at=_state.relay_last_poll_at,
            relay_last_error=_state.relay_last_error,
            consumer_running=_state.consumer_running,
            consumer_acked=_state.consumer_acked,
            consumer_nakd=_state.consumer_nakd,
            consumer_terminated=_state.consumer_terminated,
            consumer_errors=_state.consumer_errors,
            consumer_manifest_success=_state.consumer_manifest_success,
            consumer_manifest_failed=_state.consumer_manifest_failed,
            consumer_manifest_skipped=_state.consumer_manifest_skipped,
            service=_state.service,
            started_at=_state.started_at,
        )


def set_db_ok(ok: bool) -> None:
    with _lock:
        _state.db_ok = ok


def set_nats_connected(connected: bool) -> None:
    with _lock:
        _state.nats_connected = connected


def set_publisher_ready(ready: bool) -> None:
    with _lock:
        _state.publisher_ready = ready


def set_consumer_ready(ready: bool) -> None:
    with _lock:
        _state.consumer_ready = ready


def bump_relay_published() -> None:
    with _lock:
        _state.relay_published += 1
        _state.relay_last_poll_at = time.time()


def bump_relay_failed(error: str | None = None) -> None:
    with _lock:
        _state.relay_failed += 1
        if error:
            _state.relay_last_error = error


def bump_relay_dead_letter() -> None:
    with _lock:
        _state.relay_dead_letter += 1


def set_relay_running(running: bool) -> None:
    with _lock:
        _state.relay_running = running


def set_consumer_running(running: bool) -> None:
    with _lock:
        _state.consumer_running = running


def bump_consumer_acked() -> None:
    with _lock:
        _state.consumer_acked += 1


def bump_consumer_nakd() -> None:
    with _lock:
        _state.consumer_nakd += 1


def bump_consumer_terminated() -> None:
    with _lock:
        _state.consumer_terminated += 1


def bump_consumer_errors() -> None:
    with _lock:
        _state.consumer_errors += 1


def bump_manifest_success() -> None:
    with _lock:
        _state.consumer_manifest_success += 1


def bump_manifest_failed() -> None:
    with _lock:
        _state.consumer_manifest_failed += 1


def bump_manifest_skipped() -> None:
    with _lock:
        _state.consumer_manifest_skipped += 1
