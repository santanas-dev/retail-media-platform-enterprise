"""
UI-smoke: campaign.submit — CAMPAIGN-UX-001B readiness checklist progression.
Happy-path: Overview checklist → missing steps → flight → placement → creative ready → submit.
"""
import os, pytest

if not os.environ.get("UI_SMOKE_RUN"):
    pytest.skip("UI_SMOKE_RUN not set", allow_module_level=True)

from playwright.sync_api import Page, expect
from conftest import BASE_URL

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "test-creative.png")


def test_uismoke__campaign__submit(smoke_page: Page) -> None:
    page = smoke_page
    import time; t0 = time.time()

    # ── Login ──
    page.select_option("#login-provider", "local_break_glass")
    page.fill("#login-username", "break_glass_admin")
    page.fill("#login-password", "break-glass-dev-only")
    page.click('button[type="submit"]')
    page.wait_for_url("**/campaigns", timeout=15000)
    page.wait_for_load_state("networkidle")

    # ── Create campaign ──
    page.click('[data-testid="campaign-create-open"]')
    page.wait_for_url("**/campaigns/new", timeout=10000)
    page.select_option("#c-org", index=1)
    page.select_option("#c-contract", index=1)
    campaign_code = f"SMOKE-SUB-{os.urandom(2).hex()}"
    page.fill("#c-code", campaign_code)
    page.fill("#c-name", f"Submit {campaign_code}")
    page.fill("#c-budget", "100000")
    page.click('button:has-text("Создать черновик")')
    page.wait_for_url(lambda url: url != BASE_URL + "/campaigns/new", timeout=15000)
    page.wait_for_load_state("networkidle")

    # ── CAMPAIGN-UX-001B: Step 0 — Dismiss guided banner if present ──
    # CAMPAIGN-UX-002D added a guided banner after campaign creation.
    # CampaignCreatePage passes state: { guided: true } → initialTab="content"
    # Banner renders async — wait briefly for it to appear before checking
    dismiss_btn = page.locator('[data-testid="campaign-created-dismiss"]')
    try:
        expect(dismiss_btn).to_be_visible(timeout=3000)
        dismiss_btn.click()
        page.wait_for_timeout(500)
    except Exception:
        pass  # banner may not have appeared (rare)
    # Switch to Overview tab — guidedFromCreate sets initialTab="content"
    page.click('[data-testid="tab-overview"]')
    page.wait_for_load_state("networkidle")

    # ── Step 1 — Verify checklist on Overview ──
    checklist = page.locator('[data-testid="campaign-readiness-checklist"]')
    expect(checklist).to_be_visible(timeout=5000)
    # All three items should show missing
    assert page.locator('[data-testid="readiness-flight-status"]').inner_text() == "—"
    assert page.locator('[data-testid="readiness-placement-status"]').inner_text() == "—"
    assert page.locator('[data-testid="readiness-creative-status"]').inner_text() == "—"
    # Submit status shows what's missing
    submit_status = page.locator('[data-testid="readiness-submit-status"]').inner_text()
    assert "Осталось" in submit_status
    assert "рейс" in submit_status
    print(f"[{time.time()-t0:.1f}s] Checklist missing ✓")

    # ── Use checklist action: flight ──
    page.locator('[data-testid="readiness-flight-action"]').click()
    page.wait_for_load_state("networkidle")
    # Should now be on flights tab
    expect(page.locator('[data-testid="flight-add-btn"]')).to_be_visible(timeout=5000)
    page.click('[data-testid="flight-add-btn"]')
    page.fill('[data-testid="flight-start"]', "2027-03-01")
    page.fill('[data-testid="flight-end"]', "2027-03-31")
    page.click('[data-testid="flight-submit"]')
    page.wait_for_load_state("networkidle")

    # Return to Overview
    page.click('button:has-text("Обзор")')
    page.wait_for_load_state("networkidle")
    # Wait for flight status to update (refreshFlights is async)
    page.wait_for_function(
        "document.querySelector('[data-testid=\"readiness-flight-status\"]')?.textContent === '✅'",
        timeout=10000,
    )
    print(f"[{time.time()-t0:.1f}s] Flight ✓")

    # ── Use checklist action: placement ──
    page.locator('[data-testid="readiness-placement-action"]').click()
    page.wait_for_load_state("networkidle")
    expect(page.locator('[data-testid="placement-add-btn"]')).to_be_visible(timeout=5000)
    page.click('[data-testid="placement-add-btn"]')
    page.locator('[data-testid="placement-surface"]').select_option(index=1)
    page.click('[data-testid="placement-submit"]')
    page.wait_for_load_state("networkidle")

    page.click('button:has-text("Обзор")')
    page.wait_for_load_state("networkidle")
    page.wait_for_function(
        "document.querySelector('[data-testid=\"readiness-placement-status\"]')?.textContent === '✅'",
        timeout=10000,
    )
    print(f"[{time.time()-t0:.1f}s] Placement ✓")

    # ── Use checklist action: creative ──
    creative_code = f"SUB-CR-{os.urandom(2).hex()}"
    page.locator('[data-testid="readiness-creative-action"]').click()
    page.wait_for_load_state("networkidle")
    expect(page.locator('[data-testid="tab-content"]')).to_be_visible(timeout=5000)

    # Use primary upload path
    page.locator('[data-testid="creative-upload-select-file"]').click()
    page.locator('[data-testid="creative-upload-primary-file-input"]').set_input_files(FIXTURE)
    expect(page.locator('[data-testid="creative-upload-primary-code"]')).to_be_visible(timeout=5000)
    page.locator('[data-testid="creative-upload-primary-code"]').fill("")
    page.locator('[data-testid="creative-upload-primary-code"]').fill(creative_code)
    page.locator('[data-testid="creative-upload-metadata-submit"]').click()
    expect(page.locator('[data-testid="creative-upload-done"]')).to_be_visible(timeout=30000)

    # Return to Overview
    page.click('button:has-text("Обзор")')
    page.wait_for_load_state("networkidle")
    page.wait_for_function(
        "document.querySelector('[data-testid=\"readiness-creative-status\"]')?.textContent === '✅'",
        timeout=15000,
    )
    print(f"[{time.time()-t0:.1f}s] Creative ✓")

    # ── All three ready → submit possible ──
    submit_status = page.locator('[data-testid="readiness-submit-status"]').inner_text()
    assert "Можно отправить" in submit_status
    print(f"[{time.time()-t0:.1f}s] Ready to submit ✓")

    # 🔍 SUBMIT-READINESS-CI-004 DIAGNOSTIC — one-render debug element
    diag = page.evaluate("""() => {
      const flights = document.querySelector('[data-testid="readiness-flight-status"]')?.textContent || 'N/A';
      const placements = document.querySelector('[data-testid="readiness-placement-status"]')?.textContent || 'N/A';
      const creatives = document.querySelector('[data-testid="readiness-creative-status"]')?.textContent || 'N/A';
      const submit = document.querySelector('[data-testid="readiness-submit-status"]')?.textContent || 'N/A';
      const btn = document.querySelector('[data-testid="campaign-submit-btn"]');
      const btnDisabled = btn ? btn.disabled : 'BTN_NOT_FOUND';
      const btnText = btn ? btn.textContent : 'N/A';
      const debugEl = document.querySelector('[data-testid="campaign-readiness-debug"]');
      const debugJson = debugEl ? debugEl.getAttribute('data-debug') : 'EL_NOT_FOUND';
      const url = window.location.href;
      return { url, flights, placements, creatives, submit, btnDisabled, btnText, debugJson };
    }""")
    print(f"[{time.time()-t0:.1f}s] 🔍 DIAG: {diag}")

    # ── Submit — button enabled ──
    submit_btn = page.locator('[data-testid="campaign-submit-btn"]')
    expect(submit_btn).to_be_enabled(timeout=10000)
    submit_btn.click()
    try:
        page.wait_for_selector('[data-testid="campaign-submit-error"]', timeout=5000)
        err = page.locator('[data-testid="campaign-submit-error"]').inner_text()
        raise AssertionError(f"Submit failed: {err}")
    except Exception as e:
        if "Submit failed" in str(e):
            raise
    page.wait_for_load_state("networkidle")
    print(f"[{time.time()-t0:.1f}s] Submit done")

    # ── Verify ──
    status_badge = page.locator('[data-testid="campaign-status-badge"]')
    expect(status_badge).to_be_visible(timeout=10000)
    assert "На согласовании" in status_badge.inner_text()
    print(f"[{time.time()-t0:.1f}s] Status ✓")

    page.reload()
    page.wait_for_load_state("networkidle")
    # After reload, wait for campaign detail to render
    page.wait_for_selector("h2", state="visible", timeout=15000)
    page.wait_for_timeout(1000)  # let React finish
    status_badge = page.locator('[data-testid="campaign-status-badge"]')
    expect(status_badge).to_be_visible(timeout=20000)
    expect(status_badge).to_contain_text("На согласовании", timeout=5000)
    print(f"[{time.time()-t0:.1f}s] Reload ✓ — DONE")
