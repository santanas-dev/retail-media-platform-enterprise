"""ADVERTISER-UX-001A1 — Legal requisites schema validation + API persistence tests.

Tests:
- Schema validation (unit, no DB)
- API PUT endpoint (integration with mocks)
- Permission 403, org 404
- Existing org without requisites still readable
- Checksum is deferred — no checksum tests
"""

import importlib.util
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from packages.domain.schemas import (
    AdvertiserLegalRequisites,
    AdvertiserOrganizationDetailOut,
)

# Lazy app import (hyphens in control-api dir name)
_APP = None


def _get_app():
    global _APP
    if _APP is None:
        path = os.path.join(os.path.dirname(__file__), "..", "apps", "control-api", "main.py")
        spec = importlib.util.spec_from_file_location("control_api_main", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _APP = mod.app
    return _APP


# ---------------------------------------------------------------------------
# Schema unit tests — no DB needed
# ---------------------------------------------------------------------------


class TestLegalRequisitesValidation(unittest.TestCase):
    """Pydantic validation for legal requisites."""

    VALID_LEGAL_ENTITY = {
        "legal_entity_type": "legal_entity",
        "legal_form": "ooo",
        "legal_name": "ООО Ромашка",
        "inn": "7707083893",
        "legal_address": "г. Москва, ул. Тверская, д. 1",
        "settlement_account": "40702810500000000001",
        "correspondent_account": "30101810200000000593",
        "bik": "044525593",
        "bank_name": "ПАО Сбербанк",
        "kpp": "770701001",
        "ogrn": "1027700132195",
    }

    VALID_IE = {
        "legal_entity_type": "individual_entrepreneur",
        "legal_form": "ip",
        "legal_name": "Иванов Иван Иванович",
        "inn": "770708389300",
        "legal_address": "г. Москва, ул. Арбат, д. 10",
        "settlement_account": "40802810500000000002",
        "correspondent_account": "30101810200000000593",
        "bik": "044525593",
        "bank_name": "ПАО Сбербанк",
        "ogrnip": "304770000000001",
    }

    # --- Valid payloads ---

    def test_legal_entity_valid(self):
        req = AdvertiserLegalRequisites.model_validate(self.VALID_LEGAL_ENTITY)
        self.assertEqual(req.legal_entity_type, "legal_entity")
        self.assertEqual(req.inn, "7707083893")
        self.assertEqual(req.kpp, "770701001")
        self.assertEqual(req.ogrn, "1027700132195")
        self.assertIsNone(req.ogrnip)

    def test_individual_entrepreneur_valid(self):
        req = AdvertiserLegalRequisites.model_validate(self.VALID_IE)
        self.assertEqual(req.legal_entity_type, "individual_entrepreneur")
        self.assertEqual(req.inn, "770708389300")
        self.assertEqual(req.ogrnip, "304770000000001")
        self.assertIsNone(req.kpp)
        self.assertIsNone(req.ogrn)

    # --- Digit normalization ---

    def test_normalize_spaces_in_inn(self):
        data = {**self.VALID_LEGAL_ENTITY, "inn": "7707 0838 93"}
        req = AdvertiserLegalRequisites.model_validate(data)
        self.assertEqual(req.inn, "7707083893")

    def test_normalize_dashes_in_bik(self):
        data = {**self.VALID_LEGAL_ENTITY, "bik": "044-525-593"}
        req = AdvertiserLegalRequisites.model_validate(data)
        self.assertEqual(req.bik, "044525593")

    def test_normalize_spaces_in_accounts(self):
        data = {
            **self.VALID_LEGAL_ENTITY,
            "settlement_account": "40702 81050 00000 00001",
            "correspondent_account": "30101 81020 00000 00593",
        }
        req = AdvertiserLegalRequisites.model_validate(data)
        self.assertEqual(req.settlement_account, "40702810500000000001")
        self.assertEqual(req.correspondent_account, "30101810200000000593")

    # --- Invalid lengths ---

    def test_inn_wrong_length_rejected(self):
        with self.assertRaises(Exception):
            AdvertiserLegalRequisites.model_validate({**self.VALID_LEGAL_ENTITY, "inn": "123"})

    def test_bik_not_9_rejected(self):
        with self.assertRaises(Exception):
            AdvertiserLegalRequisites.model_validate({**self.VALID_LEGAL_ENTITY, "bik": "12345"})

    def test_settlement_not_20_rejected(self):
        with self.assertRaises(Exception):
            AdvertiserLegalRequisites.model_validate(
                {**self.VALID_LEGAL_ENTITY, "settlement_account": "123"}
            )

    def test_correspondent_not_20_rejected(self):
        with self.assertRaises(Exception):
            AdvertiserLegalRequisites.model_validate(
                {**self.VALID_LEGAL_ENTITY, "correspondent_account": "123"}
            )

    # --- legal_form_other ---

    def test_legal_form_other_valid_with_other(self):
        data = {**self.VALID_LEGAL_ENTITY, "legal_form": "other", "legal_form_other": "Производственный кооператив"}
        req = AdvertiserLegalRequisites.model_validate(data)
        self.assertEqual(req.legal_form_other, "Производственный кооператив")

    def test_legal_form_other_not_required_for_non_other(self):
        req = AdvertiserLegalRequisites.model_validate({**self.VALID_LEGAL_ENTITY, "legal_form": "ooo"})
        self.assertIsNone(req.legal_form_other)

    # --- Empty strings rejected ---

    def test_empty_legal_name_rejected(self):
        with self.assertRaises(Exception):
            AdvertiserLegalRequisites.model_validate({**self.VALID_LEGAL_ENTITY, "legal_name": "   "})

    def test_empty_bank_name_rejected(self):
        with self.assertRaises(Exception):
            AdvertiserLegalRequisites.model_validate({**self.VALID_LEGAL_ENTITY, "bank_name": ""})


# ---------------------------------------------------------------------------
# Schema detail-out test — existing org without requisites
# ---------------------------------------------------------------------------


class TestAdvertiserOrganizationDetailOut(unittest.TestCase):
    """DetailOut model_validate with and without requisites."""

    def test_existing_org_without_requisites_readable(self):
        data = {
            "id": "org-1", "code": "TEST", "legal_name": "Test Org",
            "display_name": "Test", "status": "active",
            "created_at": None, "updated_at": None,
        }
        out = AdvertiserOrganizationDetailOut.model_validate(data)
        self.assertEqual(out.id, "org-1")
        self.assertIsNone(out.inn)
        self.assertIsNone(out.kpp)
        self.assertIsNone(out.legal_entity_type)

    def test_org_with_requisites_readable(self):
        data = {
            "id": "org-2", "code": "ORG2", "legal_name": "ООО Тест",
            "display_name": "Тест", "status": "active",
            "created_at": None, "updated_at": None,
            "legal_entity_type": "legal_entity", "legal_form": "ooo",
            "legal_form_other": None, "inn": "7707083893",
            "legal_address": "г. Москва",
            "settlement_account": "40702810500000000001",
            "correspondent_account": "30101810200000000593",
            "bik": "044525593", "bank_name": "ПАО Сбербанк",
            "kpp": "770701001", "ogrn": "1027700132195", "ogrnip": None,
        }
        out = AdvertiserOrganizationDetailOut.model_validate(data)
        self.assertEqual(out.inn, "7707083893")
        self.assertEqual(out.kpp, "770701001")
        self.assertIsNone(out.legal_form_other)


# ---------------------------------------------------------------------------
# Checksum: deferred — explicit note
# ---------------------------------------------------------------------------


class TestChecksumDeferred(unittest.TestCase):
    """Confirm checksum validation is NOT implemented in A1."""

    def test_valid_inn_with_wrong_checksum_still_passes(self):
        data = {**TestLegalRequisitesValidation.VALID_LEGAL_ENTITY, "inn": "7707083894"}
        req = AdvertiserLegalRequisites.model_validate(data)
        self.assertEqual(req.inn, "7707083894")


# ---------------------------------------------------------------------------
# API integration tests
# ---------------------------------------------------------------------------


class TestLegalRequisitesAPI(unittest.TestCase):
    """PUT /api/v1/identity/advertiser-organizations/{org_id}/legal-requisites"""

    def setUp(self):
        self.org_id = "00000000-0000-0000-0000-000000000300"
        self.valid_body = {
            "legal_entity_type": "legal_entity",
            "legal_form": "ooo",
            "legal_name": "ООО Ромашка",
            "inn": "7707083893",
            "legal_address": "г. Москва, ул. Тверская, д. 1",
            "settlement_account": "40702810500000000001",
            "correspondent_account": "30101810200000000593",
            "bik": "044525593",
            "bank_name": "ПАО Сбербанк",
            "kpp": "770701001",
            "ogrn": "1027700132195",
        }
        self.app = _get_app()
        # Clear any prior overrides
        self.app.dependency_overrides.clear()

    def tearDown(self):
        self.app.dependency_overrides.clear()

    @patch(
        "packages.api.identity_routes.advertisers.repository.update_advertiser_organization_requisites",
        new_callable=AsyncMock,
    )
    @patch(
        "packages.api.identity_routes.advertisers.repository.create_audit_event",
        new_callable=AsyncMock,
    )
    @patch(
        "packages.api.dependencies.resolve_scope_context",
        new_callable=AsyncMock,
    )
    def test_put_legal_requisites_200(self, mock_scope, mock_audit, mock_update):
        """Valid legal_entity requisites update returns 200."""
        from packages.domain.scopes import ScopeContext
        mock_scope.return_value = ScopeContext(
            user_id="admin-1",
            is_admin=True,
            retailer_scope_ids=set(),
            advertiser_scope_ids=set(),
            all_permissions={"advertisers.manage"},
            global_permissions={"advertisers.manage"},
        )
        mock_org = MagicMock()
        mock_org.id = self.org_id
        mock_org.code = "TEST"
        mock_org.legal_name = "ООО Ромашка"
        mock_org.display_name = "Test"
        mock_org.status = "active"
        mock_org.created_at = None
        mock_org.updated_at = None
        for field in [
            "legal_entity_type", "legal_form", "legal_form_other", "inn",
            "legal_address", "settlement_account", "correspondent_account",
            "bik", "bank_name", "kpp", "ogrn", "ogrnip",
        ]:
            setattr(mock_org, field, self.valid_body.get(field))
        mock_update.return_value = mock_org

        from starlette.testclient import TestClient

        fake_user = {"sub": "admin-1", "user_status": "active", "scope": {}}
        from packages.api.dependencies import get_current_active_user, set_rls_context, get_db
        from packages.domain.repository import AsyncSession

        mock_db = AsyncMock(spec=AsyncSession)
        self.app.dependency_overrides[get_db] = lambda: mock_db
        self.app.dependency_overrides[get_current_active_user] = lambda: fake_user
        self.app.dependency_overrides[set_rls_context] = lambda: lambda: None

        client = TestClient(self.app)
        response = client.put(
            f"/api/v1/identity/advertiser-organizations/{self.org_id}/legal-requisites",
            json=self.valid_body,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["inn"], "7707083893")
        self.assertEqual(data["kpp"], "770701001")

    @patch(
        "packages.api.identity_routes.advertisers.repository.update_advertiser_organization_requisites",
        new_callable=AsyncMock,
        return_value=None,
    )
    @patch(
        "packages.api.dependencies.resolve_scope_context",
        new_callable=AsyncMock,
    )
    def test_put_legal_requisites_404(self, mock_scope, mock_update):
        """Non-existent org returns 404."""
        from packages.domain.scopes import ScopeContext
        mock_scope.return_value = ScopeContext(
            user_id="admin-1", is_admin=True,
            retailer_scope_ids=set(), advertiser_scope_ids=set(),
            all_permissions={"advertisers.manage"}, global_permissions={"advertisers.manage"},
        )
        from starlette.testclient import TestClient
        from packages.api.dependencies import get_current_active_user, set_rls_context, get_db
        from packages.domain.repository import AsyncSession

        fake_user = {"sub": "admin-1", "user_status": "active", "scope": {}}
        mock_db = AsyncMock(spec=AsyncSession)
        self.app.dependency_overrides[get_db] = lambda: mock_db
        self.app.dependency_overrides[get_current_active_user] = lambda: fake_user
        self.app.dependency_overrides[set_rls_context] = lambda: lambda: None

        client = TestClient(self.app)
        response = client.put(
            "/api/v1/identity/advertiser-organizations/nonexistent/legal-requisites",
            json=self.valid_body,
        )
        self.assertEqual(response.status_code, 404)

    @patch(
        "packages.api.dependencies.resolve_scope_context",
        new_callable=AsyncMock,
    )
    def test_put_legal_requisites_422_invalid(self, mock_scope):
        """Invalid payload (wrong inn length) returns 422."""
        from packages.domain.scopes import ScopeContext
        mock_scope.return_value = ScopeContext(
            user_id="admin-1", is_admin=True,
            retailer_scope_ids=set(), advertiser_scope_ids=set(),
            all_permissions={"advertisers.manage"}, global_permissions={"advertisers.manage"},
        )
        from starlette.testclient import TestClient
        from packages.api.dependencies import get_current_active_user, set_rls_context, get_db
        from packages.domain.repository import AsyncSession

        fake_user = {"sub": "admin-1", "user_status": "active", "scope": {}}
        mock_db = AsyncMock(spec=AsyncSession)
        self.app.dependency_overrides[get_db] = lambda: mock_db
        self.app.dependency_overrides[get_current_active_user] = lambda: fake_user
        self.app.dependency_overrides[set_rls_context] = lambda: lambda: None

        client = TestClient(self.app)
        bad_body = {**self.valid_body, "inn": "123"}
        response = client.put(
            f"/api/v1/identity/advertiser-organizations/{self.org_id}/legal-requisites",
            json=bad_body,
        )
        self.assertEqual(response.status_code, 422)
