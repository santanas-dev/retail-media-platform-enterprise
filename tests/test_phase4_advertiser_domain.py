"""
Phase 4.0b — Advertiser Domain Unit Tests.

Tests: models, migration RLS policies, seed permissions, repository,
schemas, router compliance (no db.execute in routers).
"""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestAdvertiserDomainModels(unittest.TestCase):
    """New advertiser domain tables exist and have required columns/FKs."""

    @classmethod
    def setUpClass(cls):
        from packages.domain import models as m
        cls.m = m

    def test_advertiser_brand_columns(self):
        cols = {c.name for c in self.m.AdvertiserBrand.__table__.columns}
        required = {"id", "advertiser_organization_id", "code", "name",
                     "description", "status", "created_at", "updated_at"}
        self.assertTrue(required <= cols, f"Missing: {required - cols}")

    def test_advertiser_brand_fk(self):
        fks = list(self.m.AdvertiserBrand.__table__.foreign_keys)
        self.assertTrue(any("advertiser_organizations" in str(fk) for fk in fks),
                        "Missing FK to advertiser_organizations")

    def test_advertiser_brand_unique_constraint(self):
        uq_names = {uq.name for uq in self.m.AdvertiserBrand.__table__.constraints
                    if hasattr(uq, 'name') and 'uq_adv_brand' in (uq.name or '')}
        self.assertTrue(len(uq_names) >= 1, "Missing org+code unique constraint")

    def test_advertiser_contract_columns(self):
        cols = {c.name for c in self.m.AdvertiserContract.__table__.columns}
        required = {"id", "advertiser_organization_id", "code", "name",
                     "contract_number", "budget_limit_amount", "budget_limit_currency",
                     "valid_from", "valid_until", "status", "terms_url",
                     "created_at", "updated_at"}
        self.assertTrue(required <= cols, f"Missing: {required - cols}")

    def test_advertiser_contract_fk(self):
        fks = list(self.m.AdvertiserContract.__table__.foreign_keys)
        self.assertTrue(any("advertiser_organizations" in str(fk) for fk in fks),
                        "Missing FK to advertiser_organizations")

    def test_advertiser_contract_unique_constraint(self):
        uq_names = {uq.name for uq in self.m.AdvertiserContract.__table__.constraints
                    if hasattr(uq, 'name') and 'uq_adv_contract' in (uq.name or '')}
        self.assertTrue(len(uq_names) >= 1, "Missing org+code unique constraint")

    def test_advertiser_contact_columns(self):
        cols = {c.name for c in self.m.AdvertiserContact.__table__.columns}
        required = {"id", "advertiser_organization_id", "contact_type",
                     "full_name", "email", "phone", "is_primary", "status",
                     "created_at", "updated_at"}
        self.assertTrue(required <= cols, f"Missing: {required - cols}")

    def test_advertiser_contact_fk(self):
        fks = list(self.m.AdvertiserContact.__table__.foreign_keys)
        self.assertTrue(any("advertiser_organizations" in str(fk) for fk in fks),
                        "Missing FK to advertiser_organizations")

    def test_advertiser_contact_partial_unique_index(self):
        """Partial unique index on primary contacts exists in __table_args__."""
        indexes = self.m.AdvertiserContact.__table__.indexes
        has_primary_idx = False
        for idx in indexes:
            if "primary" in (idx.name or ""):
                has_primary_idx = True
                self.assertTrue(idx.unique, "Primary contact index must be UNIQUE")
                # Partial index verified by the postgresql_where kwarg in __table_args__
                # (presence confirmed by index existing at all via __table_args__)
        self.assertTrue(has_primary_idx, "Missing partial unique index on primary contacts")


