"""
Tests — Commerce Contour 2 pricing choke-point (COMMERCE-CONTUR2-001A1).
"""
from datetime import date
from decimal import Decimal

import pytest

from packages.domain import CommerceTariffStatus, BillingUnit
from packages.domain.schemas import (
    CommerceOrderLineCreate,
    CommerceQuoteRequest,
    CommerceQuoteResponse,
)


# ── Unit tests: CommerceQuoteResponse structure ──


class TestCommerceQuoteResponse:
    def test_empty_quote_defaults(self):
        resp = CommerceQuoteResponse(tariff_version_id="tv-1", currency="RUB")
        assert resp.total_amount == 0.0
        assert resp.lines == []
        assert resp.errors == []

    def test_quote_with_lines_and_total(self):
        resp = CommerceQuoteResponse(
            tariff_version_id="tv-1",
            currency="RUB",
            lines=[],
            total_amount=1500.0,
            errors=[],
        )
        assert resp.total_amount == 1500.0

    def test_quote_with_errors(self):
        resp = CommerceQuoteResponse(
            tariff_version_id="tv-1",
            currency="RUB",
            errors=["No price for surface s1"],
        )
        assert len(resp.errors) == 1
        assert "No price" in resp.errors[0]


# ── Unit tests: CommerceQuoteRequest validation ──


class TestCommerceQuoteRequest:
    def test_valid_request(self):
        req = CommerceQuoteRequest(
            tariff_version_id="tv-1",
            advertiser_organization_id="org-1",
            lines=[
                CommerceOrderLineCreate(
                    surface_id="s1",
                    date_from=date(2026, 8, 1),
                    date_to=date(2026, 8, 5),
                    quantity_days=5,
                    unit_price_amount=100.0,
                    line_amount=500.0,
                ),
            ],
        )
        assert len(req.lines) == 1
        assert req.lines[0].quantity_days == 5

    def test_no_lines_rejected(self):
        with pytest.raises(Exception):  # pydantic validation error
            CommerceQuoteRequest(
                tariff_version_id="tv-1",
                advertiser_organization_id="org-1",
                lines=[],
            )


# ── Unit tests: pricing logic (pure function, no DB) ──


class TestPricingLogic:
    """Test the pricing calculation independently of the DB-dependent function."""

    def test_single_surface_day_pricing(self):
        """surface_day: unit_price * days = line_amount."""
        unit_price = Decimal("150.00")
        days = 10
        expected = unit_price * days
        assert float(expected) == 1500.0

    def test_multiple_surfaces_sum(self):
        prices = {"s1": Decimal("100"), "s2": Decimal("200")}
        days = {"s1": 5, "s2": 3}
        total = prices["s1"] * days["s1"] + prices["s2"] * days["s2"]
        assert float(total) == 1100.0

    def test_zero_days_zero_amount(self):
        assert float(Decimal("500") * 0) == 0.0

    def test_date_range_to_days(self):
        """Verify date arithmetic: (date_to - date_from).days + 1 = quantity."""
        d1 = date(2026, 8, 1)
        d2 = date(2026, 8, 5)
        days = (d2 - d1).days + 1  # inclusive
        assert days == 5


# ── Unit tests: enums ──


class TestCommerceEnums:
    def test_order_statuses(self):
        from packages.domain import CommerceOrderStatus
        assert CommerceOrderStatus.DRAFT == "draft"
        assert CommerceOrderStatus.CONFIRMED == "confirmed"
        assert CommerceOrderStatus.CANCELLED == "cancelled"

    def test_payment_statuses(self):
        from packages.domain import CommercePaymentStatus
        assert CommercePaymentStatus.NOT_REQUIRED == "not_required"
        assert CommercePaymentStatus.PAID == "paid"

    def test_tariff_statuses(self):
        from packages.domain import CommerceTariffStatus
        assert CommerceTariffStatus.DRAFT == "draft"
        assert CommerceTariffStatus.ACTIVE == "active"
        assert CommerceTariffStatus.ARCHIVED == "archived"

    def test_billing_unit(self):
        from packages.domain import BillingUnit
        assert BillingUnit.SURFACE_DAY == "surface_day"


