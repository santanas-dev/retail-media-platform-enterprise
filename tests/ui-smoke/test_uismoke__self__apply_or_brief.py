"""
UI-smoke: self.apply_or_brief — advertiser submits a placement brief.

Uses seed advertiser (advertiser_test / advertiser-dev-only).
Self-contained: login → briefs → create → fill → submit → verify.

URL configuration:
  UI_SMOKE_ADVERTISER_URL — advertiser-web base URL (default http://localhost:3001)
"""
import os
import time

import pytest

if not os.environ.get("UI_SMOKE_RUN"):
    pytest.skip("UI_SMOKE_RUN not set", allow_module_level=True)

from playwright.sync_api import Page, expect

ADVERTISER_URL = os.environ.get(
    "UI_SMOKE_ADVERTISER_URL", "http://localhost:3001"
)
ADV_LOGIN_URL = f"{ADVERTISER_URL}/login"
ADV_USERNAME = os.environ.get("UI_SMOKE_ADV_USERNAME", "advertiser_test")
ADV_PASSWORD = os.environ.get("UI_SMOKE_ADV_PASSWORD", "advertiser-dev-only")


def test_uismoke__self__apply_or_brief(page: Page):
    """Advertiser logs in, creates a brief, submits it, sees it in list."""
    TS = str(int(time.time()))
    BRIEF_TITLE = f"Смок-бриф {TS}"

    # ═══════════════════════════════════════════════════════════
    # Phase 1: Login as advertiser
    # ═══════════════════════════════════════════════════════════
    page.goto(ADV_LOGIN_URL)
    page.wait_for_load_state("networkidle")

    # Select local_advertiser provider if present, or just fill fields
    provider_select = page.locator("#login-provider")
    if provider_select.count() > 0:
        provider_select.select_option("local_advertiser")

    page.fill("#login-username", ADV_USERNAME)
    page.fill("#login-password", ADV_PASSWORD)
    page.click('button[type="submit"]')
    # Login redirects to /campaigns (default) or /dashboard
    page.wait_for_url(f"{ADVERTISER_URL}/campaigns", timeout=15000)
    page.wait_for_load_state("networkidle")

    # ═══════════════════════════════════════════════════════════
    # Phase 2: Navigate to Briefs
    # ═══════════════════════════════════════════════════════════
    nav_briefs = page.get_by_test_id("nav-briefs")
    expect(nav_briefs).to_be_visible(timeout=5000)
    nav_briefs.click()
    page.wait_for_url(f"{ADVERTISER_URL}/briefs", timeout=10000)
    page.wait_for_load_state("networkidle")

    # ═══════════════════════════════════════════════════════════
    # Phase 3: Create new brief
    # ═══════════════════════════════════════════════════════════
    create_btn = page.get_by_test_id("brief-list-create-btn")
    expect(create_btn).to_be_visible(timeout=5000)
    create_btn.click()
    page.wait_for_url(f"{ADVERTISER_URL}/briefs/new", timeout=10000)
    page.wait_for_load_state("networkidle")

    # ═══════════════════════════════════════════════════════════
    # Phase 4: Fill form
    # ═══════════════════════════════════════════════════════════
    expect(page.get_by_test_id("brief-create-title")).to_be_visible(timeout=5000)
    page.get_by_test_id("brief-create-title").fill(BRIEF_TITLE)
    page.get_by_test_id("brief-create-objective").fill("Продвижение новой линейки продуктов")
    page.get_by_test_id("brief-create-category").fill("Молочная продукция")
    page.get_by_test_id("brief-create-budget").fill("500000")
    page.get_by_test_id("brief-create-channels").fill("КСО на кассах")
    page.get_by_test_id("brief-create-comment").fill(f"Авто-тест {TS}")

    # ═══════════════════════════════════════════════════════════
    # Phase 5: Submit brief
    # ═══════════════════════════════════════════════════════════
    expect(page.get_by_test_id("brief-create-submit")).to_be_visible(timeout=5000)
    page.get_by_test_id("brief-create-submit").click()

    # After submit, redirected to brief detail page
    page.wait_for_url(f"{ADVERTISER_URL}/briefs/**", timeout=15000)
    page.wait_for_load_state("networkidle")

    # ═══════════════════════════════════════════════════════════
    # Phase 6: Verify brief is visible with submitted status
    # ═══════════════════════════════════════════════════════════
    expect(page.locator("h1")).to_contain_text(BRIEF_TITLE, timeout=5000)

    # Should show submitted badge (status = "submitted")
    status_badge = page.locator('[class*="badge"]')
    expect(status_badge).to_contain_text("На рассмотрении", timeout=5000)
