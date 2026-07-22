"""
UI-smoke: advertiser.application_review — admin reviews a public application.
Self-contained: creates application via public form, then reviews as admin.
"""
import os
import time

import pytest

if not os.environ.get("UI_SMOKE_RUN"):
    pytest.skip("UI_SMOKE_RUN not set", allow_module_level=True)

from playwright.sync_api import Page, expect

BASE_URL = os.environ.get("UI_SMOKE_BASE_URL", "http://localhost:3000")
LOGIN_URL = f"{BASE_URL}/login"
PUBLIC_URL = f"{BASE_URL}/become-advertiser"
ADMIN_USER = os.environ.get("UI_SMOKE_BG_USERNAME", "break_glass_admin")
ADMIN_PASS = os.environ.get("UI_SMOKE_BG_PASSWORD", "break-glass-dev-only")


def test_uismoke__advertiser__application_review(page: Page):
    """Admin reviews a public advertiser application: new → reviewing."""
    TS = str(int(time.time()))

    # ── Phase 1: Create application via public form ──
    page.goto(PUBLIC_URL)
    page.wait_for_load_state("networkidle")
    expect(page.get_by_test_id("advertiser-apply-company-name")).to_be_visible()

    page.get_by_test_id("advertiser-apply-company-name").fill(f"ООО Смоук-{TS}")
    page.get_by_test_id("advertiser-apply-contact-name").fill("Смоук Контакт")
    page.get_by_test_id("advertiser-apply-email").fill(f"smoke-{TS}@example.com")
    page.get_by_test_id("advertiser-apply-phone").fill("+7-000-000-0000")
    page.get_by_test_id("advertiser-apply-consent").check()
    page.get_by_test_id("advertiser-apply-submit").click()

    expect(page.locator("text=Заявка отправлена")).to_be_visible(timeout=10000)

    # ── Phase 2: Login as admin ──
    page.goto(LOGIN_URL)
    page.wait_for_load_state("networkidle")
    page.select_option("#login-provider", "local_break_glass")
    page.fill("#login-username", ADMIN_USER)
    page.fill("#login-password", ADMIN_PASS)
    page.click('button[type="submit"]')
    page.wait_for_url("**/campaigns", timeout=15000)
    page.wait_for_load_state("networkidle")

    # ── Phase 3: Navigate to advertiser applications ──
    page.get_by_role("link", name="Заявки рекламодателей").click()
    page.wait_for_load_state("networkidle")

    # ── Phase 4: Find the application and click to open detail ──
    table = page.get_by_test_id("advertiser-applications-table")
    expect(table).to_be_visible(timeout=10000)

    # Use .first() — may have multiple apps from prior runs
    row = page.locator(f"tr:has-text('ООО Смоук-{TS}')").first
    expect(row).to_be_visible(timeout=5000)
    row.click()

    # ── Phase 5: Click "Начать рассмотрение" ──
    page.get_by_test_id("advertiser-review-start").click()

    # ── Phase 6: Verify success — status changed to "На рассмотрении"
    expect(page.locator("text=Заявка переведена в статус «На рассмотрении»")).to_be_visible(timeout=10000)

    # Verify the application now shows "На рассмотрении" badge
    expect(page.locator(f"tr:has-text('ООО Смоук-{TS}') >> text=На рассмотрении")).to_be_visible()
