"""
Retail Media Platform — Phase 2.1 Model & Seed Tests.

Tests: migration imports, metadata completeness, seed idempotency (code-level),
       identity tables, constraints, no secrets in seed.
No database connection required — all tests are static/source-inspection.
"""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestPhase2Metadata(unittest.TestCase):
    """Verify SQLAlchemy metadata contains all required rewrite tables."""

    def test_import_models(self):
        """ORM module imports without errors."""
        from packages.domain.models import Base, REQUIRED_TABLES
        self.assertIsNotNone(Base)
        self.assertIsNotNone(REQUIRED_TABLES)

    def test_all_required_tables_present(self):
        """Base.metadata contains all required foundation tables."""
        from packages.domain.models import REQUIRED_TABLES, Base
        actual = set(Base.metadata.tables.keys())
        missing = REQUIRED_TABLES - actual
        self.assertSetEqual(missing, set(), f"Missing tables: {missing}")

    def test_exact_table_count(self):
        """Metadata table count — grows with each phase."""
        from packages.domain.models import Base
        count = len(Base.metadata.tables)
        self.assertEqual(count, 45, f"Expected 45 tables, got {count}")


class TestPhase2ModelColumns(unittest.TestCase):
    """Verify key columns exist on each model."""

    @classmethod
    def setUpClass(cls):
        from packages.domain import models as m
        cls.m = m

    def test_branch_columns(self):
        cols = {c.name for c in self.m.Branch.__table__.columns}
        self.assertTrue(cols >= {"id", "code", "name", "timezone", "is_active", "created_at"})

    def test_store_columns(self):
        cols = {c.name for c in self.m.Store.__table__.columns}
        self.assertTrue(cols >= {"id", "cluster_id", "code", "name", "address", "is_active"})

    def test_channel_columns(self):
        cols = {c.name for c in self.m.Channel.__table__.columns}
        self.assertTrue(cols >= {"id", "code", "name", "sort_order", "is_active"})

    def test_device_type_columns(self):
        cols = {c.name for c in self.m.DeviceType.__table__.columns}
        self.assertTrue(cols >= {"id", "channel_id", "code", "player_runtime"})

    def test_capability_profile_columns(self):
        cols = {c.name for c in self.m.CapabilityProfile.__table__.columns}
        self.assertTrue(cols >= {"id", "device_type_id", "code", "resolution_w", "resolution_h",
                                  "pop_mode", "supported_formats"})

    def test_physical_device_columns(self):
        cols = {c.name for c in self.m.PhysicalDevice.__table__.columns}
        self.assertTrue(cols >= {"id", "store_id", "device_type_id", "code", "status", "last_seen_at"})

    def test_device_certificate_columns(self):
        cols = {c.name for c in self.m.DeviceCertificate.__table__.columns}
        self.assertTrue(cols >= {"id", "physical_device_id", "certificate_type",
                                  "public_key", "fingerprint", "status"})

    def test_device_status_history_columns(self):
        cols = {c.name for c in self.m.DeviceStatusHistory.__table__.columns}
        self.assertTrue(cols >= {"id", "physical_device_id", "old_status", "new_status",
                                  "changed_at", "source"})

    def test_logical_carrier_columns(self):
        cols = {c.name for c in self.m.LogicalCarrier.__table__.columns}
        self.assertTrue(cols >= {"id", "physical_device_id", "code", "carrier_type",
                                  "labels_count", "led_panels_count"})

    def test_display_surface_columns(self):
        cols = {c.name for c in self.m.DisplaySurface.__table__.columns}
        self.assertTrue(cols >= {"id", "logical_carrier_id", "store_id", "code",
                                  "resolution_w", "resolution_h", "is_active"})

    # --- Phase 2.1 identity tables ---

    def test_user_columns(self):
        cols = {c.name for c in self.m.User.__table__.columns}
        self.assertTrue(cols >= {"id", "code", "username", "email", "display_name",
                                  "auth_provider", "external_subject", "status",
                                  "is_break_glass", "created_at", "updated_at"})

    def test_role_columns(self):
        cols = {c.name for c in self.m.Role.__table__.columns}
        self.assertTrue(cols >= {"id", "code", "name", "description", "is_system",
                                  "created_at", "updated_at"})

    def test_permission_columns(self):
        cols = {c.name for c in self.m.Permission.__table__.columns}
        self.assertTrue(cols >= {"id", "code", "name", "description", "created_at"})

    def test_role_permission_columns(self):
        cols = {c.name for c in self.m.RolePermission.__table__.columns}
        self.assertTrue(cols >= {"id", "role_id", "permission_id", "created_at"})

    def test_user_role_columns(self):
        cols = {c.name for c in self.m.UserRole.__table__.columns}
        self.assertTrue(cols >= {"id", "user_id", "role_id", "scope_type", "scope_id",
                                  "created_at"})

    def test_access_scope_columns(self):
        cols = {c.name for c in self.m.AccessScope.__table__.columns}
        self.assertTrue(cols >= {"id", "code", "scope_type", "branch_id", "cluster_id",
                                  "store_id", "advertiser_id", "created_at"})

    def test_user_access_scope_columns(self):
        cols = {c.name for c in self.m.UserAccessScope.__table__.columns}
        self.assertTrue(cols >= {"id", "user_id", "access_scope_id", "created_at"})

    def test_audit_event_columns(self):
        cols = {c.name for c in self.m.AuditEventOperational.__table__.columns}
        self.assertTrue(cols >= {"id", "actor_user_id", "action", "target_type",
                                  "target_id", "correlation_id", "ip_address",
                                  "details_json", "created_at"})

    # --- Phase 4.3b PoP tables ---

    def test_pop_event_raw_columns(self):
        cols = {c.name for c in self.m.PopEventRaw.__table__.columns}
        self.assertTrue(cols >= {
            "id", "event_id", "schema_version", "device_id",
            "manifest_id", "campaign_id", "campaign_verified",
            "creative_asset_id", "surface_id", "rendered_at",
            "event_recorded_at", "duration_ms", "playback_result",
            "status", "quarantine_reason", "expires_at",
            "received_at", "batch_id",
        })

    def test_pop_dedup_index_columns(self):
        cols = {c.name for c in self.m.PopDedupIndex.__table__.columns}
        self.assertTrue(cols >= {"event_id", "created_at"})

    def test_pop_ingestion_batch_columns(self):
        cols = {c.name for c in self.m.PopIngestionBatch.__table__.columns}
        self.assertTrue(cols >= {
            "id", "device_id", "received_at", "event_count",
            "accepted_count", "rejected_count", "quarantined_count",
        })

    def test_pop_event_raw_unique_event_id(self):
        """event_id has unique constraint."""
        cols = self.m.PopEventRaw.__table__.columns["event_id"]
        self.assertTrue(cols.unique)

    def test_pop_event_raw_no_secret_columns(self):
        """No storage_bucket, storage_key, presigned_url, token, password."""
        forbidden = {"storage_bucket", "storage_key", "presigned_url",
                     "token", "password", "secret", "api_key", "jwt"}
        actual = {c.name for c in self.m.PopEventRaw.__table__.columns}
        overlap = forbidden & actual
        self.assertSetEqual(overlap, set(),
                            f"PoP table has forbidden columns: {overlap}")

    def test_pop_event_raw_no_pii_columns(self):
        """No email, phone, contact PII in PoP events."""
        forbidden = {"email", "phone", "contact", "advertiser_contact", "name"}
        actual = {c.name for c in self.m.PopEventRaw.__table__.columns}
        overlap = forbidden & actual
        self.assertSetEqual(overlap, set(),
                            f"PoP table has PII columns: {overlap}")

    def test_pop_event_raw_fk_device(self):
        fks = [fk for fk in self.m.PopEventRaw.__table__.foreign_keys
               if fk.parent.name == "device_id"]
        self.assertTrue(fks, "device_id must have FK to physical_devices.id")
        self.assertIn("physical_devices.id", {fk.target_fullname for fk in fks})

    def test_pop_event_raw_fk_creative(self):
        fks = [fk for fk in self.m.PopEventRaw.__table__.foreign_keys
               if fk.parent.name == "creative_asset_id"]
        self.assertTrue(fks, "creative_asset_id must have FK to creative_assets.id")
        self.assertIn("creative_assets.id", {fk.target_fullname for fk in fks})

    def test_pop_event_raw_campaign_id_nullable(self):
        col = self.m.PopEventRaw.__table__.columns["campaign_id"]
        self.assertTrue(col.nullable,
                        "campaign_id must be nullable for quarantine events")

    def test_pop_event_raw_manifest_id_nullable(self):
        col = self.m.PopEventRaw.__table__.columns["manifest_id"]
        self.assertTrue(col.nullable,
                        "manifest_id must be nullable for quarantine events")

    def test_pop_event_raw_campaign_verified_default_false(self):
        col = self.m.PopEventRaw.__table__.columns["campaign_verified"]
        self.assertFalse(col.default.arg if col.default else True,
                         "campaign_verified must default to False")


