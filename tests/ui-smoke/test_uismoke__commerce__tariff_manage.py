"""
COMMERCE-CONTUR2-001A3a — commerce.tariff_manage + commerce.price_list_manage UI-smoke.

Happy-path (10 шагов):
  1. login → 2. Коммерция (nav) → 3. create tariff (code/name/valid_from)
  → 4. save → 5. verify row → 6. edit tariff status
  → 7. switch to Прайс-листы → 8. select tariff → 9. create price item
  → 10. reload persistence (tariff + price item survive).

Only /login via page.goto(); all navigation via clicks.
SEED_SURFACE_ID = 00000000-0000-0000-0000-000000000031 — deterministic from seed.

UI-SMOKE-FLAKE-003 fix: navigation race — after clicking "Коммерция" the
React Router SPA transition is asynchronous; `wait_for_url` + `networkidle`
pass BEFORE the new page renders, so a bare `h1` selector grabbed the old
"Кампании" h1. Replaced with state-based waits on the page container
(`data-testid="commerce-tariffs-page"`) and form detach/attach, removing
all arbitrary `wait_for_timeout` sleeps.
"""
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
    # State-based wait: the commerce page container must actually render.
    # `networkidle` is not sufficient — React Router SPA transition can leave
    # the old page's h1 ("Кампании") in the DOM while the new page mounts.
    page.wait_for_selector(
        '[data-testid="commerce-tariffs-page"]', state="visible", timeout=10000
    )


def test_uismoke__commerce__tariff_manage(smoke_page):
    page = smoke_page
    login_as_break_glass_admin(page)
    _nav_commerce(page)

    # State-based: commerce page container is visible (proves nav completed)
    page.wait_for_selector(
        '[data-testid="commerce-tariffs-page"]', state="visible", timeout=10000
    )

    # 1. Create tariff
    page.locator('[data-testid="commerce-tariff-create-open"]').click()
    page.wait_for_selector(
        '[data-testid="commerce-tariff-form"]', state="visible", timeout=5000
    )

    tariff_code = f"SMOKE-{int(time.time()) % 100000}"
    page.fill('[data-testid="commerce-tariff-code"]', tariff_code)
    page.fill('[data-testid="commerce-tariff-name"]', f"Смоук тариф {tariff_code}")
    page.locator('[data-testid="commerce-tariff-submit"]').click()

    # State-based: form closes, then the new tariff row appears in the list
    page.wait_for_selector(
        '[data-testid="commerce-tariff-form"]', state="detached", timeout=8000
    )
    page.wait_for_selector(f'text={tariff_code}', timeout=8000)

    # 2. Edit tariff status via inline edit
    page.locator(
        f'[data-testid^="commerce-tariff-row-"]:has-text("{tariff_code}") button:has-text("Изменить")'
    ).click()
    page.wait_for_selector(
        '[data-testid="commerce-tariff-form"]', state="visible", timeout=5000
    )
    page.select_option('[data-testid="commerce-tariff-status"]', "active")
    page.locator('[data-testid="commerce-tariff-submit"]').click()
    # State-based: edit form detaches when the update round-trip finishes
    page.wait_for_selector(
        '[data-testid="commerce-tariff-form"]', state="detached", timeout=8000
    )
    # State-based: the row now shows "Активен" — proves loadTariffs() finished
    # re-rendering the list after the update. This closes the gap between the
    # form detaching (setEditingTariff(null)) and the re-fetched row replacing
    # the stale one, so the step-3 row click can't hit a detached element.
    page.wait_for_selector(
        f'[data-testid^="commerce-tariff-row-"]:has-text("{tariff_code}"):has-text("Активен")',
        timeout=8000,
    )

    # ── Price Item ──

    # 3. Select tariff on the Тарифы tab first (sets selectedTariffId), then switch
    page.locator(
        f'[data-testid^="commerce-tariff-row-"]:has-text("{tariff_code}")'
    ).click()

    # 4. Switch to Прайс-листы sub-tab
    page.locator('button:has-text("Прайс-листы")').click()
    # State-based: the prices header renders only when a tariff is selected
    # AND the sub-tab actually switched. This also proves the row click above
    # registered (selectedTariffId is set) — no arbitrary sleep needed.
    page.wait_for_selector('h3:has-text("Прайс-лист:")', timeout=8000)
    page.wait_for_selector(
        '[data-testid="commerce-price-item-create-open"]', state="visible", timeout=8000
    )

    # 5. Open price item creation form
    page.locator('[data-testid="commerce-price-item-create-open"]').click()
    page.wait_for_selector(
        '[data-testid="commerce-price-item-form"]', state="visible", timeout=5000
    )

    # 6. Select first available surface — wait for API data to populate
    price_value = 150.00
    page.wait_for_function(
        "document.querySelector('[data-testid=\"commerce-price-item-surface\"]')?.options?.length > 1",
        timeout=15000,
    )
    page.select_option('[data-testid="commerce-price-item-surface"]', index=1)
    page.fill('[data-testid="commerce-price-item-unit-price"]', str(price_value))
    page.locator('[data-testid="commerce-price-item-submit"]').click()
    # State-based: form detaches, price items table appears with the new row
    page.wait_for_selector(
        '[data-testid="commerce-price-item-form"]', state="detached", timeout=8000
    )

    # 7. Verify price item row
    page.wait_for_selector(
        '[data-testid="commerce-price-items-table"]', state="visible", timeout=8000
    )
    # billing_unit must be surface_day
    page.wait_for_selector('text=surface_day', timeout=5000)
    # price displayed
    page.wait_for_selector(f'text=150', timeout=5000)

    # 8. Reload persistence check — both tariff and price item
    page.reload()
    page.wait_for_load_state("networkidle")
    page.wait_for_selector(
        '[data-testid="commerce-tariffs-page"]', state="visible", timeout=10000
    )

    # Verify tariff survived reload (on Тарифы tab by default after reload)
    page.wait_for_selector(f'text={tariff_code}', timeout=8000)
    page.wait_for_selector(f'text=Активен', timeout=5000)

    # Switch back to Прайс-листы and verify price item survived
    page.locator(
        f'[data-testid^="commerce-tariff-row-"]:has-text("{tariff_code}")'
    ).click()
    page.locator('button:has-text("Прайс-листы")').click()
    page.wait_for_selector('h3:has-text("Прайс-лист:")', timeout=8000)
    page.wait_for_selector(
        '[data-testid="commerce-price-items-table"]', state="visible", timeout=8000
    )
    page.wait_for_selector('text=surface_day', timeout=5000)
    page.wait_for_selector(f'text=150', timeout=5000)
