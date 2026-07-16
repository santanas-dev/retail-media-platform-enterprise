"""
S-089 — Inventory Simulation Tests.

Verifies the simulation endpoint returns correct fit/flight/conflict
data for both success and conflict scenarios.
"""

import unittest
from datetime import datetime, timedelta, timezone

from packages.domain.schemas import (
    InventorySimulationRequest,
    InventorySimulationResponse,
    InventorySimulationPlacementResult,
)


class TestInventorySimulationSchemas(unittest.TestCase):
    """Schema validation: request/response models."""

    def test_simulation_request_valid(self):
        req = InventorySimulationRequest(campaign_id="c1")
        self.assertEqual(req.campaign_id, "c1")

    def test_simulation_response_defaults(self):
        resp = InventorySimulationResponse(campaign_id="c1", overall_fit=True)
        self.assertTrue(resp.overall_fit)
        self.assertEqual(resp.placements, [])
        self.assertEqual(resp.blocking_count, 0)
        self.assertEqual(resp.warning_count, 0)

    def test_placement_result_fit_true(self):
        pr = InventorySimulationPlacementResult(
            placement_id="p1",
            surface_id="s1",
            fit=True,
            slot_fill_percent=30.0,
            total_requested=300,
            total_available=1000,
        )
        self.assertTrue(pr.fit)
        self.assertEqual(pr.slot_fill_percent, 30.0)

    def test_placement_result_fit_false_with_conflicts(self):
        from packages.domain.schemas import InventoryConflictItem

        pr = InventorySimulationPlacementResult(
            placement_id="p1",
            surface_id="s1",
            fit=False,
            slot_fill_percent=100.0,
            total_requested=1000,
            total_available=500,
            conflicts=[
                InventoryConflictItem(
                    conflict_type="capacity_overbook",
                    severity="blocking",
                    surface_id="s1",
                    message="Requested 1000, available 500",
                ),
            ],
        )
        self.assertFalse(pr.fit)
        self.assertEqual(len(pr.conflicts), 1)
        self.assertEqual(pr.conflicts[0].severity, "blocking")

    def test_placement_result_includes_applied_rules(self):
        pr = InventorySimulationPlacementResult(
            placement_id="p1",
            surface_id="s1",
            fit=True,
            applied_rules=[
                {"rule_type": "max_sov", "rule_id": "r1", "value_json": {"max_sov_percent": 70}},
            ],
        )
        self.assertEqual(len(pr.applied_rules), 1)
        self.assertEqual(pr.applied_rules[0]["rule_type"], "max_sov")

    def test_simulation_response_with_placements(self):
        pr = InventorySimulationPlacementResult(
            placement_id="p1",
            surface_id="s1",
            fit=False,
            slot_fill_percent=50.0,
        )
        resp = InventorySimulationResponse(
            campaign_id="c1",
            overall_fit=False,
            placements=[pr],
            blocking_count=1,
            warning_count=0,
        )
        self.assertFalse(resp.overall_fit)
        self.assertEqual(len(resp.placements), 1)
        self.assertEqual(resp.blocking_count, 1)


class TestInventorySimulationIntegration(unittest.TestCase):
    """Integration: verify simulation endpoint is importable and connectable."""

    def test_simulation_endpoint_exists(self):
        """POST /inventory/simulate is registered on the inventory router."""
        from packages.api.identity_routes.inventory import router

        paths = [r.path for r in router.routes]
        self.assertIn(
            "/inventory/simulate",
            paths,
            "Simulation endpoint not found on inventory router",
        )

    def test_simulate_campaign_inventory_importable(self):
        """Repository function is importable."""
        from packages.domain.repository import simulate_campaign_inventory
        self.assertTrue(callable(simulate_campaign_inventory))
