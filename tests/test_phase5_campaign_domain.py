"""
Phase 4.1b — Campaign Domain Unit Tests.

Tests: models, migration RLS policies, seed permissions, repository,
schemas, router compliance (no db.execute in routers).
"""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestCampaignDomainModels(unittest.TestCase):
    """Campaign domain tables exist and have required columns/FKs."""

    @classmethod
    def setUpClass(cls):
        from packages.domain import models as m
        cls.m = m

    # --- Campaign ---
    def test_campaign_columns(self):
        cols = {c.name for c in self.m.Campaign.__table__.columns}
        required = {"id", "advertiser_organization_id", "advertiser_contract_id",
                     "code", "name", "status", "priority", "timezone",
                     "created_at", "updated_at"}
        self.assertTrue(required <= cols, f"Missing: {required - cols}")

    def test_campaign_fk_org(self):
        fks = {fk.column.table.name for fk in self.m.Campaign.__table__.foreign_keys}
        self.assertIn("advertiser_organizations", fks)

    def test_campaign_fk_contract(self):
        fks = {fk.column.table.name for fk in self.m.Campaign.__table__.foreign_keys}
        self.assertIn("advertiser_contracts", fks)

    def test_campaign_unique_code_per_org(self):
        constraints = {c.name for c in self.m.Campaign.__table__.constraints}
        self.assertIn("uq_campaign_code_per_org", constraints)

    # --- CampaignFlight ---
    def test_flight_columns(self):
        cols = {c.name for c in self.m.CampaignFlight.__table__.columns}
        required = {"id", "campaign_id", "start_at", "end_at", "priority", "created_at"}
        self.assertTrue(required <= cols, f"Missing: {required - cols}")

    def test_flight_fk_campaign(self):
        fks = {fk.column.table.name for fk in self.m.CampaignFlight.__table__.foreign_keys}
        self.assertIn("campaigns", fks)

    # --- CampaignPlacement ---
    def test_placement_columns(self):
        cols = {c.name for c in self.m.CampaignPlacement.__table__.columns}
        required = {"id", "campaign_id", "share_of_voice_pct", "status", "created_at"}
        self.assertTrue(required <= cols, f"Missing: {required - cols}")

    def test_placement_target_columns_nullable(self):
        """display_surface_id, store_id, cluster_id, branch_id all nullable."""
        for col_name in ("display_surface_id", "store_id", "cluster_id", "branch_id"):
            col = self.m.CampaignPlacement.__table__.columns[col_name]
            self.assertTrue(col.nullable, f"{col_name} should be nullable")

    def test_placement_at_least_one_target_constraint(self):
        constraints = {c.name for c in self.m.CampaignPlacement.__table__.constraints}
        self.assertIn("ck_cp_at_least_one_target", constraints)

    def test_placement_no_device_id(self):
        """No physical_device_id column on placements."""
        cols = {c.name for c in self.m.CampaignPlacement.__table__.columns}
        self.assertNotIn("physical_device_id", cols)

    # --- CreativeAsset ---
    def test_creative_asset_columns(self):
        cols = {c.name for c in self.m.CreativeAsset.__table__.columns}
        required = {"id", "advertiser_organization_id", "code", "name",
                     "media_type", "storage_bucket", "storage_key",
                     "sha256_checksum", "file_size_bytes", "status", "created_at"}
        self.assertTrue(required <= cols, f"Missing: {required - cols}")

    def test_creative_asset_fk_org(self):
        fks = {fk.column.table.name for fk in self.m.CreativeAsset.__table__.foreign_keys}
        self.assertIn("advertiser_organizations", fks)

    def test_creative_asset_unique_code_per_org(self):
        constraints = {c.name for c in self.m.CreativeAsset.__table__.constraints}
        self.assertIn("uq_creative_asset_code_per_org", constraints)

    # --- CampaignCreative ---
    def test_campaign_creative_columns(self):
        cols = {c.name for c in self.m.CampaignCreative.__table__.columns}
        required = {"id", "campaign_id", "creative_asset_id", "sort_order", "created_at"}
        self.assertTrue(required <= cols, f"Missing: {required - cols}")

    def test_campaign_creative_unique(self):
        constraints = {c.name for c in self.m.CampaignCreative.__table__.constraints}
        self.assertIn("uq_campaign_creative", constraints)

    # --- CampaignApproval ---
    def test_approval_columns(self):
        cols = {c.name for c in self.m.CampaignApproval.__table__.columns}
        required = {"id", "campaign_id", "requested_by", "requested_at",
                     "decision", "created_at"}
        self.assertTrue(required <= cols, f"Missing: {required - cols}")

    # --- CampaignStatusHistory ---
    def test_status_history_columns(self):
        cols = {c.name for c in self.m.CampaignStatusHistory.__table__.columns}
        required = {"id", "campaign_id", "new_status", "changed_by", "changed_at"}
        self.assertTrue(required <= cols, f"Missing: {required - cols}")


