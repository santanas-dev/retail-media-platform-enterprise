"""Prometheus-compatible metrics for Retail Media Platform.

Exposes counters and gauges in Prometheus exposition format
(text/plain; version=0.0.4) via the /metrics HTTP endpoint.

No third-party dependency — pure Python stdlib.
Counters are atomic integers safe for async context.
"""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Metric registry
# ---------------------------------------------------------------------------

@dataclass
class Metric:
    name: str
    type: str  # counter | gauge
    help: str
    labels: dict[str, str] = field(default_factory=dict)


_registry: dict[str, Metric] = {}
_counters: dict[str, int] = {}
_gauges: dict[str, float] = {}
_lock = threading.Lock()

_SERVICE = os.environ.get("RMP_SERVICE", "unknown")
_STARTED_AT = time.time()


def _register(metric: Metric) -> None:
    with _lock:
        _registry[metric.name] = metric
        if metric.type == "counter":
            _counters.setdefault(metric.name, 0)
        elif metric.type == "gauge":
            _gauges.setdefault(metric.name, 0.0)


def inc_counter(name: str, amount: int = 1) -> None:
    with _lock:
        _counters[name] = _counters.get(name, 0) + amount


def set_gauge(name: str, value: float) -> None:
    with _lock:
        _gauges[name] = value


# ---------------------------------------------------------------------------
# Service info (registered once at import)
# ---------------------------------------------------------------------------

_service_labels = {"service": _SERVICE}
_register(Metric("rmp_service_info", "gauge", "Service metadata", _service_labels))


# ---------------------------------------------------------------------------
# HTTP metrics (called from middleware)
# ---------------------------------------------------------------------------

_register(Metric("rmp_http_requests_total", "counter", "Total HTTP requests"))
_register(Metric("rmp_http_5xx_total", "counter", "HTTP 5xx responses"))


def record_http_request(status_code: int) -> None:
    inc_counter("rmp_http_requests_total")
    if 500 <= status_code < 600:
        inc_counter("rmp_http_5xx_total")


# ---------------------------------------------------------------------------
# Domain metrics (updated from HealthState or directly)
# ---------------------------------------------------------------------------

_domain_metrics = [
    ("rmp_outbox_published_total", "counter", "Outbox events published to NATS"),
    ("rmp_outbox_failed_total", "counter", "Outbox publish failures"),
    ("rmp_outbox_dead_letter_total", "counter", "Outbox dead-letter events"),
    ("rmp_nats_consumer_processed_total", "counter", "NATS consumer acked events"),
    ("rmp_nats_consumer_failed_total", "counter", "NATS consumer nakd + terminated"),
    ("rmp_nats_consumer_errors_total", "counter", "NATS consumer error count"),
    ("rmp_manifest_generated_total", "counter", "Manifests generated successfully"),
    ("rmp_manifest_generation_failed_total", "counter", "Manifest generation failures"),
    ("rmp_manifest_skipped_total", "counter", "Manifests skipped (no-op)"),
    ("rmp_pop_batches_total", "counter", "PoP batches ingested"),
    ("rmp_pop_events_accepted_total", "counter", "PoP events accepted (billing-grade)"),
    ("rmp_pop_events_quarantined_total", "counter", "PoP events quarantined"),
    ("rmp_creative_upload_completed_total", "counter", "Creative upload completions"),
    ("rmp_auth_login_failed_total", "counter", "Failed login attempts"),
    ("rmp_db_ready", "gauge", "Database readiness (1=ok, 0=fail)"),
    ("rmp_nats_ready", "gauge", "NATS readiness (1=ok, 0=fail)"),
    ("rmp_service_uptime_seconds", "gauge", "Service uptime in seconds"),
]

for _name, _type, _help in _domain_metrics:
    _register(Metric(_name, _type, _help))


# ---------------------------------------------------------------------------
# Sync from HealthState
# ---------------------------------------------------------------------------

def sync_from_health_state() -> None:
    """Pull counters from health_state into the Prometheus registry."""
    try:
        from packages.services.health_state import get_health_state

        state = get_health_state()
    except Exception:
        return

    set_gauge("rmp_db_ready", 1.0 if state.db_ok else 0.0)
    set_gauge("rmp_nats_ready", 1.0 if state.nats_connected else 0.0)
    set_gauge("rmp_service_uptime_seconds", time.time() - state.started_at)

    # relay
    if state.relay_published:
        _set_counter("rmp_outbox_published_total", state.relay_published)
    if state.relay_failed:
        _set_counter("rmp_outbox_failed_total", state.relay_failed)
    if state.relay_dead_letter:
        _set_counter("rmp_outbox_dead_letter_total", state.relay_dead_letter)

    # consumer
    consumer_processed = state.consumer_acked
    consumer_failed = state.consumer_nakd + state.consumer_terminated
    if consumer_processed:
        _set_counter("rmp_nats_consumer_processed_total", consumer_processed)
    if consumer_failed:
        _set_counter("rmp_nats_consumer_failed_total", consumer_failed)
    if state.consumer_errors:
        _set_counter("rmp_nats_consumer_errors_total", state.consumer_errors)

    # manifest
    if state.consumer_manifest_success:
        _set_counter("rmp_manifest_generated_total", state.consumer_manifest_success)
    if state.consumer_manifest_failed:
        _set_counter("rmp_manifest_generation_failed_total", state.consumer_manifest_failed)
    if state.consumer_manifest_skipped:
        _set_counter("rmp_manifest_skipped_total", state.consumer_manifest_skipped)


def _set_counter(name: str, value: int) -> None:
    with _lock:
        _counters[name] = value


# ---------------------------------------------------------------------------
# Prometheus text format renderer
# ---------------------------------------------------------------------------

def _escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def _format_labels(labels: dict[str, str]) -> str:
    if not labels:
        return ""
    parts = [f'{k}="{_escape(v)}"' for k, v in labels.items()]
    return "{" + ",".join(parts) + "}"


def render_metrics() -> str:
    """Render all registered metrics in Prometheus exposition format."""
    sync_from_health_state()

    # Uptime is always current
    set_gauge("rmp_service_uptime_seconds", time.time() - _STARTED_AT)

    lines: list[str] = []

    with _lock:
        for metric in sorted(_registry.values(), key=lambda m: m.name):
            lines.append(f"# HELP {metric.name} {metric.help}")
            lines.append(f"# TYPE {metric.name} {metric.type}")

            if metric.type == "counter":
                val = _counters.get(metric.name, 0)
                lines.append(f"{metric.name}{_format_labels(metric.labels)} {val}")
            elif metric.type == "gauge":
                val = _gauges.get(metric.name, 0.0)
                if isinstance(val, float) and val == int(val):
                    val = int(val)
                lines.append(f"{metric.name}{_format_labels(metric.labels)} {val}")

    lines.append("")
    return "\n".join(lines)
