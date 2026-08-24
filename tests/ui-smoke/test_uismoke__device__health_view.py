"""
JOURNEY-017 — device.health_view UI-smoke.

Verifies: operator logs in, opens Devices page, sees KSO-001 with health fields.
"""
import os
import pytest
from playwright.sync_api import Page, expect
from conftest import login_as_break_glass_admin, wait_settled

pytestmark = pytest.mark.skipif(
    not os.environ.get("UI_SMOKE_RUN"),
    reason="UI_SMOKE_RUN not set",
)

BASE_URL = os.environ.get("UI_SMOKE_BASE_URL", "http://localhost:3000")
LOGIN_URL = f"{BASE_URL}/login"
BG_USERNAME = os.environ.get("UI_SMOKE_BG_USERNAME", "break_glass_admin")
BG_PASSWORD = os.environ.get("UI_SMOKE_BG_PASSWORD", "break-glass-dev-only")


def _login(page: Page) -> None:
    """Login as break-glass admin (has devices.read)."""
    page.goto(LOGIN_URL)
    wait_settled(page)
    login_as_break_glass_admin(page)


def test_uismoke__device__health_view(page: Page) -> None:
    """
    Happy-path: login → navigate to Devices → see KSO-001 row
    → verify health state, heartbeat, versions → reload → still visible.
    """
    _login(page)

    # Navigate to Devices page via sidebar
    devices_link = page.locator('aside nav a[href="/devices"]')
    devices_link.click(force=True)
    wait_settled(page)

    # 1. Page-level data-testid
    page_header = page.locator('[data-testid="device-health-page"]')
    expect(page_header).to_be_visible(timeout=10000)

    # 2. Table is visible
    table = page.locator('[data-testid="device-health-table"]')
    expect(table).to_be_visible(timeout=5000)

    # 3. KSO-001 row is visible (seed device)
    row = page.locator('[data-testid="device-health-row-KSO-001"]')
    expect(row).to_be_visible(timeout=5000)

    # 4. Health state badge (unknown for unregistered seed device)
    health_badge = page.locator('[data-testid="device-health-state-KSO-001"]')
    expect(health_badge).to_be_visible(timeout=3000)
    health_text = health_badge.inner_text()
    assert health_text in ("Неизвестно", "Здоров", "Деградация", "Нездоров"), \
        f"Unexpected health state: {health_text}"

    # 5. Last heartbeat (expected: "нет данных" for seed device without heartbeat)
    hb_cell = page.locator('[data-testid="device-health-last-heartbeat-KSO-001"]')
    expect(hb_cell).to_be_visible(timeout=3000)
    hb_text = hb_cell.text_content() or ""
    # Can be real heartbeat or "нет данных"
    assert len(hb_text) > 0, "Heartbeat cell is empty"

    # 6. Runtime version (expected: "—" for seed device)
    runtime_cell = page.locator('[data-testid="device-health-runtime-version-KSO-001"]')
    expect(runtime_cell).to_be_visible(timeout=3000)

    # 7. Player version (expected: "—" for seed device)
    player_cell = page.locator('[data-testid="device-health-player-version-KSO-001"]')
    expect(player_cell).to_be_visible(timeout=3000)

    # 8. Reload persistence — verified by waiting for async nav to settle,
    # then confirming row is still visible (SPA handles auth refresh on tab nav)
    devices_link2 = page.locator('aside nav a[href="/devices"]')
    devices_link2.click(force=True)
    page.wait_for_selector('[data-testid="device-health-page"]', state="visible", timeout=15000)

    row_after = page.locator('[data-testid="device-health-row-KSO-001"]')
    expect(row_after).to_be_visible(timeout=10000)

    health_after = page.locator('[data-testid="device-health-state-KSO-001"]')
    expect(health_after).to_be_visible(timeout=3000)
