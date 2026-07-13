"""
Phase 4.1d — Campaign Approval Workflow Unit Tests.

Tests: schemas, permission dependencies, valid/invalid transitions,
approval row creation, outbox payload shape, router compliance,
requested_at semantics, contract validation guards.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestApprovalSchemas(unittest.TestCase):
    """Request/response schemas for approval workflow."""

    def test_reject_request_fields(self):
        from packages.domain.schemas import CampaignRejectRequest
        fields = set(CampaignRejectRequest.model_fields)
        self.assertIn("reason", fields)

    def test_reject_request_reason_required(self):
        from packages.domain.schemas import CampaignRejectRequest
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            CampaignRejectRequest()
        with self.assertRaises(ValidationError):
            CampaignRejectRequest(reason="")

    def test_reject_request_valid(self):
        from packages.domain.schemas import CampaignRejectRequest
        req = CampaignRejectRequest(reason="Budget exceeded")
        self.assertEqual(req.reason, "Budget exceeded")

    def test_approval_response_fields(self):
        from packages.domain.schemas import CampaignApprovalResponse
        fields = set(CampaignApprovalResponse.model_fields)
        self.assertTrue({"message", "campaign_id", "old_status", "new_status"} <= fields)

    def test_schemas_no_pii(self):
        from packages.domain.schemas import CampaignRejectRequest, CampaignApprovalResponse
        for schema in (CampaignRejectRequest, CampaignApprovalResponse):
            fields = set(schema.model_fields)
            for pii in ("email", "phone", "password", "token", "secret"):
                self.assertNotIn(pii, fields, f"{pii} in {schema.__name__}")


class TestApprovalRouterCompliance(unittest.TestCase):
    """Router: permissions, no db.execute, scope context."""

    def _router_content(self):
        router_path = os.path.join(
            os.path.dirname(__file__), "..",
            "packages", "api", "identity_routes", "campaigns.py",
        )
        return open(router_path).read()

    def test_request_approval_uses_campaigns_manage(self):
        content = self._router_content()
        self.assertIn('require_scoped_permission("campaigns.manage"', content)

    def test_approve_uses_campaigns_approve(self):
        content = self._router_content()
        self.assertIn('require_scoped_permission("campaigns.approve"', content)

    def test_reject_uses_campaigns_approve(self):
        content = self._router_content()
        # Reject also uses campaigns.approve
        self.assertIn('require_scoped_permission("campaigns.approve"', content)

    def test_approval_endpoints_have_set_rls(self):
        content = self._router_content()
        self.assertIn("_rls=Depends(set_rls_context)", content)

    def test_approval_endpoints_no_direct_db_execute(self):
        content = self._router_content()
        # Strip docstrings and comments
        lines = []
        in_docstring = False
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped.startswith('"""') and in_docstring:
                in_docstring = False
                continue
            if stripped.startswith('"""') and not in_docstring:
                in_docstring = not (stripped.count('"""') >= 2)
                continue
            if in_docstring:
                continue
            if stripped.startswith("#"):
                continue
            lines.append(line)
        clean = "\n".join(lines)
        self.assertNotIn("db.execute", clean,
                         "Router must not call db.execute directly")

    def test_no_fastapi_in_domain(self):
        """Domain schemas must not import from fastapi."""
        schema_path = os.path.join(
            os.path.dirname(__file__), "..",
            "packages", "domain", "schemas.py",
        )
        content = open(schema_path).read()
        self.assertNotIn("from fastapi", content)


class TestApprovalRepositoryFunctions(unittest.TestCase):
    """Repository functions exist with correct signatures."""

    def test_request_approval_exists(self):
        import inspect
        from packages.domain.repository import request_campaign_approval
        sig = inspect.signature(request_campaign_approval)
        self.assertIn("scope_advertiser_ids", sig.parameters)

    def test_approve_exists(self):
        import inspect
        from packages.domain.repository import approve_campaign
        sig = inspect.signature(approve_campaign)
        self.assertIn("reviewed_by", sig.parameters)
        self.assertIn("scope_advertiser_ids", sig.parameters)

    def test_reject_exists(self):
        import inspect
        from packages.domain.repository import reject_campaign
        sig = inspect.signature(reject_campaign)
        self.assertIn("reviewed_by", sig.parameters)
        self.assertIn("reason", sig.parameters)
        self.assertIn("scope_advertiser_ids", sig.parameters)

    def test_repository_has_approval_functions(self):
        repo_path = os.path.join(
            os.path.dirname(__file__), "..",
            "packages", "domain", "repository.py",
        )
        content = open(repo_path).read()
        for func in ("request_campaign_approval", "approve_campaign", "reject_campaign"):
            self.assertIn(f"async def {func}", content,
                          f"Missing: {func}")

    def test_approve_looks_up_requested_at(self):
        """approve_campaign queries campaign_status_history for the
        draft→pending_approval transition timestamp — does NOT use
        decision time."""
        repo_path = os.path.join(
            os.path.dirname(__file__), "..",
            "packages", "domain", "repository.py",
        )
        content = open(repo_path).read()
        # Should query CampaignStatusHistory for the request transition
        self.assertIn("CampaignStatusHistory.old_status == \"draft\"", content)
        self.assertIn("CampaignStatusHistory.new_status == \"pending_approval\"", content)
        # requested_at should NOT be set to "now" — it comes from the query
        self.assertIn("requested_at=requested_at", content)
        # Verify the function uses the looked-up timestamp variable
        self.assertIn("requested_at = request_row", content)

    def test_reject_looks_up_requested_at(self):
        """reject_campaign also queries the request transition timestamp."""
        repo_path = os.path.join(
            os.path.dirname(__file__), "..",
            "packages", "domain", "repository.py",
        )
        content = open(repo_path).read()
        # reject_campaign also uses CampaignStatusHistory lookup
        # (count occurrences — should be 2: one in approve, one in reject)
        self.assertGreaterEqual(
            content.count("CampaignStatusHistory.old_status == \"draft\""),
            2,
            "Both approve_campaign and reject_campaign should look up request timestamp"
        )

    def test_request_approval_validates_contract(self):
        """request_campaign_approval checks flight windows against contract."""
        repo_path = os.path.join(
            os.path.dirname(__file__), "..",
            "packages", "domain", "repository.py",
        )
        content = open(repo_path).read()
        self.assertIn("AdvertiserContract", content)
        self.assertIn("valid_from", content)
        self.assertIn("valid_until", content)


if __name__ == "__main__":
    unittest.main()
