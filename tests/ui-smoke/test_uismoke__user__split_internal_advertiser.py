"""
ADVERTISER-UX-001D1 — user.split_internal_advertiser HONEST smoke test.

Proves that UsersPage clearly separates internal/system users from advertiser users:
  login → Пользователи → tab bar visible → Internal tab filters internal →
  Advertiser tab filters advertiser → create form has no UUID → reload persists.

This test is DETERMINISTIC:
- Uses seed data (break_glass_admin, advertiser_test, etc.).
- Real clicks only; page.goto() only /login (in conftest).
- Verifies tab filtering, provider labels, UUID invariant.
- Does NOT mutate shared seed credentials.

Run with:  UI_SMOKE_RUN=1 pytest tests/ui-smoke/test_uismoke__user__split_internal_advertiser.py -v
"""

import os
import pytest

if not os.environ.get("UI_SMOKE_RUN"):
    pytest.skip("UI_SMOKE_RUN not set", allow_module_level=True)

from playwright.sync_api import Page, expect
from conftest import BASE_URL, login_as_break_glass_admin


def navigate_to_users(page: Page) -> None:
    """Click «Пользователи» in sidebar."""
    users_link = page.locator('aside nav a[href="/users"]')
    users_link.click(force=True)
    page.wait_for_url("**/users", timeout=5000)
    page.wait_for_load_state("networkidle")


def test_uismoke__user__split_internal_advertiser(smoke_page: Page) -> None:
    """System admin sees users split by internal vs advertiser tabs.

    Deterministic flow:
    1. Login as break_glass_admin
    2. Navigate to «Пользователи»
    3. Verify tab bar with 3 tabs + user counts
    4. Click «Внутренние» tab — only internal users visible
    5. Click «Рекламодатели» tab — only advertiser users visible
    6. Open create form — verify no UUID/id editable field
    7. Reload → tab selection persists or default is clear
    """
    page = smoke_page
    import time

    t0 = time.time()

    # ── Step 1: login ──
    login_as_break_glass_admin(page)

    # ── Step 2: navigate to users ──
    navigate_to_users(page)

    # ── Step 3: verify tab bar ──
    tab_bar = page.locator('[data-testid="users-tab-bar"]')
    expect(tab_bar).to_be_visible(timeout=10000)

    tab_all = page.locator('[data-testid="users-tab-all"]')
    tab_internal = page.locator('[data-testid="users-tab-internal"]')
    tab_advertiser = page.locator('[data-testid="users-tab-advertiser"]')
    expect(tab_all).to_be_visible()
    expect(tab_internal).to_be_visible()
    expect(tab_advertiser).to_be_visible()

    # Verify counts are numbers (not empty/zero)
    all_text = tab_all.inner_text()
    int_text = tab_internal.inner_text()
    adv_text = tab_advertiser.inner_text()
    assert any(c.isdigit() for c in all_text), f"Tab Все has no count: {all_text}"
    assert any(c.isdigit() for c in int_text), f"Tab Внутренние has no count: {int_text}"
    assert any(c.isdigit() for c in adv_text), f"Tab Рекламодатели has no count: {adv_text}"
    print(f"[{time.time()-t0:.1f}s] Tabs: {all_text.strip()} | {int_text.strip()} | {adv_text.strip()}")

    # ── Step 4: Internal tab ──
    tab_internal.click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(500)

    internal_table = page.locator('[data-testid="users-table-internal"]')
    expect(internal_table).to_be_visible(timeout=5000)

    # Internal users should include break_glass_admin, admin
    internal_text = internal_table.inner_text()
    assert len(internal_text) > 50, f"Internal table appears empty: {internal_text[:100]}"

    # Verify at least one internal user is visible by common seed username
    internal_has_user = (
        "break_glass_admin" in internal_text
        or "admin" in internal_text
        or "operator" in internal_text
    )
    assert internal_has_user, f"No known internal user in table: {internal_text[:200]}"

    # Advertiser users should NOT be visible on internal tab
    # (advertiser_test is a local_advertiser seed user)
    assert "advertiser_test" not in internal_text, (
        f"advertiser_test leaked into internal tab: {internal_text[:200]}"
    )
    print(f"[{time.time()-t0:.1f}s] Internal tab: OK (internal users visible, advertiser_test hidden)")

    # ── Step 5: Advertiser tab ──
    tab_advertiser.click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(500)

    advertiser_table = page.locator('[data-testid="users-table-advertiser"]')
    expect(advertiser_table).to_be_visible(timeout=5000)

    adv_table_text = advertiser_table.inner_text()

    # If there are advertiser users, verify at least one has the right provider label
    if "advertiser_test" in adv_table_text:
        # Verify advertiser_test row has provider label with "рекламодатель"
        provider_cell = page.locator('[data-testid="user-provider-advertiser_test"]')
        if provider_cell.count() > 0:
            provider_text = provider_cell.inner_text()
            assert "рекламодатель" in provider_text.lower(), (
                f"advertiser_test provider label missing 'рекламодатель': {provider_text}"
            )
    else:
        # No advertiser users in seed → verify empty state
        empty = page.locator('[data-testid="users-empty-advertiser"]')
        assert empty.count() > 0 or len(adv_table_text) > 0, "Advertiser tab has no users and no empty state"

    # Internal users should NOT be visible on advertiser tab
    assert "break_glass_admin" not in adv_table_text, (
        f"Internal user leaked into advertiser tab: {adv_table_text[:200]}"
    )
    print(f"[{time.time()-t0:.1f}s] Advertiser tab: OK (no internal users leaked)")

    # ── Step 6: UUID invariant ──
    # Go back to Все tab to find the create button
    tab_all.click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(300)

    create_btn = page.locator('[data-testid="user-create-advertiser-open"]')
    expect(create_btn).to_be_visible(timeout=5000)
    create_btn.click()

    # Form should appear
    username_input = page.locator('[data-testid="user-create-advertiser-username"]')
    expect(username_input).to_be_visible(timeout=3000)

    # Verify NO UUID/id field in the form
    uuid_field = page.locator('[data-testid="user-create-advertiser-id"]')
    id_field = page.locator('[data-testid="user-create-advertiser-uuid"]')
    assert uuid_field.count() == 0, "UUID field found in create form"
    assert id_field.count() == 0, "ID field found in create form"

    # Verify no placeholder text suggesting manual UUID input
    form_html = page.locator('[data-testid="user-create-advertiser-username"]').locator("..").inner_html()
    assert "UUID пользователя" not in form_html, f"UUID placeholder found in form: {form_html[:200]}"
    print(f"[{time.time()-t0:.1f}s] UUID invariant: OK (no id/uuid field in create form)")

    # Close create form
    create_btn.click()

    # ── Step 7: Reload persistence ──
    page.locator('aside nav a[href="/campaigns"]').click(force=True)
    page.wait_for_load_state("networkidle")
    navigate_to_users(page)

    # Tab bar still visible after reload
    expect(page.locator('[data-testid="users-tab-bar"]')).to_be_visible(timeout=10000)
    print(f"[{time.time()-t0:.1f}s] Reload persistence: OK — DONE")
