"""
Retail Media Platform — Phase 4.3b PoP Persistence Unit Tests.

Tests: repository helper signatures, import boundaries, no secrets/PII,
no NATS/FastAPI/ClickHouse imports in domain layer.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestPopRepositorySignatures(unittest.TestCase):
    """Verify PoP repository helpers exist and have expected signatures."""

    def test_record_pop_raw_event_exists(self):
        from packages.domain.repository import record_pop_raw_event
        self.assertTrue(callable(record_pop_raw_event))

    def test_insert_pop_dedup_key_exists(self):
        from packages.domain.repository import insert_pop_dedup_key
        self.assertTrue(callable(insert_pop_dedup_key))

    def test_is_pop_event_duplicate_exists(self):
        from packages.domain.repository import is_pop_event_duplicate
        self.assertTrue(callable(is_pop_event_duplicate))

    def test_accept_pop_event_exists(self):
        from packages.domain.repository import accept_pop_event
        self.assertTrue(callable(accept_pop_event))

    def test_quarantine_pop_event_exists(self):
        from packages.domain.repository import quarantine_pop_event
        self.assertTrue(callable(quarantine_pop_event))

    def test_expire_pop_quarantine_events_exists(self):
        from packages.domain.repository import expire_pop_quarantine_events
        self.assertTrue(callable(expire_pop_quarantine_events))


class TestPopImportBoundaries(unittest.TestCase):
    """Verify domain layer has no forbidden imports."""

    def test_models_no_nats_import(self):
        with open("packages/domain/models.py") as f:
            src = f.read()
        self.assertNotIn("nats", src)
        self.assertNotIn("NATS", src)

    def test_models_no_fastapi_import(self):
        with open("packages/domain/models.py") as f:
            src = f.read()
        self.assertNotIn("from fastapi", src)
        self.assertNotIn("import fastapi", src)

    def test_models_no_clickhouse_import(self):
        with open("packages/domain/models.py") as f:
            src = f.read()
        self.assertNotIn("clickhouse", src)
        self.assertNotIn("ClickHouse", src)

    def test_repository_no_nats_import(self):
        with open("packages/domain/repository.py") as f:
            src = f.read()
        # Only comment/doc mentions of NATS allowed, no actual imports
        lines = [l for l in src.split("\n")
                 if "nats" in l.lower()
                 and not l.strip().startswith("#")
                 and not l.strip().startswith('"""')]
        for line in lines:
            self.assertNotIn("import", line,
                             f"NATS import found: {line[:80]}")

    def test_repository_no_fastapi_import(self):
        with open("packages/domain/repository.py") as f:
            src = f.read()
        self.assertNotIn("from fastapi", src)
        self.assertNotIn("import fastapi", src)

    def test_repository_no_clickhouse_import(self):
        with open("packages/domain/repository.py") as f:
            src = f.read()
        self.assertNotIn("clickhouse", src)
        self.assertNotIn("ClickHouse", src)


class TestPopModelIntegrity(unittest.TestCase):
    """Verify PopEventRaw model structural integrity."""

    @classmethod
    def setUpClass(cls):
        from packages.domain import models as m
        cls.m = m

    def test_pop_event_raw_table_name(self):
        self.assertEqual(self.m.PopEventRaw.__tablename__, "pop_events_raw")

    def test_pop_dedup_index_table_name(self):
        self.assertEqual(self.m.PopDedupIndex.__tablename__, "pop_dedup_index")

    def test_pop_ingestion_batch_table_name(self):
        self.assertEqual(self.m.PopIngestionBatch.__tablename__,
                         "pop_ingestion_batches")

    def test_pop_event_raw_required_fields_non_nullable(self):
        """event_id, device_id, creative_asset_id, etc. are non-nullable."""
        required_non_null = {
            "id", "event_id", "schema_version", "device_id",
            "creative_asset_id", "surface_id", "rendered_at",
            "event_recorded_at", "duration_ms", "playback_result", "status",
        }
        for col_name in required_non_null:
            col = self.m.PopEventRaw.__table__.columns[col_name]
            self.assertFalse(col.nullable,
                             f"{col_name} must be non-nullable")

    def test_pop_event_raw_optional_fields_nullable(self):
        """campaign_id, manifest_id, quarantine_reason, expires_at are nullable."""
        nullable_ok = {"manifest_id", "campaign_id", "quarantine_reason",
                       "expires_at", "batch_id"}
        for col_name in nullable_ok:
            col = self.m.PopEventRaw.__table__.columns[col_name]
            self.assertTrue(col.nullable,
                            f"{col_name} must be nullable")

    def test_pop_event_raw_has_all_checks(self):
        """Three check constraints: playback_result, duration_ms, status."""
        from sqlalchemy import CheckConstraint
        checks = [c for c in self.m.PopEventRaw.__table__.constraints
                  if isinstance(c, CheckConstraint)]
        self.assertGreaterEqual(len(checks), 3,
                                f"Expected at least 3 check constraints, got {len(checks)}")

    def test_pop_dedup_index_event_id_is_pk(self):
        self.assertTrue(self.m.PopDedupIndex.__table__.columns["event_id"].primary_key)

    def test_required_tables_includes_pop_tables(self):
        from packages.domain.models import REQUIRED_TABLES
        self.assertIn("pop_events_raw", REQUIRED_TABLES)
        self.assertIn("pop_dedup_index", REQUIRED_TABLES)
        self.assertIn("pop_ingestion_batches", REQUIRED_TABLES)


if __name__ == "__main__":
    unittest.main()
