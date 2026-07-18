"""
Manifest signing and verification — contracts-layer utilities.

Neutral layer: both backend (domain) and runtime (simulator/player) import from here.
No FastAPI, no database, no security-config dependency.

Algorithm: HMAC-SHA256 over canonical JSON (sorted keys, compact separators).
Signature key excluded from signed payload to avoid circular dependency.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any


def canonical_json(payload: dict[str, Any]) -> str:
    """Serialize a manifest payload dict to canonical JSON for deterministic signing.

    Sorted keys, compact separators — no whitespace.
    Excludes the ``signature`` key from output.
    """
    signable = {k: v for k, v in payload.items() if k != "signature"}
    return json.dumps(signable, sort_keys=True, separators=(",", ":"))


def sign_manifest_payload(payload: dict[str, Any], key: str) -> str:
    """HMAC-SHA256 sign a manifest payload dict.

    Returns hex-encoded HMAC digest.
    """
    canonical = canonical_json(payload)
    mac = hmac.new(key.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256)
    return mac.hexdigest()


def verify_manifest_signature(
    payload: dict[str, Any],
    signature: str,
    key: str,
) -> bool:
    """Verify HMAC-SHA256 signature of a manifest payload.

    Constant-time comparison via ``hmac.compare_digest``.
    """
    expected = sign_manifest_payload(payload, key)
    return hmac.compare_digest(expected, signature)