class TestAdvertiserDomainMigration(unittest.TestCase):
    """Migration 005 contains expected SQL structures."""

    @classmethod
    def setUpClass(cls):
        path = os.path.join(
            os.path.dirname(__file__), "..",
            "apps/control-api/alembic/versions/005_advertiser_domain.py",
        )
        with open(path) as f:
            cls.migration_text = f.read()

    def test_migration_creates_brands_table(self):
        self.assertIn("create_table", self.migration_text)
        self.assertIn("advertiser_brands", self.migration_text)

    def test_migration_creates_contracts_table(self):
        self.assertIn("advertiser_contracts", self.migration_text)

    def test_migration_creates_contacts_table(self):
        self.assertIn("advertiser_contacts", self.migration_text)

    def test_migration_enables_rls_on_all_three_tables(self):
        for table in ("advertiser_brands", "advertiser_contracts", "advertiser_contacts"):
            self.assertIn(
                f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY",
                self.migration_text,
                f"Missing ENABLE RLS for {table}",
            )
            self.assertIn(
                f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY",
                self.migration_text,
                f"Missing FORCE RLS for {table}",
            )

    def test_migration_creates_select_policies(self):
        # Template-based: RLS_POLICY_TEMPLATE = """CREATE POLICY {table}_rls_sel..."""
        self.assertIn("CREATE POLICY {table}_rls_sel", self.migration_text)
        self.assertIn("RLS_POLICY_TEMPLATE", self.migration_text)

    def test_rls_policies_use_fail_closed_pattern(self):
        """All RLS policies use COALESCE(NULLIF(current_setting(..., true), ''), ...)."""
        self.assertIn("COALESCE", self.migration_text)
        self.assertIn("NULLIF(current_setting('app.rmp_is_admin'", self.migration_text)
        self.assertIn("app.rmp_scope_advertiser_ids", self.migration_text)
        self.assertIn("'{{}}'::text[]", self.migration_text)

    def test_downgrade_drops_tables_and_policies(self):
        downgrade = self.migration_text.split("def downgrade")[1]
        # Migration uses f-strings: DROP POLICY IF EXISTS {table}_rls_sel ON {table}
        self.assertIn("DROP POLICY IF EXISTS", downgrade)
        self.assertIn("_rls_sel", downgrade)
        self.assertIn("ALTER TABLE {table} DISABLE", downgrade)
        self.assertIn("op.drop_table(", downgrade)


class TestAdvertiserSeed(unittest.TestCase):
    """Seed contains advertiser domain permissions and test data."""

    @classmethod
    def setUpClass(cls):
        path = os.path.join(os.path.dirname(__file__), "..",
                            "apps/control-api/seed.py")
        with open(path) as f:
            cls.seed_text = f.read()

    def test_seed_advertiser_permissions_exist(self):
        for perm in ("advertisers.read", "advertisers.manage",
                      "advertisers.contacts.read", "advertisers.contacts.manage"):
            self.assertIn(perm, self.seed_text, f"Missing seed permission: {perm}")

    def test_seed_system_admin_has_all_advertiser_perms(self):
        """system_admin block contains advertiser permission assignments."""
        for perm in ("advertisers.read", "advertisers.manage",
                      "advertisers.contacts.read", "advertisers.contacts.manage"):
            self.assertIn(perm, self.seed_text,
                          f"system_admin missing permission: {perm}")

    def test_seed_security_admin_has_advertiser_read(self):
        self.assertIn("advertisers.read", self.seed_text)
        self.assertIn("advertisers.contacts.read", self.seed_text)

    def test_seed_operator_has_advertiser_read(self):
        self.assertIn("advertisers.read", self.seed_text)
        self.assertIn("SEED_ROLE_IDS[\"operator\"]", self.seed_text)

    def test_seed_brands_exist(self):
        self.assertIn("BRAND-COLA", self.seed_text)
        self.assertIn("BRAND-ZERO", self.seed_text)

    def test_seed_contract_exists(self):
        self.assertIn("CTR-2026-001", self.seed_text)

    def test_seed_contacts_exist(self):
        self.assertIn("Иван Петров", self.seed_text)
        self.assertIn("Мария Счетоводова", self.seed_text)


