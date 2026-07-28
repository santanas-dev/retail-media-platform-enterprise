"""
UI-smoke: audit.view — view audit event journal.
Pattern: login → emergency activate/deactivate → audit page → find event → verify.
Creates real audit events via emergency UI actions, then reads them back.
"""
import os, pytest

if not os.environ.get("UI_SMOKE_RUN"):
    pytest.skip("UI_SMOKE_RUN not set", allow_module_level=True)

from playwright.sync_api import Page, expect
from conftest import BASE_URL


def test_uismoke__audit__view(smoke_page: Page) -> None:
    page = smoke_page
    import time; t0 = time.time()

    # ── Login as break_glass_admin ──
    page.select_option("#login-provider", "local_break_glass")
    page.fill("#login-username", "break_glass_admin")
    page.fill("#login-password", "break-glass-dev-only")
    page.click('button[type="submit"]')
    page.wait_for_url("**/campaigns", timeout=15000)
    page.wait_for_load_state("networkidle")
    print(f"[{time.time()-t0:.1f}s] Logged in")

    # ── Create audit events: emergency activate → deactivate ──
    # Navigate to Emergency
    page.locator('aside nav a[href="/emergency"]').click(force=True)
    page.wait_for_load_state("networkidle")

    status_el = page.locator('[data-testid="emergency-status"]')
    expect(status_el).to_be_visible(timeout=10000)

    # Always activate first (idempotent — creates emergency.activated audit event)
    reason_input = page.locator('[data-testid="emergency-reason-input"]')
    reason_input.fill("Smoke audit test — activate")
    page.wait_for_timeout(300)
    act_btn = page.locator('[data-testid="emergency-activate-btn"]')
    expect(act_btn).to_be_enabled(timeout=5000)
    act_btn.click()
    page.locator('[data-testid="emergency-confirm-activate"]').click()
    page.wait_for_load_state("networkidle")
    expect(page.locator('[data-testid="emergency-status"]')).to_contain_text("АКТИВЕН", timeout=10000)
    print(f"[{time.time()-t0:.1f}s] Emergency activated — audit event created")

    # Deactivate (creates emergency.deactivated audit event)
    reason_input = page.locator('[data-testid="emergency-reason-input"]')
    reason_input.fill("Smoke audit test — deactivate")
    page.wait_for_timeout(300)
    deact_btn = page.locator('[data-testid="emergency-deactivate-btn"]')
    expect(deact_btn).to_be_enabled(timeout=5000)
    deact_btn.click()
    page.locator('[data-testid="emergency-confirm-deactivate"]').click()
    page.wait_for_load_state("networkidle")
    expect(page.locator('[data-testid="emergency-status"]')).to_contain_text("НЕ АКТИВЕН", timeout=10000)
    print(f"[{time.time()-t0:.1f}s] Emergency deactivated — audit event created")

    # ── Navigate to Audit page ──
    page.locator('aside nav a[href="/audit"]').click(force=True)
    page.wait_for_load_state("networkidle")

    # Verify page structure
    expect(page.locator('[data-testid="audit-page"]')).to_be_visible(timeout=10000)
    expect(page.locator('[data-testid="audit-table"]')).to_be_visible(timeout=10000)
    print(f"[{time.time()-t0:.1f}s] Audit page visible")

    # Find emergency.deactivated event (most recent)
    # Look for any row whose action cell contains "Отмена аварийного режима"
    action_cells = page.locator('[data-testid^="audit-action-"]')
    found = False
    event_id = None
    count = action_cells.count()
    for i in range(count):
        cell = action_cells.nth(i)
        if "Отмена аварийного режима" in (cell.inner_text() or ""):
            testid = cell.get_attribute("data-testid") or ""
            event_id = testid.replace("audit-action-", "")
            found = True
            break

    assert found, "Expected emergency.deactivated audit event not found"
    print(f"[{time.time()-t0:.1f}s] Found event: {event_id}")

    # Verify row cells
    actor_cell = page.locator(f'[data-testid="audit-actor-{event_id}"]')
    resource_cell = page.locator(f'[data-testid="audit-resource-{event_id}"]')
    created_cell = page.locator(f'[data-testid="audit-created-at-{event_id}"]')

    expect(actor_cell).to_be_visible()
    actor_text = actor_cell.inner_text()
    assert actor_text and actor_text != "—", f"Actor should not be empty: {actor_text}"
    print(f"[{time.time()-t0:.1f}s] Actor: {actor_text}")

    expect(resource_cell).to_be_visible()
    resource_text = resource_cell.inner_text()
    assert resource_text, f"Resource should not be empty: {resource_text}"
    print(f"[{time.time()-t0:.1f}s] Resource: {resource_text}")

    expect(created_cell).to_be_visible()
    created_text = created_cell.inner_text()
    assert created_text and created_text != "—", f"Created-at should not be empty: {created_text}"
    print(f"[{time.time()-t0:.1f}s] Created-at: {created_text}")

    # Verify pagination info shows total > 0
    pagination = page.locator("text=/Всего: \\d+/")
    expect(pagination).to_be_visible(timeout=5000)
    print(f"[{time.time()-t0:.1f}s] Pagination: {pagination.inner_text()}")

    # ── Persistence: navigate away and back ──
    page.locator('aside nav a[href="/campaigns"]').click(force=True)
    page.wait_for_load_state("networkidle")
    page.locator('aside nav a[href="/audit"]').click(force=True)
    page.wait_for_load_state("networkidle")

    # Event still visible after re-navigation
    expect(page.locator(f'[data-testid="audit-action-{event_id}"]')).to_be_visible(timeout=10000)
    print(f"[{time.time()-t0:.1f}s] Event persists after navigation ✓ — DONE")
