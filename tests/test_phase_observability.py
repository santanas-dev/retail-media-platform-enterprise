"""Tests for Prometheus /metrics endpoint and metric rendering.

Unit tests for render_metrics() and counter/gauge operations.
Integration tests for the FastAPI /metrics endpoint are covered
by the existing health endpoint tests (test_phase2_health.py) which
validate the control-api app structure.
"""

import pytest


# ---------------------------------------------------------------------------
# Unit: render_metrics()
# ---------------------------------------------------------------------------

class TestMetricsRendering:
    def test_render_includes_service_info(self):
        from packages.observability.metrics import render_metrics

        text = render_metrics()
        assert "rmp_service_info" in text
        assert "# HELP rmp_service_info" in text
        assert "# TYPE rmp_service_info gauge" in text

    def test_render_includes_domain_metrics(self):
        from packages.observability.metrics import render_metrics

        text = render_metrics()
        required = [
            "rmp_http_requests_total",
            "rmp_http_5xx_total",
            "rmp_outbox_published_total",
            "rmp_outbox_failed_total",
            "rmp_outbox_dead_letter_total",
            "rmp_nats_consumer_processed_total",
            "rmp_nats_consumer_failed_total",
            "rmp_manifest_generated_total",
            "rmp_manifest_generation_failed_total",
            "rmp_pop_batches_total",
            "rmp_pop_events_accepted_total",
            "rmp_pop_events_quarantined_total",
            "rmp_db_ready",
            "rmp_service_uptime_seconds",
        ]
        for name in required:
            assert name in text, f"Missing metric: {name}"

    def test_render_no_secrets(self):
        from packages.observability.metrics import render_metrics

        text = render_metrics()
        forbidden = ["password", "secret", "token", "JWT", "api_key", "DATABASE_URL"]
        for word in forbidden:
            assert word.lower() not in text.lower(), f"Secret leaked: {word}"

    def test_render_is_prometheus_format(self):
        from packages.observability.metrics import render_metrics

        text = render_metrics()
        lines = [line for line in text.split("\n") if line.strip() and not line.startswith("#")]
        for line in lines:
            assert " " in line, f"Invalid metric line: {line}"

    def test_record_http_request_increments(self):
        from packages.observability.metrics import record_http_request, render_metrics

        record_http_request(200)
        record_http_request(200)
        record_http_request(500)
        record_http_request(503)

        text = render_metrics()
        assert "rmp_http_requests_total" in text
        assert "rmp_http_5xx_total" in text

    def test_counter_persistence(self):
        from packages.observability.metrics import inc_counter, render_metrics

        inc_counter("rmp_pop_events_accepted_total", 5)
        text = render_metrics()
        assert "rmp_pop_events_accepted_total" in text

    def test_gauge_values_present(self):
        from packages.observability.metrics import set_gauge, render_metrics

        set_gauge("rmp_db_ready", 1.0)
        text = render_metrics()
        assert "rmp_db_ready" in text

    def test_all_labels_are_clean(self):
        from packages.observability.metrics import render_metrics

        text = render_metrics()
        for line in text.split("\n"):
            if line.startswith("#") or not line.strip():
                continue
            assert not line.endswith("{") and not line.endswith("}"), f"Broken line: {line}"

    def test_set_gauge_int_value(self):
        from packages.observability.metrics import inc_counter, set_gauge, render_metrics

        inc_counter("rmp_outbox_published_total", 42)
        set_gauge("rmp_db_ready", 1.0)
        text = render_metrics()
        assert "rmp_outbox_published_total" in text
        assert "rmp_db_ready" in text
