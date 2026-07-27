"""
UI-smoke: inventory.rule_create — admin creates a max_sov rule and verifies row + persistence.
Pattern: login → inventory → rules tab → create max_sov rule → verify row → reload → still visible.
Scope: global, future dates to avoid interfering with existing inventory.simulate.
"""
import os, pytest

if not os.environ.get("UI_SMOKE_RUN"):
    pytest.skip("UI_SMOKE_RUN not set", allow_module_level=True)

from playwright.sync_api import Page, expect
from conftest import BASE_URL


def test_uismoke__inventory__rule_create(smoke_page: Page) -> None:
    page = smoke_page
    import time; t0 = time.time()

    # ── Login as break_glass_admin (has inventory.manage) ──
    page.select_option("#login-provider", "local_break_glass")
    page.fill("#login-username", "break_glass_admin")
    page.fill("#login-password", "break-glass-dev-only")
    page.click('button[type="submit"]')
    page.wait_for_url("**/campaigns", timeout=15000)
    page.wait_for_load_state("networkidle")
    print(f"[{time.time()-t0:.1f}s] Logged in")

    # ── Navigate to Inventory → Rules tab ──
    page.locator('aside nav a[href="/inventory"]').click(force=True)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)

    # Click "Правила" tab
    page.locator("button", has=page.locator("text=Правила")).click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    print(f"[{time.time()-t0:.1f}s] Rules tab loaded")

    # ── Click "+ Создать" ──
    create_btn = page.locator('[data-testid="inventory-rule-create-open"]')
    expect(create_btn).to_be_visible(timeout=5000)
    create_btn.click()
    page.wait_for_timeout(500)

    # ── Fill form: max_sov, global, priority=17, SOV=35%, future dates ──
    page.select_option('[data-testid="inventory-rule-type"]', "max_sov")
    page.fill('[data-testid="inventory-rule-value"]', "35")
    page.fill('[data-testid="inventory-rule-priority"]', "17")
    page.fill('[data-testid="inventory-rule-starts-at"]', "2027-01-01")
    page.fill('[data-testid="inventory-rule-ends-at"]', "2027-03-31")
    print(f"[{time.time()-t0:.1f}s] Form filled")

    # ── Submit ──
    page.click('[data-testid="inventory-rule-submit"]')
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)

    # ── Verify success banner ──
    success = page.locator('[data-testid="inventory-rule-success"]')
    expect(success).to_be_visible(timeout=5000)
    success_text = success.inner_text()
    assert "Правило создано" in success_text, f"Unexpected success: {success_text}"
    print(f"[{time.time()-t0:.1f}s] Success: {success_text}")

    # ── Find the row (first row in table after create) ──
    rule_rows = page.locator('[data-testid^="inventory-rule-row-"]')
    expect(rule_rows.first).to_be_visible(timeout=5000)
    first_row_id = rule_rows.first.get_attribute("data-testid") or ""
    row_key = first_row_id.replace("inventory-rule-row-", "")
    print(f"[{time.time()-t0:.1f}s] Found row: {row_key[:8]}...")

    # ── Verify row fields ──
    type_cell = page.locator(f'[data-testid="inventory-rule-row-type-{row_key}"]')
    expect(type_cell).to_be_visible()
    assert "Макс. доля показов" in type_cell.inner_text()

    scope_cell = page.locator(f'[data-testid="inventory-rule-row-scope-{row_key}"]')
    expect(scope_cell).to_be_visible()
    assert "Глобально" in scope_cell.inner_text()

    value_cell = page.locator(f'[data-testid="inventory-rule-row-value-{row_key}"]')
    expect(value_cell).to_be_visible()
    assert "35%" in value_cell.inner_text()
    print(f"[{time.time()-t0:.1f}s] Value: 35% ✓")

    priority_cell = page.locator(f'[data-testid="inventory-rule-row-priority-{row_key}"]')
    expect(priority_cell).to_be_visible()
    assert "17" in priority_cell.inner_text()

    active_cell = page.locator(f'[data-testid="inventory-rule-row-active-{row_key}"]')
    expect(active_cell).to_be_visible()
    assert "Да" in active_cell.inner_text()

    period_cell = page.locator(f'[data-testid="inventory-rule-row-period-{row_key}"]')
    expect(period_cell).to_be_visible()
    period_text = period_cell.inner_text()
    assert "2027-01-01" in period_text
    assert "2027-03-31" in period_text
    assert "[object Object]" not in period_text
    print(f"[{time.time()-t0:.1f}s] All fields verified ✓")

    # ── Persistence: reload page, verify row still present ──
    page.locator('aside nav a[href="/campaigns"]').click(force=True)
    page.wait_for_load_state("networkidle")
    page.locator('aside nav a[href="/inventory"]').click(force=True)
    page.wait_for_load_state("networkidle")
    page.locator("button", has=page.locator("text=Правила")).click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)

    persisted_row = page.locator(f'[data-testid="inventory-rule-row-{row_key}"]')
    expect(persisted_row).to_be_visible(timeout=10000)
    persist_value = page.locator(f'[data-testid="inventory-rule-row-value-{row_key}"]')
    assert "35%" in persist_value.inner_text()
    print(f"[{time.time()-t0:.1f}s] Reload persistence: 35% ✓ — DONE")
