"""
ADVERTISER-UX-001C1 — Auto-generated advertiser organization code tests.
"""
import datetime as dt
import re
from unittest.mock import AsyncMock, Mock, patch

import pytest

from packages.domain.schemas import AdvertiserOrganizationCreate

# ── Schema tests ──


class TestOrgCreateSchemaCodeOptional:
    def test_code_can_be_none(self):
        """Code is now optional — omitting it is valid."""
        body = AdvertiserOrganizationCreate(
            legal_name="ООО Тест",
            display_name="Тест",
        )
        assert body.code is None

    def test_code_can_be_explicit(self):
        """Backward compat — explicit code still accepted."""
        body = AdvertiserOrganizationCreate(
            code="EXPLICIT-01",
            legal_name="ООО Тест",
            display_name="Тест",
        )
        assert body.code == "EXPLICIT-01"


# ── Code generation pattern tests ──


class TestGenerateAdvertiserOrgCode:
    def test_pattern_matches_format(self):
        """Generated code must match ADV-YYYY-NNNN."""
        year = dt.date.today().year
        pattern = re.compile(rf"^ADV-{year}-\d{{4}}$")
        candidate = f"ADV-{year}-0001"
        assert pattern.match(candidate), f"{candidate} does not match {pattern.pattern}"

    @pytest.mark.asyncio
    async def test_first_code_when_empty(self):
        """When no existing codes for this year, first code is ADV-YYYY-0001."""
        from packages.domain.repository import generate_advertiser_org_code

        session = AsyncMock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None  # no existing codes
        session.execute.return_value = mock_result

        code = await generate_advertiser_org_code(session)
        year = dt.date.today().year
        assert code == f"ADV-{year}-0001"

    @pytest.mark.asyncio
    async def test_increments_last_code(self):
        """When ADV-2026-0005 exists, next is ADV-2026-0006."""
        from packages.domain.repository import generate_advertiser_org_code

        session = AsyncMock()
        year = dt.date.today().year
        last_code = f"ADV-{year}-0005"

        mock_result_last = Mock()
        mock_result_last.scalar_one_or_none.return_value = last_code

        mock_result_check = Mock()
        mock_result_check.scalar_one_or_none.return_value = None  # candidate is free

        session.execute.side_effect = [mock_result_last, mock_result_check]

        code = await generate_advertiser_org_code(session)
        assert code == f"ADV-{year}-0006"

    @pytest.mark.asyncio
    async def test_retries_on_collision(self):
        """When candidate collides, retries with next number."""
        from packages.domain.repository import generate_advertiser_org_code

        session = AsyncMock()
        year = dt.date.today().year
        last_code = f"ADV-{year}-0002"

        # First query: max code = 0002
        mock_result_last = Mock()
        mock_result_last.scalar_one_or_none.return_value = last_code

        # Second query: check ADV-2026-0003 → exists (collision)
        mock_result_check_collision = Mock()
        mock_result_check_collision.scalar_one_or_none.return_value = "existing-id"

        # Third query: check ADV-2026-0004 → free
        mock_result_check_free = Mock()
        mock_result_check_free.scalar_one_or_none.return_value = None

        session.execute.side_effect = [
            mock_result_last,
            mock_result_check_collision,
            mock_result_check_free,
        ]

        code = await generate_advertiser_org_code(session)
        assert code == f"ADV-{year}-0004"


# ── Repository create tests ──


class TestCreateAdvertiserOrgAutoCode:
    @pytest.mark.asyncio
    async def test_auto_generates_code_when_none(self):
        """create_advertiser_organization auto-generates code when code=None."""
        from packages.domain.repository import create_advertiser_organization

        session = AsyncMock()
        year = dt.date.today().year
        generated = f"ADV-{year}-0001"

        with patch(
            "packages.domain.repository.generate_advertiser_org_code",
            return_value=generated,
        ):
            org = await create_advertiser_organization(
                session,
                code=None,
                legal_name="ООО Тест",
                display_name="Тест",
            )

        assert org.code == generated
        session.add.assert_called_once()
        session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_uses_explicit_code_when_provided(self):
        """Backward compat — explicit code passed through unchanged."""
        from packages.domain.repository import create_advertiser_organization

        session = AsyncMock()

        org = await create_advertiser_organization(
            session,
            code="EXPLICIT-01",
            legal_name="ООО Тест",
            display_name="Тест",
        )

        assert org.code == "EXPLICIT-01"
