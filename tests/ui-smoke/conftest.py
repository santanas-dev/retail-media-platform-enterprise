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
    unique_suffix = _stub

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

    @pytest.fixture(scope="session", autouse=True)
    def _clear_smoke_users_for_smoke() -> None:
        """Delete accumulated smoke-test users before the suite (test isolation).

        Repeated smoke runs create `smoke_*` / `selogin-*` users that persist
        in a long-lived DB. The admin users list is fetched with `limit=50`
        ordered by `created_at DESC`, so as smoke users accumulate the old
        seed users — `break_glass_admin` (the ONLY internal user) and
        `advertiser_test` — get pushed off the page, intermittently breaking
        `user__split_internal_advertiser` and `user__assign_roles`. Deleting
        smoke users at session start keeps the count bounded so seed users
        stay reachable.

        Safety: the deletion logic lives in `smoke_cleanup.delete_smoke_users`,
        which (1) only matches the `smoke`/`selogin` username prefixes, (2) is
        fail-closed (raises unless UI_SMOKE_RUN is set), and (3) deletes FK
        children before `users` (all users FKs are ON DELETE NO ACTION). Only
        per-table row counts are logged — never credentials or PII.
        """
        import smoke_cleanup
        db_url = os.environ.get(
            "DATABASE_URL",
            "postgresql://retail_media_owner:retail_media_owner_pass@localhost:5432/retail_media_platform",
        )
        counts = smoke_cleanup.delete_smoke_users(db_url)
        total = sum(counts.values())
        print(f"[smoke-cleanup] removed {total} smoke-owned rows: {counts}")

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
        # SPA transition: wait for the campaigns LIST page to actually mount
        # (the create button is unique to it), not just the URL change or
        # `networkidle`. Fixes the login → /campaigns mount race.
        page.wait_for_url(f"{BASE_URL}/campaigns", timeout=15000)
        page.wait_for_selector(
            '[data-testid="campaign-create-open"]', state="visible", timeout=15000
        )

    def navigate_to_campaigns(page: Page) -> None:
        campaigns_link = page.locator('aside nav a[href="/campaigns"]')
        campaigns_link.click(force=True)
        page.wait_for_url(f"{BASE_URL}/campaigns", timeout=10000)
        # State-based: wait for the campaigns list page marker, not networkidle.
        page.wait_for_selector(
            '[data-testid="campaign-create-open"]', state="visible", timeout=10000
        )

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
        # Navigate AWAY from /campaigns/new (the create form) to /campaigns/<id>.
        # `**/campaigns/**` also matches /campaigns/new, so it does not prove
        # the detail page loaded — a failed create leaves the form open.
        page.wait_for_url(
            lambda url: "/campaigns/new" not in url and "/campaigns" in url,
            timeout=15000,
        )
        # The detail page h2 shows the campaign name («Smoke …»), while the
        # create form h2 is «Новая кампания». Waiting for the name proves the
        # detail page mounted AND the create succeeded (the h2 is tab-agnostic,
        # unlike campaign-status-badge which only renders on the overview tab).
        expect(page.locator("h2")).to_contain_text("Smoke", timeout=15000)

    def unique_suffix() -> str:
        """Truly-unique 8-hex suffix for smoke test data isolation.

        Replaces the `int(time.time()) % 100000` pattern, which wraps every
        ~27.8 hours and collides on re-runs against a long-lived DB, causing
        unique-constraint violations and strict-mode locator collisions.
        """
        import secrets
        return secrets.token_hex(4)