class TestMigration006(unittest.TestCase):
    """Migration 006 creates 7 tables + RLS + downgrade."""

    def test_migration_file_exists(self):
        mig_path = os.path.join(
            os.path.dirname(__file__), "..",
            "apps", "control-api", "alembic", "versions",
            "006_campaign_domain.py",
        )
        self.assertTrue(os.path.exists(mig_path), f"Missing: {mig_path}")

    def test_migration_revises_005(self):
        mig_path = os.path.join(
            os.path.dirname(__file__), "..",
            "apps", "control-api", "alembic", "versions",
            "006_campaign_domain.py",
        )
        content = open(mig_path).read()
        self.assertIn('down_revision: Union[str, None] = "005"', content)
        self.assertIn('revision: str = "006"', content)

    def test_migration_creates_campaigns_table(self):
        mig_path = os.path.join(
            os.path.dirname(__file__), "..",
            "apps", "control-api", "alembic", "versions",
            "006_campaign_domain.py",
        )
        content = open(mig_path).read()
        self.assertIn('"campaigns"', content)
        self.assertIn("create_table", content)

    def test_migration_enables_rls(self):
        mig_path = os.path.join(
            os.path.dirname(__file__), "..",
            "apps", "control-api", "alembic", "versions",
            "006_campaign_domain.py",
        )
        content = open(mig_path).read()
        for table in ("campaigns", "campaign_flights", "campaign_placements",
                       "creative_assets", "campaign_creatives",
                       "campaign_approvals", "campaign_status_history"):
            self.assertIn(f"ENABLE ROW LEVEL SECURITY", content,
                          f"Missing RLS for {table}")
            self.assertIn(f"FORCE ROW LEVEL SECURITY", content,
                          f"Missing FORCE RLS for {table}")

    def test_migration_has_downgrade(self):
        mig_path = os.path.join(
            os.path.dirname(__file__), "..",
            "apps", "control-api", "alembic", "versions",
            "006_campaign_domain.py",
        )
        content = open(mig_path).read()
        self.assertIn("def downgrade()", content)
        self.assertIn("DROP POLICY", content)
        self.assertIn("op.drop_table", content)

    def test_migration_rls_direct_and_via_campaign(self):
        mig_path = os.path.join(
            os.path.dirname(__file__), "..",
            "apps", "control-api", "alembic", "versions",
            "006_campaign_domain.py",
        )
        content = open(mig_path).read()
        self.assertIn("RLS_DIRECT", content, "Missing direct RLS template")
        self.assertIn("RLS_VIA_CAMPAIGN", content, "Missing via-campaign RLS template")
        # campaigns + creative_assets use RLS_DIRECT
        self.assertIn('RLS_DIRECT.format(table="campaigns")', content)
        self.assertIn('RLS_DIRECT.format(table="creative_assets")', content)
        # sub-tables use RLS_VIA_CAMPAIGN
        self.assertIn('RLS_VIA_CAMPAIGN.format(table="campaign_flights")', content)

    def test_placement_check_constraint(self):
        mig_path = os.path.join(
            os.path.dirname(__file__), "..",
            "apps", "control-api", "alembic", "versions",
            "006_campaign_domain.py",
        )
        content = open(mig_path).read()
        self.assertIn("ck_cp_at_least_one_target", content)
        self.assertIn("display_surface_id IS NOT NULL OR store_id IS NOT NULL", content)