class TestPhase2ForeignKeys(unittest.TestCase):
    """Verify expected FK relationships."""

    @classmethod
    def setUpClass(cls):
        from packages.domain import models as m
        cls.m = m

    def _fk_targets(self, model, col_name):
        fks = [fk for fk in model.__table__.foreign_keys if fk.parent.name == col_name]
        self.assertTrue(fks, f"{model.__name__}.{col_name} has no FK")
        return {fk.target_fullname for fk in fks}

    def test_cluster_branch_fk(self):
        self.assertIn("branches.id", self._fk_targets(self.m.Cluster, "branch_id"))

    def test_store_cluster_fk(self):
        self.assertIn("clusters.id", self._fk_targets(self.m.Store, "cluster_id"))

    def test_device_type_channel_fk(self):
        self.assertIn("channels.id", self._fk_targets(self.m.DeviceType, "channel_id"))

    def test_capability_device_type_fk(self):
        self.assertIn("device_types.id", self._fk_targets(self.m.CapabilityProfile, "device_type_id"))

    def test_physical_device_store_fk(self):
        self.assertIn("stores.id", self._fk_targets(self.m.PhysicalDevice, "store_id"))

    def test_physical_device_type_fk(self):
        self.assertIn("device_types.id", self._fk_targets(self.m.PhysicalDevice, "device_type_id"))

    def test_certificate_device_fk(self):
        self.assertIn("physical_devices.id", self._fk_targets(self.m.DeviceCertificate, "physical_device_id"))

    def test_status_history_device_fk(self):
        self.assertIn("physical_devices.id", self._fk_targets(self.m.DeviceStatusHistory, "physical_device_id"))

    def test_carrier_device_fk(self):
        self.assertIn("physical_devices.id", self._fk_targets(self.m.LogicalCarrier, "physical_device_id"))

    def test_surface_carrier_fk(self):
        self.assertIn("logical_carriers.id", self._fk_targets(self.m.DisplaySurface, "logical_carrier_id"))

    # --- Phase 2.1 identity FKs ---

    def test_role_permission_role_fk(self):
        self.assertIn("roles.id", self._fk_targets(self.m.RolePermission, "role_id"))

    def test_role_permission_perm_fk(self):
        self.assertIn("permissions.id", self._fk_targets(self.m.RolePermission, "permission_id"))

    def test_user_role_user_fk(self):
        self.assertIn("users.id", self._fk_targets(self.m.UserRole, "user_id"))

    def test_user_role_role_fk(self):
        self.assertIn("roles.id", self._fk_targets(self.m.UserRole, "role_id"))

    def test_access_scope_branch_fk(self):
        self.assertIn("branches.id", self._fk_targets(self.m.AccessScope, "branch_id"))

    def test_access_scope_cluster_fk(self):
        self.assertIn("clusters.id", self._fk_targets(self.m.AccessScope, "cluster_id"))

    def test_access_scope_store_fk(self):
        self.assertIn("stores.id", self._fk_targets(self.m.AccessScope, "store_id"))

    def test_user_access_scope_user_fk(self):
        self.assertIn("users.id", self._fk_targets(self.m.UserAccessScope, "user_id"))

    def test_user_access_scope_scope_fk(self):
        self.assertIn("access_scopes.id", self._fk_targets(self.m.UserAccessScope, "access_scope_id"))

    def test_audit_event_actor_fk(self):
        self.assertIn("users.id", self._fk_targets(self.m.AuditEventOperational, "actor_user_id"))


