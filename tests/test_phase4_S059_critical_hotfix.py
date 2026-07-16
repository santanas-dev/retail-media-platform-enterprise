"""
S-059 — v0.6 Critical Hotfix Verification Tests.

CRITICAL-2: Moderation/approval queue RLS context enforcement.
These tests verify that the four admin endpoints from the audit
include the ``set_rls_context`` dependency so that PostgreSQL
RLS policies are actually applied at query time.
"""

import ast
import inspect
import unittest
from pathlib import Path

from packages.api.identity_routes import campaigns, creatives


def _endpoint_source(module, func_name: str) -> str:
    """Return the source lines of an async endpoint function."""
    try:
        return inspect.getsource(getattr(module, func_name))
    except OSError:
        return ""


class TestCriticalHotfixRLS(unittest.TestCase):
    """Verify set_rls_context is wired on all admin queue endpoints."""

    def test_moderation_queue_has_rls_context(self):
        """GET /creative-assets/moderation-queue must have set_rls_context."""
        src = _endpoint_source(creatives, "moderation_queue_endpoint")
        self.assertIn("set_rls_context", src,
                      "moderation_queue_endpoint missing set_rls_context dependency")

    def test_approve_creative_has_rls_context(self):
        """POST /creative-assets/{id}/approve must have set_rls_context."""
        src = _endpoint_source(creatives, "approve_creative_endpoint")
        self.assertIn("set_rls_context", src,
                      "approve_creative_endpoint missing set_rls_context dependency")

    def test_reject_creative_has_rls_context(self):
        """POST /creative-assets/{id}/reject must have set_rls_context."""
        src = _endpoint_source(creatives, "reject_creative_endpoint")
        self.assertIn("set_rls_context", src,
                      "reject_creative_endpoint missing set_rls_context dependency")

    def test_approval_queue_has_rls_context(self):
        """GET /campaigns/approval-queue must have set_rls_context."""
        src = _endpoint_source(campaigns, "approval_queue_endpoint")
        self.assertIn("set_rls_context", src,
                      "approval_queue_endpoint missing set_rls_context dependency")

    def test_no_rls_context_on_permission_only_endpoints(self):
        """Sanity: require_permission alone does NOT set RLS context.

        If a future refactor removes set_rls_context from an admin
        endpoint and only leaves require_permission, this test won't
        catch it — but the source-inspection tests above will.
        This test documents the invariant.
        """
        from packages.api.dependencies import require_permission

        # require_permission is a factory — the inner enforce function
        # only checks permissions, no RLS SQL.
        dep = require_permission("creatives.moderate")
        self.assertIsNotNone(dep)
        # The returned dependency is enforce(), not set_rls_context
        self.assertNotEqual(dep.__name__, "set_rls_context",
                            "require_permission should not return set_rls_context")


class TestCriticalHotfixLDAPS(unittest.TestCase):
    """CRITICAL-1: LDAPS certificate validation tests."""

    def test_explicit_cert_required_in_connect(self):
        """_connect() source must contain ssl.CERT_REQUIRED branch."""
        from packages.auth.ad_provider import RealLDAPAuthProvider
        src = inspect.getsource(RealLDAPAuthProvider._connect)
        self.assertIn("ssl.CERT_REQUIRED", src,
                      "_connect() missing explicit ssl.CERT_REQUIRED branch")
        self.assertIn("ssl.CERT_NONE", src,
                      "_connect() missing CERT_NONE branch")

    def test_fail_secure_else_branch_exists(self):
        """_connect() must have an else/fallback defaulting to CERT_REQUIRED."""
        from packages.auth.ad_provider import RealLDAPAuthProvider
        src = inspect.getsource(RealLDAPAuthProvider._connect)
        # The fail-secure default is in the else: block with
        # "Unrecognised value" comment.
        has_else_default = (
            "else:" in src
            and "Unrecognised" in src
            and "fail-secure" in src
        )
        self.assertTrue(has_else_default,
                        "_connect() missing fail-secure else for unknown cert_val")

    def test_no_ad_use_tls_gate_in_connect(self):
        """_connect() must NOT gate TLS creation on ad_use_tls."""
        from packages.auth.ad_provider import RealLDAPAuthProvider
        src = inspect.getsource(RealLDAPAuthProvider._connect)
        self.assertNotIn("ad_use_tls", src,
                         "_connect() must not gate TLS on ad_use_tls")

    def test_ca_cert_file_config_field_exists(self):
        """SecurityConfig must have ad_ca_cert_file field."""
        from packages.security.config import SecurityConfig
        self.assertTrue(hasattr(SecurityConfig, "ad_ca_cert_file"),
                        "SecurityConfig missing ad_ca_cert_file")

    def test_ldap3_in_control_api_requirements(self):
        """control-api/requirements.txt must declare ldap3."""
        req_path = Path(__file__).resolve().parent.parent / "apps" / "control-api" / "requirements.txt"
        req_text = req_path.read_text()
        self.assertIn("ldap3", req_text,
                      "control-api/requirements.txt missing ldap3 declaration")

    def test_ldap3_in_ci(self):
        """CI workflow must include ldap3 in pip install commands."""
        ci_path = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "phase1-ci.yml"
        ci_text = ci_path.read_text()
        # At least one pip install line with ldap3
        lines_with_ldap3 = [l for l in ci_text.split("\n")
                            if "pip install" in l and "ldap3" in l]
        self.assertGreater(len(lines_with_ldap3), 0,
                           "CI workflow missing ldap3 in pip install commands")
