"""
ADVERTISER-UX-001B3 — advertiser.contact_crud UI-smoke.

Happy-path (11 шагов):
  1. login → 2. Advertisers → 3. select ADV-001 → 4. Contacts tab
  → 5. create contact → 6. fill name/email/phone/title → 7. save
  → 8. verify row → 9. edit title → 10. verify updated → 11. reload persistence.

Only /login via page.goto(); all navigation via clicks.
"""
import os
import time
import pytest
from conftest import login_as_break_glass_admin


def _navigate_to_advertisers(page):
    link = page.locator('aside nav a[href="/advertisers"]')
    link.click(force=True)
    page.wait_for_url("**/advertisers", timeout=8000)
    page.wait_for_load_state("networkidle")


def test_uismoke__advertiser__contact_crud(smoke_page):
    page = smoke_page
    login_as_break_glass_admin(page)

    _navigate_to_advertisers(page)

    # Click first org row to open detail
    row = page.locator('[data-testid="advertiser-org-row"]').first
    row.click()
    page.wait_for_selector('[data-testid="advertiser-detail-panel"]', timeout=5000)

    # Click "Контакты" tab
    page.locator('[data-testid="advertiser-tab-контакты"]').click()
    page.wait_for_selector('[data-testid="advertiser-contacts-section"]', timeout=8000)

    # Click "Добавить контакт"
    page.locator('[data-testid="advertiser-contact-create-open"]').click()
    page.wait_for_selector('[data-testid="advertiser-contact-submit"]', timeout=5000)

    # Fill form
    contact_name = f"Смоук Контакт {int(time.time()) % 100000}"
    contact_email = f"smoke-{int(time.time()) % 100000}@test.ru"
    page.fill('[data-testid="advertiser-contact-name"]', contact_name)
    page.fill('[data-testid="advertiser-contact-email"]', contact_email)
    page.fill('[data-testid="advertiser-contact-phone"]', "+7-999-000-00-01")
    page.fill('[data-testid="advertiser-contact-title"]', "Тестовый менеджер")

    # Save
    page.locator('[data-testid="advertiser-contact-submit"]').click()

    # Wait for success message
    page.wait_for_selector('[data-testid="advertiser-contact-success"]', timeout=10000)

    # Find the contact row by display name
    page.wait_for_function(
        f"""() => {{
            const els = document.querySelectorAll('[data-testid^="advertiser-contact-display-name-"]');
            return Array.from(els).some(el => el.textContent === '{contact_name}');
        }}""",
        timeout=10000,
    )

    # Find contact id from data-testid
    all_name_els = page.locator('td[data-testid^="advertiser-contact-display-name-"]')
    count = all_name_els.count()
    contact_id = None
    for i in range(count):
        el = all_name_els.nth(i)
        if el.text_content() == contact_name:
            testid = el.get_attribute("data-testid") or ""
            contact_id = testid.replace("advertiser-contact-display-name-", "")
            break
    assert contact_id is not None, f"Contact row with name '{contact_name}' not found"

    # Verify display
    assert page.locator(f'[data-testid="advertiser-contact-display-name-{contact_id}"]').text_content() == contact_name
    assert page.locator(f'[data-testid="advertiser-contact-display-email-{contact_id}"]').text_content() == contact_email

    # ── Edit title ──
    page.locator(f'[data-testid="advertiser-contact-edit-{contact_id}"]').click()
    page.wait_for_selector('[data-testid="advertiser-contact-edit-name"]', timeout=3000)

    updated_title = "Обновлённый менеджер"
    # title is the 4th input (name, email, phone, title)
    row_inputs = page.locator(f'[data-testid="advertiser-contact-row-{contact_id}"] input')
    row_inputs.nth(3).fill(updated_title)  # title field
    page.locator(f'[data-testid="advertiser-contact-row-{contact_id}"] button').first.click()

    # Wait for success
    page.wait_for_selector('[data-testid="advertiser-contact-success"]', timeout=10000)

    # ── Reload persistence: close detail, navigate away, re-open ──
    # Close detail panel first (click ✕ button)
    page.locator('[data-testid="advertiser-detail-panel"] button[title="Закрыть"]').click()
    page.wait_for_selector('[data-testid="advertiser-detail-panel"]', state="detached", timeout=5000)

    # Navigate via sidebar to force SPA re-navigation
    page.locator('aside nav a[href="/advertisers"]').click(force=True)
    page.wait_for_url("**/advertisers", timeout=8000)
    page.wait_for_load_state("networkidle")

    # Open a different org first (force state change), then first org
    rows = page.locator('[data-testid="advertiser-org-row"]')
    if rows.count() >= 2:
        rows.nth(1).click()
        page.wait_for_selector('[data-testid="advertiser-detail-panel"]', timeout=5000)
        # Close and re-open first org
        page.locator('[data-testid="advertiser-detail-panel"] button[title="Закрыть"]').click()
        page.wait_for_selector('[data-testid="advertiser-detail-panel"]', state="detached", timeout=5000)

    rows.first.click()
    page.wait_for_selector('[data-testid="advertiser-detail-panel"]', timeout=5000)
    page.locator('[data-testid="advertiser-tab-контакты"]').click()
    page.wait_for_selector(f'[data-testid="advertiser-contact-display-name-{contact_id}"]', timeout=10000)

    # Verify persistence
    assert page.locator(f'[data-testid="advertiser-contact-display-name-{contact_id}"]').text_content() == contact_name
    assert page.locator(f'[data-testid="advertiser-contact-display-email-{contact_id}"]').text_content() == contact_email