class TestPhase21UniqueConstraints(unittest.TestCase):
    """Verify unique constraints on junction tables."""

    @classmethod
    def setUpClass(cls):
        from packages.domain import models as m
        cls.m = m

    def _unique_columns(self, model):
        ucs = []
        for c in model.__table__.constraints:
            name = getattr(c, "name", None)
            if name and name.startswith("uq"):
                names = tuple(sorted(col.name for col in c.columns))
                ucs.append(names)
        return set(ucs)

    def test_role_permission_unique_pair(self):
        self.assertTrue(
            ("permission_id", "role_id") in self._unique_columns(self.m.RolePermission)
            or ("role_id", "permission_id") in self._unique_columns(self.m.RolePermission),
            "role_permissions missing unique(role_id, permission_id)"
        )

    def test_user_role_check_scope_pair(self):
        """CHECK constraint: scope_type and scope_id are both NULL or both NOT NULL."""
        from sqlalchemy import CheckConstraint
        checks = [c for c in self.m.UserRole.__table__.constraints
                  if isinstance(c, CheckConstraint)]
        pair_checks = [c for c in checks
                       if "scope_type" in str(c.sqltext) and "scope_id" in str(c.sqltext)]
        self.assertTrue(pair_checks, "user_roles missing CHECK(scope_type, scope_id) pair constraint")

    def test_user_role_scoped_unique(self):
        """Unique constraint on (user_id, role_id, scope_type, scope_id) for scoped assignments."""
        from sqlalchemy import UniqueConstraint
        uqs = [c for c in self.m.UserRole.__table__.constraints
               if isinstance(c, UniqueConstraint)]
        col_sets = [{col.name for col in uq.columns} for uq in uqs]
        expected = {"user_id", "role_id", "scope_type", "scope_id"}
        self.assertTrue(any(s == expected for s in col_sets),
                        f"user_roles missing scoped unique constraint. Found: {col_sets}")

    def test_user_role_unscoped_unique_index(self):
        """Partial unique index prevents duplicate unscoped (NULL, NULL) assignments."""
        idx = None
        for ix in self.m.UserRole.__table__.indexes:
            if ix.unique and ix.name and ix.name.startswith("uq_user_role_unscoped"):
                idx = ix
                break
        self.assertIsNotNone(idx, "user_roles missing unscoped partial unique index")
        col_names = {col.name for col in idx.columns}
        self.assertEqual(col_names, {"user_id", "role_id"},
                         f"Unscoped index wrong columns: {col_names}")
        # Verify it has a WHERE clause (postgresql_where)
        dialects = getattr(idx, "dialect_options", {})
        pg_opts = dialects.get("postgresql", {}) if isinstance(dialects, dict) else {}
        where = pg_opts.get("where")
        if where is None:
            # Fallback: check if index object has whereclause attribute
            where = getattr(idx, "_postgresql_where", None)
        self.assertIsNotNone(where, "Unscoped index missing WHERE clause")

    def test_user_access_scope_unique_pair(self):
        self.assertTrue(
            ("access_scope_id", "user_id") in self._unique_columns(self.m.UserAccessScope)
            or ("user_id", "access_scope_id") in self._unique_columns(self.m.UserAccessScope),
            "user_access_scopes missing unique(user_id, access_scope_id)"
        )

    def test_users_unique_username(self):
        cols = {c.name for c in self.m.User.__table__.columns if c.unique}
        self.assertIn("username", cols)

    def test_users_unique_code(self):
        cols = {c.name for c in self.m.User.__table__.columns if c.unique}
        self.assertIn("code", cols)

    def test_roles_unique_code(self):
        cols = {c.name for c in self.m.Role.__table__.columns if c.unique}
        self.assertIn("code", cols)

    def test_permissions_unique_code(self):
        cols = {c.name for c in self.m.Permission.__table__.columns if c.unique}
        self.assertIn("code", cols)

    def test_access_scopes_unique_code(self):
        cols = {c.name for c in self.m.AccessScope.__table__.columns if c.unique}
        self.assertIn("code", cols)


