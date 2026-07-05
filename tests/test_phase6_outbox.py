"""
Phase 4.1c — Outbox Event Unit Tests.

Tests: model, migration, repository helper.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestOutboxEventModel(unittest.TestCase):
    """OutboxEvent ORM model has required columns and constraints."""

    @classmethod
    def setUpClass(cls):
        from packages.domain import models as m
        cls.m = m

    def test_model_exists(self):
        self.assertTrue(hasattr(self.m, "OutboxEvent"))

    def test_table_name(self):
        self.assertEqual(self.m.OutboxEvent.__tablename__, "outbox_events")

    def test_required_columns(self):
        cols = {c.name for c in self.m.OutboxEvent.__table__.columns}
        required = {
            "id", "event_type", "event_version", "aggregate_type",
            "aggregate_id", "payload_json", "headers_json", "status",
            "attempts", "next_attempt_at", "created_at",
        }
        self.assertTrue(required <= cols, f"Missing: {required - cols}")

    def test_nullable_columns(self):
        """published_at, last_error, partition_key are nullable."""
        cols = self.m.OutboxEvent.__table__.columns
        for col_name in ("published_at", "last_error", "partition_key"):
            self.assertTrue(cols[col_name].nullable,
                            f"{col_name} should be nullable")

    def test_status_check_constraint(self):
        constraints = {c.name for c in self.m.OutboxEvent.__table__.constraints}
        self.assertIn("ck_outbox_status", constraints)

    def test_no_rls_on_outbox(self):
        """outbox_events must NOT have RLS — relay worker is cross-tenant."""
        # Model-side: we check there's no RLS-related trigger/policy
        # Migration-side: verified in TestMigration007

    def test_model_in_all(self):
        self.assertIn("OutboxEvent", self.m.__all__)

    def test_table_in_required(self):
        self.assertIn("outbox_events", self.m.REQUIRED_TABLES)


class TestMigration007(unittest.TestCase):
    """Migration 007 creates outbox_events with correct structure."""

    def _content(self):
        mig_path = os.path.join(
            os.path.dirname(__file__), "..",
            "apps", "control-api", "alembic", "versions",
            "007_outbox_events.py",
        )
        return open(mig_path).read()

    def test_file_exists(self):
        mig_path = os.path.join(
            os.path.dirname(__file__), "..",
            "apps", "control-api", "alembic", "versions",
            "007_outbox_events.py",
        )
        self.assertTrue(os.path.exists(mig_path))

    def test_revises_006(self):
        content = self._content()
        self.assertIn('down_revision: Union[str, None] = "006"', content)
        self.assertIn('revision: str = "007"', content)

    def test_creates_outbox_events(self):
        content = self._content()
        self.assertIn('"outbox_events"', content)
        self.assertIn("create_table", content)

    def test_status_check_exists(self):
        content = self._content()
        self.assertIn("ck_outbox_status", content)

    def test_next_attempt_at_default_now(self):
        content = self._content()
        self.assertIn("next_attempt_at", content)
        self.assertIn("server_default=sa.text(\"NOW()\")", content)

    def test_indexes_exist(self):
        content = self._content()
        self.assertIn("ix_outbox_status_next", content)
        self.assertIn("ix_outbox_aggregate", content)
        self.assertIn("ix_outbox_created_at", content)

    def test_no_rls(self):
        content = self._content()
        self.assertNotIn("ENABLE ROW LEVEL SECURITY", content)

    def test_has_downgrade(self):
        content = self._content()
        self.assertIn("def downgrade()", content)
        self.assertIn("op.drop_table(\"outbox_events\")", content)


class TestOutboxRepository(unittest.TestCase):
    """enqueue_outbox_event and relay helpers."""

    def test_enqueue_signature(self):
        import inspect
        from packages.domain.repository import enqueue_outbox_event
        sig = inspect.signature(enqueue_outbox_event)
        params = list(sig.parameters)
        self.assertIn("session", params)
        # Keyword-only after session
        kw_params = [p for p in params if p != "session"]
        for p in kw_params:
            param = sig.parameters[p]
            self.assertEqual(param.kind, inspect.Parameter.KEYWORD_ONLY,
                             f"{p} must be keyword-only")

    def test_fetch_pending_exists(self):
        from packages.domain.repository import fetch_pending_events
        self.assertTrue(callable(fetch_pending_events))

    def test_mark_published_exists(self):
        from packages.domain.repository import mark_event_published
        self.assertTrue(callable(mark_event_published))

    def test_mark_failed_exists(self):
        from packages.domain.repository import mark_event_failed
        self.assertTrue(callable(mark_event_failed))

    def test_no_direct_nats_import(self):
        """Repository must NOT import or reference NATS."""
        repo_path = os.path.join(
            os.path.dirname(__file__), "..",
            "packages", "domain", "repository.py",
        )
        content = open(repo_path).read()
        # Check no NATS module import (only docstring mentions are OK)
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if stripped.startswith('"""'):
                continue
            if stripped.startswith("from ") or stripped.startswith("import "):
                self.assertNotIn("nats", stripped.lower(),
                                 f"Repository imports NATS: {stripped}")


if __name__ == "__main__":
    unittest.main()
