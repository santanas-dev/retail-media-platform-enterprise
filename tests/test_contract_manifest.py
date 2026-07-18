"""
S-018 — Manifest contract tests.

Proves:
- generated manifest validates against manifest_v1.schema.json
- schema rejects manifest containing storage_bucket/storage_key
- malformed manifest without required fields is rejected
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from packages.domain.delivery import generate_manifest_json


def _load_schema():
    schema_path = os.path.join(
        os.path.dirname(__file__),
        "..", "packages", "contracts", "manifest_v1.schema.json",
    )
    with open(schema_path) as f:
        return json.load(f)


SCHEMA = _load_schema()

# Sample playlist item matching actual delivery.py output
SAMPLE_PLAYLIST_ITEM = {
    "order": 0,
    "weight": 1,
    "priority": 1,
    "creative_asset_id": "00000000-0000-0000-0000-000000000222",
    "media_type": "image/png",
    "sha256_checksum": "ff61a0ae3ab5b1aa2c5f2eaac78b4addd8d7a1d72b22d79fbc8e27e74cb3d4f0",
    "duration_ms": 15000,
    "start_time": None,
    "days_of_week": None,
}


def _make_manifest(**overrides):
    """Build a minimal valid manifest dict with defaults."""
    base = {
        "manifest_id": "test-manifest-001",
        "manifest_version": 1,
        "schema_version": "1.0",
        "device_id": "00000000-0000-0000-0000-000000000020",
        "device_code": "KSO-001",
        "store_id": "00000000-0000-0000-0000-000000000003",
        "store_code": "STORE-001",
        "channel_type": "kso",
        "device_type": "KSO_SHERMAN_J51",
        "valid_from": "2026-01-01T00:00:00Z",
        "valid_to": "2026-12-31T23:59:59Z",
        "offline_ttl_hours": 168,
        "display_surfaces": [
            {"surface_id": "00000000-0000-0000-0000-000000000031", "surface_code": "SURF-001"}
        ],
        "playlist": [SAMPLE_PLAYLIST_ITEM],
        "media_files": [],
        "adapter_payload": {},
        "fallback_rules": {
            "on_manifest_expired": "show_fallback",
            "on_network_lost": "continue_last_valid",
            "filler_media_ids": [],
            "emit_pop": False,
        },
        "signature": {
            "algorithm": "HMAC-SHA256",
            "value": "",
        },
        "emergency": {
            "active": False,
            "activated_at": None,
            "reason": "",
        },
        "retailer_id": "ret-001",
    }
    base.update(overrides)
    return base


class TestManifestSchemaValidation(unittest.TestCase):
    """Prove: generated manifest and hand-crafted manifests validate or reject correctly."""

    def setUp(self):
        self.validator = __import__("jsonschema").validate

    def test_generated_manifest_validates(self):
        """generate_manifest_json output passes schema validation."""
        manifest = generate_manifest_json(
            manifest_id="test-gen-001",
            manifest_version=1,
            device_id="dev-1",
            device_code="DEV-001",
            store_id="store-1",
            store_code="STORE-001",
            channel_type="kso",
            device_type="KSO_SHERMAN_J51",
            surface_ids=["surf-1", "surf-2"],
            surface_codes={"surf-1": "S-001", "surf-2": "S-002"},
            playlist_items=[SAMPLE_PLAYLIST_ITEM],
            valid_from="2026-01-01T00:00:00Z",
            valid_to="2026-12-31T23:59:59Z",
        )
        self.validator(instance=manifest, schema=SCHEMA)

    def test_minimal_valid_manifest_passes(self):
        manifest = _make_manifest()
        self.validator(instance=manifest, schema=SCHEMA)

    def test_rejects_storage_bucket(self):
        manifest = _make_manifest()
        manifest["storage_bucket"] = "bucket-1"
        with self.assertRaises(Exception):
            self.validator(instance=manifest, schema=SCHEMA)

    def test_rejects_storage_key(self):
        manifest = _make_manifest()
        manifest["storage_key"] = "org/asset/file.png"
        with self.assertRaises(Exception):
            self.validator(instance=manifest, schema=SCHEMA)

    def test_rejects_missing_manifest_id(self):
        manifest = _make_manifest()
        del manifest["manifest_id"]
        with self.assertRaises(Exception):
            self.validator(instance=manifest, schema=SCHEMA)

    def test_rejects_missing_display_surfaces(self):
        manifest = _make_manifest()
        del manifest["display_surfaces"]
        with self.assertRaises(Exception):
            self.validator(instance=manifest, schema=SCHEMA)

    def test_rejects_missing_playlist(self):
        manifest = _make_manifest()
        del manifest["playlist"]
        with self.assertRaises(Exception):
            self.validator(instance=manifest, schema=SCHEMA)

    def test_rejects_missing_fallback_rules(self):
        manifest = _make_manifest()
        del manifest["fallback_rules"]
        with self.assertRaises(Exception):
            self.validator(instance=manifest, schema=SCHEMA)

    def test_rejects_playlist_without_required_fields(self):
        manifest = _make_manifest()
        manifest["playlist"] = [{"order": 1}]  # missing creative_asset_id etc.
        with self.assertRaises(Exception):
            self.validator(instance=manifest, schema=SCHEMA)

    def test_rejects_display_surface_missing_surface_code(self):
        manifest = _make_manifest()
        manifest["display_surfaces"] = [{"surface_id": "sid"}]
        with self.assertRaises(Exception):
            self.validator(instance=manifest, schema=SCHEMA)

    def test_null_valid_from_is_allowed(self):
        manifest = _make_manifest(valid_from=None)
        self.validator(instance=manifest, schema=SCHEMA)

    def test_null_valid_to_is_allowed(self):
        manifest = _make_manifest(valid_to=None)
        self.validator(instance=manifest, schema=SCHEMA)

    def test_manifest_version_zero_rejected(self):
        manifest = _make_manifest(manifest_version=0)
        with self.assertRaises(Exception):
            self.validator(instance=manifest, schema=SCHEMA)

    def test_playlist_items_optional_fields(self):
        """Playlist items with only required fields pass."""
        manifest = _make_manifest()
        manifest["playlist"] = [{
            "creative_asset_id": "ca-1",
            "media_type": "image/png",
            "sha256_checksum": "a" * 64,
            "duration_ms": 5000,
        }]
        self.validator(instance=manifest, schema=SCHEMA)

    def test_schema_has_no_forbidden_storage_fields(self):
        """Schema does not list storage_bucket/storage_key as declared properties."""
        self.assertNotIn("storage_bucket", SCHEMA.get("properties", {}))
        self.assertNotIn("storage_key", SCHEMA.get("properties", {}))

    def test_rejects_missing_retailer_id(self):
        manifest = _make_manifest()
        del manifest["retailer_id"]
        with self.assertRaises(Exception):
            self.validator(instance=manifest, schema=SCHEMA)

    def test_rejects_missing_emergency(self):
        manifest = _make_manifest()
        del manifest["emergency"]
        with self.assertRaises(Exception):
            self.validator(instance=manifest, schema=SCHEMA)


if __name__ == "__main__":
    unittest.main()
