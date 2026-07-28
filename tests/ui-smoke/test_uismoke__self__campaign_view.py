"""
UI-smoke: self.campaign_view — advertiser sees their campaign in advertiser-web.
Uses seed advertiser (advertiser_test / advertiser-dev-only) and seed campaign (CAMP-2026-001).

URL configuration:
  UI_SMOKE_ADVERTISER_URL — advertiser-web base URL (default http://localhost:3001)
"""
import os
import re

import pytest

if not os.environ.get("UI_SMOKE_RUN"):
    pytest.skip("UI_SMOKE_RUN not set", allow_module_level=True)

from playwright.sync_api import Page, expect

ADMIN_URL = os.environ.get("UI_SMOKE_BASE_URL", "http://localhost:3000")
ADVERTISER_URL = os.environ.get(
    "UI_SMOKE_ADVERTISER_URL",
    re.sub(r":(\d+)$", lambda m: f":{int(m.group(1)) + 1}", ADMIN_URL),
)

ADV_USERNAME = os.environ.get("UI_SMOKE_ADV_USERNAME", "advertiser_test")
ADV_PASSWORD = os.environ.get("UI_SMOKE_ADV_PASSWORD", "advertiser-dev-only")
SEED_CAMPAIGN_CODE = "CAMP-2026-001"
SEED_CAMPAIGN_NAME = "Тестовая кампания №1"


def test_uismoke__self__campaign_view(page: Page):
    """Advertiser logs in and sees their campaign with name, code, status."""

    # ═══════════════════════════════════════════════════════════
    # Phase 1: Login as seed advertiser in advertiser-web
    # ═══════════════════════════════════════════════════════════

    page.goto(f"{ADVERTISER_URL}/login")
    page.wait_for_load_state("networkidle")
    expect(page.locator("#login-username")).to_be_visible(timeout=10000)

    page.fill("#login-username", ADV_USERNAME)
    page.fill("#login-password", ADV_PASSWORD)
    page.click('button[type="submit"]')

    # Login redirects to /campaigns (advertiser default landing)
    page.wait_for_load_state("networkidle")

    # ═══════════════════════════════════════════════════════════
    # Phase 2: Verify campaign list is visible with seed campaign
    # ═══════════════════════════════════════════════════════════

    expect(page.get_by_test_id("self-campaign-list")).to_be_visible(timeout=10000)

    # Verify seed campaign row with all data-testid elements
    campaign_row = page.get_by_test_id(f"self-campaign-row-{SEED_CAMPAIGN_CODE}")
    expect(campaign_row).to_be_visible(timeout=10000)

    name_el = page.get_by_test_id(f"self-campaign-name-{SEED_CAMPAIGN_CODE}")
    expect(name_el).to_be_visible()
    expect(name_el).to_have_text(SEED_CAMPAIGN_NAME)

    status_el = page.get_by_test_id(f"self-campaign-status-{SEED_CAMPAIGN_CODE}")
    expect(status_el).to_be_visible()
    status_text = status_el.text_content()
    assert status_text and len(status_text) > 0, f"Status should not be empty: {status_text}"

    # ═══════════════════════════════════════════════════════════
    # Phase 3: Click into detail and verify
    # ═══════════════════════════════════════════════════════════

    campaign_row.click()
    page.wait_for_load_state("networkidle")

    expect(page.get_by_test_id("self-campaign-detail")).to_be_visible(timeout=10000)
    expect(page.get_by_test_id("self-campaign-detail-status")).to_be_visible()
    expect(page.get_by_text("Период", exact=True)).to_be_visible(timeout=5000)

    # ═══════════════════════════════════════════════════════════
    # Phase 4: Reload — campaign still visible
    # ═══════════════════════════════════════════════════════════

    page.goto(f"{ADVERTISER_URL}/campaigns")
    page.wait_for_load_state("networkidle")

    expect(page.get_by_test_id("self-campaign-list")).to_be_visible(timeout=10000)
    expect(page.get_by_test_id(f"self-campaign-row-{SEED_CAMPAIGN_CODE}")).to_be_visible(timeout=10000)
