"""
Retail Media Platform — Phase 2.3 DB Setup Tests.

Tests: migration/seed scripts exist, compose has db-setup service,
       README documents clean setup flow.
Static/source-inspection only — no real database required.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

ROOT = os.path.join(os.path.dirname(__file__), "..")


def _read(path: str) -> str:
    with open(os.path.join(ROOT, path)) as f:
        return f.read()


# ---------------------------------------------------------------------------
# Scripts Exist
# ---------------------------------------------------------------------------


class TestDbScriptsExist(unittest.TestCase):
    """Migration and seed scripts are present and executable."""

    def test_migrate_script_exists(self):
        path = os.path.join(ROOT, "scripts", "db", "migrate.sh")
        self.assertTrue(os.path.isfile(path), f"Missing: {path}")
        self.assertTrue(os.access(path, os.X_OK), f"Not executable: {path}")

    def test_seed_script_exists(self):
        path = os.path.join(ROOT, "scripts", "db", "seed.sh")
        self.assertTrue(os.path.isfile(path), f"Missing: {path}")
        self.assertTrue(os.access(path, os.X_OK), f"Not executable: {path}")


# ---------------------------------------------------------------------------
# Scripts Reference Correct Commands
# ---------------------------------------------------------------------------


class TestDbScriptsContent(unittest.TestCase):
    """Migration/seed scripts reference the right tools."""

    def test_migrate_script_uses_alembic(self):
        src = _read("scripts/db/migrate.sh")
        self.assertIn("alembic upgrade head", src)

    def test_seed_script_uses_seed_py(self):
        src = _read("scripts/db/seed.sh")
        self.assertIn("apps/control-api/seed.py", src)

    def test_seed_script_uses_python3(self):
        src = _read("scripts/db/seed.sh")
        self.assertIn("python3 apps/control-api/seed.py", src)

    def test_migrate_script_uses_set_euo_pipefail(self):
        """Script exits on error (set -euo pipefail)."""
        src = _read("scripts/db/migrate.sh")
        self.assertIn("set -euo pipefail", src)

    def test_seed_script_uses_set_euo_pipefail(self):
        src = _read("scripts/db/seed.sh")
        self.assertIn("set -euo pipefail", src)

    def test_migrate_script_never_echoes_database_url(self):
        """Script must not print DATABASE_URL value (credential leak)."""
        import re
        src = _read("scripts/db/migrate.sh")
        # Find echo/printf lines, check none contain ${DATABASE_URL} unguarded
        for line in src.split("\n"):
            stripped = line.strip()
            if stripped.startswith("echo") or stripped.startswith("printf"):
                self.assertNotIn("${DATABASE_URL}", stripped,
                                 f"migrate.sh echo/printf leaks DATABASE_URL: {stripped}")

    def test_seed_script_never_echoes_database_url(self):
        """Script must not print DATABASE_URL value (credential leak)."""
        import re
        src = _read("scripts/db/seed.sh")
        for line in src.split("\n"):
            stripped = line.strip()
            if stripped.startswith("echo") or stripped.startswith("printf"):
                self.assertNotIn("${DATABASE_URL}", stripped,
                                 f"seed.sh echo/printf leaks DATABASE_URL: {stripped}")


# ---------------------------------------------------------------------------
# Compose Has db-setup Service
# ---------------------------------------------------------------------------


class TestComposeDbSetup(unittest.TestCase):
    """docker-compose.phase1.yml has a profile-gated db-setup service."""

    @classmethod
    def setUpClass(cls):
        import yaml
        with open(os.path.join(ROOT, "infra", "compose", "docker-compose.phase1.yml")) as f:
            cls.compose = yaml.safe_load(f)

    def test_db_setup_service_exists(self):
        services = self.compose.get("services", {})
        self.assertIn("db-setup", services, "Missing db-setup service")

    def test_db_setup_has_setup_profile(self):
        svc = self.compose["services"]["db-setup"]
        profiles = svc.get("profiles", [])
        self.assertIn("setup", profiles, "db-setup missing 'setup' profile")

    def test_db_setup_depends_on_postgres_healthy(self):
        svc = self.compose["services"]["db-setup"]
        deps = svc.get("depends_on", {})
        pg_dep = deps.get("postgres", {})
        self.assertEqual(pg_dep.get("condition"), "service_healthy",
                         "db-setup must depend on postgres healthy")

    def test_db_setup_command_runs_migrations_then_seed(self):
        svc = self.compose["services"]["db-setup"]
        cmd = svc.get("command", "")
        self.assertIn("alembic upgrade head", str(cmd))
        self.assertIn("seed.py", str(cmd))
        # Migrations must run BEFORE seed
        cmd_str = str(cmd)
        mig_pos = cmd_str.index("alembic")
        seed_pos = cmd_str.index("seed.py")
        self.assertLess(mig_pos, seed_pos,
                        "Migrations must run before seed")

    def test_db_setup_has_database_url(self):
        svc = self.compose["services"]["db-setup"]
        env = svc.get("environment", {})
        self.assertIn("DATABASE_URL", env)

    def test_control_api_does_not_auto_migrate(self):
        """control-api service must NOT auto-run migrations on startup."""
        svc = self.compose["services"]["control-api"]
        cmd = svc.get("command", "")
        self.assertNotIn("alembic", str(cmd).lower(),
                         "control-api must not auto-run migrations")


# ---------------------------------------------------------------------------
# README Documents Clean Setup
# ---------------------------------------------------------------------------


class TestReadmeDbSetup(unittest.TestCase):
    """README documents the clean database setup flow."""

    @classmethod
    def setUpClass(cls):
        cls.readme = _read("README.md")

    def test_readme_has_db_setup_section(self):
        self.assertIn("Database Setup", self.readme)

    def test_readme_mentions_migrate_script(self):
        self.assertIn("scripts/db/migrate.sh", self.readme)

    def test_readme_mentions_seed_script(self):
        self.assertIn("scripts/db/seed.sh", self.readme)

    def test_readme_mentions_profile_gated_setup(self):
        self.assertIn("--profile setup", self.readme)
        self.assertIn("db-setup", self.readme)

    def test_readme_starts_postgres_first(self):
        """Clean setup starts postgres before anything else."""
        rm = self.readme.lower()
        # "up -d postgres" appears before "db-setup" or "migrate"
        pg_pos = rm.index("up -d postgres")
        setup_pos = rm.index("db-setup")
        self.assertLess(pg_pos, setup_pos,
                        "README must start postgres before db-setup")

    def test_readme_mentions_legacy_reference_only(self):
        self.assertIn("reference-only", self.readme)
        self.assertIn("retail-media-platform", self.readme)


if __name__ == "__main__":
    unittest.main()
