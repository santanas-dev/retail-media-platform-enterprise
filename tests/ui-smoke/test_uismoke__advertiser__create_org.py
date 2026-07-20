"""
G3-FIX — advertiser.create_org HONEST smoke test.

Proves that a system_admin can create a new advertiser organization through the UI:
  login → Рекламодатели → «+ Создать организацию» → fill form → save → verify.

DETERMINISTIC:
- Fills all required fields (code, legal_name, display_name).
- Asserts the new org code appears in the table after creation.
- Only /login via page.goto() (in conftest fixture); all navigation via clicks.

Run with:  UI_SMOKE_RUN=1 pytest tests/ui-smoke/test_uismoke__advertiser__create_org.py -v
"""

import random
import string
import pytest
from conftest import login_as_break_glass_admin


def _random_code():
    """Generate a unique org code for each test run."""
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"TEST-ORG-{suffix}"


ORG_CODE = _random_code()
ORG_LEGAL = f"ООО «Тест-{ORG_CODE}»"
ORG_DISPLAY = f"Тест-{ORG_CODE}"


def navigate_to_advertisers(page):
    """Click «Рекламодатели» in sidebar."""
    link = page.locator('aside nav a[href="/advertisers"]')
    link.click(force=True)
    page.wait_for_url("**/advertisers", timeout=5000)
    page.wait_for_load_state("networkidle")


def test_uismoke__advertiser__create_org(smoke_page):
    """System admin creates a new advertiser organization.

    Deterministic flow:
    1. Login as break_glass_admin
    2. Navigate to «Рекламодатели»
    3. Click «+ Создать организацию»
    4. Fill form: code, legal_name, display_name
    5. Click «Сохранить»
    6. Verify the new org code appears in the table
    """
    page = smoke_page

    # Step 1: login
    login_as_break_glass_admin(page)

    # Step 2: navigate to «Рекламодатели»
    navigate_to_advertisers(page)

    # Step 3: click «+ Создать организацию»
    create_btn = page.locator('[data-testid="advertiser-create-open"]')
    create_btn.wait_for(state="visible", timeout=10000)
    create_btn.click()

    # Step 4: fill the form
    page.wait_for_selector('[data-testid="advertiser-create-code"]', state="visible", timeout=5000)

    page.locator('[data-testid="advertiser-create-code"]').fill(ORG_CODE)
    page.locator('[data-testid="advertiser-create-legal-name"]').fill(ORG_LEGAL)
    page.locator('[data-testid="advertiser-create-display-name"]').fill(ORG_DISPLAY)

    # Step 5: save
    save_btn = page.locator('[data-testid="advertiser-create-save"]')
    assert save_btn.is_enabled(), "Save button should be enabled"
    save_btn.click()

    # Step 6: verify the new org appears in the table
    # Wait for the table to reload (detail panel opens for new org)
    page.wait_for_timeout(1500)

    # The new org code should be visible on the page
    page.wait_for_selector(f"text={ORG_CODE}", state="visible", timeout=10000)

    # Also verify the detail panel shows the org
    assert ORG_DISPLAY in page.inner_text("body"), (
        f"Expected display name '{ORG_DISPLAY}' to appear on the page after creation"
    )
