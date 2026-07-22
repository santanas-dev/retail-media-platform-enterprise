"""
UI-smoke: creative.upload — operator uploads creative file and attaches to campaign.

Journey: creative.upload (managed-first)
Role: campaign_manager
Path: /login → Кампании → draft campaign → Креативы → add library → attach → upload file
"""
import os
import pathlib
import pytest

if not os.environ.get("UI_SMOKE_RUN"):
    pytest.skip("UI_SMOKE_RUN not set", allow_module_level=True)

from playwright.sync_api import Page, expect
from conftest import (
    BASE_URL,
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

    page.fill("#c-code", f"SMOKE-UPLOAD-{os.urandom(2).hex()}")
    page.fill("#c-name", "Smoke Upload Test")
    page.fill("#c-budget", "100000")

    page.click('button:has-text("Создать черновик")')
    page.wait_for_url("**/campaigns/**", timeout=15000)
    page.wait_for_load_state("networkidle")

    url = page.url
    return url.rstrip("/").split("/")[-1]


def test_uismoke__creative__upload(smoke_page: Page) -> None:
    """Upload a creative file and attach it to a campaign through admin-web UI."""
    page = smoke_page
    campaign_id = _create_draft_campaign(page)

    # ── Navigate to Creatives tab ──
    tab_creatives = page.locator('[data-testid="tab-creatives"]')
    expect(tab_creatives).to_be_visible(timeout=5000)
    tab_creatives.click()
    page.wait_for_load_state("networkidle")

    # ── Add creative to library ──
    add_library_btn = page.locator('[data-testid="creative-add-library-btn"]')
    expect(add_library_btn).to_be_visible(timeout=3000)
    add_library_btn.click()

    creative_code = f"TEST-UP-{os.urandom(2).hex()}"
    page.fill('[data-testid="creative-code"]', creative_code)
    page.fill('[data-testid="creative-name"]', "Test Upload Creative")

    page.click('[data-testid="creative-add-submit"]')
    page.wait_for_load_state("networkidle")

    expect(add_library_btn).to_be_visible(timeout=5000)

    # ── Verify creative in library ──
    page_content = page.content()
    assert "Существующие креативы" in page_content, "Creative library section missing"
    assert creative_code in page_content, f"Creative code '{creative_code}' not in library"

    # ── Attach creative to campaign ──
    attach_btn = page.locator('[data-testid="creative-attach-btn"]')
    expect(attach_btn).to_be_visible(timeout=3000)
    attach_btn.click()

    attach_select = page.locator('[data-testid="creative-attach-select"]')
    expect(attach_select).to_be_visible(timeout=3000)
    # Select by option label containing our creative code
    options = attach_select.locator("option")
    option_count = options.count()
    assert option_count >= 2, f"Expected ≥2 options, got {option_count}"
    # Select the last option (our newly created asset)
    attach_select.select_option(index=option_count - 1)

    page.click('[data-testid="creative-attach-submit"]')
    page.wait_for_load_state("networkidle")

    # ── Verify creative attached ──
    page_content = page.content()
    assert creative_code in page_content, f"Creative '{creative_code}' not in campaign list after attach"

    # ── Upload file ──
    upload_btn = page.locator('button[data-upload]')
    expect(upload_btn).to_be_visible(timeout=5000)
    upload_btn.click()

    fixture_path = pathlib.Path(__file__).parent / "fixtures" / "test-creative.png"
    assert fixture_path.exists(), f"Test fixture not found: {fixture_path}"
    page.set_input_files('[data-testid="creative-file-input"]', str(fixture_path))

    # Upload starts — wait for progress or completion
    page.wait_for_timeout(10000)

    # ── Final verification ──
    page_content = page.content()
    # The creative should still be visible (attached)
    assert creative_code in page_content, f"Creative '{creative_code}' disappeared after upload"
    assert "Test Upload Creative" in page_content, "Creative name disappeared after upload"

    # ── Reload persistence ──
    page.reload()
    page.wait_for_load_state("networkidle")
    tab_creatives.click()
    page.wait_for_load_state("networkidle")

    page_content = page.content()
    assert creative_code in page_content, f"Creative '{creative_code}' not found after reload"