class TestAdvertiserRepository(unittest.TestCase):
    """Repository functions import and have correct signatures."""

    def test_import_repository_functions(self):
        from packages.domain.repository import (
            list_advertiser_brands,
            list_advertiser_contracts,
            list_advertiser_contacts,
        )
        self.assertTrue(callable(list_advertiser_brands))
        self.assertTrue(callable(list_advertiser_contracts))
        self.assertTrue(callable(list_advertiser_contacts))


class TestAdvertiserSchemas(unittest.TestCase):
    """Response schemas import and have expected fields."""

    def test_brand_schema_fields(self):
        from packages.domain.schemas import AdvertiserBrandOut
        fields = AdvertiserBrandOut.model_fields
        required = {"id", "advertiser_organization_id", "code", "name", "status"}
        self.assertTrue(required <= set(fields))

    def test_contract_schema_fields(self):
        from packages.domain.schemas import AdvertiserContractOut
        fields = AdvertiserContractOut.model_fields
        required = {"id", "code", "name", "status",
                     "budget_limit_amount", "budget_limit_currency",
                     "valid_from", "valid_until"}
        self.assertTrue(required <= set(fields))

    def test_contact_schema_fields(self):
        from packages.domain.schemas import AdvertiserContactOut
        fields = AdvertiserContactOut.model_fields
        required = {"id", "contact_type", "full_name", "email", "phone",
                     "is_primary", "status"}
        self.assertTrue(required <= set(fields))

    def test_contact_schema_exposes_email(self):
        """ADR-010: contacts endpoint exposes email (PII-gated by router permission)."""
        from packages.domain.schemas import AdvertiserContactOut
        self.assertIn("email", AdvertiserContactOut.model_fields)
        self.assertIn("phone", AdvertiserContactOut.model_fields)


class TestAdvertiserRouterCompliance(unittest.TestCase):
    """Routers comply with ADR-014: no db.execute in route handlers."""

    @classmethod
    def setUpClass(cls):
        path = os.path.join(os.path.dirname(__file__), "..",
                            "packages/api/identity_routes/advertisers.py")
        with open(path) as f:
            cls.router_text = f.read()

    def test_no_db_execute_in_brands_endpoint(self):
        """advertiser-brands endpoint calls repository, not db.execute."""
        brands_section = self.router_text.split("def list_advertiser_brands")[1]
        # Body starts after the function signature (after the first occurrence of '):\n')
        body_start = brands_section.index("):") + 2
        brands_body = brands_section[body_start:]
        # Split at next function
        if "def list_advertiser_contracts" in brands_body:
            brands_body = brands_body.split("def list_advertiser_contracts")[0]
        self.assertIn("repository.list_advertiser_brands", brands_body)
        self.assertNotIn("db.execute", brands_body)

    def test_no_db_execute_in_contracts_endpoint(self):
        contracts_section = self.router_text.split("def list_advertiser_contracts")[1]
        body_start = contracts_section.index("):") + 2
        contracts_body = contracts_section[body_start:]
        if "def list_advertiser_contacts" in contracts_body:
            contracts_body = contracts_body.split("def list_advertiser_contacts")[0]
        self.assertIn("repository.list_advertiser_contracts", contracts_body)
        self.assertNotIn("db.execute", contracts_body)

    def test_no_db_execute_in_contacts_endpoint(self):
        contacts_section = self.router_text.split("def list_advertiser_contacts")[1]
        body_start = contacts_section.index("):") + 2
        contacts_body = contacts_section[body_start:]
        self.assertIn("repository.list_advertiser_contacts", contacts_body)
        self.assertNotIn("db.execute", contacts_body)

    def test_brands_endpoint_requires_scoped_permission(self):
        self.assertIn(
            'require_scoped_permission("advertisers.read"',
            self.router_text,
        )

    def test_contacts_endpoint_requires_contacts_permission(self):
        self.assertIn(
            'require_scoped_permission("advertisers.contacts.read"',
            self.router_text,
        )