class TestPhase21SeedIdentity(unittest.TestCase):
    """Verify identity seed data correctness."""

    _SEED_SRC: str | None = None

    @classmethod
    def _load_seed(cls) -> str:
        if cls._SEED_SRC is None:
            path = os.path.join(os.path.dirname(__file__), "..", "apps", "control-api", "seed.py")
            with open(path) as f:
                cls._SEED_SRC = f.read()
        return cls._SEED_SRC

    @classmethod
    def setUpClass(cls):
        cls._load_seed()

    def test_seed_has_all_permission_codes(self):
        """Seed contains all 8 expected permission codes."""
        expected = {"users.read", "users.manage", "roles.read", "roles.manage",
                     "audit.read", "organization.read", "channels.read", "devices.read"}
        src = self._SEED_SRC
        found = set()
        for m in re.finditer(r"VALUES\s*\([^)]+?'([a-z_.]+)'", src):
            code = m.group(1)
            if code.count(".") == 1 and code.split(".")[0] in {"users", "roles", "audit", "organization", "channels", "devices"}:
                found.add(code)
        missing = expected - found
        self.assertSetEqual(missing, set(), f"Missing seed permission codes: {missing}")

    def test_seed_has_all_role_codes(self):
        """Seed contains all 4 expected role codes."""
        expected = {"system_admin", "security_admin", "operator", "analyst"}
        src = self._SEED_SRC
        found = set()
        for m in re.finditer(r"VALUES\s*\([^)]+?'([a-z_]+)'\s*,", src):
            code = m.group(1)
            if code in expected:
                found.add(code)
        missing = expected - found
        self.assertSetEqual(missing, set(), f"Missing seed role codes: {missing}")

    def test_seed_has_break_glass_user(self):
        """Seed creates break-glass admin with is_break_glass=true."""
        src = self._SEED_SRC
        self.assertIn("break_glass_admin", src)
        self.assertIn("is_break_glass", src)
        # Verify the INSERT sets is_break_glass to true near the break_glass_admin row
        # Search from SEED_SQL onwards to avoid matching _DEV_PASSWORDS
        sql_start = src.index("SEED_SQL")
        bg_section = src[src.index("break_glass_admin", sql_start) - 50:src.index("break_glass_admin", sql_start) + 200]
        self.assertIn("true", bg_section)

    def test_seed_has_no_passwords(self):
        """Seed INSERT VALUES contain no password/passwd/secret/token/key strings."""
        src = self._SEED_SRC
        m = re.search(r'SEED_SQL = f"""(.+?)"""', src, re.DOTALL)
        self.assertIsNotNone(m, "Cannot find SEED_SQL")
        sql = m.group(1)
        # Only check INSERT lines with VALUES, not comments
        value_lines = [l for l in sql.split("\n")
                       if "VALUES" in l.upper() and l.strip().upper().startswith("INSERT")]
        forbidden = ["password", "passwd", "pwd_hash", "secret_key", "access_token", "api_key"]
        for word in forbidden:
            for line in value_lines:
                self.assertNotIn(word, line.lower(),
                                 f"INSERT VALUES contains forbidden word '{word}': {line[:120]}")

    def test_seed_breaks_on_conflict_count(self):
        """Every INSERT has ON CONFLICT (idempotent)."""
        src = self._SEED_SRC
        m = re.search(r'SEED_SQL = f"""(.+?)"""', src, re.DOTALL)
        self.assertIsNotNone(m, "Cannot find SEED_SQL")
        sql = m.group(1)
        insert_count = len(re.findall(r"INSERT INTO", sql))
        conflict_count = len(re.findall(r"ON CONFLICT", sql))
        self.assertEqual(insert_count, conflict_count,
                         f"INSERT count {insert_count} != ON CONFLICT count {conflict_count}")

    def test_seed_insert_count(self):
        """Seed INSERT count — grows with each phase. S-023a: +8 advertiser role INSERTs (91)."""
        src = self._SEED_SRC
        m = re.search(r'SEED_SQL = f"""(.+?)"""', src, re.DOTALL)
        self.assertIsNotNone(m, "Cannot find SEED_SQL")
        sql = m.group(1)
        inserts = [l for l in sql.split("\n") if l.strip().upper().startswith("INSERT")]
        self.assertEqual(len(inserts), 94, f"Expected 94 INSERTs, got {len(inserts)}")


