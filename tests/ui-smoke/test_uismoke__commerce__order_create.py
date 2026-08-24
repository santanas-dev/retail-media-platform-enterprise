"""
COMMERCE-CONTUR2-001A3b+A3c — commerce.order_create + close UI-smoke.

Happy-path (12 шагов):
  1. login → 2. Коммерция (nav) → 3. create tariff
  → 4. switch to Заказы → 5. create order (org + tariff + surface + dates)
  → 6. verify order row (code, status, total) → 7. click row → verify lines
  → 8. transition draft→offered→booked→confirmed→closed
  → 9. update payment_status → 10. reload persistence (status=closed).
  → 11. no transition buttons for closed order (terminal).
  → 12. commerce.order_close smoke proof.

Only /login via page.goto(); all navigation via clicks.
SEED_ADV_ORG_ID = 00000000-0000-0000-0000-000000000200
SEED_SURFACE_ID = 00000000-0000-0000-0000-000000000031
"""
import os
import re
import time
import pytest
from playwright.sync_api import expect
from conftest import login_as_break_glass_admin, unique_suffix, wait_settled

SEED_ADV_ORG_ID = "00000000-0000-0000-0000-000000000200"
SEED_SURFACE_ID = "00000000-0000-0000-0000-000000000031"


def _nav_commerce(page):
    link = page.locator('aside nav a:has-text("Коммерция")')
    link.wait_for(state="visible", timeout=10000)
    link.click(force=True)
    page.wait_for_url("**/commerce/tariffs", timeout=8000)
    # State-based: the commerce page container must actually render before
    # proceeding. `networkidle` + a bare h1 can grab the old «Кампании» page
    # during the SPA transition (UI-SMOKE-FLAKE-003).
    page.wait_for_selector(
        '[data-testid="commerce-tariffs-page"]', state="visible", timeout=10000
    )


