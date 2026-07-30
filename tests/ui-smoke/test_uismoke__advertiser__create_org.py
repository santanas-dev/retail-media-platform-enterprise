"""
ADVERTISER-UX-001C2 — advertiser create wizard UI-smoke.

Multi-step guided onboarding: Main → Legal → Contact → Confirm.
Reuses existing A/B/C backend endpoints.

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
CONTACT_NAME = f"Контакт-{SUFFIX}"
CONTACT_EMAIL = f"contact-{SUFFIX}@test.ru"


def navigate_to_advertisers(page):
    link = page.locator('aside nav a[href="/advertisers"]')
    link.click(force=True)
    page.wait_for_url("**/advertisers", timeout=5000)
    page.wait_for_load_state("networkidle")


def test_uismoke__advertiser__create_org(smoke_page):
    """System admin creates advertiser through multi-step wizard.

    Flow:
    1. Login → Advertisers → Create
    2. Main: fill org name, verify auto-code note, Next
    3. Legal: fill INN/bank/account, Next
    4. Contact: fill name/email, Next
    5. Confirm: verify summary, Finish → card opens
    """
    page = smoke_page

    # Step 1: login + navigate
    login_as_break_glass_admin(page)
    navigate_to_advertisers(page)

    # Step 2: open wizard
    create_btn = page.locator('[data-testid="advertiser-create-open"]')
    create_btn.wait_for(state="visible", timeout=10000)
    create_btn.click()

    # Wizard is visible
    page.wait_for_selector('[data-testid="advertiser-wizard"]', state="visible", timeout=5000)
    page.wait_for_selector('[data-testid="advertiser-wizard-step-main"]', state="visible", timeout=3000)

    # Verify auto-code note
    code_note = page.locator('[data-testid="advertiser-wizard-code-note"]')
    assert "автоматически" in (code_note.text_content() or "").lower()

    # Fill main step
    page.fill('[data-testid="advertiser-wizard-name"]', ORG_LEGAL)
    page.fill('[data-testid="advertiser-wizard-display-name"]', ORG_DISPLAY)

    # Next → legal step
    page.locator('[data-testid="advertiser-wizard-next"]').click()
    page.wait_for_selector('[data-testid="advertiser-wizard-step-legal-active"]', timeout=5000)

    # Fill legal step
    page.fill('[data-testid="advertiser-wizard-legal-inn"]', "7700000000")
    page.fill('[data-testid="advertiser-wizard-legal-bank"]', "ПАО Сбербанк")
    page.fill('[data-testid="advertiser-wizard-legal-bik"]', "044525225")
    page.fill('[data-testid="advertiser-wizard-legal-settlement"]', "40702810000000000001")

    # Next → contact step (or error)
    page.locator('[data-testid="advertiser-wizard-next"]').click()

    # Debug: wait a bit and check what's visible
    page.wait_for_timeout(2000)
    # Check for error first
    err_el = page.locator('[data-testid="advertiser-wizard-error"]')
    if err_el.count() > 0 and err_el.is_visible():
        raise AssertionError(f"Legal step error: {err_el.text_content()}")

    # Wait for contact step
    page.wait_for_selector('[data-testid="advertiser-wizard-step-contact-contract"]', state="visible", timeout=5000)

    # Fill contact step
    page.fill('[data-testid="advertiser-wizard-contact-name"]', CONTACT_NAME)
    page.fill('[data-testid="advertiser-wizard-contact-email"]', CONTACT_EMAIL)

    # Next → confirm step
    page.locator('[data-testid="advertiser-wizard-next"]').click()
    page.wait_for_selector('[data-testid="advertiser-wizard-step-confirm"]', timeout=5000)

    # Verify summary
    summary_code = page.locator('[data-testid="advertiser-wizard-summary-code"]')
    code_text = summary_code.text_content() or ""
    assert code_text.startswith("ADV-"), f"Expected auto-generated code, got '{code_text}'"

    summary_inn = page.locator('[data-testid="advertiser-wizard-summary-inn"]')
    assert summary_inn.text_content() == "7700000000"

    summary_contact = page.locator('[data-testid="advertiser-wizard-summary-contact"]')
    assert CONTACT_NAME in (summary_contact.text_content() or "")

    # Finish → open card
    page.locator('[data-testid="advertiser-wizard-submit"]').click()

    # Wizard closes, detail panel opens
    page.wait_for_selector('[data-testid="advertiser-detail-panel"]', state="visible", timeout=10000)

    # Verify org display name visible
    page.wait_for_timeout(1000)
    assert ORG_DISPLAY in page.inner_text("body"), (
        f"Expected display name '{ORG_DISPLAY}' on page after wizard"
    )

    # Verify generated code is read-only in the table
    code_cells = page.locator('[data-testid="advertiser-code-readonly"]')
    found = False
    for i in range(code_cells.count()):
        if code_text in (code_cells.nth(i).text_content() or ""):
            found = True
            break
    assert found, f"Generated code '{code_text}' not found in table"

    # Close detail, reload page, re-open — persistence
    page.locator('[data-testid="advertiser-detail-panel"] button[title="Закрыть"]').click()
    page.wait_for_selector('[data-testid="advertiser-detail-panel"]', state="detached", timeout=5000)

    page.locator('aside nav a[href="/advertisers"]').click(force=True)
    page.wait_for_url("**/advertisers", timeout=5000)
    page.wait_for_load_state("networkidle")

    # Re-open the org
    rows = page.locator('[data-testid="advertiser-org-row"]')
    for i in range(rows.count()):
        if ORG_DISPLAY in (rows.nth(i).text_content() or ""):
            rows.nth(i).click()
            break

    page.wait_for_selector('[data-testid="advertiser-detail-panel"]', state="visible", timeout=5000)

    # Check legal tab for requisites
    page.locator('[data-testid="advertiser-tab-реквизиты"]').click()
    page.wait_for_timeout(1000)
    body = page.inner_text("body")
    assert "7700000000" in body, "INN should persist after reload"
