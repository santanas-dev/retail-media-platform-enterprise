"""
K2 — Manifest Signature Verification Before Player Execution.

Unit tests for contracts/manifest_signing.py and runtime/simulator.py verification.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from packages.contracts.manifest_signing import (
    canonical_json,
    sign_manifest_payload,
    verify_manifest_signature,
)
from packages.runtime.simulator import (
    RuntimeSimulator,
    make_test_manifest,
)


TEST_KEY = "test-manifest-signing-key-min-32-chars!!"
TEST_KEY_ALT = "alt-manifest-signing-key-min-32-chars!!"
TEST_DEVICE_ID = "dev-00000000-0000-0000-0000-000000000001"


def _signed_manifest(**overrides) -> dict:
    """Build a valid manifest signed with TEST_KEY."""
    m = make_test_manifest(device_id=TEST_DEVICE_ID, **overrides)
    # Remove default empty signature, sign properly
    sig = sign_manifest_payload(m, TEST_KEY)
    m["signature"] = {"algorithm": "HMAC-SHA256", "value": sig}
    return m


def _unsigned_manifest(**overrides) -> dict:
    """Build a valid manifest with empty signature (dev mode)."""
    return make_test_manifest(device_id=TEST_DEVICE_ID, **overrides)


# ═══════════════════════════════════════════════════════════════════
# Contracts: canonical_json, sign_manifest_payload, verify_manifest_signature
# ═══════════════════════════════════════════════════════════════════


class TestCanonicalJson(unittest.TestCase):
    """canonical_json() produces deterministic, sorted, compact output."""

    def test_sorted_keys(self):
        a = canonical_json({"z": 1, "a": 2})
        self.assertTrue(a.startswith('{"a":2'))

    def test_excludes_signature(self):
        payload = {"manifest_id": "m1", "signature": {"value": "xyz"}}
        result = canonical_json(payload)
        self.assertNotIn("signature", result)
        self.assertIn("manifest_id", result)

    def test_compact_no_spaces(self):
        result = canonical_json({"a": 1, "b": "hello"})
        self.assertNotIn(" ", result)
        self.assertNotIn("\n", result)

    def test_deterministic(self):
        a = canonical_json({"c": "v", "b": 1, "a": True})
        b = canonical_json({"a": True, "b": 1, "c": "v"})
        self.assertEqual(a, b)


class TestSignAndVerify(unittest.TestCase):

    def test_sign_produces_hex_digest(self):
        m = _unsigned_manifest()
        sig = sign_manifest_payload(m, TEST_KEY)
        self.assertEqual(len(sig), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in sig))

    def test_verify_valid_signature(self):
        m = _unsigned_manifest()
        sig = sign_manifest_payload(m, TEST_KEY)
        self.assertTrue(verify_manifest_signature(m, sig, TEST_KEY))

    def test_verify_wrong_key(self):
        m = _unsigned_manifest()
        sig = sign_manifest_payload(m, TEST_KEY)
        self.assertFalse(verify_manifest_signature(m, sig, TEST_KEY_ALT))

    def test_verify_wrong_signature(self):
        m = _unsigned_manifest()
        self.assertFalse(verify_manifest_signature(m, "00" * 32, TEST_KEY))

    def test_verify_empty_signature(self):
        m = _unsigned_manifest()
        self.assertFalse(verify_manifest_signature(m, "", TEST_KEY))

    def test_sign_deterministic(self):
        m = _unsigned_manifest()
        sig1 = sign_manifest_payload(m, TEST_KEY)
        sig2 = sign_manifest_payload(m, TEST_KEY)
        self.assertEqual(sig1, sig2)

    def test_signature_changes_on_tampered_payload(self):
        m = _unsigned_manifest()
        sig1 = sign_manifest_payload(m, TEST_KEY)
        m["retailer_id"] = "tampered-retailer"
        sig2 = sign_manifest_payload(m, TEST_KEY)
        self.assertNotEqual(sig1, sig2)


# ═══════════════════════════════════════════════════════════════════
# Runtime Simulator: real signature verification (K2)
# ═══════════════════════════════════════════════════════════════════


class TestSignedManifestAccepted(unittest.TestCase):
    """Valid signed manifest is accepted when signing_key is configured."""

    def setUp(self):
        self.sim = RuntimeSimulator(
            device_id=TEST_DEVICE_ID,
            signing_key=TEST_KEY,
        )

    def test_valid_signed_manifest_accepted(self):
        m = _signed_manifest()
        result = self.sim.apply_manifest(m)
        self.assertTrue(result.success, f"Expected success, got: {result.failure_reason}")
        self.assertEqual(self.sim.current_manifest, m)

    def test_unsigned_manifest_rejected_when_key_configured(self):
        m = _unsigned_manifest()
        result = self.sim.apply_manifest(m)
        self.assertFalse(result.success)
        self.assertIn("missing", result.failure_reason.lower())
        self.assertIsNone(self.sim.current_manifest)

    def test_wrong_signature_rejected(self):
        m = _unsigned_manifest()
        m["signature"] = {"algorithm": "HMAC-SHA256", "value": "00" * 32}
        result = self.sim.apply_manifest(m)
        self.assertFalse(result.success)
        self.assertIn("verification failed", result.failure_reason.lower())

    def test_wrong_key_signature_rejected(self):
        m = _unsigned_manifest()
        sig = sign_manifest_payload(m, TEST_KEY_ALT)
        m["signature"] = {"algorithm": "HMAC-SHA256", "value": sig}
        result = self.sim.apply_manifest(m)
        self.assertFalse(result.success)
        self.assertIn("verification failed", result.failure_reason.lower())

    def test_unsupported_algorithm_rejected(self):
        m = _unsigned_manifest()
        m["signature"] = {"algorithm": "RSA-SHA256", "value": "00" * 32}
        result = self.sim.apply_manifest(m)
        self.assertFalse(result.success)
        self.assertIn("Unsupported", result.failure_reason)


class TestTamperedManifestRejected(unittest.TestCase):
    """Tampering any signed field after signing is rejected."""

    def setUp(self):
        self.sim = RuntimeSimulator(
            device_id=TEST_DEVICE_ID,
            signing_key=TEST_KEY,
        )

    def _apply_tampered(self, tampered: dict) -> bool:
        result = self.sim.apply_manifest(tampered)
        return result.success

    def test_tampered_retailer_id_rejected(self):
        m = _signed_manifest()
        m["retailer_id"] = "evil-retailer"
        self.assertFalse(self._apply_tampered(m))

    def test_tampered_playlist_rejected(self):
        m = _signed_manifest()
        m["playlist"] = [{"creative_asset_id": "evil", "media_type": "image"}]
        self.assertFalse(self._apply_tampered(m))

    def test_tampered_emergency_rejected(self):
        m = _signed_manifest()
        m["emergency"] = {"active": True, "activated_at": "now", "reason": "evil"}
        self.assertFalse(self._apply_tampered(m))

    def test_tampered_content_hash_rejected(self):
        m = _signed_manifest()
        m["content_hash"] = "sha256:evilhash"
        self.assertFalse(self._apply_tampered(m))

    def test_tampered_device_id_rejected(self):
        m = _signed_manifest()
        m["device_id"] = "other-device"
        self.assertFalse(self._apply_tampered(m))

    def test_tampered_manifest_version_rejected(self):
        m = _signed_manifest()
        m["manifest_version"] = 9999
        self.assertFalse(self._apply_tampered(m))


class TestTamperingBeforeApply(unittest.TestCase):
    """Prove: tampered manifest is rejected BEFORE any side effect (apply/play)."""

    def setUp(self):
        self.sim = RuntimeSimulator(
            device_id=TEST_DEVICE_ID,
            signing_key=TEST_KEY,
        )

    def test_tampered_manifest_preserves_last_known_good(self):
        # Apply a valid signed manifest first
        m1 = _signed_manifest(manifest_version=1, manifest_id="m1")
        result1 = self.sim.apply_manifest(m1)
        self.assertTrue(result1.success)

        # Tamper manifest_id post-signing
        m2 = _signed_manifest(manifest_version=2, manifest_id="m2")
        m2["playlist"] = [{"creative_asset_id": "evil-after-signing"}]
        result2 = self.sim.apply_manifest(m2)
        self.assertFalse(result2.success)

        # Current manifest should STILL be m1 (last known good preserved)
        self.assertIsNotNone(self.sim.current_manifest)
        self.assertEqual(self.sim.current_manifest["manifest_id"], "m1")

    def test_no_playback_after_signature_failure(self):
        m = _signed_manifest()
        m["retailer_id"] = "tampered"
        result = self.sim.apply_manifest(m)
        self.assertFalse(result.success)
        self.assertFalse(self.sim.playback_active)


class TestBackwardCompatUnsignedManifest(unittest.TestCase):
    """When signing_key is NOT configured, unsigned manifests are accepted (dev mode)."""

    def setUp(self):
        self.sim = RuntimeSimulator(device_id=TEST_DEVICE_ID)  # no signing_key

    def test_unsigned_manifest_accepted(self):
        m = _unsigned_manifest()
        result = self.sim.apply_manifest(m)
        self.assertTrue(result.success)

    def test_magic_invalid_still_rejected(self):
        m = _unsigned_manifest()
        m["signature"] = {"algorithm": "HMAC-SHA256", "value": "INVALID"}
        result = self.sim.apply_manifest(m)
        self.assertFalse(result.success)
        self.assertIn("verification failed", result.failure_reason.lower())


class TestMissingSignatureBlock(unittest.TestCase):
    """Missing signature block handling."""

    def setUp(self):
        self.sim = RuntimeSimulator(
            device_id=TEST_DEVICE_ID,
            signing_key=TEST_KEY,
        )

    def test_no_signature_key_rejected(self):
        m = _unsigned_manifest()
        del m["signature"]
        result = self.sim.apply_manifest(m)
        # Missing signature block → sig_value is empty → rejected
        self.assertFalse(result.success)
