"""
JOURNEY-006 — advertiser.view HONEST smoke test.

Proves that an admin can view an advertiser organization's detail through the UI:
  login → Рекламодатели → click org row → verify detail panel → check users tab.

DETERMINISTIC:
- Uses seed advertiser organization (ADV-001, ООО «Рекламный Альянс»).
- Verifies code, display_name, legal_name in overview tab.
- Switches to Пользователи tab — honest state (empty or with users).
- No API calls, no localStorage, no deep links.
- Only /login via page.goto() (in conftest fixture).

Run:  UI_SMOKE_RUN=1 pytest tests/ui-smoke/test_uismoke__advertiser__view.py -v
"""

from conftest import login_as_break_glass_admin

# Seed org ADV-001 — must exist in seed
TARGET_ORG_CODE = "ADV-001"
TARGET_ORG_DISPLAY_NAME = "Рекламный Альянс"
TARGET_ORG_LEGAL_NAME = "ООО «Рекламный Альянс»"


def navigate_to_advertisers(page):
    """Click «Рекламодатели» in sidebar."""
    link = page.locator('aside nav a[href="/advertisers"]')
    link.click(force=True)
    page.wait_for_url("**/advertisers", timeout=5000)
    page.wait_for_load_state("networkidle")


def test_uismoke__advertiser__view(smoke_page):
    """Admin views advertiser organization detail.

    Flow:
    1. Login as break_glass_admin
    2. Navigate to «Рекламодатели»
    3. Click on the seed org row (ADV-001)
    4. Verify detail panel with code, display_name, legal_name, status
    5. Switch to «Пользователи» tab — honest state
    """
    page = smoke_page

    # Step 1: login
    login_as_break_glass_admin(page)

    # Step 2: navigate to «Рекламодатели»
    navigate_to_advertisers(page)

    # Step 3: find the ADV-001 org row and click it
    page.wait_for_selector('[data-testid="advertiser-org-row"]', state="visible", timeout=10000)

    rows = page.locator('[data-testid="advertiser-org-row"]')
    row_count = rows.count()
    assert row_count >= 1, f"Expected at least 1 org, got {row_count}"

    # Find row containing ADV-001
    target_idx = -1
    for i in range(row_count):
        row_text = rows.nth(i).inner_text()
        if TARGET_ORG_CODE in row_text:
            target_idx = i
            break

    assert target_idx >= 0, (
        f"Could not find org '{TARGET_ORG_CODE}' in the table. "
        f"Row texts: {[rows.nth(i).inner_text()[:60] for i in range(min(row_count, 5))]}"
    )

    rows.nth(target_idx).click()

    # Step 4: verify detail panel with overview data
    panel = page.locator('[data-testid="advertiser-detail-panel"]')
    panel.wait_for(state="visible", timeout=5000)

    # Wait for detail data to load (API call completes, Overview tab renders)
    code_el = page.locator('[data-testid="advertiser-detail-code"]')
    code_el.wait_for(state="visible", timeout=10000)
    assert TARGET_ORG_CODE in code_el.inner_text(), (
        f"Expected code '{TARGET_ORG_CODE}', got '{code_el.inner_text()}'"
    )

    display_el = page.locator('[data-testid="advertiser-detail-display-name"]')
    assert display_el.is_visible(), "Display name not visible"
    assert TARGET_ORG_DISPLAY_NAME in display_el.inner_text(), (
        f"Expected name '{TARGET_ORG_DISPLAY_NAME}', got '{display_el.inner_text()}'"
    )

    legal_el = page.locator('[data-testid="advertiser-detail-legal-name"]')
    assert legal_el.is_visible(), "Legal name not visible"
    assert TARGET_ORG_LEGAL_NAME in legal_el.inner_text(), (
        f"Expected legal name '{TARGET_ORG_LEGAL_NAME}', got '{legal_el.inner_text()}'"
    )

    status_el = page.locator('[data-testid="advertiser-detail-status"]')
    assert status_el.is_visible(), "Status not visible"
    assert "Актив" in status_el.inner_text(), f"Expected active status, got '{status_el.inner_text()}'"

    # Step 5: switch to Пользователи tab — honest state (scope inside detail panel)
    users_tab = panel.locator('text=Пользователи').first
    users_tab.click()

    # Wait for users tab content — either empty state or user list
    page.wait_for_timeout(500)

    has_users = page.locator('[data-testid="advertiser-detail-users"]')
    has_empty = page.locator('[data-testid="advertiser-detail-users-empty"]')

    # One of these must be visible
    assert has_users.is_visible() or has_empty.is_visible(), (
        "Neither users table nor empty state is visible"
    )
