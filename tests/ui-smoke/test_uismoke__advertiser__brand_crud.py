"""
ADVERTISER-UX-001B1 — advertiser.brand_crud UI-smoke.

Happy-path: login → Рекламодатели → select ADV-001 → Бренды → create brand → verify → edit → verify → reload persist.

Only /login via page.goto(); all navigation via clicks.
"""
import pytest
from conftest import login_as_break_glass_admin


def _navigate_to_advertisers(page):
    link = page.locator('aside nav a[href="/advertisers"]')
    link.click(force=True)
    page.wait_for_url("**/advertisers", timeout=8000)
    page.wait_for_load_state("networkidle")


def test_uismoke__advertiser__brand_crud(smoke_page):
    page = smoke_page
    login_as_break_glass_admin(page)

    _navigate_to_advertisers(page)

    # Click first org row to open detail
    row = page.locator('[data-testid="advertiser-org-row"]').first
    row.click()
    page.wait_for_selector('[data-testid="advertiser-detail-panel"]', timeout=5000)

    # Click "Бренды" tab
    page.locator('text=Бренды').last.click()
    page.wait_for_selector('[data-testid="advertiser-brands-section"]', timeout=5000)

    # Click "Добавить бренд"
    page.locator('[data-testid="advertiser-brand-create-open"]').click()
    page.wait_for_selector('[data-testid="advertiser-brand-submit"]', timeout=5000)

    # Fill form with deterministic but unique data
    import time
    brand_code = f"SMOKE-{int(time.time()) % 100000}"
    brand_name = f"Смоук Бренд {brand_code}"
    page.fill('[data-testid="advertiser-brand-code"]', brand_code)
    page.fill('[data-testid="advertiser-brand-name"]', brand_name)
    page.fill('[data-testid="advertiser-brand-description"]', "Smoke test brand description")

    # Save
    page.locator('[data-testid="advertiser-brand-submit"]').click()

    # Wait for brand row with our specific code TEXT (not just any brand row)
    page.wait_for_function(
        f"""() => {{
            const els = document.querySelectorAll('[data-testid^="advertiser-brand-display-code-"]');
            return Array.from(els).some(el => el.textContent === '{brand_code}');
        }}""",
        timeout=10000,
    )

    # Find the row containing our brand code
    all_code_els = page.locator('td[data-testid^="advertiser-brand-display-code-"]')
    count = all_code_els.count()
    brand_id = None
    for i in range(count):
        el = all_code_els.nth(i)
        if el.text_content() == brand_code:
            testid = el.get_attribute("data-testid") or ""
            brand_id = testid.replace("advertiser-brand-display-code-", "")
            break
    assert brand_id is not None, f"Brand row with code '{brand_code}' not found"

    # Verify display
    assert page.locator(f'[data-testid="advertiser-brand-display-name-{brand_id}"]').text_content() == brand_name
    assert page.locator(f'[data-testid="advertiser-brand-display-code-{brand_id}"]').text_content() == brand_code

    # Edit brand
    page.locator(f'[data-testid="advertiser-brand-edit-{brand_id}"]').click()
    # Wait for inline edit — name input should be visible
    page.wait_for_selector(f'[data-testid="advertiser-brand-row-{brand_id}"] input[data-testid="advertiser-brand-name"]', timeout=3000)

    updated_name = "Смоук Бренд Обновлён"
    page.fill(f'[data-testid="advertiser-brand-row-{brand_id}"] input[data-testid="advertiser-brand-name"]', updated_name)
    # Click ✓ save
    page.locator(f'[data-testid="advertiser-brand-row-{brand_id}"] button').first.click()

    # Wait for detail reload and updated name
    page.wait_for_selector(f'[data-testid="advertiser-brand-display-name-{brand_id}"]', timeout=10000)

    # Verify updated name
    assert page.locator(f'[data-testid="advertiser-brand-display-name-{brand_id}"]').text_content() == updated_name

    # Reload persistence via sidebar navigation
    page.locator('aside nav a[href="/advertisers"]').click(force=True)
    page.wait_for_url("**/advertisers", timeout=8000)
    page.wait_for_load_state("networkidle")

    # Re-open detail
    row = page.locator('[data-testid="advertiser-org-row"]').first
    row.click()
    page.wait_for_selector('[data-testid="advertiser-detail-panel"]', timeout=5000)
    page.locator('text=Бренды').last.click()
    page.wait_for_selector(f'[data-testid="advertiser-brand-display-name-{brand_id}"]', timeout=10000)

    # Verify persistence
    assert page.locator(f'[data-testid="advertiser-brand-display-name-{brand_id}"]').text_content() == updated_name
    assert page.locator(f'[data-testid="advertiser-brand-display-code-{brand_id}"]').text_content() == brand_code
