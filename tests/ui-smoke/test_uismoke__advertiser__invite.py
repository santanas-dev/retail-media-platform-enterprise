"""
UI-smoke: advertiser.invite — admin creates invite for approved application.
Self-contained: creates application via public form, reviews + approves, creates invite.
Does NOT accept the invite — that is the self.login flow.
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


def test_uismoke__advertiser__invite(page: Page):
    """Admin creates an invite for an approved advertiser application."""
    TS = str(int(time.time()))

    # ── Phase 1: Create application via public form ──
    page.goto(PUBLIC_URL)
    page.wait_for_load_state("networkidle")
    expect(page.get_by_test_id("advertiser-apply-company-name")).to_be_visible()

    page.get_by_test_id("advertiser-apply-company-name").fill(f"ООО Инвайт-{TS}")
    page.get_by_test_id("advertiser-apply-contact-name").fill("Инвайт Контакт")
    page.get_by_test_id("advertiser-apply-email").fill(f"invite-{TS}@example.com")
    page.get_by_test_id("advertiser-apply-phone").fill("+7-111-111-1111")
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

    table = page.get_by_test_id("advertiser-applications-table")
    expect(table).to_be_visible(timeout=10000)

    # ── Phase 4: Find the application and open detail ──
    row = page.locator(f"tr:has-text('ООО Инвайт-{TS}')").first
    expect(row).to_be_visible(timeout=5000)
    row.click()

    # ── Phase 5: Review → reviewing → approve ──
    page.get_by_test_id("advertiser-review-start").click()
    expect(page.locator("text=Заявка переведена в статус «На рассмотрении»")).to_be_visible(timeout=10000)

    # Re-select the row (UI re-renders detail after review action)
    row = page.locator(f"tr:has-text('ООО Инвайт-{TS}')").first
    row.click()

    # Click approve
    expect(page.get_by_test_id("advertiser-approve-btn")).to_be_visible(timeout=5000)
    page.get_by_test_id("advertiser-approve-btn").click()
    expect(page.locator("text=Заявка одобрена")).to_be_visible(timeout=10000)

    # ── Phase 6: Open approved application detail and create invite ──
    row = page.locator(f"tr:has-text('ООО Инвайт-{TS}')").first
    row.click()

    # "Создать приглашение" button should be visible for approved app without existing invite
    expect(page.get_by_test_id("advertiser-invite-create")).to_be_visible(timeout=10000)
    page.get_by_test_id("advertiser-invite-create").click()

    # ── Phase 7: Verify invite created — token visible, status pending ──
    expect(page.locator("text=Приглашение создано")).to_be_visible(timeout=10000)

    invite_status = page.get_by_test_id("advertiser-invite-status")
    expect(invite_status).to_be_visible(timeout=5000)
    expect(invite_status).to_contain_text("Ожидает принятия")

    token_el = page.get_by_test_id("advertiser-invite-token")
    expect(token_el).to_be_visible(timeout=5000)
    token_text = token_el.text_content()
    assert token_text, "Invite token should not be empty"
    assert len(token_text) >= 20, f"Token too short, got {len(token_text)} chars"