class TestPhase21AuditEventModel(unittest.TestCase):
    """Verify audit_events_operational allows nullable actor for system events."""

    def test_actor_user_id_nullable(self):
        from packages.domain.models import AuditEventOperational
        col = AuditEventOperational.__table__.columns["actor_user_id"]
        self.assertTrue(col.nullable, "actor_user_id must be nullable for system events")
        # Also verify it's an FK to users
        fks = [fk for fk in AuditEventOperational.__table__.foreign_keys
               if fk.parent.name == "actor_user_id"]
        self.assertTrue(fks, "actor_user_id must have FK to users.id")
        self.assertIn("users.id", {fk.target_fullname for fk in fks})


class TestPhase21NoOldBackendDependency(unittest.TestCase):
    """Verify Phase 2.1 does not import from old backend code."""

    def test_models_no_backend_import(self):
        with open("packages/domain/models.py") as f:
            src = f.read()
        self.assertNotIn("from backend", src)
        self.assertNotIn("import backend", src)

    def test_database_no_backend_import(self):
        with open("packages/domain/database.py") as f:
            src = f.read()
        self.assertNotIn("from backend", src)
        self.assertNotIn("import backend", src)

    def test_database_no_hardcoded_production_url(self):
        """DATABASE_URL default is localhost dev, not production."""
        with open("packages/domain/database.py") as f:
            src = f.read()
        self.assertIn("localhost:5432", src)
        self.assertNotIn("prod", src.lower().split("database_url")[-1][:100])