# ── Unit tests: schema validation ──


class TestCommerceOrderLineCreate:
    def test_negative_days_rejected(self):
        with pytest.raises(Exception):
            CommerceOrderLineCreate(
                surface_id="s1",
                date_from=date(2026, 8, 1),
                date_to=date(2026, 8, 5),
                quantity_days=-1,
                unit_price_amount=100.0,
                line_amount=-500.0,
            )

    def test_zero_price_accepted(self):
        """Zero unit_price/line_amount is valid at Pydantic level (ge=0).
        Business validation (nonzero price) happens at service layer."""
        line = CommerceOrderLineCreate(
            surface_id="s1",
            date_from=date(2026, 8, 1),
            date_to=date(2026, 8, 5),
            quantity_days=5,
            unit_price_amount=0.0,
            line_amount=0.0,
        )
        assert line.unit_price_amount == 0.0
        assert line.line_amount == 0.0

    def test_date_to_before_date_from_rejected(self):
        """COMMERCE-PRICING-001: date_to < date_from must be rejected (422)."""
        with pytest.raises(Exception):
            CommerceOrderLineCreate(
                surface_id="s1",
                date_from=date(2026, 8, 5),
                date_to=date(2026, 8, 1),
            )

    def test_client_quantity_days_ignored_field_retained(self):
        """quantity_days remains in DTO for backward compat; value is not used
        for pricing (server derives from dates)."""
        line = CommerceOrderLineCreate(
            surface_id="s1",
            date_from=date(2026, 8, 1),
            date_to=date(2026, 8, 5),
            quantity_days=0,  # client sends 0 — accepted, ignored for pricing
        )
        assert line.quantity_days == 0


# ── COMMERCE-PRICING-001: server-derived quantity_days ──


class TestDeriveQuantityDays:
    def test_one_day_range(self):
        from packages.domain.commerce_repository import derive_quantity_days
        d = date(2026, 8, 1)
        assert derive_quantity_days(d, d) == 1

    def test_multi_day_range_inclusive(self):
        from packages.domain.commerce_repository import derive_quantity_days
        assert derive_quantity_days(date(2026, 8, 1), date(2026, 8, 5)) == 5

    def test_date_to_before_date_from_raises(self):
        from packages.domain.commerce_repository import derive_quantity_days
        with pytest.raises(ValueError, match="date_to must be >= date_from"):
            derive_quantity_days(date(2026, 8, 5), date(2026, 8, 1))

    def test_never_zero(self):
        from packages.domain.commerce_repository import derive_quantity_days
        # Any valid inclusive range yields >= 1 — never 0.
        assert derive_quantity_days(date(2026, 8, 1), date(2026, 8, 1)) == 1


# ── COMMERCE-PRICING-001: calculate_order_quote with server-derived days ──


class _FakeTariff:
    id = "tv-1"
    code = "TV-1"
    currency = "RUB"


class _FakePriceItem:
    def __init__(self, unit_price: Decimal):
        self.unit_price_amount = unit_price


class _FakeSurfaceResult:
    """Mimics SQLAlchemy result with .all() returning rows indexed by [0]."""

    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


