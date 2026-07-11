"""
Retail Media Platform — Phase 3.2a Auth Persistence Tests.

Tests: new tables present, FK/unique constraints, seed safety (no passwords/tokens).
No database connection required — all tests are static/source-inspection.
"""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# Table presence + column checks
# ---------------------------------------------------------------------------


class TestPhase3AuthTables(unittest.TestCase):
    """Verify 6 new auth persistence tables exist in metadata."""

    @classmethod
    def setUpClass(cls):
        from packages.domain import models as m
        cls.m = m

    def test_advertiser_organizations_columns(self):
        cols = {c.name for c in self.m.AdvertiserOrganization.__table__.columns}
        self.assertTrue(cols >= {"id", "code", "legal_name", "display_name",
                                   "status", "created_at", "updated_at"})

    def test_advertiser_organizations_code_unique(self):
        cols = {c.name for c in self.m.AdvertiserOrganization.__table__.columns
                if c.unique}
        self.assertIn("code", cols)

    def test_advertiser_user_memberships_columns(self):
        cols = {c.name for c in self.m.AdvertiserUserMembership.__table__.columns}
        self.assertTrue(cols >= {"id", "user_id", "advertiser_organization_id",
                                   "status", "created_at"})

    def test_local_credentials_columns(self):
        cols = {c.name for c in self.m.LocalCredential.__table__.columns}
        self.assertTrue(cols >= {
            "id", "user_id", "credential_type", "password_hash",
            "password_hash_algorithm", "password_changed_at",
            "email_verified_at", "must_change_password", "status",
            "created_at", "updated_at",
        })

    def test_local_credentials_user_id_unique(self):
        cols = {c.name for c in self.m.LocalCredential.__table__.columns
                if c.unique}
        self.assertIn("user_id", cols)

    def test_local_credentials_credential_type_check(self):
        """CHECK constraint restricts credential_type values."""
        from sqlalchemy import CheckConstraint
        checks = [c for c in self.m.LocalCredential.__table__.constraints
                  if isinstance(c, CheckConstraint)]
        type_checks = [c for c in checks if "credential_type" in str(c.sqltext)]
        self.assertTrue(type_checks,
                        "local_credentials missing CHECK on credential_type")

    def test_refresh_sessions_columns(self):
        cols = {c.name for c in self.m.RefreshSession.__table__.columns}
        self.assertTrue(cols >= {
            "id", "user_id", "token_hash", "token_family_id",
            "issued_at", "expires_at", "rotated_at", "revoked_at",
            "ip_address", "user_agent", "created_at",
        })

    def test_refresh_sessions_token_hash_unique(self):
        cols = {c.name for c in self.m.RefreshSession.__table__.columns
                if c.unique}
        self.assertIn("token_hash", cols)

    def test_login_attempts_columns(self):
        cols = {c.name for c in self.m.LoginAttempt.__table__.columns}
        self.assertTrue(cols >= {
            "id", "username_or_email_hash", "auth_provider",
            "success", "failure_reason", "ip_address",
            "correlation_id", "created_at",
        })

    def test_login_attempts_no_raw_password(self):
        """login_attempts must not have password/token columns."""
        cols = {c.name for c in self.m.LoginAttempt.__table__.columns}
        forbidden = {"password", "password_hash", "token", "secret"}
        overlap = cols & forbidden
        self.assertSetEqual(overlap, set(),
                            f"login_attempts has forbidden columns: {overlap}")

    def test_password_reset_tokens_columns(self):
        cols = {c.name for c in self.m.PasswordResetToken.__table__.columns}
        self.assertTrue(cols >= {
            "id", "user_id", "token_hash", "expires_at",
            "used_at", "created_at",
        })

    def test_password_reset_tokens_token_hash_unique(self):
        cols = {c.name for c in self.m.PasswordResetToken.__table__.columns
                if c.unique}
        self.assertIn("token_hash", cols)

    def test_password_reset_tokens_no_raw_token_column(self):
        """password_reset_tokens stores token_hash only, not raw token."""
        cols = {c.name for c in self.m.PasswordResetToken.__table__.columns}
        self.assertIn("token_hash", cols)
        self.assertNotIn("token", cols)
        self.assertNotIn("raw_token", cols)


