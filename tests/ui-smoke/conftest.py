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
    select_first_org = _stub
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

    @pytest.fixture(scope="session", autouse=True)
    def _clear_inventory_for_smoke() -> None:
        """Clear all reserved inventory bookings before smoke tests.

        Each smoke test creates campaigns with placements that reserve
        inventory slots.  Over time, all slots fill up and subsequent
        submit calls fail with CAPACITY_OVERBOOKED.  Clearing at session
        start via direct DB ensures a clean slate.
        """
        import subprocess
        db_url = os.environ.get(
            "DATABASE_URL",
            "postgresql://retail_media_owner:retail_media_owner_pass@localhost:5432/retail_media_platform",
        )
        # Extract connection params from asyncpg URL
        # postgresql+asyncpg://user:pass@host:port/db → psql-compatible
        clean_url = db_url.replace("+asyncpg", "").replace("***", "retail_media_owner_pass")
        subprocess.run(
            [
                "psql", clean_url, "-c",
                "UPDATE inventory_bookings SET status='released', released_at=NOW(), release_reason='smoke test reset' WHERE status='reserved'; UPDATE inventory_slots SET reserved_capacity = 0, booked_capacity = 0;",
            ],
            capture_output=True,
        )

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

    def select_first_org(page: Page) -> None:
        """Select the first advertiser organization — makes contract select visible."""
        page.select_option("[data-testid='campaign-create-org']", index=1)
        page.wait_for_selector(
            "[data-testid='campaign-create-contract']",
            state="visible", timeout=10000
        )

    def choose_first_contract(page: Page) -> None:
        page.select_option("[data-testid='campaign-create-contract']", index=1)

    def fill_campaign_code_and_name(
        page: Page, code: str, name: str
    ) -> None:
        page.fill("[data-testid='campaign-create-code']", code)
        page.fill("[data-testid='campaign-create-name']", name)

    def submit_campaign_form(page: Page) -> None:
        page.click("[data-testid='campaign-create-submit']")

    def verify_campaign_created(page: Page) -> None:
        page.wait_for_url("**/campaigns/**", timeout=15000)
        page.wait_for_load_state("networkidle")
        # Should be on campaign detail page — look for campaign name
        expect(page.locator("h2")).to_contain_text("Smoke", timeout=5000)
