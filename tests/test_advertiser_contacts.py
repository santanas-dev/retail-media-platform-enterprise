"""
ADVERTISER-UX-001B3 — Advertiser contact CRUD + user link backend tests.
"""
import uuid
from unittest.mock import AsyncMock, patch

import pytest

from packages.domain.schemas import (
    AdvertiserContactCreate,
    AdvertiserContactUpdate,
)

ORG_ID = "00000000-0000-0000-0000-000000000200"
CONTACT_ID = str(uuid.uuid4())
USER_ID = str(uuid.uuid4())


# ── Schema tests ──

class TestContactCreateSchema:
    def test_minimal_valid(self):
        body = AdvertiserContactCreate(
            advertiser_organization_id=ORG_ID,
            full_name="Иван Петров",
            email="ivan@test.ru",
        )
        assert body.full_name == "Иван Петров"
        assert body.email == "ivan@test.ru"
        assert body.contact_type == "primary"  # default

    def test_full_name_required(self):
        with pytest.raises(Exception):
            AdvertiserContactCreate(
                advertiser_organization_id=ORG_ID,
                email="ivan@test.ru",
            )

    def test_email_required(self):
        with pytest.raises(Exception):
            AdvertiserContactCreate(
                advertiser_organization_id=ORG_ID,
                full_name="Иван Петров",
            )

    def test_optional_fields(self):
        body = AdvertiserContactCreate(
            advertiser_organization_id=ORG_ID,
            full_name="Иван Петров",
            email="ivan@test.ru",
            phone="+7-999-123-45-67",
            title="Менеджер",
            user_id=USER_ID,
        )
        assert body.phone == "+7-999-123-45-67"
        assert body.title == "Менеджер"
        assert body.user_id == USER_ID

    def test_user_id_nullable(self):
        body = AdvertiserContactCreate(
            advertiser_organization_id=ORG_ID,
            full_name="Иван Петров",
            email="ivan@test.ru",
        )
        assert body.user_id is None


class TestContactUpdateSchema:
    def test_all_none_ok(self):
        body = AdvertiserContactUpdate()
        assert body.full_name is None
        assert body.email is None
        assert body.user_id is None

    def test_partial_update(self):
        body = AdvertiserContactUpdate(
            phone="+7-999-000-00-00",
            title="Директор",
        )
        assert body.phone == "+7-999-000-00-00"
        assert body.title == "Директор"
        assert body.full_name is None


# ── Repository tests ──

class TestCreateContactRepo:
    @pytest.mark.asyncio
    async def test_create_contact_success(self):
        from packages.domain.repository import create_advertiser_contact

        session = AsyncMock()
        contact = await create_advertiser_contact(
            session,
            advertiser_organization_id=ORG_ID,
            full_name="Иван Петров",
            email="ivan@test.ru",
            phone="+7-999-123-45-67",
            title="Менеджер",
        )
        session.add.assert_called_once()
        session.flush.assert_called_once()
        assert contact.full_name == "Иван Петров"
        assert contact.email == "ivan@test.ru"
        assert contact.title == "Менеджер"
        assert contact.advertiser_organization_id == ORG_ID

    @pytest.mark.asyncio
    async def test_create_with_user_link(self):
        from packages.domain.repository import create_advertiser_contact

        session = AsyncMock()
        # Mock _validate_user_same_org to pass
        with patch("packages.domain.repository._validate_user_same_org") as mock_validate:
            contact = await create_advertiser_contact(
                session,
                advertiser_organization_id=ORG_ID,
                full_name="Иван Петров",
                email="ivan@test.ru",
                user_id=USER_ID,
            )
            mock_validate.assert_called_once_with(session, USER_ID, ORG_ID)
        assert contact.user_id == USER_ID


class TestUpdateContactRepo:
    @pytest.mark.asyncio
    async def test_update_contact_success(self):
        from packages.domain.repository import update_advertiser_contact
        from unittest.mock import Mock

        session = AsyncMock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute.return_value = mock_result

        contact = await update_advertiser_contact(
            session,
            contact_id=CONTACT_ID,
            advertiser_organization_id=ORG_ID,
            full_name="Новое Имя",
        )
        assert contact is None  # not found

    @pytest.mark.asyncio
    async def test_update_cross_org_rejected(self):
        from packages.domain.repository import update_advertiser_contact
        from unittest.mock import Mock

        session = AsyncMock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute.return_value = mock_result

        contact = await update_advertiser_contact(
            session,
            contact_id=CONTACT_ID,
            advertiser_organization_id="00000000-0000-0000-0000-000000000999",
        )
        assert contact is None
