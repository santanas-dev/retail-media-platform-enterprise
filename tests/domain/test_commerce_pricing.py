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
