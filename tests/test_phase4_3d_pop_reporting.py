"""
Retail Media Platform — Phase 4.3d PoP Reporting Unit Tests.

Tests: schemas validation, import boundaries, no PII/secrets,
no NATS/FastAPI/ClickHouse in domain layer.
"""

import os
import sys
import unittest
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestPopReportingSchemas(unittest.TestCase):
    """Verify PoP reporting Pydantic schemas."""

    def test_summary_defaults(self):
        from packages.domain.schemas import CampaignPopSummaryOut
        s = CampaignPopSummaryOut(campaign_id="cam-001")
        self.assertEqual(s.campaign_id, "cam-001")
        self.assertEqual(s.impressions_count, 0)
        self.assertEqual(s.total_duration_ms, 0)
        self.assertIsNone(s.first_rendered_at)
        self.assertIsNone(s.last_rendered_at)
        self.assertEqual(s.unique_devices, 0)
        self.assertEqual(s.unique_surfaces, 0)

    def test_summary_with_data(self):
        from packages.domain.schemas import CampaignPopSummaryOut
        now = datetime.now(timezone.utc)
        s = CampaignPopSummaryOut(
            campaign_id="cam-001",
            impressions_count=42,
            total_duration_ms=210000,
            first_rendered_at=now,
            last_rendered_at=now,
            unique_devices=3,
            unique_surfaces=2,
        )
        self.assertEqual(s.impressions_count, 42)
        self.assertEqual(s.total_duration_ms, 210000)
        self.assertEqual(s.unique_devices, 3)

    def test_summary_no_pii(self):
        """CampaignPopSummaryOut has no PII fields."""
        from packages.domain.schemas import CampaignPopSummaryOut
        s = CampaignPopSummaryOut(campaign_id="cam-001")
        d = s.model_dump()
        forbidden = {"email", "phone", "password", "token", "secret", "contact", "presigned_url", "storage_bucket", "storage_key"}
        self.assertTrue(forbidden.isdisjoint(set(d.keys())))

    def test_by_day_defaults(self):
        from packages.domain.schemas import CampaignPopByDayOut
        r = CampaignPopByDayOut(date="2026-07-01")
        self.assertEqual(r.date, "2026-07-01")
        self.assertEqual(r.impressions_count, 0)
        self.assertEqual(r.total_duration_ms, 0)

    def test_by_day_with_data(self):
        from packages.domain.schemas import CampaignPopByDayOut
        r = CampaignPopByDayOut(date="2026-07-01", impressions_count=10, total_duration_ms=50000)
        self.assertEqual(r.impressions_count, 10)

    def test_by_surface_defaults(self):
        from packages.domain.schemas import CampaignPopBySurfaceOut
        r = CampaignPopBySurfaceOut(surface_id="surf-001")
        self.assertEqual(r.surface_id, "surf-001")
        self.assertEqual(r.impressions_count, 0)

    def test_by_surface_no_pii(self):
        """CampaignPopBySurfaceOut has no PII fields."""
        from packages.domain.schemas import CampaignPopBySurfaceOut
        r = CampaignPopBySurfaceOut(surface_id="surf-001", impressions_count=5, total_duration_ms=25000)
        d = r.model_dump()
        forbidden = {"email", "phone", "password", "token", "secret", "contact", "presigned_url", "storage_bucket", "storage_key"}
        self.assertTrue(forbidden.isdisjoint(set(d.keys())))


class TestPopReportingImportBoundaries(unittest.TestCase):
    """Verify domain layer has no forbidden imports."""

    def test_repository_no_nats(self):
        with open("packages/domain/repository.py") as f:
            src = f.read()
        # Only check new reporting helpers
        self.assertNotIn("import nats", src.lower())
        self.assertNotIn("from nats", src.lower())

    def test_repository_no_clickhouse(self):
        with open("packages/domain/repository.py") as f:
            src = f.read()
        self.assertNotIn("import clickhouse", src.lower())
        self.assertNotIn("from clickhouse", src.lower())

    def test_repository_no_fastapi(self):
        with open("packages/domain/repository.py") as f:
            src = f.read()
        self.assertNotIn("from fastapi", src)
        self.assertNotIn("import fastapi", src)

    def test_identity_router_no_db_execute(self):
        """Router must not call db.execute — use repository helpers."""
        with open("packages/api/identity.py") as f:
            src = f.read()
        self.assertNotIn("db.execute", src)
        self.assertNotIn("session.execute", src)

    def test_identity_router_no_nats(self):
        with open("packages/api/identity.py") as f:
            src = f.read()
        self.assertNotIn("nats", src.lower())

    def test_identity_router_no_clickhouse(self):
        with open("packages/api/identity.py") as f:
            src = f.read()
        self.assertNotIn("clickhouse", src.lower())


if __name__ == "__main__":
    unittest.main()
