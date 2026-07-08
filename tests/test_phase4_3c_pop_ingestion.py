"""
Retail Media Platform — Phase 4.3c PoP Ingestion Unit Tests.

Tests: schemas validation, auth dependency behavior, import boundaries,
no NATS/FastAPI/ClickHouse in domain layer.
"""
import os
import sys
import unittest
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestPopSchemas(unittest.TestCase):
    """Verify PoP Pydantic schemas."""

    @classmethod
    def setUpClass(cls):
        from packages.domain.schemas import PopEventIn
        cls.PopEventIn = PopEventIn

    def _valid_event(self, **overrides):
        data = {
            "event_id": "evt-001",
            "device_id": "dev-001",
            "creative_asset_id": "cr-001",
            "surface_id": "surf-001",
            "duration_ms": 5000,
            "playback_result": "success",
            "rendered_at": datetime.now(timezone.utc),
            "event_recorded_at": datetime.now(timezone.utc),
        }
        data.update(overrides)
        return data

    def test_valid_event_parses(self):
        event = self.PopEventIn(**self._valid_event())
        self.assertEqual(event.event_id, "evt-001")
        self.assertEqual(event.schema_version, "1.0")

    def test_default_schema_version(self):
        event = self.PopEventIn(**self._valid_event())
        self.assertEqual(event.schema_version, "1.0")

    def test_explicit_schema_version(self):
        event = self.PopEventIn(**self._valid_event(schema_version="2.0"))
        self.assertEqual(event.schema_version, "2.0")

    def test_manifest_id_optional(self):
        event = self.PopEventIn(**self._valid_event())
        self.assertIsNone(event.manifest_id)

    def test_manifest_id_set(self):
        event = self.PopEventIn(**self._valid_event(manifest_id="man-001"))
        self.assertEqual(event.manifest_id, "man-001")

    def test_campaign_id_optional(self):
        event = self.PopEventIn(**self._valid_event())
        self.assertIsNone(event.campaign_id)

    def test_duration_min_bound(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            self.PopEventIn(**self._valid_event(duration_ms=0))

    def test_duration_max_bound(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            self.PopEventIn(**self._valid_event(duration_ms=86_400_001))

    def test_playback_result_must_be_valid(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            self.PopEventIn(**self._valid_event(playback_result="invalid"))

    def test_playback_result_success_valid(self):
        event = self.PopEventIn(**self._valid_event(playback_result="success"))
        self.assertEqual(event.playback_result, "success")

    def test_playback_result_fallback_valid(self):
        event = self.PopEventIn(**self._valid_event(playback_result="fallback"))
        self.assertEqual(event.playback_result, "fallback")

    def test_missing_required_field(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            self.PopEventIn(event_id="evt-001")  # missing device_id etc.

    def test_event_id_required(self):
        from pydantic import ValidationError
        data = self._valid_event()
        del data["event_id"]
        with self.assertRaises(ValidationError):
            self.PopEventIn(**data)


class TestPopBatchRequest(unittest.TestCase):
    """Verify batch request schema."""

    @classmethod
    def setUpClass(cls):
        from packages.domain.schemas import PopBatchRequest, PopEventIn, POP_MAX_BATCH_SIZE
        cls.PopBatchRequest = PopBatchRequest
        cls.PopEventIn = PopEventIn
        cls.POP_MAX_BATCH_SIZE = POP_MAX_BATCH_SIZE

    def _valid_event(self, idx=1):
        return self.PopEventIn(
            event_id=f"evt-{idx:03d}",
            device_id=f"dev-{idx:03d}",
            creative_asset_id=f"cr-{idx:03d}",
            surface_id=f"surf-{idx:03d}",
            duration_ms=5000,
            playback_result="success",
            rendered_at=datetime.now(timezone.utc),
            event_recorded_at=datetime.now(timezone.utc),
        )

    def test_single_event_batch(self):
        batch = self.PopBatchRequest(events=[self._valid_event(1)])
        self.assertEqual(len(batch.events), 1)

    def test_empty_batch_rejected(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            self.PopBatchRequest(events=[])

    def test_too_large_batch_rejected(self):
        from pydantic import ValidationError
        events = [self._valid_event(i) for i in range(self.POP_MAX_BATCH_SIZE + 1)]
        with self.assertRaises(ValidationError):
            self.PopBatchRequest(events=events)


class TestPopBatchResponse(unittest.TestCase):
    """Verify batch response schema."""

    def test_defaults(self):
        from packages.domain.schemas import PopBatchResponse
        resp = PopBatchResponse()
        self.assertEqual(resp.accepted_count, 0)
        self.assertEqual(resp.rejected_count, 0)
        self.assertEqual(resp.quarantined_count, 0)
        self.assertEqual(resp.duplicate_count, 0)
        self.assertEqual(resp.results, [])

    def test_with_results(self):
        from packages.domain.schemas import PopBatchResponse, PopEventResult
        resp = PopBatchResponse(
            accepted_count=2,
            rejected_count=1,
            results=[
                PopEventResult(event_id="e1", status="accepted"),
                PopEventResult(event_id="e2", status="accepted"),
                PopEventResult(event_id="e3", status="rejected", reason="invalid_duration"),
            ],
        )
        self.assertEqual(resp.accepted_count, 2)
        self.assertEqual(resp.rejected_count, 1)
        self.assertEqual(len(resp.results), 3)


class TestPopImportBoundaries(unittest.TestCase):
    """Verify domain layer has no forbidden imports."""

    def test_pop_ingestion_no_fastapi(self):
        with open("packages/domain/pop_ingestion.py") as f:
            src = f.read()
        self.assertNotIn("from fastapi", src)
        self.assertNotIn("import fastapi", src)

    def test_pop_ingestion_no_nats(self):
        with open("packages/domain/pop_ingestion.py") as f:
            src = f.read()
        # Docstring may mention "no nats" — only check for actual imports
        self.assertNotIn("import nats", src.lower())
        self.assertNotIn("from nats", src.lower())

    def test_pop_ingestion_no_clickhouse(self):
        with open("packages/domain/pop_ingestion.py") as f:
            src = f.read()
        self.assertNotIn("import clickhouse", src.lower())
        self.assertNotIn("from clickhouse", src.lower())

    def test_pop_router_no_db_execute(self):
        """Router must not call db.execute — use repository helpers."""
        with open("packages/api/pop.py") as f:
            src = f.read()
        # db.execute should not appear in router
        self.assertNotIn("db.execute", src)
        self.assertNotIn("session.execute", src)

    def test_pop_router_no_nats(self):
        with open("packages/api/pop.py") as f:
            src = f.read()
        self.assertNotIn("nats", src.lower())

    def test_pop_router_no_clickhouse(self):
        with open("packages/api/pop.py") as f:
            src = f.read()
        self.assertNotIn("clickhouse", src.lower())


class TestPopConstants(unittest.TestCase):
    """Verify constants are reasonable."""

    def test_batch_limit(self):
        from packages.domain.schemas import POP_MAX_BATCH_SIZE
        self.assertEqual(POP_MAX_BATCH_SIZE, 500)

    def test_schema_version(self):
        from packages.domain.schemas import POP_SCHEMA_VERSION
        self.assertEqual(POP_SCHEMA_VERSION, "1.0")

    def test_max_duration(self):
        from packages.domain.schemas import POP_MAX_DURATION_MS
        self.assertEqual(POP_MAX_DURATION_MS, 86_400_000)

    def test_quarantine_ttl(self):
        from packages.domain.schemas import POP_QUARANTINE_TTL_HOURS
        self.assertEqual(POP_QUARANTINE_TTL_HOURS, 72)

    def test_clock_drift(self):
        from packages.domain.schemas import POP_CLOCK_DRIFT_MINUTES
        self.assertEqual(POP_CLOCK_DRIFT_MINUTES, 5)


class TestPopDedupViolationDetection(unittest.TestCase):
    """Unit tests for _is_pop_dedup_unique_violation.

    No database required — the helper duck-types the DB-API exception
    chain, so we test with lightweight mocks.
    """

    def _mock_integrity_error(self, cls_name, constraint_name=None):
        """Construct an IntegrityError wrapping a mock DB-API exception."""
        from sqlalchemy.exc import IntegrityError

        class MockDBAPIError(Exception):
            pass

        # Attach class name dynamically
        MockDBAPIError.__name__ = cls_name
        orig = MockDBAPIError("duplicate key")
        if constraint_name is not None:
            orig.constraint_name = constraint_name  # type: ignore[attr-defined]
        exc = IntegrityError("stmt", {}, orig)
        return exc

    def test_dedup_pkey_violation_returns_true(self):
        from packages.domain.pop_ingestion import _is_pop_dedup_unique_violation
        exc = self._mock_integrity_error(
            "UniqueViolationError", "pop_dedup_index_pkey",
        )
        self.assertTrue(_is_pop_dedup_unique_violation(exc))

    def test_dedup_with_prefix_returns_true(self):
        """Constraint name like 'uq_pop_dedup_index_event' should match."""
        from packages.domain.pop_ingestion import _is_pop_dedup_unique_violation
        exc = self._mock_integrity_error(
            "UniqueViolationError", "uq_pop_dedup_index_event_id",
        )
        self.assertTrue(_is_pop_dedup_unique_violation(exc))

    def test_unrelated_unique_violation_returns_false(self):
        from packages.domain.pop_ingestion import _is_pop_dedup_unique_violation
        exc = self._mock_integrity_error(
            "UniqueViolationError", "campaigns_pkey",
        )
        self.assertFalse(_is_pop_dedup_unique_violation(exc))

    def test_fk_violation_returns_false(self):
        from packages.domain.pop_ingestion import _is_pop_dedup_unique_violation
        exc = self._mock_integrity_error("ForeignKeyViolationError")
        self.assertFalse(_is_pop_dedup_unique_violation(exc))

    def test_check_violation_returns_false(self):
        from packages.domain.pop_ingestion import _is_pop_dedup_unique_violation
        exc = self._mock_integrity_error("CheckViolationError")
        self.assertFalse(_is_pop_dedup_unique_violation(exc))

    def test_not_null_violation_returns_false(self):
        from packages.domain.pop_ingestion import _is_pop_dedup_unique_violation
        exc = self._mock_integrity_error("NotNullViolationError")
        self.assertFalse(_is_pop_dedup_unique_violation(exc))

    def test_no_orig_returns_false(self):
        from sqlalchemy.exc import IntegrityError
        from packages.domain.pop_ingestion import _is_pop_dedup_unique_violation
        exc = IntegrityError("bare statement", {}, Exception("inner"))
        self.assertFalse(_is_pop_dedup_unique_violation(exc))


if __name__ == "__main__":
    unittest.main()