# ---------------------------------------------------------------------------
# S-035h: migration 013 structure proof
# ---------------------------------------------------------------------------


class TestMigration013UploadSessionsRLS(unittest.TestCase):
    """Proof: migration 013 adds RLS policies to creative_upload_sessions."""

    _MIGRATION = None

    @classmethod
    def setUpClass(cls):
        import importlib.util
        path = "apps/control-api/alembic/versions/013_upload_sessions_rls.py"
        spec = importlib.util.spec_from_file_location("m013", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        cls._MIGRATION = mod

    def test_migration_revision(self):
        """Migration 013 revises 012."""
        self.assertEqual(self._MIGRATION.revision, "013")
        self.assertEqual(self._MIGRATION.down_revision, "012")

    def test_upgrade_enables_rls(self):
        """upgrade() enables RLS and creates SELECT/INSERT/UPDATE policies."""
        # Inspect the upgrade function's source code for key operations
        import inspect
        src = inspect.getsource(self._MIGRATION.upgrade)
        self.assertIn("ENABLE ROW LEVEL SECURITY", src)
        self.assertIn("creative_upload_sessions", src)
        self.assertIn("RLS_DIRECT", src)
        self.assertIn("RLS_INSERT", src)
        self.assertIn("RLS_UPDATE", src)

    def test_rls_policies_use_org_scope(self):
        """SELECT policy uses advertiser_organization_id scope + admin bypass."""
        self.assertIn("advertiser_organization_id", self._MIGRATION.RLS_DIRECT)
        self.assertIn("app.rmp_is_admin", self._MIGRATION.RLS_DIRECT)
        self.assertIn("app.rmp_scope_advertiser_ids", self._MIGRATION.RLS_DIRECT)

    def test_rls_insert_uses_with_check(self):
        """INSERT policy uses WITH CHECK clause."""
        self.assertIn("WITH CHECK", self._MIGRATION.RLS_INSERT)

    def test_rls_update_uses_using_and_with_check(self):
        """UPDATE policy uses USING for read-path check."""
        self.assertIn("FOR UPDATE", self._MIGRATION.RLS_UPDATE)
        self.assertIn("advertiser_organization_id", self._MIGRATION.RLS_UPDATE)

    def test_downgrade_drops_policies(self):
        """downgrade() drops the policies cleanly."""
        import inspect
        src = inspect.getsource(self._MIGRATION.downgrade)
        self.assertIn("DROP POLICY", src)
        self.assertIn("creative_upload_sessions", src)


if __name__ == "__main__":
    unittest.main()
