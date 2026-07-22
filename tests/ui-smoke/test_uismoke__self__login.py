"""
UI-smoke: self.login — advertiser accepts invite, logs into advertiser-web.
Self-contained full flow across admin-web and advertiser-web.

URL configuration:
  UI_SMOKE_BASE_URL       — admin-web base URL (default http://localhost:3000)
  UI_SMOKE_ADVERTISER_URL — advertiser-web base URL (default: admin URL port + 1)

Phases:
  1. admin-web  — public submit application
  2. admin-web  — admin login, review → approve, create invite
  3. advertiser-web — accept invite, login, verify dashboard
"""
import os
import re
import time

import pytest

if not os.environ.get("UI_SMOKE_RUN"):
    pytest.skip("UI_SMOKE_RUN not set", allow_module_level=True)

from playwright.sync_api import Page, expect

ADMIN_URL = os.environ.get("UI_SMOKE_BASE_URL", "http://localhost:3000")
# Explicit override or derive from admin URL (port + 1 for local/dev)
ADVERTISER_URL = os.environ.get(
    "UI_SMOKE_ADVERTISER_URL",
    re.sub(r":(\d+)$", lambda m: f":{int(m.group(1)) + 1}", ADMIN_URL),
)
LOGIN_URL = f"{ADMIN_URL}/login"
PUBLIC_URL = f"{ADMIN_URL}/become-advertiser"
ADV_LOGIN_URL = f"{ADVERTISER_URL}/login"
ADMIN_USER = os.environ.get("UI_SMOKE_BG_USERNAME", "break_glass_admin")
ADMIN_PASS = os.environ.get("UI_SMOKE_BG_PASSWORD", "break-glass-dev-only")


def test_uismoke__self__login(page: Page):
    """Advertiser accepts invite, logs in, sees dashboard with org."""
    TS = str(int(time.time()))
    APP_EMAIL = f"selogin-{TS}@example.com"
    APP_PASS = f"SmokeLogin-{TS}!"

    # ═══════════════════════════════════════════════════════════
    # Phase 1: Create application via public form (admin-web :3000)
    # ═══════════════════════════════════════════════════════════
    page.goto(PUBLIC_URL)
    page.wait_for_load_state("networkidle")
    expect(page.get_by_test_id("advertiser-apply-company-name")).to_be_visible()

    page.get_by_test_id("advertiser-apply-company-name").fill(f"ООО Логин-{TS}")
    page.get_by_test_id("advertiser-apply-contact-name").fill("Логин Контакт")
    page.get_by_test_id("advertiser-apply-email").fill(APP_EMAIL)
    page.get_by_test_id("advertiser-apply-phone").fill("+7-222-222-2222")
    page.get_by_test_id("advertiser-apply-consent").check()
    page.get_by_test_id("advertiser-apply-submit").click()

    expect(page.locator("text=Заявка отправлена")).to_be_visible(timeout=10000)

    # ═══════════════════════════════════════════════════════════
    # Phase 2: Admin login → review → approve → create invite (admin-web :3000)
    # ═══════════════════════════════════════════════════════════
    page.goto(LOGIN_URL)
    page.wait_for_load_state("networkidle")
    page.select_option("#login-provider", "local_break_glass")
    page.fill("#login-username", ADMIN_USER)
    page.fill("#login-password", ADMIN_PASS)
    page.click('button[type="submit"]')
    page.wait_for_url("**/campaigns", timeout=15000)
    page.wait_for_load_state("networkidle")

    # Navigate to applications
    page.get_by_role("link", name="Заявки рекламодателей").click()
    page.wait_for_load_state("networkidle")
    expect(page.get_by_test_id("advertiser-applications-table")).to_be_visible(timeout=10000)

    # Find and click our application
    row = page.locator(f"tr:has-text('ООО Логин-{TS}')").first
    expect(row).to_be_visible(timeout=5000)
    row.click()

    # Start review
    page.get_by_test_id("advertiser-review-start").click()
    expect(page.locator("text=Заявка переведена в статус «На рассмотрении»")).to_be_visible(timeout=10000)

    # Re-select and approve
    row = page.locator(f"tr:has-text('ООО Логин-{TS}')").first
    row.click()
    expect(page.get_by_test_id("advertiser-approve-btn")).to_be_visible(timeout=5000)
    page.get_by_test_id("advertiser-approve-btn").click()
    expect(page.locator("text=Заявка одобрена")).to_be_visible(timeout=10000)

    # Re-select approved app and create invite
    row = page.locator(f"tr:has-text('ООО Логин-{TS}')").first
    row.click()
    expect(page.get_by_test_id("advertiser-invite-create")).to_be_visible(timeout=10000)
    page.get_by_test_id("advertiser-invite-create").click()

    # Extract invite token
    expect(page.locator("text=Приглашение создано")).to_be_visible(timeout=10000)
    token_el = page.get_by_test_id("advertiser-invite-token")
    expect(token_el).to_be_visible(timeout=5000)
    invite_token = token_el.text_content()
    assert invite_token, "Invite token should not be empty"
    assert len(invite_token) >= 20, f"Token too short: {len(invite_token)}"

    # ═══════════════════════════════════════════════════════════
    # Phase 3: Accept invite in advertiser-web (:3001)
    # ═══════════════════════════════════════════════════════════
    accept_url = f"{ADVERTISER_URL}/accept-invite/{invite_token}"
    page.goto(accept_url)
    page.wait_for_load_state("networkidle")

    expect(page.locator("text=Принять приглашение")).to_be_visible(timeout=10000)
    page.get_by_test_id("accept-invite-password").fill(APP_PASS)
    page.get_by_test_id("accept-invite-submit").click()

    # Wait for success
    expect(page.locator("text=Приглашение принято!")).to_be_visible(timeout=15000)

    # Click "Перейти к входу"
    page.get_by_test_id("accept-invite-go-to-login").click()
    page.wait_for_url("**/login", timeout=10000)
    page.wait_for_load_state("networkidle")

    # ═══════════════════════════════════════════════════════════
    # Phase 4: Login as advertiser in advertiser-web (:3001)
    # ═══════════════════════════════════════════════════════════
    expect(page.locator("#login-username")).to_be_visible(timeout=10000)
    page.fill("#login-username", APP_EMAIL)
    page.fill("#login-password", APP_PASS)
    page.click('button[type="submit"]')

    # Should land on campaigns or some protected page
    page.wait_for_load_state("networkidle")

    # ═══════════════════════════════════════════════════════════
    # Phase 5: Verify dashboard — org name, "Рекламодатель"
    # ═══════════════════════════════════════════════════════════
    # Check that we see the advertiser dashboard with org name
    expect(page.locator(f"text=ООО Логин-{TS}")).to_be_visible(timeout=15000)
    expect(page.locator("text=Мой кабинет")).to_be_visible(timeout=10000)
    expect(page.locator("text=Рекламодатель")).to_be_visible(timeout=10000)
