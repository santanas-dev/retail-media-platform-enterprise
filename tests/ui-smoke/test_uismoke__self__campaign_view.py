"""
UI-smoke: self.campaign_view — advertiser sees their campaign in advertiser-web.
Creates advertiser + campaign via admin-web, then verifies visibility in advertiser-web.

URL configuration:
  UI_SMOKE_BASE_URL       — admin-web base URL (default http://localhost:3000)
  UI_SMOKE_ADVERTISER_URL — advertiser-web base URL (default: admin URL port + 1)
"""
import os
import re
import time

import pytest

if not os.environ.get("UI_SMOKE_RUN"):
    pytest.skip("UI_SMOKE_RUN not set", allow_module_level=True)

from playwright.sync_api import Page, expect

ADMIN_URL = os.environ.get("UI_SMOKE_BASE_URL", "http://localhost:3000")
ADVERTISER_URL = os.environ.get(
    "UI_SMOKE_ADVERTISER_URL",
    re.sub(r":(\d+)$", lambda m: f":{int(m.group(1)) + 1}", ADMIN_URL),
)
ADV_LOGIN_URL = f"{ADVERTISER_URL}/login"
ADMIN_USER = os.environ.get("UI_SMOKE_BG_USERNAME", "break_glass_admin")
ADMIN_PASS = os.environ.get("UI_SMOKE_BG_PASSWORD", "break-glass-dev-only")


