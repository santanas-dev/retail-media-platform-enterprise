"""
S-089 — Inventory Simulation Tests (v2).

Covers:
  - Schema: slot_fill_percent accepts >100 (overbook regression fix).
  - Endpoint: success simulation, conflict simulation, overbook >100%.
  - Endpoint: applied_rules, blocking_count, missing campaign_id → 422.
"""
import importlib.util
import json
import os
import sys
import unittest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["ENVIRONMENT"] = "dev"
os.environ["JWT_SECRET"] = "test-jwt-secret-for-s089-simulation-32bytes"

from fastapi.testclient import TestClient

from packages.security.config import reset_security_config
from packages.security.jwt import create_access_token


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_APP = None


def _get_app():
    global _APP
    if _APP is None:
        path = os.path.join(
            os.path.dirname(__file__), "..", "apps", "control-api", "main.py"
        )
        spec = importlib.util.spec_from_file_location("control_api_main", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _APP = mod.app
    return _APP


def _token():
    return create_access_token("u-1", "local_break_glass")


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


class TestInventorySimulationSchemas(unittest.TestCase):
    """Schema validation: request/response shapes and constraints."""

    @classmethod
    def setUpClass(cls):
        from packages.domain.schemas import (
            InventorySimulationRequest,
            InventorySimulationResponse,
            InventorySimulationPlacementResult,
            InventoryConflictItem,
        )
        cls.Req = InventorySimulationRequest
        cls.Resp = InventorySimulationResponse
        cls.PlRes = InventorySimulationPlacementResult
        cls.Conflict = InventoryConflictItem

    def test_request_valid(self):
        req = self.Req(campaign_id="c1")
        self.assertEqual(req.campaign_id, "c1")

    def test_request_missing_campaign_id_raises(self):
        with self.assertRaises(Exception):
            self.Req()

    def test_response_defaults(self):
        resp = self.Resp(campaign_id="c1", overall_fit=True)
        self.assertTrue(resp.overall_fit)
        self.assertEqual(resp.placements, [])
        self.assertEqual(resp.blocking_count, 0)

    def test_placement_fit_true(self):
        pr = self.PlRes(
            placement_id="p1", surface_id="s1", fit=True,
            slot_fill_percent=30.0, total_requested=300, total_available=1000,
        )
        self.assertTrue(pr.fit)
        self.assertEqual(pr.slot_fill_percent, 30.0)

    # --- THE REGRESSION: >100% overbook ---

    def test_slot_fill_percent_accepts_over_100_percent(self):
        """Regression: overbook scenario — 150% must NOT be rejected by schema."""
        pr = self.PlRes(
            placement_id="p1", surface_id="s1", fit=False,
            slot_fill_percent=150.0, total_requested=1500, total_available=1000,
        )
        self.assertEqual(pr.slot_fill_percent, 150.0)
        self.assertFalse(pr.fit)

    def test_placement_with_conflicts(self):
        pr = self.PlRes(
            placement_id="p1", surface_id="s1", fit=False,
            slot_fill_percent=150.0, total_requested=1500, total_available=1000,
            conflicts=[
                self.Conflict(
                    conflict_type="capacity_overbook", severity="blocking",
                    surface_id="s1",
                    message="Requested 1500, available 1000",
                ),
            ],
        )
        self.assertFalse(pr.fit)
        self.assertEqual(len(pr.conflicts), 1)
        self.assertEqual(pr.conflicts[0].severity, "blocking")

    def test_applied_rules_present(self):
        pr = self.PlRes(
            placement_id="p1", surface_id="s1", fit=True,
            applied_rules=[
                {"rule_type": "max_sov", "rule_id": "r1",
                 "value_json": {"max_sov_percent": 70}},
            ],
        )
        self.assertEqual(len(pr.applied_rules), 1)
        self.assertEqual(pr.applied_rules[0]["rule_type"], "max_sov")

    def test_response_with_placements(self):
        pr = self.PlRes(
            placement_id="p1", surface_id="s1", fit=False,
            slot_fill_percent=120.0,
        )
        resp = self.Resp(
            campaign_id="c1", overall_fit=False,
            placements=[pr], blocking_count=1, warning_count=0,
        )
        self.assertFalse(resp.overall_fit)
        self.assertEqual(len(resp.placements), 1)
        self.assertEqual(resp.blocking_count, 1)


# ---------------------------------------------------------------------------
# Endpoint tests (real TestClient)
# ---------------------------------------------------------------------------


class TestInventorySimulationEndpoint(unittest.TestCase):
    """POST /inventory/simulate — real endpoint through TestClient."""

    @classmethod
    def setUpClass(cls):
        reset_security_config()
        cls.client = TestClient(_get_app())

    def setUp(self):
        """Set up authz mocks so the endpoint passes permission checks."""
        self._patchers = []
        self._overrides = {}

        # Authz: find_user_by_id
        p_find = patch(
            "packages.api.dependencies.repository.find_user_by_id",
            new_callable=AsyncMock,
        )
        self._patchers.append(p_find)
        mock_find = p_find.start()
        mock_find.return_value = type("U", (), {"id": "u-1", "status": "active"})()

        # Authz: get_user_permissions
        p_perms = patch(
            "packages.api.dependencies.repository.get_user_permissions",
            new_callable=AsyncMock,
        )
        self._patchers.append(p_perms)
        mock_perms = p_perms.start()
        mock_perms.return_value = {"inventory.read"}

        # Scope context + RLS
        app = _get_app()
        from packages.api.dependencies import get_scope_context, set_rls_context
        from packages.domain.scopes import ScopeContext

        async def _fake_scope():
            return ScopeContext(
                user_id="u-1", is_admin=True,
                role_codes={"system_admin"},
                global_permissions={"inventory.read"},
                all_permissions={"inventory.read"},
            )

        async def _fake_rls():
            return None

        app.dependency_overrides[get_scope_context] = _fake_scope
        app.dependency_overrides[set_rls_context] = _fake_rls
        self._overrides["scope"] = get_scope_context
        self._overrides["rls"] = set_rls_context

    def tearDown(self):
        for p in self._patchers:
            p.stop()
        app = _get_app()
        for key in list(self._overrides.values()):
            app.dependency_overrides.pop(key, None)

    # ------------------------------------------------------------------
    # Success scenario
    # ------------------------------------------------------------------

    def test_simulation_success_all_fit(self):
        """Campaign fits all placements — overall_fit=true, no conflicts."""
        backend_result = {
            "campaign_id": "c-success",
            "overall_fit": True,
            "placements": [{
                "placement_id": "p-1",
                "surface_id": "s-1",
                "surface_code": "SURF-01",
                "surface_name": "Main Screen",
                "store_code": "ST-01",
                "store_name": "Store Alpha",
                "fit": True,
                "slot_fill_percent": 30.0,
                "total_requested": 300,
                "total_available": 1000,
                "conflicts": [],
                "applied_rules": [],
            }],
            "blocking_count": 0,
            "warning_count": 0,
        }

        with patch(
            "packages.api.identity_routes.inventory.repository.simulate_campaign_inventory",
            new_callable=AsyncMock,
        ) as mock_sim:
            mock_sim.return_value = backend_result
            resp = self.client.post(
                "/api/v1/identity/inventory/simulate",
                json={"campaign_id": "c-success"},
                headers={"Authorization": f"Bearer {_token()}"},
            )

        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        self.assertTrue(data["overall_fit"])
        self.assertEqual(data["campaign_id"], "c-success")
        self.assertEqual(len(data["placements"]), 1)
        self.assertEqual(data["placements"][0]["fit"], True)
        self.assertEqual(data["placements"][0]["slot_fill_percent"], 30.0)
        self.assertEqual(data["blocking_count"], 0)

    # ------------------------------------------------------------------
    # Conflict scenario: capacity overbook with >100%
    # ------------------------------------------------------------------

    def test_simulation_conflict_overbook_over_100_percent(self):
        """Overbook: total_requested > total_available → slot_fill >100%."""
        backend_result = {
            "campaign_id": "c-overbook",
            "overall_fit": False,
            "placements": [{
                "placement_id": "p-1",
                "surface_id": "s-1",
                "surface_code": "SURF-01",
                "surface_name": None,
                "store_code": None,
                "store_name": None,
                "fit": False,
                "slot_fill_percent": 150.0,
                "total_requested": 1500,
                "total_available": 1000,
                "conflicts": [{
                    "conflict_type": "capacity_overbook",
                    "severity": "blocking",
                    "surface_id": "s-1",
                    "message": "Requested 1500, available 1000",
                    "placement_id": "p-1",
                }],
                "applied_rules": [],
            }],
            "blocking_count": 1,
            "warning_count": 0,
        }

        with patch(
            "packages.api.identity_routes.inventory.repository.simulate_campaign_inventory",
            new_callable=AsyncMock,
        ) as mock_sim:
            mock_sim.return_value = backend_result
            resp = self.client.post(
                "/api/v1/identity/inventory/simulate",
                json={"campaign_id": "c-overbook"},
                headers={"Authorization": f"Bearer {_token()}"},
            )

        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        self.assertFalse(data["overall_fit"])
        self.assertEqual(data["blocking_count"], 1)
        self.assertEqual(len(data["placements"]), 1)
        pl = data["placements"][0]
        self.assertFalse(pl["fit"])
        self.assertEqual(pl["slot_fill_percent"], 150.0)
        self.assertEqual(len(pl["conflicts"]), 1)
        self.assertEqual(pl["conflicts"][0]["conflict_type"], "capacity_overbook")
        self.assertEqual(pl["conflicts"][0]["severity"], "blocking")

    # ------------------------------------------------------------------
    # Applied rules present
    # ------------------------------------------------------------------

    def test_simulation_applied_rules_in_response(self):
        """Active inventory rules appear in the simulation response."""
        backend_result = {
            "campaign_id": "c-rules",
            "overall_fit": True,
            "placements": [{
                "placement_id": "p-1",
                "surface_id": "s-1",
                "surface_code": None,
                "surface_name": None,
                "store_code": None,
                "store_name": None,
                "fit": True,
                "slot_fill_percent": 40.0,
                "total_requested": 400,
                "total_available": 1000,
                "conflicts": [],
                "applied_rules": [
                    {"rule_id": "r-max-sov", "rule_type": "max_sov",
                     "scope_type": "surface", "scope_id": "s-1",
                     "value_json": {"max_sov_percent": 70}, "priority": 10},
                ],
            }],
            "blocking_count": 0,
            "warning_count": 0,
        }

        with patch(
            "packages.api.identity_routes.inventory.repository.simulate_campaign_inventory",
            new_callable=AsyncMock,
        ) as mock_sim:
            mock_sim.return_value = backend_result
            resp = self.client.post(
                "/api/v1/identity/inventory/simulate",
                json={"campaign_id": "c-rules"},
                headers={"Authorization": f"Bearer {_token()}"},
            )

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        pl = data["placements"][0]
        self.assertEqual(len(pl["applied_rules"]), 1)
        self.assertEqual(pl["applied_rules"][0]["rule_type"], "max_sov")

    # ------------------------------------------------------------------
    # Blocking_count reflects conflict count
    # ------------------------------------------------------------------

    def test_simulation_blocking_count_matches(self):
        """blocking_count equals number of blocking conflicts."""
        backend_result = {
            "campaign_id": "c-multi",
            "overall_fit": False,
            "placements": [{
                "placement_id": "p-1", "surface_id": "s-1",
                "fit": False, "slot_fill_percent": 200.0,
                "total_requested": 2000, "total_available": 1000,
                "conflicts": [
                    {"conflict_type": "capacity_overbook", "severity": "blocking",
                     "surface_id": "s-1", "message": "over capacity", "placement_id": "p-1"},
                    {"conflict_type": "blackout", "severity": "blocking",
                     "surface_id": "s-1", "message": "blackout period", "placement_id": "p-1"},
                ],
                "applied_rules": [],
                "surface_code": None, "surface_name": None,
                "store_code": None, "store_name": None,
            }],
            "blocking_count": 2,
            "warning_count": 0,
        }

        with patch(
            "packages.api.identity_routes.inventory.repository.simulate_campaign_inventory",
            new_callable=AsyncMock,
        ) as mock_sim:
            mock_sim.return_value = backend_result
            resp = self.client.post(
                "/api/v1/identity/inventory/simulate",
                json={"campaign_id": "c-multi"},
                headers={"Authorization": f"Bearer {_token()}"},
            )

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["blocking_count"], 2)
        self.assertFalse(data["overall_fit"])

    # ------------------------------------------------------------------
    # Error: missing campaign_id
    # ------------------------------------------------------------------

    def test_simulation_missing_campaign_id_422(self):
        """Missing campaign_id → 422 Unprocessable Entity."""
        resp = self.client.post(
            "/api/v1/identity/inventory/simulate",
            json={},
            headers={"Authorization": f"Bearer {_token()}"},
        )
        self.assertEqual(resp.status_code, 422, resp.text)