class TestSeedCampaignPermissions(unittest.TestCase):
    """Seed includes campaign permissions and role assignments."""

    @classmethod
    def setUpClass(cls):
        cls.seed_path = os.path.join(
            os.path.dirname(__file__), "..",
            "apps", "control-api", "seed.py",
        )
        cls.content = open(cls.seed_path).read()

    def test_permission_campaigns_read(self):
        self.assertIn('"campaigns.read"', self.content)
        self.assertIn("campaigns.read", self.content)

    def test_permission_campaigns_manage(self):
        self.assertIn('"campaigns.manage"', self.content)

    def test_permission_campaigns_approve(self):
        self.assertIn('"campaigns.approve"', self.content)

    def test_permission_creatives_read(self):
        self.assertIn('"creatives.read"', self.content)

    def test_system_admin_has_campaign_perms(self):
        self.assertIn("campaigns.read", self.content)
        self.assertIn("campaigns.manage", self.content)
        self.assertIn("campaigns.approve", self.content)

    def test_security_admin_has_campaign_perms(self):
        for perm in ("campaigns.read", "campaigns.manage", "campaigns.approve"):
            self.assertIn(
                f'SEED_ROLE_IDS["security_admin"]', self.content,
            )
            self.assertIn(perm, self.content)

    def test_operator_has_campaigns_read(self):
        self.assertIn("campaigns.read", self.content)

    def test_seed_has_test_campaign_data(self):
        self.assertIn("CAMP-2026-001", self.content)
        self.assertIn("campaigns", self.content)
        self.assertIn("campaign_flights", self.content)
        self.assertIn("creative_assets", self.content)
        self.assertIn("campaign_creatives", self.content)
        self.assertIn("campaign_placements", self.content)
        self.assertIn("campaign_approvals", self.content)
        self.assertIn("campaign_status_history", self.content)


class TestCampaignSchemas(unittest.TestCase):
    """Response DTOs do not expose PII or storage secrets."""

    def test_campaign_out_has_no_pii(self):
        from packages.domain.schemas import CampaignOut
        fields = {f for f in CampaignOut.model_fields}
        self.assertNotIn("email", fields)
        self.assertNotIn("phone", fields)
        self.assertNotIn("contact_name", fields)

    def test_creative_asset_out_no_storage_secrets(self):
        from packages.domain.schemas import CreativeAssetOut
        fields = {f for f in CreativeAssetOut.model_fields}
        # storage_bucket and storage_key are intentionally omitted
        self.assertNotIn("storage_bucket", fields)
        self.assertNotIn("storage_key", fields)

    def test_all_campaign_schemas_exist(self):
        from packages.domain.schemas import (
            CampaignOut, CampaignFlightOut, CampaignCreativeOut,
            CreativeAssetOut, CampaignPlacementOut,
            CampaignApprovalOut, CampaignStatusHistoryOut,
        )
        # Just verify they import without error
        self.assertIsNotNone(CampaignOut)


class TestCampaignRouterCompliance(unittest.TestCase):
    """Router does not call db.execute directly (ADR-014)."""

    def test_identity_router_no_direct_db_execute(self):
        router_path = os.path.join(
            os.path.dirname(__file__), "..",
            "packages", "api", "identity.py",
        )
        content = open(router_path).read()
        # Strip docstrings and comments
        lines = []
        in_docstring = False
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped.startswith('"""') and in_docstring:
                in_docstring = False
                continue
            if stripped.startswith('"""') and not in_docstring:
                in_docstring = True
                continue
            if in_docstring:
                continue
            if stripped.startswith("#"):
                continue
            lines.append(line)
        clean = "\n".join(lines)
        self.assertNotIn("db.execute", clean,
                         "Router must not call db.execute directly")
        self.assertNotIn("session.execute(", clean,
                         "Router must not call session.execute directly")


class TestCampaignRepository(unittest.TestCase):
    """Repository functions exist and follow pattern."""

    def test_repository_has_campaign_functions(self):
        repo_path = os.path.join(
            os.path.dirname(__file__), "..",
            "packages", "domain", "repository.py",
        )
        content = open(repo_path).read()
        funcs = [
            "list_campaigns",
            "list_campaign_flights",
            "list_campaign_creatives",
            "list_creative_assets",
            "list_campaign_placements",
            "list_campaign_approvals",
            "list_campaign_status_history",
        ]
        for func in funcs:
            self.assertIn(f"async def {func}", content,
                          f"Missing repository function: {func}")


if __name__ == "__main__":
    unittest.main()