# ---------------------------------------------------------------------------
# Foreign Key checks
# ---------------------------------------------------------------------------


class TestPhase3AuthForeignKeys(unittest.TestCase):
    """Verify FK relationships on new auth tables."""

    @classmethod
    def setUpClass(cls):
        from packages.domain import models as m
        cls.m = m

    def _fk_targets(self, model, col_name):
        fks = [fk for fk in model.__table__.foreign_keys if fk.parent.name == col_name]
        self.assertTrue(fks, f"{model.__name__}.{col_name} has no FK")
        return {fk.target_fullname for fk in fks}

    def test_membership_user_fk(self):
        self.assertIn("users.id",
                      self._fk_targets(self.m.AdvertiserUserMembership, "user_id"))

    def test_membership_org_fk(self):
        self.assertIn("advertiser_organizations.id",
                      self._fk_targets(self.m.AdvertiserUserMembership,
                                       "advertiser_organization_id"))

    def test_local_credentials_user_fk(self):
        self.assertIn("users.id",
                      self._fk_targets(self.m.LocalCredential, "user_id"))

    def test_refresh_sessions_user_fk(self):
        self.assertIn("users.id",
                      self._fk_targets(self.m.RefreshSession, "user_id"))

    def test_password_reset_tokens_user_fk(self):
        self.assertIn("users.id",
                      self._fk_targets(self.m.PasswordResetToken, "user_id"))


# ---------------------------------------------------------------------------
# Unique constraint checks
# ---------------------------------------------------------------------------


class TestPhase3AuthUniqueConstraints(unittest.TestCase):
    """Verify unique constraints on new auth tables."""

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

    def test_membership_unique_pair(self):
        pairs = self._unique_columns(self.m.AdvertiserUserMembership)
        self.assertTrue(
            ("advertiser_organization_id", "user_id") in pairs
            or ("user_id", "advertiser_organization_id") in pairs,
            "advertiser_user_memberships missing unique(user_id, advertiser_organization_id)"
        )

    def test_advertiser_org_unique_code(self):
        cols = {c.name for c in self.m.AdvertiserOrganization.__table__.columns
                if c.unique}
        self.assertIn("code", cols)


# ---------------------------------------------------------------------------
# Seed safety checks
# ---------------------------------------------------------------------------


