"""
Retail Media Platform — S-009h Reference Data Tests.

Tests: schema validation, 401 on missing token, import boundaries.
Repository + endpoint behavior is tested in behavioral suite.
"""

import importlib.util
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["ENVIRONMENT"] = "dev"
os.environ["JWT_SECRET"] = "test-jwt-secret-for-refdata-tests-32bytes!!"

from fastapi.testclient import TestClient
from packages.security.config import reset_security_config

# ── App loader ──

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


# ── Tests ──

class TestReferenceEndpoints(unittest.TestCase):
    """Reference data endpoints — auth + schema validation."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(_get_app())

    def setUp(self):
        reset_security_config()
        os.environ["ENVIRONMENT"] = "dev"
        os.environ["JWT_SECRET"] = "test-jwt-secret-for-refdata-tests-32bytes!!"
        _get_app().dependency_overrides.clear()

    def tearDown(self):
        reset_security_config()
        _get_app().dependency_overrides.clear()

    # ── 401 — no token → rejected ──

    def test_branches_missing_token_401(self):
        resp = self.client.get("/api/v1/identity/branches")
        self.assertEqual(resp.status_code, 401)

    def test_clusters_missing_token_401(self):
        resp = self.client.get("/api/v1/identity/clusters")
        self.assertEqual(resp.status_code, 401)

    def test_stores_missing_token_401(self):
        resp = self.client.get("/api/v1/identity/stores")
        self.assertEqual(resp.status_code, 401)

    def test_surfaces_missing_token_401(self):
        resp = self.client.get("/api/v1/identity/display-surfaces")
        self.assertEqual(resp.status_code, 401)


class TestReferenceSchemas(unittest.TestCase):
    """Schema validation — construct and serialise output DTOs."""

    def test_branch_out_shape(self):
        from packages.domain.schemas import BranchOut
        b = BranchOut(id="br-1", code="BR001", name="Центральный", is_active=True)
        d = b.model_dump()
        self.assertEqual(d["id"], "br-1")
        self.assertEqual(d["code"], "BR001")
        self.assertEqual(d["name"], "Центральный")
        self.assertEqual(d["is_active"], True)
        self.assertNotIn("timezone", d)  # timezone not exposed

    def test_store_out_shape(self):
        from packages.domain.schemas import StoreOut
        s = StoreOut(id="st-1", cluster_id="cl-1", code="ST001",
                     name="Магазин", address="ул. Ленина", is_active=True)
        d = s.model_dump()
        self.assertEqual(d["address"], "ул. Ленина")
        self.assertEqual(d["cluster_id"], "cl-1")

    def test_display_surface_out_shape(self):
        from packages.domain.schemas import DisplaySurfaceOut
        ds = DisplaySurfaceOut(id="ds-1", store_id="st-1", code="SURF-001",
                               resolution_w=1920, resolution_h=1080, is_active=True)
        d = ds.model_dump()
        self.assertEqual(d["resolution_w"], 1920)
        self.assertEqual(d["store_id"], "st-1")
        # No storage keys, no PII
        self.assertNotIn("current_manifest_id", d)
        self.assertNotIn("logical_carrier_id", d)

    def test_branch_deactivated(self):
        from packages.domain.schemas import BranchOut
        b = BranchOut(id="br-2", code="BR002", name="Test", is_active=False)
        self.assertFalse(b.is_active)

    def test_store_empty_address(self):
        from packages.domain.schemas import StoreOut
        s = StoreOut(id="st-1", cluster_id="cl-1", code="ST001",
                     name="Store", address="", is_active=True)
        self.assertEqual(s.address, "")


if __name__ == "__main__":
    unittest.main()
