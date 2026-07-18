"""
UI-smoke conftest — Playwright harness for Retail Media Platform.

CI gate: this entire module is a no-op unless UI_SMOKE_RUN=1 is set.
No playwright imports at module level — they happen conditionally.
"""

import os

_RUN_SMOKE = bool(os.environ.get("UI_SMOKE_RUN", ""))

if not _RUN_SMOKE:
    # Silence collection — pytest will skip this directory
    def pytest_ignore_collect(collection_path, config):
        return True

    # Stub fixtures that won't be used (pytest still imports conftest)
    def _stub():
        pass

    smoke_page = _stub
    browser_context_args = _stub
    login_as_break_glass_admin = _stub
    navigate_to_campaigns = _stub
    try_find_create_campaign_button = _stub

else:
    import pytest
    from playwright.sync_api import Page, expect

    BASE_URL = os.environ.get("UI_SMOKE_BASE_URL", "http://localhost:3000")
    LOGIN_URL = f"{BASE_URL}/login"
    BG_USERNAME = os.environ.get("UI_SMOKE_BG_USERNAME", "break_glass_admin")
    BG_PASSWORD = os.environ.get(
        "UI_SMOKE_BG_PASSWORD", "break-glass-dev-only"
    )

    @pytest.fixture(scope="session")
    def browser_context_args(browser_context_args: dict) -> dict:
        return {
            **browser_context_args,
            "viewport": {"width": 1440, "height": 900},
            "locale": "ru-RU",
        }

    @pytest.fixture
    def smoke_page(page: Page) -> Page:
        page.goto(LOGIN_URL)
        page.wait_for_load_state("networkidle")
        return page

    def login_as_break_glass_admin(page: Page) -> None:
        page.select_option("#login-provider", "local_break_glass")
        page.fill("#login-username", BG_USERNAME)
        page.fill("#login-password", BG_PASSWORD)
        page.click('button[type="submit"]')
        page.wait_for_url(f"{BASE_URL}/campaigns", timeout=15000)
        page.wait_for_selector("aside nav", state="visible", timeout=10000)
        page.wait_for_load_state("networkidle")

    def navigate_to_campaigns(page: Page) -> None:
        campaigns_link = page.locator('aside nav a[href="/campaigns"]')
        campaigns_link.click(force=True)
        page.wait_for_load_state("networkidle")

    def try_find_create_campaign_button(page: Page) -> None:
        selectors = [
            'text="Создать кампанию"',
            'text="Новая кампания"',
            'a[href="/campaigns/new"]',
            'button:has-text("Создать")',
            '[data-testid="create-campaign-btn"]',
        ]
        for sel in selectors:
            if page.locator(sel).count() > 0:
                return
        raise AssertionError(
            "G1 CONFIRMED: No 'Create Campaign' button found on campaign list page. "
            "CampaignListPage renders text 'Создайте первую кампанию' but provides "
            "no clickable element to navigate to /campaigns/new. "
            "Tested selectors: "
            + ", ".join(selectors)
        )
