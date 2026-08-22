"""
ADVERTISER-UX-001B1 — Advertiser brand CRUD backend tests.
"""
import uuid
from unittest.mock import AsyncMock, Mock

import pytest

from packages.domain.schemas import (
    AdvertiserBrandCreate,
    AdvertiserBrandUpdate,
)

ORG_ID = "00000000-0000-0000-0000-000000000200"


# ── Schema tests ──

class TestBrandCreateSchema:
    def test_minimal_valid(self):
        body = AdvertiserBrandCreate(
            advertiser_organization_id=ORG_ID,
            code="TST-001",
            name="Test Brand",
        )
        assert body.code == "TST-001"
        assert body.name == "Test Brand"

    def test_name_required(self):
        with pytest.raises(Exception):
            AdvertiserBrandCreate(
                advertiser_organization_id=ORG_ID,
                code="TST-001",
            )

    def test_code_required(self):
        with pytest.raises(Exception):
            AdvertiserBrandCreate(
                advertiser_organization_id=ORG_ID,
                name="No Code",
            )


class TestBrandUpdateSchema:
    def test_partial_update_name_only(self):
        body = AdvertiserBrandUpdate(name="New Name")
        assert body.name == "New Name"
        assert body.code is None

    def test_empty_body_ok(self):
        body = AdvertiserBrandUpdate()
        assert body.name is None


# ── Repository tests ──

@pytest.mark.asyncio
async def test_create_brand_repo():
    from packages.domain.repository import create_advertiser_brand
    from packages.domain.models import AdvertiserBrand

    session = AsyncMock()
    brand_id = str(uuid.uuid4())

    async def fake_flush():
        pass

    session.flush = fake_flush

    result = await create_advertiser_brand(
        session, ORG_ID, "CODE-01", "Brand One", "desc",
    )
    assert result.advertiser_organization_id == ORG_ID
    assert result.code == "CODE-01"
    assert result.name == "Brand One"
    assert result.status == "active"
    session.add.assert_called_once()


@pytest.mark.asyncio
async def test_update_brand_not_found():
    from packages.domain.repository import update_advertiser_brand

    session = AsyncMock()
    # Simulate empty result
    session.execute = AsyncMock(return_value=Mock())
    session.execute.return_value.scalar_one_or_none = Mock(return_value=None)

    result = await update_advertiser_brand(
        session, "nonexistent", ORG_ID, name="X",
    )
    assert result is None


@pytest.mark.asyncio
async def test_update_brand_cross_org_rejected():
    """Brand not found = cross-org because WHERE filters by org_id."""
    from packages.domain.repository import update_advertiser_brand

    session = AsyncMock()
    session.execute = AsyncMock(return_value=Mock())
    session.execute.return_value.scalar_one_or_none = Mock(return_value=None)

    result = await update_advertiser_brand(
        session,
        "some-brand-id",
        "00000000-0000-0000-0000-000000000999",  # wrong org
        name="X",
    )
    assert result is None
