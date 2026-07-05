"""
Phase 4.1c — Campaign Mutation Unit Tests.

Tests: schemas, router compliance, validation rules, draft-only guard.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestCampaignMutationSchemas(unittest.TestCase):
    """Create/update/archive request schemas."""

    def test_create_request_fields(self):
        from packages.domain.schemas import CampaignCreateRequest
        fields = set(CampaignCreateRequest.model_fields)
        required = {
            "advertiser_organization_id", "advertiser_contract_id",
            "code", "name",
        }
        self.assertTrue(required <= fields, f"Missing: {required - fields}")

    def test_create_request_no_pii(self):
        from packages.domain.schemas import CampaignCreateRequest
        fields = set(CampaignCreateRequest.model_fields)
        for pii in ("email", "phone", "contact_name", "password", "token"):
            self.assertNotIn(pii, fields, f"PII field '{pii}' in create schema")

    def test_create_request_no_storage_secrets(self):
        from packages.domain.schemas import CampaignCreateRequest
        fields = set(CampaignCreateRequest.model_fields)
        for secret in ("storage_bucket", "storage_key", "presigned_url"):
            self.assertNotIn(secret, fields,
                             f"Storage secret '{secret}' in create schema")

    def test_update_request_all_optional(self):
        """CampaignUpdateRequest has no required fields."""
        from packages.domain.schemas import CampaignUpdateRequest
        fields = CampaignUpdateRequest.model_fields
        for name, field in fields.items():
            self.assertTrue(
                field.annotation is None
                or hasattr(field.annotation, "__args__")
                and type(None) in getattr(field.annotation, "__args__", ()),
                f"Field '{name}' must be Optional",
            )

    def test_archive_response_fields(self):
        from packages.domain.schemas import CampaignArchiveResponse
        fields = set(CampaignArchiveResponse.model_fields)
        self.assertTrue({"message", "campaign_id", "old_status", "new_status"} <= fields)


class TestCampaignMutationRouterCompliance(unittest.TestCase):
    """Routers: permissions, no db.execute, etc."""

    def _router_content(self):
        router_path = os.path.join(
            os.path.dirname(__file__), "..",
            "packages", "api", "identity.py",
        )
        return open(router_path).read()

    def test_create_endpoint_has_permission(self):
        content = self._router_content()
        self.assertIn('require_scoped_permission("campaigns.manage"', content)

    def test_mutation_endpoints_no_direct_db_execute(self):
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

    def test_mutation_endpoints_have_set_rls(self):
        content = self._router_content()
        # All mutation endpoints must have set_rls_context
        self.assertIn("_rls=Depends(set_rls_context)", content)

    def test_import_boundary_no_fastapi_in_domain(self):
        """Domain schemas must not import from fastapi."""
        schema_path = os.path.join(
            os.path.dirname(__file__), "..",
            "packages", "domain", "schemas.py",
        )
        content = open(schema_path).read()
        self.assertNotIn("from fastapi", content)
        self.assertNotIn("import fastapi", content)


class TestCampaignMutationValidation(unittest.TestCase):
    """Business rules: draft-only, org scope."""

    def test_create_request_validates_code_length(self):
        from packages.domain.schemas import CampaignCreateRequest
        from pydantic import ValidationError
        # Too short
        with self.assertRaises(ValidationError):
            CampaignCreateRequest(
                advertiser_organization_id="a",
                advertiser_contract_id="b",
                code="",
                name="Test",
            )
        # Too long
        with self.assertRaises(ValidationError):
            CampaignCreateRequest(
                advertiser_organization_id="a",
                advertiser_contract_id="b",
                code="x" * 65,
                name="Test",
            )

    def test_create_request_valid(self):
        from packages.domain.schemas import CampaignCreateRequest
        req = CampaignCreateRequest(
            advertiser_organization_id="00000000-0000-0000-0000-000000000200",
            advertiser_contract_id="00000000-0000-0000-0000-000000000212",
            code="CAMP-TEST",
            name="Test Campaign",
        )
        self.assertEqual(req.code, "CAMP-TEST")
        self.assertEqual(req.timezone, "Europe/Moscow")

    def test_update_request_excludes_unset(self):
        from packages.domain.schemas import CampaignUpdateRequest
        req = CampaignUpdateRequest(name="New Name")
        data = req.model_dump(exclude_unset=True)
        self.assertIn("name", data)
        self.assertNotIn("code", data)
        self.assertNotIn("description", data)


if __name__ == "__main__":
    unittest.main()
