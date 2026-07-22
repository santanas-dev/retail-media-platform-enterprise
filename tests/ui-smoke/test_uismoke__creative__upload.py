"""
UI-smoke: creative.upload — proves actual file upload completion + persisted state.

Journey: creative.upload (managed-first)
Role: campaign_manager
Path: /login → Кампании → draft campaign → Креативы → add library → attach → upload → verify Готов
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

    page.fill("#c-code", f"SMOKE-UP-{os.urandom(2).hex()}")
    page.fill("#c-name", "Smoke Upload Test")
    page.fill("#c-budget", "100000")

    page.click('button:has-text("Создать черновик")')
    # Wait for navigation away from /campaigns/new
    page.wait_for_url(lambda url: url != BASE_URL + "/campaigns/new", timeout=15000)
    page.wait_for_load_state("networkidle")

    url = page.url
    return url.rstrip("/").split("/")[-1]


def test_uismoke__creative__upload(smoke_page: Page) -> None:
    """Upload a creative file, prove completion (status=Готов), verify persisted."""
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
    # Find the option with our creative code and get its value attribute
    option_locator = page.locator(
        f'[data-testid="creative-attach-select"] option'
    ).filter(has_text=creative_code)
    expect(option_locator).to_have_count(1, timeout=5000)
    option_value = option_locator.get_attribute("value")
    attach_select.select_option(value=option_value)

    page.click('[data-testid="creative-attach-submit"]')
    page.wait_for_load_state("networkidle")

    # ── Verify creative attached, status shows "Ожидает загрузки" ──
    page_content = page.content()
    assert creative_code in page_content, f"Creative '{creative_code}' not in campaign list after attach"

    status_cell = page.locator(f'[data-testid="creative-status-{creative_code}"]')
    expect(status_cell).to_be_visible(timeout=5000)
    status_text = status_cell.inner_text()
    assert "Ожидает загрузки" in status_text, \
        f"Expected 'Ожидает загрузки' before upload, got: '{status_text}'"

    # ── Upload file ──
    upload_btn = page.locator('button[data-upload]')
    expect(upload_btn).to_be_visible(timeout=5000)
    upload_btn.click()

    fixture_path = pathlib.Path(__file__).parent / "fixtures" / "test-creative.png"
    assert fixture_path.exists(), f"Test fixture not found: {fixture_path}"
    page.set_input_files('[data-testid="creative-file-input"]', str(fixture_path))

    # ── WAIT for upload completion proof: "✅ Готов" indicator ──
    upload_done = page.locator('[data-testid="creative-upload-done"]')
    expect(upload_done).to_be_visible(timeout=30000)
    done_text = upload_done.inner_text()
    assert "Готов" in done_text, f"Upload done indicator missing 'Готов': {done_text}"
    assert "test-creative.png" in done_text, \
        f"Upload done indicator missing filename, got: {done_text}"

    # ── Verify status changed to "Готов" ──
    status_cell = page.locator(f'[data-testid="creative-status-{creative_code}"]')
    status_text = status_cell.inner_text()
    assert status_text == "Готов", \
        f"Expected status 'Готов' after upload, got: '{status_text}'"

    # ── Reload persistence ──
    page.reload()
    page.wait_for_load_state("networkidle")
    # Re-open creatives tab after reload
    tab_creatives = page.locator('[data-testid="tab-creatives"]')
    expect(tab_creatives).to_be_visible(timeout=5000)
    tab_creatives.click()
    page.wait_for_load_state("networkidle")

    # ── Verify persisted: status still "Готов" after reload ──
    page_content = page.content()
    assert creative_code in page_content, f"Creative '{creative_code}' not found after reload"
    assert "Test Upload Creative" in page_content, "Creative name disappeared after reload"

    status_cell = page.locator(f'[data-testid="creative-status-{creative_code}"]')
    expect(status_cell).to_be_visible(timeout=5000)
    status_text = status_cell.inner_text()
    assert status_text == "Готов", \
        f"Expected status 'Готов' after reload, got: '{status_text}'"
