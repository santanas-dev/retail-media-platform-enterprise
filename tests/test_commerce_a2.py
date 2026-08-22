"""
COMMERCE-CONTUR2-001A2 — Backend tests: CRUD, quotes, orders, transitions, RLS.
"""
import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest

from packages.domain import (
    CommerceOrderStatus,
    CommercePaymentStatus,
    CommerceTariffStatus,
)
from packages.domain.commerce_repository import (
    validate_order_transition,
    _ORDER_TRANSITIONS,
    _VALID_PAYMENT_STATUSES,
)
from packages.domain.schemas import (
    CommerceTariffVersionCreate,
    CommerceTariffVersionOut,
    CommerceTariffVersionUpdate,
    CommercePriceItemCreate,
    CommercePriceItemOut,
    CommercePriceItemUpdate,
    CommerceOrderCreate,
    CommerceOrderOut,
    CommerceOrderUpdate,
    CommerceOrderLineCreate,
    CommerceQuoteRequest,
    CommerceQuoteResponse,
    CommerceQuoteLine,
)

ORG_A = "00000000-0000-0000-0000-000000000a01"
ORG_B = "00000000-0000-0000-0000-000000000b01"


# ── Tariff schema tests ──


class TestTariffVersionSchema:
    def test_create_minimal(self):
        tv = CommerceTariffVersionCreate(
            code="TV-2026",
            name="Base Tariff",
            valid_from=date(2026, 1, 1),
        )
        assert tv.code == "TV-2026"
        assert tv.currency == "RUB"

    def test_create_with_valid_to(self):
        tv = CommerceTariffVersionCreate(
            code="TV-Q1",
            name="Q1 Tariff",
            valid_from=date(2026, 1, 1),
            valid_to=date(2026, 3, 31),
        )
        assert tv.valid_to == date(2026, 3, 31)

    def test_code_required(self):
        with pytest.raises(Exception):
            CommerceTariffVersionCreate(
                name="No Code",
                valid_from=date(2026, 1, 1),
            )

    def test_name_required(self):
        with pytest.raises(Exception):
            CommerceTariffVersionCreate(
                code="TV-1",
                valid_from=date(2026, 1, 1),
            )

    def test_out_from_attributes(self):
        out = CommerceTariffVersionOut(
            id="t1",
            code="TV-1",
            name="Test",
            status="draft",
            valid_from=date(2026, 1, 1),
            currency="RUB",
        )
        assert out.code == "TV-1"
        assert out.status == "draft"

    def test_update_partial(self):
        upd = CommerceTariffVersionUpdate(name="New Name")
        assert upd.name == "New Name"
        assert upd.status is None

    def test_update_status(self):
        upd = CommerceTariffVersionUpdate(status="active")
        assert upd.status == "active"


# ── Price item schema tests ──


class TestPriceItemSchema:
    def test_create_minimal(self):
        pi = CommercePriceItemCreate(
            surface_id="s1",
            unit_price_amount=150.0,
        )
        assert pi.surface_id == "s1"
        assert pi.unit_price_amount == 150.0
        assert pi.billing_unit == "surface_day"
        assert pi.currency == "RUB"

    def test_zero_price_rejected(self):
        with pytest.raises(Exception):
            CommercePriceItemCreate(surface_id="s1", unit_price_amount=0.0)

    def test_negative_price_rejected(self):
        with pytest.raises(Exception):
            CommercePriceItemCreate(surface_id="s1", unit_price_amount=-50.0)

    def test_out_from_attributes(self):
        out = CommercePriceItemOut(
            id="p1",
            tariff_version_id="tv1",
            surface_id="s1",
            billing_unit="surface_day",
            unit_price_amount=150.0,
            currency="RUB",
        )
        assert out.unit_price_amount == 150.0

    def test_update_price(self):
        upd = CommercePriceItemUpdate(unit_price_amount=200.0)
        assert upd.unit_price_amount == 200.0


# ── Quote schema tests ──


