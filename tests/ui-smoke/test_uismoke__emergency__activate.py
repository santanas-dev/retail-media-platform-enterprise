"""
UI-smoke: emergency.activate — activate platform emergency mode.
Pattern: login → navigate to Emergency → activate with reason → verify.
"""
import os, pytest

if not os.environ.get("UI_SMOKE_RUN"):
    pytest.skip("UI_SMOKE_RUN not set", allow_module_level=True)

from playwright.sync_api import Page, expect
from conftest import BASE_URL


def test_uismoke__emergency__activate(smoke_page: Page) -> None:
    page = smoke_page
    import time; t0 = time.time()

    # ── Login ──
    page.select_option("#login-provider", "local_break_glass")
    page.fill("#login-username", "break_glass_admin")
    page.fill("#login-password", "break-glass-dev-only")
    page.click('button[type="submit"]')
    page.wait_for_url("**/campaigns", timeout=15000)
    page.wait_for_load_state("networkidle")

    # ── Navigate to Emergency page ──
    page.locator('aside nav a[href="/emergency"]').click(force=True)
    page.wait_for_load_state("networkidle")

    # ── If already active, deactivate first ──
    status_el = page.locator('[data-testid="emergency-status"]')
    expect(status_el).to_be_visible(timeout=10000)

    if "АКТИВЕН" in status_el.inner_text():
        # Deactivate to get clean state
        reason_input = page.locator('[data-testid="emergency-reason-input"]')
        reason_input.fill("Smoke test cleanup — deactivating before activate test")
        page.wait_for_timeout(300)  # React re-render
        deact_btn = page.locator('[data-testid="emergency-deactivate-btn"]')
        expect(deact_btn).to_be_enabled(timeout=5000)
        deact_btn.click()
        page.locator('[data-testid="emergency-confirm-deactivate"]').click()
        page.wait_for_load_state("networkidle")
        expect(page.locator('[data-testid="emergency-status"]')).to_contain_text("НЕ АКТИВЕН", timeout=10000)
        print(f"[{time.time()-t0:.1f}s] Deactivated previous active state")

    # ── Verify inactive state ──
    expect(status_el).to_contain_text("НЕ АКТИВЕН", timeout=5000)
    print(f"[{time.time()-t0:.1f}s] Inactive confirmed")

    # ── Activate ──
    reason_input = page.locator('[data-testid="emergency-reason-input"]')
    reason_input.fill("Срочные технические работы — smoke test")
    page.wait_for_timeout(300)  # React re-render
    act_btn = page.locator('[data-testid="emergency-activate-btn"]')
    expect(act_btn).to_be_enabled(timeout=5000)
    act_btn.click()

    # Confirm
    confirm_btn = page.locator('[data-testid="emergency-confirm-activate"]')
    expect(confirm_btn).to_be_visible(timeout=5000)
    confirm_btn.click()
    page.wait_for_load_state("networkidle")

    # ── Verify active state ──
    expect(page.locator('[data-testid="emergency-status"]')).to_contain_text("АКТИВЕН", timeout=10000)
    expect(page.locator('[data-testid="emergency-success"]')).to_be_visible(timeout=5000)
    expect(page.locator('[data-testid="emergency-warning"]')).to_be_visible(timeout=5000)
    print(f"[{time.time()-t0:.1f}s] Active — status + success + warning")

    # ── Honest scope note ──
    scope_note = page.locator('[data-testid="emergency-scope-note"]')
    expect(scope_note).to_be_visible(timeout=5000)
    note_text = scope_note.inner_text()
    assert "platform emergency state" in note_text.lower() or "backend" in note_text.lower(), \
        f"Scope note missing honest wording: {note_text}"
    print(f"[{time.time()-t0:.1f}s] Scope note honest ✓")

    # ── No misleading device-stop claims ──
    body_text = page.locator("body").inner_text()
    assert "все устройства прекратят показ" not in body_text, \
        "Misleading claim found: 'все устройства прекратят показ'"
    assert "все устройства прекращают показ" not in body_text, \
        "Misleading claim found: 'все устройства прекращают показ'"
    print(f"[{time.time()-t0:.1f}s] No misleading claims ✓")

    # ── Reload: persistence ──
    page.reload()
    page.wait_for_load_state("networkidle")
    expect(page.locator('[data-testid="emergency-status"]')).to_contain_text("АКТИВЕН", timeout=10000)
    print(f"[{time.time()-t0:.1f}s] Reload — active persists ✓ — DONE")
