"""
ADVERTISER-UX-001B2 — advertiser.contract_pdf_upload UI-smoke.

Happy-path (9 шагов):
  1. login → 2. Advertisers → 3. select ADV-001 → 4. Contracts tab
  → 5. create contract → 6. «Выбрать PDF» → 7. «Загрузить»
  → 8. verify filename in row → 9. reload persistence.

Only /login via page.goto(); all navigation via clicks.
"""
import os
import time
import pytest
from conftest import login_as_break_glass_admin, unique_suffix, wait_settled


FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
PDF_PATH = os.path.join(FIXTURE_DIR, "test-contract.pdf")


def _navigate_to_advertisers(page):
    link = page.locator('aside nav a[href="/advertisers"]')
    link.click(force=True)
    page.wait_for_url("**/advertisers", timeout=8000)
    wait_settled(page)


def test_uismoke__advertiser__contract_pdf_upload(smoke_page):
    page = smoke_page
    login_as_break_glass_admin(page)

    _navigate_to_advertisers(page)

    # Capture browser console errors for debugging
    console_errors = []
    page.on("console", lambda msg: console_errors.append(f"[{msg.type}] {msg.text}") if msg.type in ("error", "warning") else None)

    # Click first org row to open detail
    row = page.locator('[data-testid="advertiser-org-row"]').first
    row.click()
    page.wait_for_selector('[data-testid="advertiser-detail-panel"]', timeout=5000)

    # Click "Договоры" tab
    page.locator('text=Договоры').last.click()
    page.wait_for_selector('[data-testid="advertiser-contracts-section"]', timeout=5000)

    # Click "Добавить договор"
    page.locator('[data-testid="advertiser-contract-create-open"]').click()
    page.wait_for_selector('[data-testid="advertiser-contract-submit"]', timeout=5000)

    # Fill form with deterministic but unique data
    contract_code = f"SMOKE-C-{unique_suffix()}"
    contract_name = f"Смоук Договор {contract_code}"
    page.fill('[data-testid="advertiser-contract-number"]', contract_code)
    page.fill('[data-testid="advertiser-contract-title"]', contract_name)

    # Save
    page.locator('[data-testid="advertiser-contract-submit"]').click()

    # Wait for contract row with our specific code TEXT
    page.wait_for_function(
        f"""() => {{
            const els = document.querySelectorAll('[data-testid^="advertiser-contract-display-number-"]');
            return Array.from(els).some(el => el.textContent === '{contract_code}');
        }}""",
        timeout=10000,
    )

    # Find the contract row by code
    all_code_els = page.locator('td[data-testid^="advertiser-contract-display-number-"]')
    count = all_code_els.count()
    contract_id = None
    for i in range(count):
        el = all_code_els.nth(i)
        if el.text_content() == contract_code:
            testid = el.get_attribute("data-testid") or ""
            contract_id = testid.replace("advertiser-contract-display-number-", "")
            break
    assert contract_id is not None, f"Contract row with code '{contract_code}' not found"

    # Verify display
    assert page.locator(f'[data-testid="advertiser-contract-display-number-{contract_id}"]').text_content() == contract_code
    assert page.locator(f'[data-testid="advertiser-contract-display-title-{contract_id}"]').text_content() == contract_name

    # ── Upload PDF: proven filechooser pattern (display:none input + visible button + ref.click()) ──
    assert os.path.exists(PDF_PATH), f"PDF fixture not found at {PDF_PATH}"

    # Step 1: Click "Выбрать PDF" → intercept native file dialog
    with page.expect_file_chooser() as fc_info:
        page.locator(f'[data-testid="advertiser-contract-upload-{contract_id}"]').click()
    fc_info.value.set_files(PDF_PATH)

    # Step 2: Verify selected filename appears before upload
    page.wait_for_selector('[data-testid="advertiser-contract-selected-file"]', timeout=5000)
    selected = page.locator('[data-testid="advertiser-contract-selected-file"]')
    selected_text = selected.text_content()
    assert "test-contract.pdf" in selected_text, f"Expected 'test-contract.pdf' in selected file, got: {selected_text}"

    # Step 3: Click "Загрузить" to execute the upload
    page.locator('[data-testid="advertiser-contract-upload-done"]').click()

    # Wait for file name to appear in the row cell (upload complete + detail reload)
    try:
        page.wait_for_function(
            f"""() => {{
                const cell = document.querySelector('[data-testid="advertiser-contract-display-file-{contract_id}"]');
                return cell && cell.textContent.includes('test-contract.pdf');
            }}""",
            timeout=20000,
        )
    except Exception:
        # Dump console errors for debugging
        if console_errors:
            raise AssertionError(f"Upload failed. Console errors: {'; '.join(console_errors[-10:])}")
        raise

    # Verify file metadata in row
    file_cell = page.locator(f'[data-testid="advertiser-contract-display-file-{contract_id}"]')
    file_text = file_cell.text_content()
    assert "test-contract.pdf" in file_text, f"Expected 'test-contract.pdf' in file cell, got: {file_text}"

    # ── Edit contract name ──
    page.locator(f'[data-testid="advertiser-contract-edit-{contract_id}"]').click()
    page.wait_for_selector(f'[data-testid="advertiser-contract-row-{contract_id}"] input', timeout=3000)

    updated_name = "Смоук Договор Обновлён"
    row_inputs = page.locator(f'[data-testid="advertiser-contract-row-{contract_id}"] input')
    row_inputs.nth(1).fill(updated_name)  # name is the second input column
    page.locator(f'[data-testid="advertiser-contract-row-{contract_id}"] button').first.click()

    page.wait_for_selector(f'[data-testid="advertiser-contract-display-title-{contract_id}"]', timeout=10000)
    assert page.locator(f'[data-testid="advertiser-contract-display-title-{contract_id}"]').text_content() == updated_name

    # ── Reload persistence via sidebar navigation ──
    page.locator('aside nav a[href="/advertisers"]').click(force=True)
    page.wait_for_url("**/advertisers", timeout=8000)
    wait_settled(page)

    row = page.locator('[data-testid="advertiser-org-row"]').first
    row.click()
    page.wait_for_selector('[data-testid="advertiser-detail-panel"]', timeout=5000)
    page.locator('text=Договоры').last.click()
    page.wait_for_selector(f'[data-testid="advertiser-contract-display-number-{contract_id}"]', timeout=10000)

    # Verify persistence
    assert page.locator(f'[data-testid="advertiser-contract-display-number-{contract_id}"]').text_content() == contract_code
    assert page.locator(f'[data-testid="advertiser-contract-display-title-{contract_id}"]').text_content() == updated_name
    file_text_after = page.locator(f'[data-testid="advertiser-contract-display-file-{contract_id}"]').text_content()
    assert "test-contract.pdf" in file_text_after, f"File metadata lost after reload: {file_text_after}"
