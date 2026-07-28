"""Unit tests for KSO Player Client."""

import json
import os
import sys
import time
import uuid
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "apps", "kso-player-client"))

from player_client.config import load_config, PlayerConfig
from player_client.retry_backoff import (
    BackoffPolicy, RetryBackoffManager, RetryDecision,
    execute_with_retries, PlayerHttpError,
)
from player_client.http import PlayerHttpClient
from player_client.manifest import fetch_manifest, ManifestSnapshot, REQUIRED_FIELDS
from player_client.heartbeat import send_heartbeat, HeartbeatResult
from player_client.pop import send_pop_batch, PopSendResult


# ── Config ──

class TestConfig:
    def test_defaults(self):
        with patch.dict(os.environ, {"PLAYER_GATEWAY_URL": "http://test:8001"}, clear=True):
            cfg = load_config()
        assert cfg.base_url == "http://test:8001"
        assert cfg.signing_key == ""
        assert cfg.max_retries == 3

    def test_missing_url_dies(self, monkeypatch):
        monkeypatch.delenv("PLAYER_GATEWAY_URL", raising=False)
        monkeypatch.setenv("PLAYER_GATEWAY_URL", "")
        with pytest.raises(SystemExit):
            load_config()


# ── Retry/Backoff ──

class TestBackoff:
    def test_policy_validation(self):
        with pytest.raises(ValueError):
            BackoffPolicy(max_attempts=0)
        with pytest.raises(ValueError):
            BackoffPolicy(base_delay_sec=0)

    def test_compute_delay(self):
        policy = BackoffPolicy(base_delay_sec=1.0, jitter_ratio=0.0)
        mgr = RetryBackoffManager(policy)
        assert mgr.compute_delay(1) == 1.0
        assert mgr.compute_delay(2) == 2.0  # 1 * 2^1

    def test_classify_error_retryable(self):
        mgr = RetryBackoffManager(BackoffPolicy())
        retryable, _ = mgr.classify_error(ConnectionError("refused"))
        assert retryable
        retryable, _ = mgr.classify_error(PlayerHttpError(502, "bad gateway", retryable=True))
        assert retryable

    def test_classify_error_not_retryable(self):
        mgr = RetryBackoffManager(BackoffPolicy())
        retryable, _ = mgr.classify_error(ValueError("bad config"))
        assert not retryable
        retryable, _ = mgr.classify_error(PlayerHttpError(400, "bad request", retryable=False))
        assert not retryable

    def test_execute_with_retries_success(self):
        mgr = RetryBackoffManager(BackoffPolicy(max_attempts=3))
        calls = [0]

        def _op():
            calls[0] += 1
            if calls[0] < 3:
                raise ConnectionError("fail")
            return "ok"

        result = execute_with_retries(_op, mgr, sleep_fn=lambda _: None)
        assert result == "ok"
        assert calls[0] == 3

    def test_execute_with_retries_exhausted(self):
        mgr = RetryBackoffManager(BackoffPolicy(max_attempts=2))
        with pytest.raises(ConnectionError):
            execute_with_retries(lambda: (_ for _ in ()).throw(ConnectionError("fail")), mgr, sleep_fn=lambda _: None)

    def test_reason_redacted(self):
        mgr = RetryBackoffManager(BackoffPolicy())
        _, reason = mgr.classify_error(RuntimeError("leaked: access_token=xyz"))
        assert "access_token" not in reason
        assert "token" not in reason.lower()


# ── Manifest ──

VALID_MANIFEST = {
    "manifest_id": "m-1",
    "manifest_version": 1,
    "schema_version": "1.0",
    "device_id": "dev-1",
    "store_id": "s-1",
    "retailer_id": "r-1",
    "channel_type": "kso",
    "display_surfaces": [{"surface_id": "srf-1", "surface_code": "SURF-001"}],
    "playlist": [{
        "order": 0,
        "creative_asset_id": "ca-1",
        "media_type": "image/png",
        "sha256_checksum": "0" * 64,
        "duration_ms": 10000,
    }],
    "valid_from": None,
    "valid_to": None,
    "offline_ttl_hours": 168,
    "fallback_rules": {"on_manifest_expired": "show_fallback", "on_network_lost": "show_fallback"},
    "emergency": {"active": False, "activated_at": None, "reason": ""},
    "signature": {"algorithm": "HMAC-SHA256", "value": ""},
    "content_hash": "abc123",
}


