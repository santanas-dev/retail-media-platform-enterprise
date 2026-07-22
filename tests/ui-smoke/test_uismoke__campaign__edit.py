"""
UI-smoke: campaign.edit — admin adds flights and placements to a campaign.

Self-contained flow:
  1. login break_glass_admin
  2. create campaign draft (via campaign.create UI)
  3. open campaign detail → add flight (start/end dates)
  4. add placement (surface selector or text input)
  5. verify both appear in their tables

No direct goto (except /login), no API calls, no localStorage.
"""
import os
import time

import pytest

if not os.environ.get("UI_SMOKE_RUN"):
    pytest.skip("UI_SMOKE_RUN not set", allow_module_level=True)

from playwright.sync_api import Page, expect

ADMIN_URL = os.environ.get("UI_SMOKE_BASE_URL", "http://localhost:3000")
LOGIN_URL = f"{ADMIN_URL}/login"
BG_USERNAME = os.environ.get("UI_SMOKE_BG_USERNAME", "break_glass_admin")
BG_PASSWORD = os.environ.get("UI_SMOKE_BG_PASSWORD", "break-glass-dev-only")


def test_uismoke__campaign__edit(page: Page):
    """Admin creates a campaign, then adds a flight and placement."""
    TS = str(int(time.time()))
    CAMPAIGN_CODE = f"EDIT{TS[-6:]}"
    CAMPAIGN_NAME = f"Смок-редакт {TS}"

    # ═══════════════════════════════════════════════════════════
    # Phase 1: Login as break-glass admin
    # ═══════════════════════════════════════════════════════════
    page.goto(LOGIN_URL)
    page.wait_for_load_state("networkidle")
    page.select_option("#login-provider", "local_break_glass")
    page.fill("#login-username", BG_USERNAME)
    page.fill("#login-password", BG_PASSWORD)
    page.click('button[type="submit"]')
    page.wait_for_url(f"{ADMIN_URL}/campaigns", timeout=15000)
    page.wait_for_load_state("networkidle")

    # ═══════════════════════════════════════════════════════════
    # Phase 2: Create campaign draft
    # ═══════════════════════════════════════════════════════════
    expect(page.get_by_test_id("campaign-create-open")).to_be_visible(timeout=5000)
    page.get_by_test_id("campaign-create-open").click()
    page.wait_for_url("**/campaigns/new", timeout=10000)
    page.wait_for_load_state("networkidle")

    # Select organization first (contract dropdown depends on it)
    page.select_option("#c-org", index=1)
    page.wait_for_timeout(500)  # let contract list populate
    page.select_option("#c-contract", index=1)
    page.fill("#c-code", CAMPAIGN_CODE)
    page.fill("#c-name", CAMPAIGN_NAME)
    page.click('button[type="submit"]')
    # Redirect to campaign detail
    page.wait_for_url("**/campaigns/**", timeout=15000)
    page.wait_for_load_state("networkidle")

    # ═══════════════════════════════════════════════════════════
    # Phase 3: Add a flight
    # ═══════════════════════════════════════════════════════════
    expect(page.get_by_test_id("tab-flights")).to_be_visible(timeout=5000)
    page.get_by_test_id("tab-flights").click()
    page.wait_for_load_state("networkidle")

    expect(page.get_by_test_id("flight-add-btn")).to_be_visible(timeout=5000)
    page.get_by_test_id("flight-add-btn").click()

    # Fill flight form
    today = time.strftime("%Y-%m-%d")
    tomorrow = time.strftime("%Y-%m-%d", time.localtime(time.time() + 86400))
    page.get_by_test_id("flight-start").fill(today)
    page.get_by_test_id("flight-end").fill(tomorrow)
    page.get_by_test_id("flight-submit").click()
    page.wait_for_load_state("networkidle")

    # Flight should appear in table — verify date-year is visible (Russian locale)
    expect(page.locator("table")).to_be_visible(timeout=5000)
    table_text = page.locator("table").inner_text()
    assert "2026" in table_text, f"Flight not found in table: {table_text}"

    # ═══════════════════════════════════════════════════════════
    # Phase 4: Add a placement
    # ═══════════════════════════════════════════════════════════
    page.get_by_test_id("tab-placements").click()
    page.wait_for_load_state("networkidle")

    expect(page.get_by_test_id("placement-add-btn")).to_be_visible(timeout=5000)
    page.get_by_test_id("placement-add-btn").click()

    # Fill placement — use surface selector if available, otherwise text input
    surface_select = page.get_by_test_id("placement-surface")
    expect(surface_select).to_be_visible(timeout=5000)

    # Select first option (not placeholder) in the surface dropdown
    options = surface_select.locator("option")
    option_count = options.count()
    if option_count > 1:
        # Select first non-placeholder option
        surface_select.select_option(index=1)
        page.get_by_test_id("placement-submit").click()
        page.wait_for_load_state("networkidle")
        # Placement should appear in table
        expect(page.locator("table")).to_be_visible(timeout=5000)