class TestQuoteSchema:
    def test_quote_response_defaults(self):
        resp = CommerceQuoteResponse(tariff_version_id="tv1", currency="RUB")
        assert resp.total_amount == 0.0
        assert resp.lines == []
        assert resp.errors == []

    def test_quote_with_errors(self):
        resp = CommerceQuoteResponse(
            tariff_version_id="tv1",
            currency="RUB",
            errors=["No price for s1"],
        )
        assert len(resp.errors) == 1

    def test_quote_request_min_lines(self):
        with pytest.raises(Exception):
            CommerceQuoteRequest(
                tariff_version_id="tv1",
                advertiser_organization_id=ORG_A,
                lines=[],
            )

    def test_quote_request_valid(self):
        req = CommerceQuoteRequest(
            tariff_version_id="tv1",
            advertiser_organization_id=ORG_A,
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


# ── Order schema tests ──


class TestOrderSchema:
    def test_create_minimal(self):
        order = CommerceOrderCreate(
            advertiser_organization_id=ORG_A,
            tariff_version_id="tv1",
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
        assert order.advertiser_organization_id == ORG_A
        assert len(order.lines) == 1

    def test_no_lines_rejected(self):
        with pytest.raises(Exception):
            CommerceOrderCreate(
                advertiser_organization_id=ORG_A,
                lines=[],
            )

    def test_out_with_lines(self):
        from packages.domain.schemas import CommerceOrderLineOut
        out = CommerceOrderOut(
            id="o1",
            advertiser_organization_id=ORG_A,
            code="ORD-001",
            status="draft",
            payment_status="not_required",
            currency="RUB",
            total_amount=1500.0,
            lines=[
                CommerceOrderLineOut(
                    id="l1",
                    order_id="o1",
                    surface_id="s1",
                    date_from=date(2026, 8, 1),
                    date_to=date(2026, 8, 5),
                    quantity_days=5,
                    unit_price_amount=100.0,
                    line_amount=500.0,
                ),
            ],
        )
        assert len(out.lines) == 1
        assert out.total_amount == 1500.0

    def test_update_new_status(self):
        upd = CommerceOrderUpdate(new_status="offered")
        assert upd.new_status == "offered"
        assert upd.payment_status is None

    def test_update_payment(self):
        upd = CommerceOrderUpdate(payment_status="paid")
        assert upd.payment_status == "paid"


# ── Status transition tests ──


class TestOrderTransitions:
    def test_draft_to_offered_valid(self):
        validate_order_transition("draft", "offered")  # no raise

    def test_draft_to_booked_invalid(self):
        with pytest.raises(ValueError, match="Cannot transition"):
            validate_order_transition("draft", "booked")

    def test_offered_to_booked_valid(self):
        validate_order_transition("offered", "booked")

    def test_offered_to_cancelled_valid(self):
        validate_order_transition("offered", "cancelled")

    def test_booked_to_confirmed_valid(self):
        validate_order_transition("booked", "confirmed")

    def test_booked_to_closed_invalid(self):
        with pytest.raises(ValueError):
            validate_order_transition("booked", "closed")

    def test_confirmed_to_closed_valid(self):
        validate_order_transition("confirmed", "closed")

    def test_closed_terminal(self):
        with pytest.raises(ValueError):
            validate_order_transition("closed", "draft")

    def test_cancelled_terminal(self):
        with pytest.raises(ValueError):
            validate_order_transition("cancelled", "draft")

    def test_unknown_status(self):
        with pytest.raises(ValueError, match="Unknown"):
            validate_order_transition("nonexistent", "draft")

    def test_transition_map_completeness(self):
        """Every known status has an entry in the transition map."""
        all_statuses = set(v.value for v in CommerceOrderStatus)
        assert set(_ORDER_TRANSITIONS.keys()) == all_statuses

    def test_valid_payment_statuses(self):
        assert "not_required" in _VALID_PAYMENT_STATUSES
        assert "paid" in _VALID_PAYMENT_STATUSES
        assert "overdue" in _VALID_PAYMENT_STATUSES
        assert "invalid_status" not in _VALID_PAYMENT_STATUSES


# ── RLS / cross-org guard tests (unit, no DB) ──


class TestCrossOrgGuard:
    def test_scope_none_allows_all(self):
        from packages.domain.commerce_repository import _assert_org_in_scope
        _assert_org_in_scope(ORG_A, None)  # no raise

    def test_org_in_scope_passes(self):
        from packages.domain.commerce_repository import _assert_org_in_scope
        _assert_org_in_scope(ORG_A, frozenset({ORG_A, ORG_B}))

    def test_org_not_in_scope_raises(self):
        from packages.domain.commerce_repository import _assert_org_in_scope
        from packages.domain.exceptions import ScopeError
        with pytest.raises(ScopeError, match="not in scope"):
            _assert_org_in_scope(ORG_A, frozenset({ORG_B}))