def test_uismoke__self__campaign_view(page: Page):
    """Advertiser logs in and sees their campaign with name, code, status."""
    TS = str(int(time.time()))
    ORG_NAME = f"ООО Кампании-{TS}"
    CAMPAIGN_CODE = f"SMOKE-{TS[-6:]}"
    CAMPAIGN_NAME = f"Дымовая кампания {TS[-4:]}"
    APP_EMAIL = f"scview-{TS}@example.com"
    APP_PASS = f"SmokeView-{TS}!"

    # ═══════════════════════════════════════════════════════════
    # Phase 1: Create advertiser via admin-web
    # ═══════════════════════════════════════════════════════════

    # 1a. Submit application via public form
    page.goto(f"{ADMIN_URL}/become-advertiser")
    page.wait_for_load_state("networkidle")
    expect(page.get_by_test_id("advertiser-apply-company-name")).to_be_visible(timeout=10000)

    page.get_by_test_id("advertiser-apply-company-name").fill(ORG_NAME)
    page.get_by_test_id("advertiser-apply-contact-name").fill("Контакт Кампании")
    page.get_by_test_id("advertiser-apply-email").fill(APP_EMAIL)
    page.get_by_test_id("advertiser-apply-phone").fill("+7-333-333-3333")
    page.get_by_test_id("advertiser-apply-consent").check()
    page.get_by_test_id("advertiser-apply-submit").click()
    expect(page.locator("text=Заявка отправлена")).to_be_visible(timeout=10000)

    # 1b. Admin login
    page.goto(f"{ADMIN_URL}/login")
    page.wait_for_load_state("networkidle")
    page.select_option("#login-provider", "local_break_glass")
    page.fill("#login-username", ADMIN_USER)
    page.fill("#login-password", ADMIN_PASS)
    page.click('button[type="submit"]')
    page.wait_for_url("**/campaigns", timeout=15000)
    page.wait_for_load_state("networkidle")

    # 1c. Review → approve → create invite
    page.get_by_role("link", name="Заявки рекламодателей").click()
    page.wait_for_load_state("networkidle")
    expect(page.get_by_test_id("advertiser-applications-table")).to_be_visible(timeout=10000)

    row = page.locator(f"tr:has-text('{ORG_NAME}')").first
    row.click()
    page.get_by_test_id("advertiser-review-start").click()
    expect(page.locator("text=Заявка переведена в статус «На рассмотрении»")).to_be_visible(timeout=10000)

    row = page.locator(f"tr:has-text('{ORG_NAME}')").first
    row.click()
    expect(page.get_by_test_id("advertiser-approve-btn")).to_be_visible(timeout=5000)
    page.get_by_test_id("advertiser-approve-btn").click()
    expect(page.locator("text=Заявка одобрена")).to_be_visible(timeout=10000)

    row = page.locator(f"tr:has-text('{ORG_NAME}')").first
    row.click()
    expect(page.get_by_test_id("advertiser-invite-create")).to_be_visible(timeout=10000)
    page.get_by_test_id("advertiser-invite-create").click()
    expect(page.locator("text=Приглашение создано")).to_be_visible(timeout=10000)
    token_el = page.get_by_test_id("advertiser-invite-token")
    expect(token_el).to_be_visible(timeout=5000)
    invite_token = token_el.text_content()
    assert invite_token and len(invite_token) >= 20

    # 1d. Accept invite in advertiser-web
    page.goto(f"{ADVERTISER_URL}/accept-invite/{invite_token}")
    page.wait_for_load_state("networkidle")
    expect(page.locator("text=Принять приглашение")).to_be_visible(timeout=10000)
    page.get_by_test_id("accept-invite-password").fill(APP_PASS)
    page.get_by_test_id("accept-invite-submit").click()
    expect(page.locator("text=Приглашение принято!")).to_be_visible(timeout=15000)
    page.get_by_test_id("accept-invite-go-to-login").click()
    page.wait_for_url("**/login", timeout=10000)
    page.wait_for_load_state("networkidle")

    # ═══════════════════════════════════════════════════════════
    # Phase 2: Create campaign in admin-web for this advertiser
    # ═══════════════════════════════════════════════════════════

    page.goto(f"{ADMIN_URL}/login")
    page.wait_for_load_state("networkidle")
    page.select_option("#login-provider", "local_break_glass")
    page.fill("#login-username", ADMIN_USER)
    page.fill("#login-password", ADMIN_PASS)
    page.click('button[type="submit"]')
    page.wait_for_url("**/campaigns", timeout=15000)
    page.wait_for_load_state("networkidle")

    # Click "Создать кампанию"
    expect(page.get_by_test_id("campaign-create-open")).to_be_visible(timeout=10000)
    page.get_by_test_id("campaign-create-open").click()
    page.wait_for_url("**/campaigns/new", timeout=10000)
    page.wait_for_load_state("networkidle")

    # Fill campaign form: code, name, contract
    page.fill("#c-code", CAMPAIGN_CODE)
    page.fill("#c-name", CAMPAIGN_NAME)
    # Select first contract (should be the seed contract)
    page.select_option("#c-contract", index=1)
    # Select the advertiser org we just created
    org_select = page.locator("#c-org")
    if org_select.count() > 0:
        org_select.select_option(label=ORG_NAME)

    page.click('button[type="submit"]')
    page.wait_for_url("**/campaigns/**", timeout=15000)
    page.wait_for_load_state("networkidle")

    # ═══════════════════════════════════════════════════════════
    # Phase 3: Login as advertiser in advertiser-web
    # ═══════════════════════════════════════════════════════════

    page.goto(ADV_LOGIN_URL)
    page.wait_for_load_state("networkidle")
    expect(page.locator("#login-username")).to_be_visible(timeout=10000)
    page.fill("#login-username", APP_EMAIL)
    page.fill("#login-password", APP_PASS)
    page.click('button[type="submit"]')

    # Should land on dashboard
    page.wait_for_load_state("networkidle")
    expect(page.locator("text=Мой кабинет")).to_be_visible(timeout=15000)

    # ═══════════════════════════════════════════════════════════
    # Phase 4: Navigate to campaigns and verify
    # ═══════════════════════════════════════════════════════════

    # Click "Кампании" in sidebar
    page.get_by_test_id("nav-campaigns").click()
    page.wait_for_load_state("networkidle")

    # Verify campaign list is visible
    expect(page.get_by_test_id("self-campaign-list")).to_be_visible(timeout=10000)

    # Verify our campaign row appears with correct name, code, and status
    campaign_row = page.get_by_test_id(f"self-campaign-row-{CAMPAIGN_CODE}")
    expect(campaign_row).to_be_visible(timeout=10000)

    name_el = page.get_by_test_id(f"self-campaign-name-{CAMPAIGN_CODE}")
    expect(name_el).to_be_visible()
    expect(name_el).to_have_text(CAMPAIGN_NAME)

    status_el = page.get_by_test_id(f"self-campaign-status-{CAMPAIGN_CODE}")
    expect(status_el).to_be_visible()
    # Status should be non-empty
    status_text = status_el.text_content()
    assert status_text and len(status_text) > 0, f"Status should not be empty: {status_text}"

    # ═══════════════════════════════════════════════════════════
    # Phase 5: Click into detail and verify
    # ═══════════════════════════════════════════════════════════

    campaign_row.click()
    page.wait_for_load_state("networkidle")

    expect(page.get_by_test_id("self-campaign-detail")).to_be_visible(timeout=10000)
    expect(page.get_by_test_id("self-campaign-detail-status")).to_be_visible()

    # Verify campaign period is displayed somewhere in the overview section
    expect(page.locator("text=Период")).to_be_visible(timeout=5000)

    # ═══════════════════════════════════════════════════════════
    # Phase 6: Reload — campaign still visible
    # ═══════════════════════════════════════════════════════════

    page.goto(f"{ADVERTISER_URL}/campaigns")
    page.wait_for_load_state("networkidle")

    expect(page.get_by_test_id("self-campaign-list")).to_be_visible(timeout=10000)
    expect(page.get_by_test_id(f"self-campaign-row-{CAMPAIGN_CODE}")).to_be_visible(timeout=10000)
