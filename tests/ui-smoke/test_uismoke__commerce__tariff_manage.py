"""
COMMERCE-CONTUR2-001A3a — commerce.tariff_manage + commerce.price_list_manage UI-smoke.

Happy-path (10 шагов):
  1. login → 2. Коммерция (nav) → 3. create tariff (code/name/valid_from)
  → 4. save → 5. verify row → 6. edit tariff status
  → 7. switch to Прайс-листы → 8. select tariff → 9. create price item
  → 10. reload persistence (tariff + price item survive).

Only /login via page.goto(); all navigation via clicks.
SEED_SURFACE_ID = 00000000-0000-0000-0000-000000000031 — deterministic from seed.
"""
import os
import time
import pytest
from conftest import login_as_break_glass_admin

SEED_SURFACE_ID = "00000000-0000-0000-0000-000000000031"


def _nav_commerce(page):
    # Use text-based locator — more robust than CSS href selectors
    link = page.locator('aside nav a:has-text("Коммерция")')
    link.wait_for(state="visible", timeout=10000)
    link.click(force=True)
    page.wait_for_url("**/commerce/tariffs", timeout=8000)
    page.wait_for_load_state("networkidle")


def test_uismoke__commerce__tariff_manage(smoke_page):
    page = smoke_page
    login_as_break_glass_admin(page)
    _nav_commerce(page)

    # Wait for page to load — use h1 text
    page.wait_for_selector('h1', timeout=10000)
    h1_text = page.locator('h1').inner_text()
    assert "Коммерция" in h1_text, f"Expected Коммерция, got: {h1_text}"

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

    # 2. Edit tariff status via inline edit
    page.locator(f'[data-testid^="commerce-tariff-row-"]:has-text("{tariff_code}") button:has-text("Изменить")').click()
    page.wait_for_selector('[data-testid="commerce-tariff-form"]', timeout=5000)
    page.select_option('[data-testid="commerce-tariff-status"]', "active")
    page.locator('[data-testid="commerce-tariff-submit"]').click()
    page.wait_for_timeout(1000)

    # ── Price Item ──

    # 3. Select tariff on the Тарифы tab first (sets selectedTariffId), then switch
    page.locator(f'[data-testid^="commerce-tariff-row-"]:has-text("{tariff_code}")').click()
    page.wait_for_timeout(300)

    # 4. Switch to Прайс-листы sub-tab
    page.locator('button:has-text("Прайс-листы")').click()
    page.wait_for_timeout(500)
    page.wait_for_selector('[data-testid="commerce-price-item-create-open"]', timeout=5000)

    # 5. Open price item creation form
    page.locator('[data-testid="commerce-price-item-create-open"]').click()
    page.wait_for_selector('[data-testid="commerce-price-item-form"]', timeout=5000)

    # 6. Select first available surface — wait for API data to populate
    price_value = 150.00
    page.wait_for_function(
        "document.querySelector('[data-testid=\"commerce-price-item-surface\"]')?.options?.length > 1",
        timeout=15000,
    )
    page.select_option('[data-testid="commerce-price-item-surface"]', index=1)
    page.fill('[data-testid="commerce-price-item-unit-price"]', str(price_value))
    page.locator('[data-testid="commerce-price-item-submit"]').click()
    page.wait_for_timeout(1000)

    # 7. Verify price item row
    page.wait_for_selector('[data-testid="commerce-price-items-table"]', timeout=8000)
    # billing_unit must be surface_day
    page.wait_for_selector('text=surface_day', timeout=5000)
    # price displayed
    page.wait_for_selector(f'text=150', timeout=5000)

    # 8. Reload persistence check — both tariff and price item
    page.reload()
    page.wait_for_load_state("networkidle")
    page.wait_for_selector('h1', timeout=10000)

    # Verify tariff survived reload (on Тарифы tab by default after reload)
    page.wait_for_selector(f'text={tariff_code}', timeout=8000)
    page.wait_for_selector(f'text=Активен', timeout=5000)

    # Switch back to Прайс-листы and verify price item survived
    page.locator(f'[data-testid^="commerce-tariff-row-"]:has-text("{tariff_code}")').click()
    page.wait_for_timeout(300)
    page.locator('button:has-text("Прайс-листы")').click()
    page.wait_for_timeout(500)
    page.wait_for_selector('[data-testid="commerce-price-items-table"]', timeout=8000)
    page.wait_for_selector('text=surface_day', timeout=5000)
    page.wait_for_selector(f'text=150', timeout=5000)
