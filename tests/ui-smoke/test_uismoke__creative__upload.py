"""
UI-smoke: creative.upload — CAMPAIGN-UX-001A human-path.
Primary path: Выбрать файл → авто-метаданные → подтвердить → upload → Готов.
Jamie: creative.upload (managed-first)
Role: campaign_manager
Happy-path: 5 шагов — 1) Креативы → 2) Выбрать файл → 3) метаданные авто-заполнены → 4) Загрузить → 5) статус Готов + reload persistence
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
    page.fill("#c-name", "Smoke Upload Primary")
    page.fill("#c-budget", "100000")

    page.click('button:has-text("Создать черновик")')
    # Wait for navigation away from /campaigns/new
    page.wait_for_url(lambda url: url != BASE_URL + "/campaigns/new", timeout=15000)
    page.wait_for_load_state("networkidle")

    url = page.url
    return url.rstrip("/").split("/")[-1]


def test_uismoke__creative__upload(smoke_page: Page) -> None:
    """
    CAMPAIGN-UX-001A: Primary human-path upload.
    1. Navigate to Креативы tab
    2. Click «Выбрать файл» — primary upload button
    3. Select file via hidden file input
    4. Verify auto-filled metadata form appears
    5. Submit metadata → upload + attach in one flow
    6. Verify «Готов» status
    7. Reload → persistence
    """
    page = smoke_page
    campaign_id = _create_draft_campaign(page)

    # ── Step 1: Navigate to Creatives tab ──
    tab_creatives = page.locator('[data-testid="tab-creatives"]')
    expect(tab_creatives).to_be_visible(timeout=5000)
    tab_creatives.click()
    page.wait_for_load_state("networkidle")

    # ── Step 2: Verify primary upload CTA is visible ──
    primary_section = page.locator('[data-testid="creative-upload-primary"]')
    expect(primary_section).to_be_visible(timeout=5000)
    assert "Загрузить файл с ПК" in primary_section.inner_text(), \
        "Primary upload CTA heading not visible"

    select_file_btn = page.locator('[data-testid="creative-upload-select-file"]')
    expect(select_file_btn).to_be_visible(timeout=3000)

    # ── Step 3: Click «Выбрать файл» → file picker opens ──
    # Click the button to trigger primaryUploadInputRef click
    select_file_btn.click()

    # Upload a test file
    fixture_path = pathlib.Path(__file__).parent / "fixtures" / "test-creative.png"
    assert fixture_path.exists(), f"Test fixture not found: {fixture_path}"
    page.set_input_files('[data-testid="creative-upload-primary-file-input"]', str(fixture_path))

    # ── Step 4: Verify metadata form appeared with auto-filled values ──
    # Form should appear: code, name, media_type
    code_input = page.locator('[data-testid="creative-upload-primary-code"]')
    expect(code_input).to_be_visible(timeout=5000)
    name_input = page.locator('[data-testid="creative-upload-primary-name"]')
    expect(name_input).to_be_visible(timeout=3000)

    # Auto-filled code from filename (test_creative → TEST_CREATIVE)
    code_value = code_input.input_value()
    assert len(code_value) > 0, "Code should be auto-filled from filename"

    # Auto-filled name from filename
    name_value = name_input.input_value()
    assert len(name_value) > 0, "Name should be auto-filled from filename"

    # Allow editing before submit
    code_input.fill("")
    code_input.fill(f"UP-{os.urandom(2).hex()}")

    # ── Step 5: Submit metadata → upload + attach ──
    submit_btn = page.locator('[data-testid="creative-upload-metadata-submit"]')
    expect(submit_btn).to_be_visible(timeout=3000)
    submit_btn.click()

    # ── Step 6: Wait for upload completion — «Готов» indicator ──
    upload_done = page.locator('[data-testid="creative-upload-done"]')
    expect(upload_done).to_be_visible(timeout=30000)
    done_text = upload_done.inner_text()
    assert "Готов" in done_text, f"Upload done indicator missing 'Готов': {done_text}"
    assert "test-creative.png" in done_text, \
        f"Upload done indicator missing filename, got: {done_text}"

    # Verify status in the attached creatives table shows «Готов»
    page_content = page.content()
    assert "Готов" in page_content, "Status 'Готов' not found on page after upload"

    # ── Step 7: Reload persistence ──
    page.reload()
    page.wait_for_load_state("networkidle")
    # Re-open creatives tab after reload
    tab_creatives = page.locator('[data-testid="tab-creatives"]')
    expect(tab_creatives).to_be_visible(timeout=5000)
    tab_creatives.click()
    page.wait_for_load_state("networkidle")

    # Verify persisted: status still «Готов» after reload
    page_content = page.content()
    assert "Готов" in page_content, \
        "Status 'Готов' not found after reload — upload state not persisted"
