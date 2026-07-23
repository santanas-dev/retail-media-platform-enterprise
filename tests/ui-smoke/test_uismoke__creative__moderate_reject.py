"""
UI-smoke: creative.moderate_reject — proves admin can reject a pending creative with reason.

Journey: creative.moderate_reject (Wave 3 — managed-first)
Role: system_admin (break_glass_admin seed)
Path: /login → campaign → creatives (library add) → /creatives/moderation → reject with reason → verify status + reason
"""
import os
import pathlib
import pytest

if not os.environ.get("UI_SMOKE_RUN"):
    pytest.skip("UI_SMOKE_RUN not set", allow_module_level=True)

from playwright.sync_api import Page, expect
from conftest import (
    BASE_URL,
    LOGIN_URL,
    login_as_break_glass_admin,
    click_create_campaign_button,
    choose_first_contract,
)


def _create_draft_campaign(page: Page) -> str:
    """Create a draft campaign via UI and return its ID from the URL."""
    login_as_break_glass_admin(page)
    click_create_campaign_button(page)

    page.select_option("#c-org", index=1)
    choose_first_contract(page)

    page.fill("#c-code", f"SMOKE-MOD-REJ-{os.urandom(2).hex()}")
    page.fill("#c-name", "Smoke Mod Rej Test")
    page.fill("#c-budget", "100000")

    page.click('button:has-text("Создать черновик")')
    page.wait_for_url(lambda url: url != BASE_URL + "/campaigns/new", timeout=15000)
    page.wait_for_load_state("networkidle")

    url = page.url
    return url.rstrip("/").split("/")[-1]


def _add_creative_to_library(page: Page, code: str) -> None:
    """Add a metadata-only creative to the library."""
    tab = page.locator('[data-testid="tab-creatives"]')
    expect(tab).to_be_visible(timeout=5000)
    tab.click()
    page.wait_for_load_state("networkidle")

    add_lib = page.locator('[data-testid="creative-add-library-btn"]')
    expect(add_lib).to_be_visible(timeout=3000)
    add_lib.click()

    page.fill('[data-testid="creative-code"]', code)
    page.fill('[data-testid="creative-name"]', "Mod Reject Smoke")
    page.click('[data-testid="creative-add-submit"]')
    page.wait_for_load_state("networkidle")


def _navigate_to_moderation(page: Page) -> None:
    """Navigate to /creatives/moderation via sidebar."""
    mod_link = page.locator('aside nav a[href="/creatives/moderation"]')
    expect(mod_link).to_be_visible(timeout=5000)
    mod_link.click(force=True)
    page.wait_for_load_state("networkidle")


def test_uismoke__creative__moderate_reject(smoke_page: Page) -> None:
    """Reject a pending creative with reason and verify status."""
    page = smoke_page
    reject_reason = "Не соответствует брендбуку — низкое разрешение"

    # ── Create campaign with a pending creative ──
    _create_draft_campaign(page)
    creative_code = f"MR-{os.urandom(3).hex()}"
    _add_creative_to_library(page, creative_code)

    # ── Navigate to moderation page ──
    _navigate_to_moderation(page)

    # ── Wait for the moderation page to load ──
    expect(page.locator('[data-testid="moderation-page"]')).to_be_visible(timeout=10000)

    # ── Find our creative row ──
    row = page.locator(f'[data-testid="moderation-row-{creative_code}"]')
    expect(row).to_be_visible(timeout=10000)

    # ── Verify pending status ──
    status = page.locator(f'[data-testid="moderation-status-{creative_code}"]')
    expect(status).to_be_visible()
    assert "На проверке" in status.inner_text(), f"Expected pending, got: {status.inner_text()}"

    # ── Click reject to open inline reason input ──
    reject_btn = page.locator(f'[data-testid="moderation-reject-{creative_code}"]')
    expect(reject_btn).to_be_visible()
    reject_btn.click()

    # ── Wait for reject reason input to appear ──
    reason_input = page.locator(f'[data-testid="moderation-reject-reason-{creative_code}"]')
    expect(reason_input).to_be_visible(timeout=5000)

    # ── Type reject reason ──
    reason_input.fill(reject_reason)

    # ── Confirm button should now be enabled ──
    confirm_btn = page.locator(f'[data-testid="moderation-reject-confirm-{creative_code}"]')
    expect(confirm_btn).to_be_enabled(timeout=3000)
    confirm_btn.click()

    # ── Wait for reload ──
    page.wait_for_load_state("networkidle")

    # ── Switch to "Отклонены" filter to verify ──
    rejected_filter = page.locator('[data-testid="moderation-filter-rejected"]')
    rejected_filter.click()
    page.wait_for_load_state("networkidle")

    # ── Verify status is now "Отклонён" ──
    row_after = page.locator(f'[data-testid="moderation-row-{creative_code}"]')
    expect(row_after).to_be_visible(timeout=10000)

    status_after = page.locator(f'[data-testid="moderation-status-{creative_code}"]')
    expect(status_after).to_be_visible()
    assert "Отклонён" in status_after.inner_text(), \
        f"Expected rejected, got: {status_after.inner_text()}"

    # ── Verify reason is visible in the row ──
    assert reject_reason in row_after.inner_text(), \
        f"Rejection reason not visible. Row text: {row_after.inner_text()[:200]}"

    # ── Reload to verify persistence ──
    page.reload()
    page.wait_for_load_state("networkidle")

    # After reload, filter resets — switch back to "rejected"
    rejected_filter2 = page.locator('[data-testid="moderation-filter-rejected"]')
    rejected_filter2.click()
    page.wait_for_load_state("networkidle")

    row_reload = page.locator(f'[data-testid="moderation-row-{creative_code}"]')
    expect(row_reload).to_be_visible(timeout=10000)
    status_reload = page.locator(f'[data-testid="moderation-status-{creative_code}"]')
    expect(status_reload).to_be_visible()
    assert "Отклонён" in status_reload.inner_text(), \
        f"After reload, expected rejected, got: {status_reload.inner_text()}"
