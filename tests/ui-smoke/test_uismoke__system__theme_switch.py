"""
THEME-SWITCH-001B — UI-smoke: theme toggle, persist, toggle back.
"""
import os

import pytest

if not os.environ.get("UI_SMOKE_RUN"):
    pytest.skip("UI_SMOKE_RUN not set", allow_module_level=True)

from conftest import wait_settled
from playwright.sync_api import Page, expect


def test_uismoke__system__theme_switch(smoke_page: Page) -> None:
    """Login → toggle dark → assert data-theme=dark → reload → assert persisted → toggle light."""
    from conftest import login_as_break_glass_admin, BASE_URL

    page = smoke_page

    # 1. Login as admin
    login_as_break_glass_admin(page)

    # 2. Find theme toggle radiogroup in sidebar
    toggle = page.locator('[data-testid="theme-toggle"]')
    expect(toggle).to_be_visible(timeout=5000)

    dark_btn = page.locator('[data-testid="theme-option-dark"]')
    light_btn = page.locator('[data-testid="theme-option-light"]')

    expect(dark_btn).to_be_visible()
    expect(light_btn).to_be_visible()

    # 3. Click dark option
    dark_btn.click()

    # 4. Assert html[data-theme="dark"]
    expect(page.locator("html")).to_have_attribute("data-theme", "dark")

    # 5. Reload and assert persistence
    page.reload()
    wait_settled(page)
    # After reload, login again (session cookie survived)
    # Wait for layout to render
    page.wait_for_selector("aside nav", state="visible", timeout=15000)
    expect(page.locator("html")).to_have_attribute("data-theme", "dark")

    # 6. Toggle back to light
    light_btn = page.locator('[data-testid="theme-option-light"]')
    expect(light_btn).to_be_visible(timeout=5000)
    light_btn.click()
    expect(page.locator("html")).to_have_attribute("data-theme", "light")

    # 7. Reload and assert light persisted
    page.reload()
    wait_settled(page)
    page.wait_for_selector("aside nav", state="visible", timeout=15000)
    expect(page.locator("html")).to_have_attribute("data-theme", "light")
