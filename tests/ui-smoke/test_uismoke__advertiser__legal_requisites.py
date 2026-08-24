"""
ADVERTISER-UX-001A2 — advertiser.legal_requisites UI-smoke.

Happy-path: login → Рекламодатели → select ADV-001 → Реквизиты → fill LE form → save → verify display → reload persist.

Only /login via page.goto(); all navigation via clicks.
"""

import pytest
from playwright.sync_api import expect
from conftest import login_as_break_glass_admin, wait_settled


def _navigate_to_advertisers(page):
    link = page.locator('aside nav a[href="/advertisers"]')
    link.click(force=True)
    page.wait_for_url("**/advertisers", timeout=8000)
    wait_settled(page)


def test_uismoke__advertiser__legal_requisites(smoke_page):
    page = smoke_page
    login_as_break_glass_admin(page)

    # Navigate to Advertisers
    _navigate_to_advertisers(page)

    # Click first org row to open detail
    row = page.locator('[data-testid="advertiser-org-row"]').first
    row.click()
    page.wait_for_selector('[data-testid="advertiser-detail-panel"]', timeout=5000)

    # Click "Реквизиты" tab
    page.locator('text=Реквизиты').click()
    page.wait_for_selector('[data-testid="advertiser-legal-section"]', timeout=5000)

    # Click "Заполнить" or "Редактировать"
    edit_btn = page.locator('[data-testid="advertiser-legal-edit"]')
    edit_btn.click()
    page.wait_for_selector('[data-testid="advertiser-legal-submit"]', timeout=5000)

    # Fill legal_entity requisites
    # Already default: legal_entity_type = legal_entity, legal_form = ooo

    page.fill('[data-testid="advertiser-legal-name"]', "ООО Тестовый Рекламодатель")
    page.fill('[data-testid="advertiser-legal-inn"]', "7707083893")
    page.fill('[data-testid="advertiser-legal-kpp"]', "770701001")
    page.fill('[data-testid="advertiser-legal-ogrn"]', "1027700132195")
    page.fill('[data-testid="advertiser-legal-address"]', "г. Москва, ул. Тестовая, д. 1")
    page.fill('[data-testid="advertiser-legal-settlement-account"]', "40702810500000000001")
    page.fill('[data-testid="advertiser-legal-correspondent-account"]', "30101810200000000593")
    page.fill('[data-testid="advertiser-legal-bik"]', "044525593")
    page.fill('[data-testid="advertiser-legal-bank-name"]', "ПАО Сбербанк")

    # Save
    page.locator('[data-testid="advertiser-legal-submit"]').click()

    # Wait for edit form to close (confirms save succeeded, display mode active)
    expect(page.locator('[data-testid="advertiser-legal-submit"]')).not_to_be_visible(timeout=10000)

    # Wait for display with refetched data (ADV-001 seed has no pre-existing requisites,
    # so org.inn is null until refetch completes — needs generous timeout on slow CI)
    expect(page.locator('[data-testid="advertiser-legal-display-inn"]')).to_be_visible(timeout=15000)

    # Verify displayed fields
    assert page.locator('[data-testid="advertiser-legal-display-legal-name"]').text_content() == "ООО Тестовый Рекламодатель"
    assert page.locator('[data-testid="advertiser-legal-display-inn"]').text_content() == "7707083893"
    assert page.locator('[data-testid="advertiser-legal-display-kpp"]').text_content() == "770701001"
    assert page.locator('[data-testid="advertiser-legal-display-ogrn"]').text_content() == "1027700132195"
    assert page.locator('[data-testid="advertiser-legal-display-legal-address"]').text_content() == "г. Москва, ул. Тестовая, д. 1"
    assert page.locator('[data-testid="advertiser-legal-display-settlement-account"]').text_content() == "40702810500000000001"
    assert page.locator('[data-testid="advertiser-legal-display-correspondent-account"]').text_content() == "30101810200000000593"
    assert page.locator('[data-testid="advertiser-legal-display-bik"]').text_content() == "044525593"
    assert page.locator('[data-testid="advertiser-legal-display-bank-name"]').text_content() == "ПАО Сбербанк"

    # Reload and verify persistence
    page.locator('aside nav a[href="/advertisers"]').click(force=True)
    page.wait_for_url("**/advertisers", timeout=8000)
    wait_settled(page)

    # Re-open detail
    row = page.locator('[data-testid="advertiser-org-row"]').first
    row.click()
    page.wait_for_selector('[data-testid="advertiser-detail-panel"]', timeout=5000)
    page.locator('text=Реквизиты').click()
    page.wait_for_selector('[data-testid="advertiser-legal-section"]', timeout=5000)
    expect(page.locator('[data-testid="advertiser-legal-display-inn"]')).to_be_visible(timeout=10000)

    # Verify persistence
    assert page.locator('[data-testid="advertiser-legal-display-inn"]').text_content() == "7707083893"
    assert page.locator('[data-testid="advertiser-legal-display-legal-name"]').text_content() == "ООО Тестовый Рекламодатель"
    assert page.locator('[data-testid="advertiser-legal-display-legal-address"]').text_content() == "г. Москва, ул. Тестовая, д. 1"
    assert page.locator('[data-testid="advertiser-legal-display-bank-name"]').text_content() == "ПАО Сбербанк"
