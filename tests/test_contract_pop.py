"""
S-018 — Proof-event contract tests.

Proves:
- simulator PoP validates against proof_event_v1.schema.json
- simulator PoP validates against PopEventIn (Pydantic DTO)
- malformed PoP without playback_result is rejected
- malformed PoP with unknown playback_result is rejected
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from packages.domain.schemas import PopEventIn
from packages.runtime.simulator import RuntimeSimulator


def _load_schema():
    schema_path = os.path.join(
        os.path.dirname(__file__),
        "..", "packages", "contracts", "proof_event_v1.schema.json",
    )
    with open(schema_path) as f:
        return json.load(f)


SCHEMA = _load_schema()

TEST_DEVICE_ID = "00000000-0000-0000-0000-000000000020"
TEST_CAMPAIGN_ID = "00000000-0000-0000-0000-000000000220"
TEST_SURFACE_ID = "00000000-0000-0000-0000-000000000031"


def _m(
    manifest_id="m-001",
    valid_from="2024-01-01T00:00:00Z",
    valid_to="2030-12-31T23:59:59Z",
):
    """Minimal valid manifest for simulator consumption."""
    return {
        "manifest_id": manifest_id,
        "manifest_version": 1,
        "schema_version": "1.0",
        "device_id": TEST_DEVICE_ID,
        "device_code": "KSO-001",
        "store_id": "store-1",
        "store_code": "STORE-001",
        "channel_type": "kso",
        "device_type": "KSO_SHERMAN_J51",
        "display_surfaces": [
            {"surface_id": TEST_SURFACE_ID, "surface_code": "SURF-001"}
        ],
        "playlist": [
            {
                "creative_asset_id": "ca-1",
                "media_type": "image/png",
                "sha256_checksum": "a" * 64,
                "duration_ms": 15000,
            }
        ],
        "media_files": [],
        "adapter_payload": {},
        "valid_from": valid_from,
        "valid_to": valid_to,
        "offline_ttl_hours": 168,
        "fallback_rules": {
            "on_manifest_expired": "show_fallback",
            "on_network_lost": "continue_last_valid",
            "filler_media_ids": [],
            "emit_pop": False,
        },
        "signature": {"algorithm": "HMAC-SHA256", "value": ""},
    }


def _apply_and_render(sim, **render_kwargs):
    """Apply manifest, disable kill-switch, render a slot."""
    sim.apply_manifest(_m())
    sim.set_kill_switch("global", active=False)
    sim.refresh_kill_switch()
    sim.render_slot(
        campaign_id=render_kwargs.pop("campaign_id", TEST_CAMPAIGN_ID),
        surface_id=render_kwargs.pop("surface_id", TEST_SURFACE_ID),
        creative_asset_id=render_kwargs.pop("creative_asset_id", "ca-1"),
        duration_ms=render_kwargs.pop("duration_ms", 15000),
        **render_kwargs,
    )


class TestProofEventSchemaValidation(unittest.TestCase):
    """Prove: simulator PoP validates against proof_event_v1.schema.json."""

    def setUp(self):
        self.validator = __import__("jsonschema").validate

    def test_simulator_pop_validates_against_schema(self):
        sim = RuntimeSimulator(device_id=TEST_DEVICE_ID)
        _apply_and_render(sim)
        self.assertEqual(len(sim.event_queue), 1)
        event = sim.event_queue[0]
        self.validator(instance=event, schema=SCHEMA)

    def test_pop_validates_against_pydantic_dto(self):
        sim = RuntimeSimulator(device_id=TEST_DEVICE_ID)
        _apply_and_render(sim)
        event = sim.event_queue[0]
        dto = PopEventIn.model_validate(event)
        self.assertEqual(dto.event_id, event["event_id"])
        self.assertEqual(dto.playback_result, "success")
        self.assertEqual(dto.device_id, TEST_DEVICE_ID)
        self.assertEqual(dto.surface_id, TEST_SURFACE_ID)
        self.assertEqual(dto.duration_ms, 15000)

    def test_pop_includes_campaign_id_when_provided(self):
        sim = RuntimeSimulator(device_id=TEST_DEVICE_ID)
        _apply_and_render(sim, campaign_id=TEST_CAMPAIGN_ID)
        event = sim.event_queue[0]
        self.assertEqual(event["campaign_id"], TEST_CAMPAIGN_ID)
        # Validate round-trip
        PopEventIn.model_validate(event)

    def test_manifest_id_is_none_when_empty(self):
        sim = RuntimeSimulator(device_id=TEST_DEVICE_ID)
        sim.apply_manifest(_m(manifest_id="real-id"))
        sim.set_kill_switch("global", active=False)
        sim.refresh_kill_switch()
        # Direct test: manifest dict with empty manifest_id
        event = sim._build_pop_event(
            manifest={"manifest_id": ""},
            campaign_id=TEST_CAMPAIGN_ID,
            surface_id=TEST_SURFACE_ID,
            creative_asset_id="ca-1",
            duration_ms=5000,
        )
        self.assertIsNone(event["manifest_id"])
        PopEventIn.model_validate(event)

    def test_rejects_missing_playback_result(self):
        sim = RuntimeSimulator(device_id=TEST_DEVICE_ID)
        _apply_and_render(sim)
        event = sim.event_queue[0]
        del event["playback_result"]
        with self.assertRaises(Exception):
            self.validator(instance=event, schema=SCHEMA)

    def test_rejects_unknown_playback_result(self):
        sim = RuntimeSimulator(device_id=TEST_DEVICE_ID)
        _apply_and_render(sim)
        event = sim.event_queue[0]
        event["playback_result"] = "bogus"
        with self.assertRaises(Exception):
            self.validator(instance=event, schema=SCHEMA)
        with self.assertRaises(Exception):
            PopEventIn.model_validate(event)

    def test_rejects_missing_event_id(self):
        sim = RuntimeSimulator(device_id=TEST_DEVICE_ID)
        _apply_and_render(sim)
        event = sim.event_queue[0]
        del event["event_id"]
        with self.assertRaises(Exception):
            self.validator(instance=event, schema=SCHEMA)

    def test_rejects_missing_creative_asset_id(self):
        sim = RuntimeSimulator(device_id=TEST_DEVICE_ID)
        _apply_and_render(sim)
        event = sim.event_queue[0]
        del event["creative_asset_id"]
        with self.assertRaises(Exception):
            self.validator(instance=event, schema=SCHEMA)

    def test_rejects_zero_duration(self):
        sim = RuntimeSimulator(device_id=TEST_DEVICE_ID)
        _apply_and_render(sim)
        event = sim.event_queue[0]
        event["duration_ms"] = 0
        with self.assertRaises(Exception):
            self.validator(instance=event, schema=SCHEMA)

    def test_accepts_null_campaign_id(self):
        sim = RuntimeSimulator(device_id=TEST_DEVICE_ID)
        _apply_and_render(sim, campaign_id="")
        event = sim.event_queue[0]
        self.assertIsNone(event["campaign_id"])
        self.validator(instance=event, schema=SCHEMA)
        PopEventIn.model_validate(event)

    def test_all_playback_results_accepted(self):
        for result in ("success", "fallback", "interrupted", "failed"):
            sim = RuntimeSimulator(device_id=TEST_DEVICE_ID)
            sim.apply_manifest(_m())
            sim.set_kill_switch("global", active=False)
            sim.refresh_kill_switch()
            # Direct call to _build_pop_event with specific result
            event = sim._build_pop_event(
                manifest=_m(),
                campaign_id=TEST_CAMPAIGN_ID,
                surface_id=TEST_SURFACE_ID,
                creative_asset_id="ca-1",
                duration_ms=5000,
                playback_result=result,
            )
            self.validator(instance=event, schema=SCHEMA)
            PopEventIn.model_validate(event)
            self.assertEqual(event["playback_result"], result)

    def test_schema_has_no_forbidden_storage_fields(self):
        self.assertNotIn("storage_bucket", SCHEMA.get("properties", {}))
        self.assertNotIn("storage_key", SCHEMA.get("properties", {}))

    def test_simulator_applies_generated_manifest(self):
        """Prove: simulator accepts manifest from generate_manifest_json."""
        from packages.domain.delivery import generate_manifest_json
        import json as _json

        # Load manifest schema separately
        mf_schema_path = os.path.join(
            os.path.dirname(__file__),
            "..", "packages", "contracts", "manifest_v1.schema.json",
        )
        with open(mf_schema_path) as f:
            manifest_schema = _json.load(f)

        manifest = generate_manifest_json(
            manifest_id="int-test-manifest",
            manifest_version=1,
            device_id=TEST_DEVICE_ID,
            device_code="KSO-001",
            store_id="store-1",
            store_code="STORE-001",
            channel_type="kso",
            device_type="KSO_SHERMAN_J51",
            surface_ids=[TEST_SURFACE_ID],
            surface_codes={TEST_SURFACE_ID: "SURF-001"},
            playlist_items=[{
                "order": 0,
                "weight": 1,
                "priority": 1,
                "creative_asset_id": "ca-1",
                "media_type": "image/png",
                "sha256_checksum": "a" * 64,
                "duration_ms": 10000,
                "start_time": None,
                "days_of_week": None,
            }],
            valid_from="2024-01-01T00:00:00Z",
            valid_to="2030-12-31T23:59:59Z",
        )
        # Validate manifest against manifest schema
        self.validator(instance=manifest, schema=manifest_schema)

        sim = RuntimeSimulator(device_id=TEST_DEVICE_ID)
        result = sim.apply_manifest(manifest)
        self.assertTrue(result.success, f"apply_manifest failed: {result.failure_reason}")

    def test_full_chain_pop_batch_request_accepts(self):
        """Integration: generated manifest → simulator → PoP → PopBatchRequest."""
        from packages.domain.delivery import generate_manifest_json
        from packages.domain.schemas import PopBatchRequest

        manifest = generate_manifest_json(
            manifest_id="chain-test-manifest",
            manifest_version=1,
            device_id=TEST_DEVICE_ID,
            device_code="KSO-001",
            store_id="store-1",
            store_code="STORE-001",
            channel_type="kso",
            device_type="KSO_SHERMAN_J51",
            surface_ids=[TEST_SURFACE_ID],
            surface_codes={TEST_SURFACE_ID: "SURF-001"},
            playlist_items=[{
                "order": 0,
                "weight": 1,
                "priority": 1,
                "creative_asset_id": "ca-1",
                "media_type": "image/png",
                "sha256_checksum": "a" * 64,
                "duration_ms": 15000,
                "start_time": None,
                "days_of_week": None,
            }],
            valid_from="2024-01-01T00:00:00Z",
            valid_to="2030-12-31T23:59:59Z",
        )

        sim = RuntimeSimulator(device_id=TEST_DEVICE_ID)
        result = sim.apply_manifest(manifest)
        self.assertTrue(result.success)

        sim.set_kill_switch("global", active=False)
        sim.refresh_kill_switch()
        sim.render_slot(
            campaign_id=TEST_CAMPAIGN_ID,
            surface_id=TEST_SURFACE_ID,
            creative_asset_id="ca-1",
            duration_ms=15000,
        )
        self.assertEqual(len(sim.event_queue), 1)

        pop_event = sim.event_queue[0]
        dto = PopEventIn.model_validate(pop_event)
        batch = PopBatchRequest(events=[dto])
        self.assertEqual(len(batch.events), 1)
        self.assertEqual(batch.events[0].event_id, pop_event["event_id"])
        self.assertEqual(batch.events[0].playback_result, "success")


if __name__ == "__main__":
    unittest.main()
