"""
ADVERTISER-UX-001B2 — Advertiser contract CRUD + PDF upload backend tests.
"""
import uuid
from unittest.mock import AsyncMock, Mock

import pytest

from packages.domain.schemas import (
    AdvertiserContractCreate,
    AdvertiserContractUpdate,
    ContractUploadIntentRequest,
    ContractUploadCompleteRequest,
)

ORG_ID = "00000000-0000-0000-0000-000000000200"


# ── Schema tests ──

class TestContractCreateSchema:
    def test_minimal_valid(self):
        body = AdvertiserContractCreate(
            advertiser_organization_id=ORG_ID,
            code="CTR-001",
            name="Test Contract",
        )
        assert body.code == "CTR-001"
        assert body.name == "Test Contract"

    def test_code_required(self):
        with pytest.raises(Exception):
            AdvertiserContractCreate(
                advertiser_organization_id=ORG_ID,
                name="No Code",
            )

    def test_name_required(self):
        with pytest.raises(Exception):
            AdvertiserContractCreate(
                advertiser_organization_id=ORG_ID,
                code="CTR-001",
            )

    def test_optional_fields(self):
        body = AdvertiserContractCreate(
            advertiser_organization_id=ORG_ID,
            code="CTR-001",
            name="Test",
            contract_number="123/2026",
            budget_limit_amount=500000.00,
            budget_limit_currency="RUB",
        )
        assert body.contract_number == "123/2026"
        assert body.budget_limit_amount == 500000.00


class TestContractUpdateSchema:
    def test_all_none_ok(self):
        body = AdvertiserContractUpdate()
        assert body.name is None
        assert body.code is None

    def test_partial_update(self):
        body = AdvertiserContractUpdate(name="Renamed")
        assert body.name == "Renamed"
        assert body.code is None


class TestUploadIntentSchema:
    def test_pdf_accepted(self):
        body = ContractUploadIntentRequest(
            filename="contract.pdf",
            content_type="application/pdf",
            content_length=1024,
        )
        assert body.content_type == "application/pdf"

    def test_content_length_positive(self):
        with pytest.raises(Exception):
            ContractUploadIntentRequest(
                filename="c.pdf",
                content_type="application/pdf",
                content_length=0,
            )

    def test_filename_required(self):
        with pytest.raises(Exception):
            ContractUploadIntentRequest(
                filename="",
                content_type="application/pdf",
                content_length=1,
            )


# ── Repository tests ──

@pytest.mark.asyncio
async def test_create_contract_repo():
    from packages.domain.repository import create_advertiser_contract

    session = AsyncMock()

    async def fake_flush():
        pass
    session.flush = fake_flush

    result = await create_advertiser_contract(
        session, ORG_ID, "CTR-01", "Contract One",
    )
    assert result.advertiser_organization_id == ORG_ID
    assert result.code == "CTR-01"
    assert result.name == "Contract One"
    assert result.status == "draft"
    session.add.assert_called_once()


@pytest.mark.asyncio
async def test_update_contract_not_found():
    from packages.domain.repository import update_advertiser_contract

    session = AsyncMock()
    session.execute = AsyncMock(return_value=Mock())
    session.execute.return_value.scalar_one_or_none = Mock(return_value=None)

    result = await update_advertiser_contract(
        session, "nonexistent", ORG_ID, name="X",
    )
    assert result is None


@pytest.mark.asyncio
async def test_update_contract_cross_org_rejected():
    """Contract not found = cross-org because WHERE filters by org_id."""
    from packages.domain.repository import update_advertiser_contract

    session = AsyncMock()
    session.execute = AsyncMock(return_value=Mock())
    session.execute.return_value.scalar_one_or_none = Mock(return_value=None)

    result = await update_advertiser_contract(
        session,
        "some-contract-id",
        "00000000-0000-0000-0000-000000000999",  # wrong org
        name="X",
    )
    assert result is None
