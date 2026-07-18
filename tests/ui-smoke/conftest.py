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
    def _stub(*args, **kwargs):
        pass

    smoke_page = _stub
    browser_context_args = _stub
    login_as_break_glass_admin = _stub
    navigate_to_campaigns = _stub
    click_create_campaign_button = _stub
    choose_first_contract = _stub
    fill_campaign_code_and_name = _stub
    submit_campaign_form = _stub
    verify_campaign_created = _stub

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

    def click_create_campaign_button(page: Page) -> None:
        btn = page.locator('[data-testid="campaign-create-open"]')
        expect(btn).to_be_visible(timeout=5000)
        btn.click()
        page.wait_for_url("**/campaigns/new", timeout=10000)
        page.wait_for_load_state("networkidle")

    def choose_first_contract(page: Page) -> None:
        page.select_option("#c-contract", index=1)

    def fill_campaign_code_and_name(
        page: Page, code: str, name: str
    ) -> None:
        page.fill("#c-code", code)
        page.fill("#c-name", name)

    def submit_campaign_form(page: Page) -> None:
        page.click('button[type="submit"]')

    def verify_campaign_created(page: Page) -> None:
        page.wait_for_url("**/campaigns/**", timeout=15000)
        page.wait_for_load_state("networkidle")
        # Should be on campaign detail page — look for campaign name
        expect(page.locator("h2")).to_contain_text("Smoke", timeout=5000)
