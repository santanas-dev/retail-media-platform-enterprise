"""KSO Player Client — manifest fetch and verification."""

import json
import sys
from dataclasses import dataclass, field
from typing import Any, Optional

sys.path.insert(0, "")

from packages.contracts.manifest_signing import verify_manifest_signature

from .http import PlayerHttpClient
from .retry_backoff import BackoffPolicy, RetryBackoffManager, execute_with_retries

# ── Required manifest fields per manifest_v1.schema.json ──
REQUIRED_FIELDS = {"manifest_id", "device_id", "playlist", "signature", "emergency"}
FORBIDDEN_TERMS = ["storage_bucket", "storage_key", "access_key", "secret_key", "presigned_url", "token", "email", "phone", "password"]


@dataclass
class ManifestSnapshot:
    raw: dict[str, Any] = field(default_factory=dict)
    verified: bool = False

    @property
    def manifest_id(self) -> str:
        return str(self.raw.get("manifest_id", ""))

    @property
    def device_id(self) -> str:
        return str(self.raw.get("device_id", ""))

    @property
    def playlist(self) -> list[dict[str, Any]]:
        return list(self.raw.get("playlist", []))

    @property
    def emergency_active(self) -> bool:
        return bool(self.raw.get("emergency", {}).get("active", False))

    @property
    def signature(self) -> dict[str, Any]:
        return dict(self.raw.get("signature", {}))


def fetch_manifest(http: PlayerHttpClient, signing_key: str, max_retries: int = 3) -> ManifestSnapshot:
    policy = BackoffPolicy(max_attempts=max_retries, base_delay_sec=1.0)
    manager = RetryBackoffManager(policy)

    raw = execute_with_retries(
        lambda: http.get_json("/api/v1/device/manifest/latest"),
        manager,
    )

    _validate_shape(raw)
    _validate_forbidden(raw)

    sig = raw.get("signature", {})
    sig_val = sig.get("value", "")
    sig_algo = sig.get("algorithm", "")

    if sig_val == "INVALID":
        raise ValueError("manifest signature is INVALID placeholder")

    if signing_key:
        if not sig_val:
            raise ValueError("manifest missing signature (signing_key configured)")
        if sig_algo != "HMAC-SHA256":
            raise ValueError(f"unsupported signature algorithm: {sig_algo}")
        if not verify_manifest_signature(raw, sig_val, signing_key):
            raise ValueError("manifest signature verification failed")

    return ManifestSnapshot(raw=raw, verified=bool(signing_key))


def _validate_shape(data: dict[str, Any]) -> None:
    missing = REQUIRED_FIELDS - set(data.keys())
    if missing:
        raise ValueError(f"manifest missing fields: {', '.join(sorted(missing))}")


def _validate_forbidden(data: dict[str, Any]) -> None:
    body = json.dumps(data).lower()
    for term in FORBIDDEN_TERMS:
        if term in body:
            raise ValueError(f"manifest contains forbidden term: {term}")
