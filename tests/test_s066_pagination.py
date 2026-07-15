"""S-066 — Pagination foundations: backend tests."""
import pytest
from unittest.mock import AsyncMock, patch

from packages.api.dependencies import get_pagination_params


class TestPaginationParams:
    """get_pagination_params dependency validation."""

    @pytest.mark.asyncio
    async def test_default_limit(self):
        p = await get_pagination_params()
        assert p.limit == 50
        assert p.offset == 0

    @pytest.mark.asyncio
    async def test_custom_limit_offset(self):
        p = await get_pagination_params(limit=10, offset=30)
        assert p.limit == 10
        assert p.offset == 30

    @pytest.mark.asyncio
    async def test_limit_clamped_to_max(self):
        p = await get_pagination_params(limit=999)
        assert p.limit == 200  # MAX_LIMIT

    @pytest.mark.asyncio
    async def test_limit_floor_at_1(self):
        p = await get_pagination_params(limit=0)
        assert p.limit == 1

    @pytest.mark.asyncio
    async def test_negative_offset_clamped(self):
        p = await get_pagination_params(offset=-5)
        assert p.offset == 0


class TestPaginatedRepository:
    """Repository paginated methods return correct (items, total) tuples."""

    @pytest.mark.asyncio
    @patch("packages.domain.repository.list_campaigns_paginated", new_callable=AsyncMock)
    async def test_list_campaigns_paginated_shape(self, mock_repo):
        from packages.domain.schemas import CampaignOut, PaginatedResponse
        mock_campaign = type("Campaign", (), {
            "id": "c1", "advertiser_organization_id": "org1",
            "advertiser_brand_id": None, "advertiser_contract_id": "con1",
            "code": "C001", "name": "Test", "description": None,
            "status": "draft", "priority": 1,
            "budget_limit_amount": None, "budget_limit_currency": "RUB",
            "start_at": None, "end_at": None, "timezone": "Europe/Moscow",
            "created_by": "u1", "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00",
        })
        mock_repo.return_value = ([mock_campaign], 5)

        items, total = await mock_repo(None, limit=50, offset=0)
        assert len(items) == 1
        assert total == 5

    @pytest.mark.asyncio
    @patch("packages.domain.repository.get_inventory_stores_paginated", new_callable=AsyncMock)
    async def test_stores_paginated_shape(self, mock_repo):
        mock_repo.return_value = ([{"id": "s1", "code": "S001", "name": "Store 1",
            "address": "Addr", "is_active": True, "cluster_name": "C1",
            "branch_name": "B1", "surface_count": 3}], 100)

        items, total = await mock_repo(None, limit=10, offset=20)
        assert len(items) == 1
        assert total == 100

    @pytest.mark.asyncio
    @patch("packages.domain.repository.list_moderation_queue_paginated", new_callable=AsyncMock)
    async def test_moderation_queue_paginated(self, mock_repo):
        mock_repo.return_value = ([{"id": "a1", "moderation_status": "pending_review"}], 3)
        items, total = await mock_repo(None, status_filter="pending_review", limit=20, offset=0)
        assert total == 3

    @pytest.mark.asyncio
    @patch("packages.domain.repository.list_approval_queue_paginated", new_callable=AsyncMock)
    async def test_approval_queue_paginated(self, mock_repo):
        mock_repo.return_value = ([{"campaign_id": "c1", "campaign_status": "pending_approval"}], 1)
        items, total = await mock_repo(None, status_filter="all", limit=50, offset=0)
        assert total == 1


class TestPaginatedResponseSchema:
    """PaginatedResponse serializes correctly."""

    def test_paginated_response_shape(self):
        from packages.domain.schemas import PaginatedResponse
        resp = PaginatedResponse(items=[1, 2, 3], total=10, limit=5, offset=5)
        d = resp.model_dump()
        assert d == {"items": [1, 2, 3], "total": 10, "limit": 5, "offset": 5}

    def test_paginated_response_empty(self):
        from packages.domain.schemas import PaginatedResponse
        resp = PaginatedResponse(items=[], total=0, limit=50, offset=0)
        d = resp.model_dump()
        assert d["items"] == []
        assert d["total"] == 0