class TestPhase3AuthSeedSafety(unittest.TestCase):
    """Verify seed does not contain passwords, raw tokens, or credential data."""

    _SEED_SRC: str | None = None

    @classmethod
    def _load_seed(cls) -> str:
        if cls._SEED_SRC is None:
            path = os.path.join(os.path.dirname(__file__), "..",
                                "apps", "control-api", "seed.py")
            with open(path) as f:
                cls._SEED_SRC = f.read()
        return cls._SEED_SRC

    @classmethod
    def setUpClass(cls):
        cls._load_seed()

    def test_seed_has_no_password_hashes(self):
        """Seed SQL must not contain bcrypt/argon2 hash strings or password_hash."""
        src = self._SEED_SRC
        m = re.search(r'SEED_SQL = f"""(.+?)"""', src, re.DOTALL)
        self.assertIsNotNone(m, "Cannot find SEED_SQL")
        sql = m.group(1)
        self.assertNotIn("$2b$", sql)
        self.assertNotIn("$2a$", sql)
        self.assertNotIn("$argon2", sql)
        self.assertNotIn("password_hash", sql.lower())

    def test_seed_has_no_raw_tokens(self):
        """Seed must not contain token values."""
        src = self._SEED_SRC
        m = re.search(r'SEED_SQL = f"""(.+?)"""', src, re.DOTALL)
        self.assertIsNotNone(m, "Cannot find SEED_SQL")
        sql = m.group(1)
        self.assertNotIn("refresh_token", sql.lower())
        self.assertNotIn("access_token", sql.lower())
        self.assertNotIn("Bearer", sql)

    def test_seed_has_no_local_credentials_insert(self):
        """Seed must not INSERT into local_credentials."""
        src = self._SEED_SRC
        m = re.search(r'SEED_SQL = f"""(.+?)"""', src, re.DOTALL)
        self.assertIsNotNone(m, "Cannot find SEED_SQL")
        sql = m.group(1)
        # Check INSERT lines only, not comments
        for line in sql.split("\n"):
            if line.strip().upper().startswith("INSERT"):
                self.assertNotIn("local_credentials", line.lower(),
                                 f"INSERT found for local_credentials: {line[:120]}")

    def test_seed_has_no_refresh_sessions_insert(self):
        """Seed must not INSERT into refresh_sessions."""
        src = self._SEED_SRC
        m = re.search(r'SEED_SQL = f"""(.+?)"""', src, re.DOTALL)
        self.assertIsNotNone(m, "Cannot find SEED_SQL")
        sql = m.group(1)
        for line in sql.split("\n"):
            if line.strip().upper().startswith("INSERT"):
                self.assertNotIn("refresh_sessions", line.lower(),
                                 f"INSERT found for refresh_sessions: {line[:120]}")

    def test_seed_has_advertiser_org(self):
        """Seed creates one advertiser organization."""
        src = self._SEED_SRC
        self.assertIn("advertiser_organizations", src)
        self.assertIn("ADV-001", src)

    def test_seed_has_advertiser_user(self):
        """Seed creates one advertiser user with local_advertiser provider."""
        src = self._SEED_SRC
        self.assertIn("local_advertiser", src)
        self.assertIn("advertiser_test", src)

    def test_seed_break_glass_uses_correct_provider(self):
        """Break-glass user INSERT in SEED_SQL has auth_provider='local_break_glass'."""
        src = self._SEED_SRC
        m = re.search(r'SEED_SQL = f"""(.+?)"""', src, re.DOTALL)
        self.assertIsNotNone(m, "Cannot find SEED_SQL")
        sql = m.group(1)
        # Find the break_glass_admin INSERT line within SQL and verify provider
        idx = sql.index("break_glass_admin")
        bg_section = sql[max(0, idx - 100): idx + 200]
        self.assertIn("local_break_glass", bg_section)
        self.assertNotIn("'local'", bg_section)


# ---------------------------------------------------------------------------
# local_credentials not exposed by identity API schemas
# ---------------------------------------------------------------------------


class TestPhase3AuthSchemaBoundaries(unittest.TestCase):
    """Verify auth persistence tables are not exposed by identity API schemas."""

    def test_user_out_no_credential_fields(self):
        """UserOut must not expose password_hash, credential data."""
        from packages.domain.schemas import UserOut
        fields = set(UserOut.model_fields.keys())
        forbidden = {"password_hash", "password", "credential", "mfa_secret"}
        overlap = fields & forbidden
        self.assertSetEqual(overlap, set(),
                            f"UserOut exposes forbidden fields: {overlap}")

    def test_audit_event_out_no_token(self):
        """AuditEventOut must not expose raw token fields."""
        from packages.domain.schemas import AuditEventOut
        fields = set(AuditEventOut.model_fields.keys())
        forbidden = {"token", "refresh_token", "access_token", "secret"}
        overlap = fields & forbidden
        self.assertSetEqual(overlap, set(),
                            f"AuditEventOut exposes forbidden fields: {overlap}")


# ---------------------------------------------------------------------------
# No old backend dependency
# ---------------------------------------------------------------------------


class TestPhase3AuthNoOldBackend(unittest.TestCase):
    """New migration file must not import from old backend."""

    def test_migration_no_backend(self):
        path = os.path.join(
            os.path.dirname(__file__), "..",
            "apps", "control-api", "alembic", "versions",
            "003_auth_persistence.py",
        )
        with open(path) as f:
            src = f.read()
        self.assertNotIn("from backend", src)
        self.assertNotIn("import backend", src)


if __name__ == "__main__":
    unittest.main()
