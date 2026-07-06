"""
Phase 4.2b — Delivery DB Foundation Unit Tests.

Tests: models, constraints, indexes, __all__, REQUIRED_TABLES,
no secrets/storage fields, repository helpers, no NATS import.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestDeliveryModels(unittest.TestCase):
    """ORM model definitions — table names, columns, constraints."""

    def test_delivery_plan_table(self):
        from packages.domain.models import DeliveryPlan
        self.assertEqual(DeliveryPlan.__tablename__, "delivery_plans")
        cols = {c.name for c in DeliveryPlan.__table__.columns}
        required = {"id", "campaign_id", "campaign_version_hash",
                     "status", "reason", "created_at", "updated_at"}
        self.assertTrue(required <= cols)

    def test_delivery_manifest_table(self):
        from packages.domain.models import DeliveryManifest
        self.assertEqual(DeliveryManifest.__tablename__, "delivery_manifests")
        cols = {c.name for c in DeliveryManifest.__table__.columns}
        required = {"id", "manifest_id", "campaign_id", "physical_device_id",
                     "content_hash", "manifest_version", "status",
                     "generated_at", "delivered_at", "last_error", "created_at"}
        self.assertTrue(required <= cols)

    def test_delivery_manifest_surface_table(self):
        from packages.domain.models import DeliveryManifestSurface
        self.assertEqual(
            DeliveryManifestSurface.__tablename__, "delivery_manifest_surfaces",
        )
        cols = {c.name for c in DeliveryManifestSurface.__table__.columns}
        required = {"id", "manifest_id", "display_surface_id",
                     "slot_order", "created_at"}
        self.assertTrue(required <= cols)

    def test_delivery_manifest_asset_table(self):
        from packages.domain.models import DeliveryManifestAsset
        self.assertEqual(
            DeliveryManifestAsset.__tablename__, "delivery_manifest_assets",
        )
        cols = {c.name for c in DeliveryManifestAsset.__table__.columns}
        required = {"id", "manifest_id", "creative_asset_id",
                     "sha256_checksum", "duration_ms", "media_type", "created_at"}
        self.assertTrue(required <= cols)

    def test_delivery_attempt_table(self):
        from packages.domain.models import DeliveryAttempt
        self.assertEqual(DeliveryAttempt.__tablename__, "delivery_attempts")
        cols = {c.name for c in DeliveryAttempt.__table__.columns}
        required = {"id", "manifest_id", "status",
                     "attempted_at", "error_code", "error_message", "created_at"}
        self.assertTrue(required <= cols)

    def test_no_secrets_fields(self):
        """Delivery tables must not contain storage credentials or PII."""
        from packages.domain.models import (
            DeliveryPlan, DeliveryManifest,
            DeliveryManifestSurface, DeliveryManifestAsset, DeliveryAttempt,
        )
        forbidden = {"storage_bucket", "storage_key", "access_key",
                      "secret_key", "presigned_url", "token",
                      "advertiser_organization_id",
                      "email", "phone", "contact_name", "password"}
        for model in (DeliveryPlan, DeliveryManifest, DeliveryManifestSurface,
                      DeliveryManifestAsset, DeliveryAttempt):
            cols = {c.name for c in model.__table__.columns}
            overlap = cols & forbidden
            self.assertFalse(
                overlap,
                f"{model.__name__} has forbidden fields: {overlap}",
            )

    def test_manifest_unique_constraint(self):
        """manifest_id column must be unique."""
        from packages.domain.models import DeliveryManifest
        col = DeliveryManifest.__table__.columns["manifest_id"]
        self.assertTrue(col.unique, "manifest_id column must have unique=True")

    def test_constraints_present(self):
        """All status columns have CHECK constraints."""
        from packages.domain.models import (
            DeliveryPlan, DeliveryManifest, DeliveryAttempt,
        )

        def _has_check(model, col_name):
            for c in model.__table_args__:
                if hasattr(c, 'sqltext') and col_name in str(c.sqltext).lower():
                    return True
            return False

        self.assertTrue(_has_check(DeliveryPlan, "status"))
        self.assertTrue(_has_check(DeliveryManifest, "status"))
        self.assertTrue(_has_check(DeliveryAttempt, "status"))


class TestDeliveryAllAndRequiredTables(unittest.TestCase):
    """__all__ and REQUIRED_TABLES are updated."""

    def test_all_exports_models(self):
        from packages.domain import models
        for name in ("DeliveryPlan", "DeliveryManifest",
                     "DeliveryManifestSurface", "DeliveryManifestAsset",
                     "DeliveryAttempt"):
            self.assertIn(name, models.__all__,
                          f"{name} not in __all__")

    def test_required_tables(self):
        from packages.domain.models import REQUIRED_TABLES
        for table in ("delivery_plans", "delivery_manifests",
                      "delivery_manifest_surfaces", "delivery_manifest_assets",
                      "delivery_attempts"):
            self.assertIn(table, REQUIRED_TABLES,
                          f"{table} not in REQUIRED_TABLES")


class TestDeliveryRepositoryHelpers(unittest.TestCase):
    """Repository helpers — signatures and no NATS."""

    def test_create_delivery_plan_exists(self):
        import inspect
        from packages.domain.repository import create_delivery_plan
        sig = inspect.signature(create_delivery_plan)
        self.assertIn("campaign_id", sig.parameters)
        self.assertIn("campaign_version_hash", sig.parameters)

    def test_create_delivery_manifest_record_exists(self):
        import inspect
        from packages.domain.repository import create_delivery_manifest_record
        sig = inspect.signature(create_delivery_manifest_record)
        for p in ("manifest_id_external", "campaign_id",
                  "physical_device_id", "content_hash"):
            self.assertIn(p, sig.parameters)

    def test_list_delivery_manifests_exists(self):
        import inspect
        from packages.domain.repository import list_delivery_manifests
        sig = inspect.signature(list_delivery_manifests)
        self.assertIn("campaign_id", sig.parameters)
        self.assertIn("physical_device_id", sig.parameters)

    def test_mark_helpers_exist(self):
        from packages.domain.repository import (
            mark_manifest_generated, mark_manifest_failed,
            mark_manifest_delivered,
        )
        for fn in (mark_manifest_generated, mark_manifest_failed,
                   mark_manifest_delivered):
            import inspect
            sig = inspect.signature(fn)
            self.assertIn("manifest_id_external", sig.parameters)

    def test_no_nats_in_repository(self):
        """Repository helpers must not import or reference NATS."""
        repo_path = os.path.join(
            os.path.dirname(__file__), "..",
            "packages", "domain", "repository.py",
        )
        content = open(repo_path).read()
        # Only flag actual imports/calls, not docstring/comment mentions
        import re
        # Strip comments and docstrings before checking
        stripped = re.sub(r'""".*?"""', '', content, flags=re.DOTALL)
        stripped = re.sub(r'#.*', '', stripped)
        for banned in ("import nats", "from nats", "nats_publish",
                        "nats.request", "nats.publish", "nats.connect"):
            self.assertNotIn(banned, stripped.lower(),
                             f"Repository must not reference NATS: found '{banned}'")


if __name__ == "__main__":
    unittest.main()
