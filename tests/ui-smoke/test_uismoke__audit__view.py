"""
UI-smoke: audit.view — view audit event journal.
Creates real audit events via emergency API, then verifies them in UI.
"""
import os, pytest, time, httpx

if not os.environ.get("UI_SMOKE_RUN"):
    pytest.skip("UI_SMOKE_RUN not set", allow_module_level=True)

from playwright.sync_api import Page, expect
from conftest import BASE_URL

API_URL = "http://localhost:8000/api/v1/identity"


def _api_login() -> str:
    """Login via API, return access token."""
    r = httpx.post(
        "http://localhost:8000/api/v1/auth/login",
        json={"username_or_email": "break_glass_admin", "password": "break-glass-dev-only",
              "auth_provider": "local_break_glass"},
        timeout=10,
    )
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    data = r.json()
    return data["access_token"]


def test_uismoke__audit__view(smoke_page: Page) -> None:
    page = smoke_page
    t0 = time.time()

    # ── Login via UI ──
    page.select_option("#login-provider", "local_break_glass")
    page.fill("#login-username", "break_glass_admin")
    page.fill("#login-password", "break-glass-dev-only")
    page.click('button[type="submit"]')
    page.wait_for_url("**/campaigns", timeout=15000)
    page.wait_for_load_state("networkidle")
    print(f"[{time.time()-t0:.1f}s] Logged in")

    # ── Create audit events via API (deterministic setup) ──
    token = _api_login()
    ts = str(int(time.time()))
    headers = {"Authorization": f"Bearer {token}"}

    # Activate emergency (idempotent — ignore 409 if already active)
    r = httpx.post(f"{API_URL}/emergency/activate",
                   json={"reason": f"Smoke audit activate-{ts}"},
                   headers=headers, timeout=10)
    print(f"[{time.time()-t0:.1f}s] Activate API: {r.status_code}")

    # Small delay for audit event to be written
    time.sleep(0.3)

    # Deactivate emergency
    r = httpx.post(f"{API_URL}/emergency/deactivate",
                   json={"reason": f"Smoke audit deactivate-{ts}"},
                   headers=headers, timeout=10)
    print(f"[{time.time()-t0:.1f}s] Deactivate API: {r.status_code}")

    # ── Navigate to Audit page ──
    page.locator('aside nav a[href="/audit"]').click(force=True)
    page.wait_for_load_state("networkidle")

    # Verify page structure
    expect(page.locator('[data-testid="audit-page"]')).to_be_visible(timeout=10000)
    expect(page.locator('[data-testid="audit-table"]')).to_be_visible(timeout=10000)
    print(f"[{time.time()-t0:.1f}s] Audit page visible")

    # Find any emergency.deactivated event
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

    # Verify pagination
    pagination = page.locator("text=/Всего: \\d+/")
    expect(pagination).to_be_visible(timeout=5000)
    print(f"[{time.time()-t0:.1f}s] Pagination: {pagination.inner_text()}")

    # ── Persistence: navigate away and back ──
    page.locator('aside nav a[href="/campaigns"]').click(force=True)
    page.wait_for_load_state("networkidle")
    page.locator('aside nav a[href="/audit"]').click(force=True)
    page.wait_for_load_state("networkidle")

    expect(page.locator(f'[data-testid="audit-action-{event_id}"]')).to_be_visible(timeout=10000)
    print(f"[{time.time()-t0:.1f}s] Event persists after navigation ✓ — DONE")