def test_uismoke__commerce__order_create(smoke_page):
    page = smoke_page
    login_as_break_glass_admin(page)
    _nav_commerce(page)

    # 1. Create tariff (needed for order)
    page.locator('[data-testid="commerce-tariff-create-open"]').click()
    page.wait_for_selector('[data-testid="commerce-tariff-form"]', timeout=5000)

    tariff_code = f"ORD-{unique_suffix()}"
    page.fill('[data-testid="commerce-tariff-code"]', tariff_code)
    page.fill('[data-testid="commerce-tariff-name"]', f"Тариф для заказа {tariff_code}")
    page.locator('[data-testid="commerce-tariff-submit"]').click()
    wait_settled(page)
    page.wait_for_selector(f'text={tariff_code}', timeout=8000)

    # Get tariff ID from row data-testid
    tariff_row = page.locator(f'[data-testid^="commerce-tariff-row-"]:has-text("{tariff_code}")')
    tariff_testid = tariff_row.get_attribute("data-testid") or ""
    tariff_id = tariff_testid.replace("commerce-tariff-row-", "")

    # 2. Create price item for this tariff (needed for order pricing)
    tariff_row.click()
    wait_settled(page)
    page.locator('button:has-text("Прайс-листы")').click()
    wait_settled(page)
    page.wait_for_selector('[data-testid="commerce-price-item-create-open"]', timeout=5000)
    page.locator('[data-testid="commerce-price-item-create-open"]').click()
    page.wait_for_selector('[data-testid="commerce-price-item-form"]', timeout=5000)
    page.wait_for_function(
        "document.querySelector('[data-testid=\"commerce-price-item-surface\"]')?.options?.length > 1",
        timeout=15000,
    )
    page.select_option('[data-testid="commerce-price-item-surface"]', index=1)
    page.fill('[data-testid="commerce-price-item-unit-price"]', "200")
    page.locator('[data-testid="commerce-price-item-submit"]').click()
    wait_settled(page)
    page.wait_for_selector('text=surface_day', timeout=5000)

    # 3a. Activate tariff (required for order creation)
    page.locator('button:has-text("Тарифы")').click()
    wait_settled(page)
    page.locator(f'[data-testid^="commerce-tariff-row-"]:has-text("{tariff_code}") button:has-text("Изменить")').click()
    page.wait_for_selector('[data-testid="commerce-tariff-form"]', timeout=5000)
    page.select_option('[data-testid="commerce-tariff-status"]', "active")
    page.locator('[data-testid="commerce-tariff-submit"]').click()
    wait_settled(page)

    # 3b. Switch to Заказы tab
    page.locator('button:has-text("Заказы")').click()
    wait_settled(page)

    # 4. Create order
    page.wait_for_selector('[data-testid="commerce-order-create-open"]', timeout=5000)
    page.locator('[data-testid="commerce-order-create-open"]').click()
    page.wait_for_selector('[data-testid="commerce-order-create-form"]', timeout=5000)

    # Wait for reference data to populate in selects
    page.wait_for_function(
        "document.querySelector('[data-testid=\"commerce-order-org-id\"]')?.options?.length > 1",
        timeout=15000,
    )
    page.wait_for_function(
        "document.querySelector('[data-testid=\"commerce-order-tariff-id\"]')?.options?.length > 1",
        timeout=5000,
    )
    page.wait_for_function(
        "document.querySelector('[data-testid=\"commerce-order-surface-id\"]')?.options?.length > 1",
        timeout=15000,
    )

    # Select by stable identifiers, NOT index=1. Accumulated test runs leave
    # stale tariffs/orgs/surfaces in the dropdown; index=1 then picks an OLD
    # tariff with a different unit_price → line_amount mismatch (amount 1200
    # vs 1600). The org/surface are seed-stable; the tariff is per-run, so
    # select its option by code.
    page.select_option('[data-testid="commerce-order-org-id"]', value=SEED_ADV_ORG_ID)
    page.select_option('[data-testid="commerce-order-surface-id"]', value=SEED_SURFACE_ID)
    tariff_option = page.locator(
        f'[data-testid="commerce-order-tariff-id"] option:has-text("{tariff_code}")'
    )
    expect(tariff_option).to_have_count(1, timeout=10000)
    page.select_option(
        '[data-testid="commerce-order-tariff-id"]',
        value=tariff_option.get_attribute("value"),
    )
    # dates pre-filled: today → today+7

    page.locator('[data-testid="commerce-order-submit"]').click()
    wait_settled(page)

    # Check for error message
    error_locator = page.locator('[data-testid="commerce-order-error"]')
    if error_locator.is_visible():
        error_text = error_locator.inner_text()
        raise AssertionError(f"Order creation error: {error_text}")

    # 5. Verify order row appears
    page.wait_for_selector('[data-testid="commerce-orders-table"]', timeout=10000)
    # Order should have status "Черновик" (draft)
    page.wait_for_selector('text=Черновик', timeout=5000)

    # COMMERCE-PRICING-001: assert non-zero total (no silent zero-priced order)
    order_row = page.locator('[data-testid^="commerce-order-row-"]').first
    order_testid = order_row.get_attribute("data-testid") or ""
    order_id = order_testid.replace("commerce-order-row-", "")
    total_el = page.locator(f'[data-testid="commerce-order-total-{order_id}"]')
    total_text = total_el.inner_text().strip()
    total_digits = re.sub(r"\D", "", total_text)
    assert total_digits and int(total_digits) > 0, (
        f"Order total must be non-zero, got: {total_text!r}"
    )

    # 6. Click order row to see detail
    order_row.click()
    wait_settled(page)
    page.wait_for_selector('[data-testid="commerce-order-detail"]', timeout=5000)
    page.wait_for_selector('[data-testid="commerce-order-lines-table"]', timeout=5000)

    # COMMERCE-PRICING-001: line_amount = unit_price × server-derived days.
    # Price item was created with unit_price=200; date range today→today+7 = 8 days.
    days_el = page.locator('[data-testid^="commerce-order-line-days-"]').first
    days_text = days_el.inner_text().strip()
    days = int(re.sub(r"\D", "", days_text))
    assert days >= 1, f"quantity_days must be >= 1 (server-derived), got: {days_text!r}"

    amount_el = page.locator('[data-testid^="commerce-order-line-amount-"]').first
    amount_text = amount_el.inner_text().strip()
    amount_digits = int(re.sub(r"\D", "", amount_text))
    assert amount_digits == 200 * days, (
        f"line_amount must equal unit_price(200) × days({days}) = {200 * days}, "
        f"got {amount_text!r}"
    )

    # 7. Transition: draft → offered
    page.locator('[data-testid="commerce-order-transition-offered"]').click()
    wait_settled(page)
    page.wait_for_selector('text=Предложен', timeout=5000)

    # 8. Transition: offered → booked
    page.locator('[data-testid="commerce-order-transition-booked"]').click()
    wait_settled(page)
    page.wait_for_selector('text=Забронирован', timeout=5000)

    # 8b. Transition: booked → confirmed
    page.locator('[data-testid="commerce-order-transition-confirmed"]').click()
    wait_settled(page)
    page.wait_for_selector('text=Подтверждён', timeout=5000)

    # 8c. Transition: confirmed → closed (A3c — order_close proof)
    page.locator('[data-testid="commerce-order-transition-closed"]').click()
    wait_settled(page)
    page.wait_for_selector('text=Закрыт', timeout=5000)

    # 9. Update payment status
    page.select_option('[data-testid="commerce-order-payment-select"]', "paid")
    wait_settled(page)
    page.wait_for_selector('[data-testid="commerce-order-payment-status"]:has-text("Оплачен")', timeout=10000)

    # 10. Reload persistence — verify order stays closed
    page.reload()
    wait_settled(page)
    page.wait_for_selector('h1', timeout=10000)

    # Switch to Заказы and verify order survived as closed
    page.locator('button:has-text("Заказы")').click()
    wait_settled(page)
    page.wait_for_selector('[data-testid="commerce-orders-table"]', timeout=8000)
    page.wait_for_selector('text=Закрыт', timeout=5000)

    # COMMERCE-PRICING-001: reload preserves same non-zero total
    reload_row = page.locator('[data-testid^="commerce-order-row-"]').first
    reload_testid = reload_row.get_attribute("data-testid") or ""
    reload_order_id = reload_testid.replace("commerce-order-row-", "")
    reload_total = page.locator(f'[data-testid="commerce-order-total-{reload_order_id}"]').inner_text().strip()
    reload_digits = re.sub(r"\D", "", reload_total)
    assert reload_digits == total_digits, (
        f"Reload must preserve total: before={total_digits!r}, after={reload_digits!r}"
    )

    # Click order row to expand detail (selectedOrder resets on reload)
    reload_row.click()
    wait_settled(page)
    page.wait_for_selector('[data-testid="commerce-order-detail"]', timeout=5000)
    page.wait_for_selector('[data-testid="commerce-order-payment-status"]:has-text("Оплачен")', timeout=5000)

    # 11. Terminal: closed order has no transition buttons
    # Verify none of the transition buttons exist
    for btn in ["offered", "booked", "confirmed", "closed", "cancelled"]:
        loc = page.locator(f'[data-testid="commerce-order-transition-{btn}"]')
        assert loc.count() == 0, f"Closed order should have no transition buttons, but found '{btn}'"
