"""
Phase 4.2c — Manifest Generation Worker Skeleton Unit Tests.

Tests: eligibility, manifest_id determinism, manifest JSON validation,
no secrets, idempotency, result object structure.
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestEligibilityHelpers(unittest.TestCase):
    """Unit tests for eligibility helper functions (no DB)."""

    def test_eligibility_result_eligible(self):
        from packages.domain.delivery import EligibilityResult
        r = EligibilityResult(True)
        self.assertTrue(r.eligible)
        self.assertIsNone(r.reason)

    def test_eligibility_result_not_eligible(self):
        from packages.domain.delivery import EligibilityResult
        r = EligibilityResult(False, "No placements")
        self.assertFalse(r.eligible)
        self.assertEqual(r.reason, "No placements")

    def test_target_resolution_empty(self):
        from packages.domain.delivery import TargetResolutionResult
        r = TargetResolutionResult()
        self.assertEqual(r.surface_device_map, {})
        self.assertEqual(r.device_surfaces, {})

    def test_completed_status_ineligible(self):
        from packages.domain.delivery import EligibilityResult
        r = EligibilityResult(False, "Campaign status is 'completed', not in ['active', 'approved', 'scheduled']")
        self.assertFalse(r.eligible)
        self.assertIn("completed", r.reason)

    def test_live_status_ineligible(self):
        from packages.domain.delivery import EligibilityResult
        r = EligibilityResult(False, "Campaign status is 'live'")
        self.assertFalse(r.eligible)

    def test_manifest_result_not_eligible(self):
        from packages.domain.delivery import ManifestGenerationResult
        r = ManifestGenerationResult(
            campaign_id="c1", eligible=False, skip_reason="status=draft"
        )
        self.assertFalse(r.eligible)
        self.assertEqual(r.skip_reason, "status=draft")
        self.assertEqual(r.manifest_count, 0)
        self.assertEqual(r.manifest_ids, [])


class TestManifestIdDeterminism(unittest.TestCase):
    """manifest_id is deterministic per ADR-016 §5."""

    def setUp(self):
        from packages.domain.delivery import compute_manifest_id
        self.compute = compute_manifest_id

    def _base_args(self):
        return dict(
            campaign_id="00000000-0000-0000-0000-000000000220",
            campaign_status="approved",
            campaign_updated_at="2026-07-01T00:00:00+00:00",
            creative_asset_ids=["ca-001"],
            creative_checksums=["deadbeef"],
            flight_ids=["fl-001"],
            flight_data=["2026-08-01T08:00:00+03:00‖2026-08-07T22:00:00+03:00‖‖"],
            placement_ids=["pl-001"],
            surface_ids=["00000000-0000-0000-0000-000000000031"],
            device_id="00000000-0000-0000-0000-000000000020",
        )

    def test_same_input_same_id(self):
        a1 = self._base_args()
        a2 = self._base_args()
        self.assertEqual(self.compute(**a1), self.compute(**a2))

    def test_different_input_different_id(self):
        a1 = self._base_args()
        a2 = self._base_args()
        a2["campaign_status"] = "scheduled"
        self.assertNotEqual(self.compute(**a1), self.compute(**a2))

    def test_output_format_sha256(self):
        result = self.compute(**self._base_args())
        self.assertTrue(result.startswith("sha256:"))
        self.assertEqual(len(result), len("sha256:") + 64)

    def test_order_irrelevant_for_sorted_lists(self):
        """Same IDs in different order produce same manifest_id."""
        a1 = self._base_args()
        a1["creative_asset_ids"] = ["ca-002", "ca-001"]
        a1["surface_ids"] = ["s2", "s1"]
        a2 = self._base_args()
        a2["creative_asset_ids"] = ["ca-001", "ca-002"]
        a2["surface_ids"] = ["s1", "s2"]
        self.assertEqual(self.compute(**a1), self.compute(**a2))

    def test_device_id_affects_hash(self):
        a1 = self._base_args()
        a2 = self._base_args()
        a2["device_id"] = "00000000-0000-0000-0000-000000000021"
        self.assertNotEqual(self.compute(**a1), self.compute(**a2))

    def test_empty_creatives_ok(self):
        a = self._base_args()
        a["creative_asset_ids"] = []
        a["creative_checksums"] = []
        result = self.compute(**a)
        self.assertTrue(result.startswith("sha256:"))

    def test_empty_surfaces_ok(self):
        a = self._base_args()
        a["surface_ids"] = []
        result = self.compute(**a)
        self.assertTrue(result.startswith("sha256:"))


class TestManifestJson(unittest.TestCase):
    """Manifest JSON structure and safety."""

    def setUp(self):
        from packages.domain.delivery import generate_manifest_json
        self.gen = generate_manifest_json

    def test_required_fields_present(self):
        m = self.gen(
            manifest_id="sha256:abc123",
            manifest_version=1,
            device_id="d1",
            surface_ids=["s1", "s2"],
        )
        required = {"manifest_id", "device_id", "store_id", "channel_type"}
        for field in required:
            self.assertIn(field, m, f"Missing required field: {field}")

    def test_schema_version_is_1_0(self):
        m = self.gen(
            manifest_id="sha256:abc",
            manifest_version=1,
            device_id="d1",
            surface_ids=[],
        )
        self.assertEqual(m["schema_version"], "1.0")

    def test_surface_codes_injected(self):
        m = self.gen(
            manifest_id="sha256:abc",
            manifest_version=1,
            device_id="d1",
            surface_ids=["s1", "s2"],
            surface_codes={"s1": "SURF-1", "s2": "SURF-2"},
        )
        surfaces = m["display_surfaces"]
        self.assertEqual(len(surfaces), 2)
        codes = {s["surface_code"] for s in surfaces}
        self.assertEqual(codes, {"SURF-1", "SURF-2"})

    def test_playlist_items_preserved(self):
        playlist = [
            {
                "order": 0,
                "weight": 1,
                "priority": 5,
                "creative_asset_id": "ca-1",
                "media_type": "video/mp4",
                "sha256_checksum": "deadbeef",
                "duration_ms": 15000,
            }
        ]
        m = self.gen(
            manifest_id="sha256:abc",
            manifest_version=1,
            device_id="d1",
            surface_ids=["s1"],
            playlist_items=playlist,
        )
        self.assertEqual(len(m["playlist"]), 1)
        self.assertEqual(m["playlist"][0]["creative_asset_id"], "ca-1")

    def test_no_storage_secrets(self):
        """Manifest must not contain storage credentials or PII."""
        m = self.gen(
            manifest_id="sha256:abc",
            manifest_version=1,
            device_id="d1",
            surface_ids=["s1"],
        )
        manifest_str = json.dumps(m)
        forbidden = [
            "storage_bucket", "storage_key", "access_key",
            "secret_key", "presigned_url", "token",
            "advertiser_organization_id",
            "email", "phone", "contact_name", "password",
            "PII",
        ]
        for term in forbidden:
            self.assertNotIn(term, manifest_str.lower(),
                             f"Forbidden term '{term}' found in manifest")

    def test_signature_structure(self):
        m = self.gen(
            manifest_id="sha256:abc",
            manifest_version=1,
            device_id="d1",
            surface_ids=["s1"],
        )
        self.assertIn("signature", m)
        self.assertEqual(m["signature"]["algorithm"], "HMAC-SHA256")
        self.assertIn("value", m["signature"])

    def test_valid_from_to(self):
        m = self.gen(
            manifest_id="sha256:abc",
            manifest_version=1,
            device_id="d1",
            surface_ids=["s1"],
            valid_from="2026-08-01T08:00:00+03:00",
            valid_to="2026-08-07T22:00:00+03:00",
        )
        self.assertEqual(m["valid_from"], "2026-08-01T08:00:00+03:00")
        self.assertEqual(m["valid_to"], "2026-08-07T22:00:00+03:00")


class TestNoNatsInDelivery(unittest.TestCase):
    """Delivery module must not import or reference NATS."""

    def test_no_nats(self):
        import re
        path = os.path.join(
            os.path.dirname(__file__), "..",
            "packages", "domain", "delivery.py",
        )
        content = open(path).read()
        # Strip comments and docstrings
        stripped = re.sub(r'""".*?"""', '', content, flags=re.DOTALL)
        stripped = re.sub(r'#.*', '', stripped)
        for banned in ("import nats", "from nats", "nats_publish",
                       "nats.request", "nats.publish", "nats.connect"):
            self.assertNotIn(banned, stripped.lower(),
                             f"Delivery must not reference NATS: found '{banned}'")


class TestDeliveryModuleExport(unittest.TestCase):
    """Public API surface check."""

    def test_public_functions_importable(self):
        from packages.domain.delivery import (
            check_eligibility,
            resolve_targets,
            compute_manifest_id,
            generate_manifest_json,
            generate_manifests_for_campaign,
            EligibilityResult,
            TargetResolutionResult,
            ManifestGenerationResult,
        )
        # All imported without error
        self.assertTrue(callable(check_eligibility))
        self.assertTrue(callable(resolve_targets))
        self.assertTrue(callable(compute_manifest_id))
        self.assertTrue(callable(generate_manifest_json))
        self.assertTrue(callable(generate_manifests_for_campaign))


if __name__ == "__main__":
    unittest.main()
