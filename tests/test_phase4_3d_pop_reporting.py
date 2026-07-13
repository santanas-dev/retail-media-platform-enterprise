"""PoP reporting tests (ADR-017 §6 smoke + ADR-014 layering)."""

import unittest


class TestFastApiLayeringSmoke(unittest.TestCase):
    """Ensure FastAPI stays in the api layer."""

    def test_repository_no_fastapi(self):
        """packages/domain/repository.py must not import FastAPI."""
        with open("packages/domain/repository.py") as f:
            src = f.read()
        self.assertNotIn("from fastapi", src)
        self.assertNotIn("import fastapi", src)

    def test_identity_router_no_db_execute(self):
        """Identity routers must not call db.execute — use repository helpers."""
        import glob
        files = glob.glob("packages/api/identity_routes/*.py")
        files.append("packages/api/identity.py")
        for path in files:
            with open(path) as f:
                src = f.read()
            self.assertNotIn("db.execute", src,
                             f"{path} must not call db.execute")
            self.assertNotIn("session.execute", src,
                             f"{path} must not call session.execute")

    def test_identity_router_no_nats(self):
        """Identity routers must not touch NATS."""
        import glob
        files = glob.glob("packages/api/identity_routes/*.py")
        files.append("packages/api/identity.py")
        for path in files:
            with open(path) as f:
                src = f.read()
            self.assertNotIn("nats", src.lower(),
                             f"{path} must not reference nats")

    def test_identity_router_no_clickhouse(self):
        """Identity routers must not touch ClickHouse."""
        import glob
        files = glob.glob("packages/api/identity_routes/*.py")
        files.append("packages/api/identity.py")
        for path in files:
            with open(path) as f:
                src = f.read()
            self.assertNotIn("clickhouse", src.lower(),
                             f"{path} must not reference clickhouse")


if __name__ == "__main__":
    unittest.main()
