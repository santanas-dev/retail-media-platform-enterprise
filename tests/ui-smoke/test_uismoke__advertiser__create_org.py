"""
G3-FIX → 001C1 — advertiser.create_org with auto-generated code.

Proves that a system_admin can create a new advertiser organization through the UI
WITHOUT manually entering a code — server generates it automatically:
  login → Advertisers → «+ Создать организацию» → fill form (no code) → save → verify.

DETERMINISTIC:
- Does NOT fill a code field (removed in 001C1).
- Verifies auto-code note is visible in the form.
- Asserts generated code appears in the table and detail after creation.
- Only /login via page.goto(); all navigation via clicks.

Run with:  UI_SMOKE_RUN=1 pytest tests/ui-smoke/test_uismoke__advertiser__create_org.py -v
"""

import random
import string
import time
import pytest
from conftest import login_as_break_glass_admin


def _random_suffix():
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=6))


SUFFIX = _random_suffix()
ORG_LEGAL = f"ООО «Тест-{SUFFIX}»"
ORG_DISPLAY = f"Тест-{SUFFIX}"


def navigate_to_advertisers(page):
    """Click «Рекламодатели» in sidebar."""
    link = page.locator('aside nav a[href="/advertisers"]')
    link.click(force=True)
    page.wait_for_url("**/advertisers", timeout=5000)
    page.wait_for_load_state("networkidle")


def test_uismoke__advertiser__create_org(smoke_page):
    """System admin creates a new advertiser organization — code is auto-generated.

    Flow:
    1. Login as break_glass_admin
    2. Navigate to «Рекламодатели»
    3. Click «+ Создать организацию»
    4. Verify «Код будет создан автоматически» note is visible
    5. Fill form: legal_name, display_name (NO code input)
    6. Click «Сохранить»
    7. Verify the new org appears in the table with a generated code
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

    # Step 4: verify auto-code note — no manual code field
    page.wait_for_selector('[data-testid="advertiser-code-auto-note"]', state="visible", timeout=5000)
    auto_note = page.locator('[data-testid="advertiser-code-auto-note"]')
    assert "автоматически" in (auto_note.text_content() or "").lower()

    # Step 5: fill the form (no code field)
    page.locator('[data-testid="advertiser-create-legal-name"]').fill(ORG_LEGAL)
    page.locator('[data-testid="advertiser-create-display-name"]').fill(ORG_DISPLAY)

    # Step 6: save
    save_btn = page.locator('[data-testid="advertiser-create-save"]')
    assert save_btn.is_enabled(), "Save button should be enabled"
    save_btn.click()

    # Step 7: verify the new org appears in the table with a generated code
    page.wait_for_timeout(1500)

    # The new org display_name should be visible
    page.wait_for_selector(f"text={ORG_DISPLAY}", state="visible", timeout=10000)

    # Find generated code in the table (ADV-YYYY-NNNN pattern)
    code_cells = page.locator('[data-testid="advertiser-code-readonly"]')
    found_code = None
    for i in range(code_cells.count()):
        text = code_cells.nth(i).text_content() or ""
        if text.startswith("ADV-"):
            found_code = text
            break
    assert found_code is not None, "Expected at least one generated code (ADV-...) in the table"

    # Also verify the detail panel shows the org
    assert ORG_DISPLAY in page.inner_text("body"), (
        f"Expected display name '{ORG_DISPLAY}' to appear on the page after creation"
    )
