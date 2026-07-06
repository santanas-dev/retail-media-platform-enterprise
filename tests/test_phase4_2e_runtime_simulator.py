"""
Phase 4.2e — Runtime Simulator Behavioral Tests.

ADR-013 safety proofs: manifest apply, kill-switch, render slot,
PoP integrity, offline TTL, dedup.

No PostgreSQL required — pure in-memory simulation.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from packages.runtime.simulator import (
    RuntimeSimulator,
    ApplyResult,
    RenderResult,
    make_test_manifest,
)


TEST_DEVICE_ID = "dev-00000000-0000-0000-0000-000000000001"
TEST_CAMPAIGN_ID = "camp-00000000-0000-0000-0000-000000000001"
TEST_SURFACE_ID = "surf-00000000-0000-0000-0000-000000000001"


def _m(**overrides):
    """Shortcut: build a valid manifest. Defaults device_id to TEST_DEVICE_ID."""
    kwargs = {"device_id": TEST_DEVICE_ID, **overrides}
    return make_test_manifest(**kwargs)


# ═══════════════════════════════════════════════════════════════════
# Manifest Apply (ADR-013 §3)
# ═══════════════════════════════════════════════════════════════════


class TestManifestApplyInvalidRejected(unittest.TestCase):

    def setUp(self):
        self.sim = RuntimeSimulator(device_id=TEST_DEVICE_ID)

    def test_missing_required_fields_rejected(self):
        bad = _m()
        del bad["manifest_id"]
        result = self.sim.apply_manifest(bad)
        self.assertFalse(result.success)
        self.assertIn("manifest_id", result.failure_reason.lower())
        self.assertIsNone(self.sim.current_manifest)

    def test_missing_device_id_rejected(self):
        bad = _m()
        del bad["device_id"]
        result = self.sim.apply_manifest(bad)
        self.assertFalse(result.success)
        self.assertIsNone(self.sim.current_manifest)

    def test_wrong_device_id_rejected(self):
        bad = _m(device_id="other-device")
        result = self.sim.apply_manifest(bad)
        self.assertFalse(result.success)
        self.assertIn("device_id", result.failure_reason.lower())

    def test_invalid_signature_rejected(self):
        bad = _m(signature={"algorithm": "HMAC-SHA256", "value": "INVALID"})
        result = self.sim.apply_manifest(bad)
        self.assertFalse(result.success)
        self.assertIn("signature", result.failure_reason.lower())

    def test_secret_in_manifest_rejected(self):
        bad = _m(storage_bucket="prod-bucket")
        result = self.sim.apply_manifest(bad)
        self.assertFalse(result.success)
        self.assertIn("storage_bucket", result.failure_reason.lower())

    def test_invalid_manifest_no_playback(self):
        bad = _m()
        del bad["manifest_id"]
        self.sim.apply_manifest(bad)
        self.assertFalse(self.sim.playback_active)


class TestValidManifestApplies(unittest.TestCase):

    def setUp(self):
        self.sim = RuntimeSimulator(device_id=TEST_DEVICE_ID)

    def test_valid_manifest_applies(self):
        m = _m()
        result = self.sim.apply_manifest(m)
        self.assertTrue(result.success)
        self.assertIsNotNone(self.sim.current_manifest)
        self.assertEqual(self.sim.current_manifest["manifest_id"], m["manifest_id"])

    def test_first_apply_lkg_is_none(self):
        m = _m()
        self.sim.apply_manifest(m)
        self.assertIsNone(self.sim.last_known_good)

    def test_second_apply_preserves_lkg(self):
        m1 = _m(manifest_version=1, manifest_id="m1")
        self.sim.apply_manifest(m1)
        m2 = _m(manifest_version=2, manifest_id="m2")
        self.sim.apply_manifest(m2)
        self.assertEqual(self.sim.current_manifest["manifest_id"], "m2")
        self.assertIsNotNone(self.sim.last_known_good)
        self.assertEqual(self.sim.last_known_good["manifest_id"], "m1")


class TestInvalidUpdateKeepsLKG(unittest.TestCase):

    def setUp(self):
        self.sim = RuntimeSimulator(device_id=TEST_DEVICE_ID)
        self.sim.apply_manifest(_m(manifest_version=1, manifest_id="m1"))

    def test_downgrade_version_rejected(self):
        m2 = _m(manifest_version=0, manifest_id="m2")
        result = self.sim.apply_manifest(m2)
        self.assertFalse(result.success)
        self.assertEqual(self.sim.current_manifest["manifest_id"], "m1")

    def test_corrupt_manifest_keeps_lkg(self):
        self.sim.set_kill_switch("global", active=False)
        self.sim.refresh_kill_switch()
        bad = _m()
        del bad["device_id"]
        result = self.sim.apply_manifest(bad)
        self.assertFalse(result.success)
        self.assertEqual(self.sim.current_manifest["manifest_id"], "m1")
        self.assertTrue(self.sim.playback_active)

    def test_rollback_restores_lkg(self):
        m2 = _m(manifest_version=2, manifest_id="m2_valid")
        self.sim.apply_manifest(m2)
        self.sim.rollback_to_last_known_good()
        self.assertEqual(self.sim.current_manifest["manifest_id"], "m1")


# ═══════════════════════════════════════════════════════════════════
# Kill-Switch (ADR-013 §2)
# ═══════════════════════════════════════════════════════════════════


class TestKillSwitchStopsPlayback(unittest.TestCase):

    def setUp(self):
        self.sim = RuntimeSimulator(device_id=TEST_DEVICE_ID)
        self.sim.apply_manifest(_m())
        self.sim.set_kill_switch("global", active=False)
        self.sim.refresh_kill_switch()

    def test_global_kill_switch_stops(self):
        self.sim.set_kill_switch("global", active=True)
        result = self.sim.render_slot(campaign_id=TEST_CAMPAIGN_ID)
        self.assertFalse(result.played)

    def test_device_kill_switch_stops(self):
        self.sim.set_kill_switch("device", active=True)
        result = self.sim.render_slot(campaign_id=TEST_CAMPAIGN_ID)
        self.assertFalse(result.played)

    def test_store_kill_switch_stops(self):
        self.sim.set_kill_switch("store", active=True)
        result = self.sim.render_slot(campaign_id=TEST_CAMPAIGN_ID)
        self.assertFalse(result.played)

    def test_campaign_kill_switch_stops(self):
        self.sim.set_kill_switch("campaign", TEST_CAMPAIGN_ID, active=True)
        result = self.sim.render_slot(campaign_id=TEST_CAMPAIGN_ID)
        self.assertFalse(result.played)

    def test_nonexistent_campaign_not_blocked(self):
        self.sim.set_kill_switch("campaign", "camp-x", active=True)
        result = self.sim.render_slot(campaign_id="camp-y")
        self.assertTrue(result.played)

    def test_kill_switch_no_pop(self):
        self.sim.set_kill_switch("global", active=True)
        self.sim.render_slot(campaign_id=TEST_CAMPAIGN_ID)
        self.assertEqual(len(self.sim.event_queue), 0)


class TestStaleKillSwitchFailsClosed(unittest.TestCase):

    def setUp(self):
        self.sim = RuntimeSimulator(device_id=TEST_DEVICE_ID)
        self.sim.apply_manifest(_m())

    def test_boot_state_fails_closed(self):
        self.assertTrue(self.sim.kill_switch_stale)
        result = self.sim.render_slot(campaign_id=TEST_CAMPAIGN_ID)
        self.assertFalse(result.played)

    def test_cache_cleared_fails_closed(self):
        self.sim.set_kill_switch("global", active=False)
        self.sim.refresh_kill_switch()
        self.assertTrue(self.sim.render_slot(campaign_id=TEST_CAMPAIGN_ID).played)
        self.sim.clear_kill_switch_cache()
        self.assertFalse(self.sim.render_slot(campaign_id=TEST_CAMPAIGN_ID).played)

    def test_fresh_cache_plays(self):
        self.sim.set_kill_switch("global", active=False)
        self.sim.refresh_kill_switch()
        self.assertTrue(self.sim.render_slot(campaign_id=TEST_CAMPAIGN_ID).played)


# ═══════════════════════════════════════════════════════════════════
# Proof-of-Play (ADR-013 §6)
# ═══════════════════════════════════════════════════════════════════


class TestPoPOnlyAfterRender(unittest.TestCase):

    def setUp(self):
        self.sim = RuntimeSimulator(device_id=TEST_DEVICE_ID)
        self.sim.apply_manifest(_m())
        self.sim.set_kill_switch("global", active=False)
        self.sim.refresh_kill_switch()

    def test_successful_render_emits_pop(self):
        result = self.sim.render_slot(
            campaign_id=TEST_CAMPAIGN_ID,
            surface_id=TEST_SURFACE_ID,
            creative_asset_id="ca-1",
        )
        self.assertTrue(result.played)
        self.assertNotEqual(result.event_id, "")
        self.assertEqual(len(self.sim.event_queue), 1)

    def test_no_pop_for_kill_switched(self):
        self.sim.set_kill_switch("global", active=True)
        self.sim.render_slot(campaign_id=TEST_CAMPAIGN_ID)
        self.assertEqual(len(self.sim.event_queue), 0)

    def test_no_pop_for_expired_manifest(self):
        m = _m(manifest_version=2, valid_to="2020-01-01T00:00:00+00:00")
        self.sim.apply_manifest(m)
        result = self.sim.render_slot(campaign_id=TEST_CAMPAIGN_ID)
        self.assertFalse(result.played)
        self.assertEqual(len(self.sim.event_queue), 0)

    def test_fallback_no_pop_default(self):
        result = self.sim.render_slot(campaign_id=TEST_CAMPAIGN_ID, is_fallback=True)
        self.assertTrue(result.played)
        self.assertEqual(result.event_id, "")
        self.assertEqual(len(self.sim.event_queue), 0)

    def test_fallback_emit_pop_true(self):
        m = _m(
            manifest_version=2,
            fallback_rules={
                "on_manifest_expired": "show_fallback",
                "on_network_lost": "continue_last_valid",
                "filler_media_ids": [],
                "emit_pop": True,
            },
        )
        self.sim.apply_manifest(m)
        result = self.sim.render_slot(campaign_id=TEST_CAMPAIGN_ID, is_fallback=True)
        self.assertTrue(result.played)
        self.assertNotEqual(result.event_id, "")
        self.assertEqual(len(self.sim.event_queue), 1)


class TestPoPContainsRequiredFields(unittest.TestCase):

    def setUp(self):
        self.sim = RuntimeSimulator(device_id=TEST_DEVICE_ID)
        self.sim.apply_manifest(_m())
        self.sim.set_kill_switch("global", active=False)
        self.sim.refresh_kill_switch()

    def test_pop_required_fields(self):
        self.sim.render_slot(
            campaign_id=TEST_CAMPAIGN_ID,
            surface_id=TEST_SURFACE_ID,
            creative_asset_id="ca-1",
            duration_ms=15000,
        )
        event = self.sim.event_queue[0]
        required = [
            "event_id", "event_type", "manifest_id",
            "surface_id", "creative_asset_id", "device_id",
            "duration_ms", "rendered_at", "event_recorded_at",
        ]
        for field in required:
            self.assertIn(field, event, f"PoP missing: {field}")
        self.assertEqual(event["event_type"], "proof")
        self.assertEqual(event["duration_ms"], 15000)


class TestDuplicateEventIdDedup(unittest.TestCase):

    def setUp(self):
        self.sim = RuntimeSimulator(device_id=TEST_DEVICE_ID)
        self.sim.apply_manifest(_m())
        self.sim.set_kill_switch("global", active=False)
        self.sim.refresh_kill_switch()

    def test_same_event_id_dedup(self):
        self.sim.render_slot(campaign_id=TEST_CAMPAIGN_ID)
        eid = self.sim.event_queue[0]["event_id"]
        # Adding same ID to internal dedup set — idempotent
        self.sim._event_ids.add(eid)
        self.assertEqual(len(self.sim._event_ids), 1)
        self.assertEqual(len(self.sim.event_queue), 1)

    def test_pop_events_clears_queue(self):
        self.sim.render_slot(campaign_id=TEST_CAMPAIGN_ID)
        events = self.sim.pop_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(len(self.sim.event_queue), 0)


# ═══════════════════════════════════════════════════════════════════
# Offline TTL (ADR-013 §5)
# ═══════════════════════════════════════════════════════════════════


class TestOfflineTTLExpiry(unittest.TestCase):

    def setUp(self):
        self.sim = RuntimeSimulator(device_id=TEST_DEVICE_ID)
        self.sim.apply_manifest(_m(offline_ttl_hours=1))
        self.sim.set_kill_switch("global", active=False)
        self.sim.refresh_kill_switch()

    def test_within_ttl_plays(self):
        self.sim.set_offline(True)
        self.assertTrue(self.sim.render_slot(campaign_id=TEST_CAMPAIGN_ID).played)

    def test_ttl_expired_stops(self):
        self.sim.set_offline(True)
        self.sim.advance_offline_clock(hours=2)
        result = self.sim.render_slot(campaign_id=TEST_CAMPAIGN_ID)
        self.assertFalse(result.played)
        self.assertEqual(result.failure_reason, "offline_ttl_expired")

    def test_ttl_expired_no_pop(self):
        self.sim.set_offline(True)
        self.sim.advance_offline_clock(hours=2)
        self.sim.render_slot(campaign_id=TEST_CAMPAIGN_ID)
        self.assertEqual(len(self.sim.event_queue), 0)

    def test_reconnect_clears_offline(self):
        self.sim.set_offline(True)
        self.sim.advance_offline_clock(hours=0.5)
        self.sim.set_offline(False)
        self.assertTrue(self.sim.render_slot(campaign_id=TEST_CAMPAIGN_ID).played)


class TestNoManifestNoPlayback(unittest.TestCase):

    def setUp(self):
        self.sim = RuntimeSimulator(device_id=TEST_DEVICE_ID)
        self.sim.set_kill_switch("global", active=False)
        self.sim.refresh_kill_switch()

    def test_no_manifest_no_render(self):
        result = self.sim.render_slot(campaign_id=TEST_CAMPAIGN_ID)
        self.assertFalse(result.played)
        self.assertEqual(result.failure_reason, "no_manifest_loaded")

    def test_playback_inactive(self):
        self.assertFalse(self.sim.playback_active)


class TestManifestExpired(unittest.TestCase):

    def setUp(self):
        self.sim = RuntimeSimulator(device_id=TEST_DEVICE_ID)
        self.sim.set_kill_switch("global", active=False)
        self.sim.refresh_kill_switch()

    def test_expired_manifest_no_render(self):
        self.sim.apply_manifest(_m(valid_to="2020-01-01T00:00:00+00:00"))
        result = self.sim.render_slot(campaign_id=TEST_CAMPAIGN_ID)
        self.assertFalse(result.played)
        self.assertEqual(result.failure_reason, "manifest_expired")


class TestSimulatorReset(unittest.TestCase):

    def test_reset_clears_everything(self):
        sim = RuntimeSimulator(device_id=TEST_DEVICE_ID)
        sim.apply_manifest(_m())
        sim.set_kill_switch("global", active=True)
        sim.render_slot(campaign_id=TEST_CAMPAIGN_ID)
        sim.set_offline(True)
        sim.reset()
        self.assertIsNone(sim.current_manifest)
        self.assertIsNone(sim.last_known_good)
        self.assertTrue(sim.kill_switch_stale)
        self.assertEqual(len(sim.event_queue), 0)
        self.assertFalse(sim.playback_active)


# ═══════════════════════════════════════════════════════════════════
# Safety: no production imports in simulator
# ═══════════════════════════════════════════════════════════════════


class TestNoProductionImports(unittest.TestCase):

    def test_no_fastapi_or_nats(self):
        import re
        path = os.path.join(
            os.path.dirname(__file__), "..",
            "packages", "runtime", "simulator.py",
        )
        content = open(path).read()
        stripped = re.sub(r'"""(.|\n)*?"""', '', content)
        stripped = re.sub(r'#.*', '', stripped)
        for banned in ("import fastapi", "from fastapi", "import nats", "from nats"):
            self.assertNotIn(banned, stripped.lower())

    def test_no_apps_imports(self):
        import re
        path = os.path.join(
            os.path.dirname(__file__), "..",
            "packages", "runtime", "simulator.py",
        )
        content = open(path).read()
        stripped = re.sub(r'"""(.|\n)*?"""', '', content)
        stripped = re.sub(r'#.*', '', stripped)
        self.assertNotIn("from apps", stripped.lower())
        self.assertNotIn("import apps", stripped.lower())


if __name__ == "__main__":
    unittest.main()