@pytest.mark.asyncio
class TestCalculateOrderQuoteServerDays:
    async def _quote(self, lines, unit_price: Decimal, monkeypatch):
        from packages.domain import commerce_repository as crepo

        async def fake_active_tariff(session, tariff_version_id=None):
            return _FakeTariff()

        async def fake_list_price_items(session, tariff_version_id, surface_ids):
            return {sid: _FakePriceItem(unit_price) for sid in surface_ids}

        async def fake_execute(stmt):
            # Surface existence check returns all requested surface ids
            surface_ids = list(stmt.right.value) if hasattr(stmt, "right") else ["s1"]
            rows = [(sid,) for sid in surface_ids]
            return _FakeSurfaceResult(rows)

        monkeypatch.setattr(crepo, "get_active_tariff_version", fake_active_tariff)
        monkeypatch.setattr(crepo, "list_price_items", fake_list_price_items)

        class _Sess:
            async def execute(self, stmt):
                return await fake_execute(stmt)

        req = CommerceQuoteRequest(
            tariff_version_id="tv-1",
            advertiser_organization_id="org-1",
            lines=lines,
        )
        return await crepo.calculate_order_quote(_Sess(), req)

    async def test_one_day_range_total_equals_unit_price(self, monkeypatch):
        line = CommerceOrderLineCreate(
            surface_id="s1",
            date_from=date(2026, 8, 1),
            date_to=date(2026, 8, 1),
        )
        quote = await self._quote([line], Decimal("100.00"), monkeypatch)
        assert quote.lines[0].quantity_days == 1
        assert quote.lines[0].line_amount == 100.0
        assert quote.total_amount == 100.0

    async def test_multi_day_range_total_is_price_times_days(self, monkeypatch):
        line = CommerceOrderLineCreate(
            surface_id="s1",
            date_from=date(2026, 8, 1),
            date_to=date(2026, 8, 5),
        )
        quote = await self._quote([line], Decimal("200.00"), monkeypatch)
        assert quote.lines[0].quantity_days == 5
        assert quote.lines[0].line_amount == 1000.0
        assert quote.total_amount == 1000.0

    async def test_client_zero_days_ignored_server_derives(self, monkeypatch):
        """Client sends quantity_days=0; server derives 5 from date range."""
        line = CommerceOrderLineCreate(
            surface_id="s1",
            date_from=date(2026, 8, 1),
            date_to=date(2026, 8, 5),
            quantity_days=0,  # client sends 0
        )
        quote = await self._quote([line], Decimal("150.00"), monkeypatch)
        assert quote.lines[0].quantity_days == 5
        assert quote.lines[0].line_amount == 750.0
        assert quote.total_amount == 750.0


# ── COMMERCE-PRICING-001: create_order wires server-derived total ──


class _FakeOrderSession:
    """Session supporting execute/add/flush/refresh used by create_order."""

    def __init__(self, surface_ids):
        self._surface_ids = surface_ids
        self.added = []
        self.order = None

    async def execute(self, stmt):
        return _FakeSurfaceResult([(sid,) for sid in self._surface_ids])

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        pass

    async def refresh(self, obj, attrs):
        # Attach the added CommerceOrderLine objects to the order for serialization
        from packages.domain.models import CommerceOrderLine
        lines = [o for o in self.added if isinstance(o, CommerceOrderLine)]
        if lines:
            obj.lines = lines


@pytest.mark.asyncio
class TestCreateOrderServerTotal:
    async def test_create_order_without_quantity_days_nonzero_total(self, monkeypatch):
        """create_order without client quantity_days → non-zero total derived from dates."""
        from packages.domain import commerce_repository as crepo
        from packages.domain.models import CommerceOrder

        async def fake_active_tariff(session, tariff_version_id=None):
            return _FakeTariff()

        async def fake_list_price_items(session, tariff_version_id, surface_ids):
            return {sid: _FakePriceItem(Decimal("200.00")) for sid in surface_ids}

        monkeypatch.setattr(crepo, "get_active_tariff_version", fake_active_tariff)
        monkeypatch.setattr(crepo, "list_price_items", fake_list_price_items)

        session = _FakeOrderSession(surface_ids=["s1"])
        line = CommerceOrderLineCreate(
            surface_id="s1",
            date_from=date(2026, 8, 1),
            date_to=date(2026, 8, 7),  # 7 days inclusive
            # no quantity_days → defaults to 0, server must derive 7
        )
        order = await crepo.create_order(
            session,
            advertiser_organization_id="org-1",
            tariff_version_id="tv-1",
            lines=[line],
            scope_advertiser_ids=None,
        )

        assert isinstance(order, CommerceOrder)
        assert order.total_amount == Decimal("1400.00")  # 200 * 7
        assert order.lines[0].quantity_days == 7
        assert order.lines[0].line_amount == Decimal("1400.00")