def _mock_http(json_body, status=200):
    http = Mock(spec=PlayerHttpClient)
    http.base_url = "http://test"
    http.get_json.return_value = json_body
    return http


class TestManifest:
    def test_fetch_valid(self):
        http = _mock_http(VALID_MANIFEST)
        snap = fetch_manifest(http, "", max_retries=1)
        assert snap.manifest_id == "m-1"
        assert snap.verified is False

    def test_missing_required_field(self):
        bad = {**VALID_MANIFEST}
        del bad["manifest_id"]
        http = _mock_http(bad)
        with pytest.raises(ValueError, match="missing"):
            fetch_manifest(http, "", max_retries=1)

    def test_forbidden_key_rejected(self):
        bad = {**VALID_MANIFEST, "storage_bucket": "leak"}
        http = _mock_http(bad)
        with pytest.raises(ValueError, match="forbidden"):
            fetch_manifest(http, "", max_retries=1)

    def test_invalid_signature_detected(self):
        http = _mock_http(VALID_MANIFEST)
        with pytest.raises(ValueError, match="missing signature"):
            fetch_manifest(http, "some-key", max_retries=1)

    def test_signature_verified(self):
        from packages.contracts.manifest_signing import sign_manifest_payload
        payload = {**VALID_MANIFEST, "signature": {"algorithm": "HMAC-SHA256", "value": ""}}
        sig = sign_manifest_payload(payload, "test-key-32chars-minimum!!!!!")
        payload["signature"]["value"] = sig
        http = _mock_http(payload)
        snap = fetch_manifest(http, "test-key-32chars-minimum!!!!!", max_retries=1)
        assert snap.verified is True

    def test_emergency_flag(self):
        emerg = {**VALID_MANIFEST, "emergency": {"active": True, "activated_at": "2026-01-01T00:00:00Z", "reason": "test"}}
        http = _mock_http(emerg)
        snap = fetch_manifest(http, "", max_retries=1)
        assert snap.emergency_active is True


# ── Heartbeat ──

class TestHeartbeat:
    def test_success(self):
        http = Mock(spec=PlayerHttpClient)
        http.post_json.return_value = {"status": "accepted", "server_time": "2026-01-01T00:00:00Z"}
        result = send_heartbeat(http, max_retries=1)
        assert result.accepted is True

    def test_failure(self):
        http = Mock(spec=PlayerHttpClient)
        http.post_json.return_value = {"status": "error"}
        result = send_heartbeat(http, max_retries=1)
        assert result.accepted is False


# ── PoP ──

class TestPop:
    def test_success(self):
        http = Mock(spec=PlayerHttpClient)
        http.post_json.return_value = {
            "accepted_count": 1, "rejected_count": 0,
            "quarantined_count": 0, "duplicate_count": 0,
        }
        result = send_pop_batch(http, manifest_id="m-1", device_id="d-1",
                                 campaign_id="c-1", surface_id="s-1",
                                 creative_asset_id="ca-1", max_retries=1)
        assert result.accepted_count == 1
        assert result.accepted is True

    def test_rejected(self):
        http = Mock(spec=PlayerHttpClient)
        http.post_json.return_value = {
            "accepted_count": 0, "rejected_count": 1,
            "quarantined_count": 0, "duplicate_count": 0,
        }
        result = send_pop_batch(http, manifest_id="m-1", device_id="d-1",
                                 creative_asset_id="ca-1", max_retries=1)
        assert result.accepted is False
        assert result.rejected_count == 1
