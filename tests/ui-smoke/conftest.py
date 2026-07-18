"""
UI-smoke conftest — Playwright harness for Retail Media Platform.

Rules:
- page.goto() is allowed ONLY for /login (entry route).
- Every subsequent navigation MUST be via real UI clicks.
- No direct URL navigation to internal routes (e.g. /campaigns/new).
- No direct API calls, no React function calls, no localStorage manipulation.
- Stable selectors preferred: #id over class, text content over CSS paths.

Credentials (break-glass admin, seed data):
- provider: local_break_glass
- username: break_glass_admin
- password: break-glass-dev-only
"""

import os
import pytest
from playwright.sync_api import Page, expect

# ── CI gate: only collect ui-smoke tests when explicitly opted in ───────
if not os.environ.get("UI_SMOKE_RUN", ""):
    collect_ignore = ["test_uismoke__campaign_create.py"]


# ── Config (override via env vars) ──────────────────────────────────────

BASE_URL = os.environ.get("UI_SMOKE_BASE_URL", "http://localhost:3000")
LOGIN_URL = f"{BASE_URL}/login"
BG_USERNAME = os.environ.get("UI_SMOKE_BG_USERNAME", "break_glass_admin")
BG_PASSWORD = os.environ.get("UI_SMOKE_BG_PASSWORD", "break-glass-dev-only")


# ── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict) -> dict:
    """Default viewport + locale for admin-web."""
    return {
        **browser_context_args,
        "viewport": {"width": 1440, "height": 900},
        "locale": "ru-RU",
    }


@pytest.fixture
def smoke_page(page: Page) -> Page:
    """Navigate to login page (the ONLY allowed goto).

    Returns a Playwright Page ready for the smoke scenario.
    """
    page.goto(LOGIN_URL)
    page.wait_for_load_state("networkidle")
    return page


# ── Helpers ─────────────────────────────────────────────────────────────


def login_as_break_glass_admin(page: Page) -> None:
    """Log in as break-glass admin via the login form.

    Uses stable #id selectors. Assumes page is already at /login.
    After login, waits for sidebar + campaign list to fully render.
    """
    # Select provider: Break-glass Admin
    page.select_option("#login-provider", "local_break_glass")

    # Fill credentials
    page.fill("#login-username", BG_USERNAME)
    page.fill("#login-password", BG_PASSWORD)

    # Submit
    page.click('button[type="submit"]')

    # Wait for post-login redirect (navigates to /campaigns)
    page.wait_for_url(f"{BASE_URL}/campaigns", timeout=15000)
    # Wait for the sidebar nav to be fully visible (indicates React hydration done)
    page.wait_for_selector("aside nav", state="visible", timeout=10000)
    page.wait_for_load_state("networkidle")


def navigate_to_campaigns(page: Page) -> None:
    """Click 'Кампании' in the sidebar.

    Assumes already logged in and on any authenticated page.
    Uses force-click to avoid 'element not stable' during React re-render.
    """
    campaigns_link = page.locator('aside nav a[href="/campaigns"]')
    # Already on /campaigns after login — this is a no-op click (stays on page)
    # but ensures the campaigns list is loaded fresh
    campaigns_link.click(force=True)
    page.wait_for_load_state("networkidle")


def try_find_create_campaign_button(page: Page) -> None:
    """Attempt to find a 'Create Campaign' button on the campaign list page.

    This is expected to FAIL (button doesn't exist — G1 gap).
    The caller must handle the failure.
    """
    # Try multiple selectors: button text, link text, aria labels
    selectors = [
        'text="Создать кампанию"',
        'text="Новая кампания"',
        'a[href="/campaigns/new"]',
        'button:has-text("Создать")',
        '[data-testid="create-campaign-btn"]',
    ]
    for sel in selectors:
        if page.locator(sel).count() > 0:
            return  # Found it — this would mean G1 is fixed

    raise AssertionError(
        "G1 CONFIRMED: No 'Create Campaign' button found on campaign list page. "
        "CampaignListPage renders text 'Создайте первую кампанию' but provides "
        "no clickable element to navigate to /campaigns/new. "
        "Tested selectors: " + ", ".join(selectors)
    )
