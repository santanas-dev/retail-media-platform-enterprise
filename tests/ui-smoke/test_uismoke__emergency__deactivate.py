"""
UI-smoke: emergency.deactivate — deactivate platform emergency mode.
Pattern: login → navigate to Emergency → activate if needed → deactivate → verify.
"""
import os, pytest

if not os.environ.get("UI_SMOKE_RUN"):
    pytest.skip("UI_SMOKE_RUN not set", allow_module_level=True)

from playwright.sync_api import Page, expect
from conftest import BASE_URL


def test_uismoke__emergency__deactivate(smoke_page: Page) -> None:
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

    # ── Ensure active (activate if inactive) ──
    status_el = page.locator('[data-testid="emergency-status"]')
    expect(status_el).to_be_visible(timeout=10000)

    if "НЕ АКТИВЕН" in status_el.inner_text():
        reason_input = page.locator('[data-testid="emergency-reason-input"]')
        reason_input.fill("Smoke test — activating before deactivate test")
        page.wait_for_timeout(300)
        act_btn = page.locator('[data-testid="emergency-activate-btn"]')
        expect(act_btn).to_be_enabled(timeout=5000)
        act_btn.click()
        page.locator('[data-testid="emergency-confirm-activate"]').click()
        page.wait_for_load_state("networkidle")
        expect(page.locator('[data-testid="emergency-status"]')).to_contain_text("АКТИВЕН", timeout=10000)
        print(f"[{time.time()-t0:.1f}s] Activated for deactivate test")

    # ── Deactivate ──
    reason_input = page.locator('[data-testid="emergency-reason-input"]')
    reason_input.fill("Работы завершены — smoke test")
    page.wait_for_timeout(300)
    deact_btn = page.locator('[data-testid="emergency-deactivate-btn"]')
    expect(deact_btn).to_be_enabled(timeout=5000)
    deact_btn.click()

    # Confirm
    confirm_btn = page.locator('[data-testid="emergency-confirm-deactivate"]')
    expect(confirm_btn).to_be_visible(timeout=5000)
    confirm_btn.click()
    page.wait_for_load_state("networkidle")

    # ── Verify inactive state ──
    expect(page.locator('[data-testid="emergency-status"]')).to_contain_text("НЕ АКТИВЕН", timeout=10000)
    expect(page.locator('[data-testid="emergency-success"]')).to_be_visible(timeout=5000)
    print(f"[{time.time()-t0:.1f}s] Inactive — status + success")

    # ── Scope note visible ──
    expect(page.locator('[data-testid="emergency-scope-note"]')).to_be_visible(timeout=5000)
    print(f"[{time.time()-t0:.1f}s] Scope note visible ✓")

    # ── Reload: persistence ──
    page.reload()
    page.wait_for_load_state("networkidle")
    expect(page.locator('[data-testid="emergency-status"]')).to_contain_text("НЕ АКТИВЕН", timeout=10000)
    print(f"[{time.time()-t0:.1f}s] Reload — inactive persists ✓ — DONE")
