"""
COMMERCE-CONTUR2-001A3a — commerce.tariff_manage UI-smoke.

Happy-path (10 шагов):
  1. login → 2. Коммерция (nav) → 3. create tariff (code/name/valid_from)
  → 4. save → 5. verify row → 6. select tariff → 7. Прайс-листы tab
  → 8. create price item → 9. verify row → 10. reload persistence.

Only /login via page.goto(); all navigation via clicks.
"""
import os
import time
import pytest
from conftest import login_as_break_glass_admin


def _nav_commerce(page):
    link = page.locator('aside nav a[href="/commerce/tariffs"]')
    link.click(force=True)
    page.wait_for_url("**/commerce/tariffs", timeout=8000)
    page.wait_for_load_state("networkidle")


def test_uismoke__commerce__tariff_manage(smoke_page):
    page = smoke_page
    login_as_break_glass_admin(page)
    _nav_commerce(page)

    # Wait for page to load — use h1 text (more robust than testid in CI)
    page.wait_for_selector('h1', timeout=10000)
    expect_text = page.locator('h1').inner_text()
    assert "Коммерция" in expect_text, f"Expected Коммерция, got: {expect_text}"

    # 1. Create tariff
    page.locator('[data-testid="commerce-tariff-create-open"]').click()
    page.wait_for_selector('[data-testid="commerce-tariff-form"]', timeout=5000)

    tariff_code = f"SMOKE-{int(time.time()) % 100000}"
    page.fill('[data-testid="commerce-tariff-code"]', tariff_code)
    page.fill('[data-testid="commerce-tariff-name"]', f"Смоук тариф {tariff_code}")
    page.locator('[data-testid="commerce-tariff-submit"]').click()

    # Wait for form to close and tariff to appear in list
    page.wait_for_timeout(1000)
    page.wait_for_selector(f'text={tariff_code}', timeout=8000)

    # 2. Click the new tariff row to select it
    page.locator(f'[data-testid^="commerce-tariff-row-"]:has-text("{tariff_code}")').click()

    # 3. Switch to prices tab
    page.locator('button:has-text("Прайс-листы")').click()
    page.wait_for_timeout(1000)

    # 4. Create price item
    page.locator('[data-testid="commerce-price-item-create-open"]').click()
    page.wait_for_selector('[data-testid="commerce-price-item-form"]', timeout=5000)

    surface_id = "aaaaaaaa-bbbb-cccc-dddd-000000000001"
    page.fill('[data-testid="commerce-price-item-surface"]', surface_id)
    page.fill('[data-testid="commerce-price-item-unit-price"]', "199.99")
    page.locator('[data-testid="commerce-price-item-submit"]').click()

    # Wait for price item to appear
    page.wait_for_timeout(1000)
    page.wait_for_selector('[data-testid^="commerce-price-item-row-"]', timeout=8000)

    # 5. Reload persistence check
    page.reload()
    page.wait_for_load_state("networkidle")
    page.wait_for_selector('[data-testid="commerce-tariffs-page"]', timeout=8000)

    # Verify tariff survived reload
    page.wait_for_selector(f'text={tariff_code}', timeout=8000)

    # Switch to prices and verify price item survived
    page.wait_for_selector(f'[data-testid^="commerce-tariff-row-"]:has-text("{tariff_code}")', timeout=5000)
    page.locator(f'[data-testid^="commerce-tariff-row-"]:has-text("{tariff_code}")').click()
    page.locator('button:has-text("Прайс-листы")').click()
    page.wait_for_timeout(1000)
    page.wait_for_selector('[data-testid^="commerce-price-item-row-"]', timeout=8000)
