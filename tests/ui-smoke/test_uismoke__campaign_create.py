"""
UI-TRUTH-001A — campaign.create smoke test.

**EXPECTED FAILURE** — G1 gap: no 'Create Campaign' button in UI.

This test PROVES the gap.  It will fail with a descriptive assertion
message until G1 is fixed.  Run with:

    pytest tests/ui-smoke/ -v

The test goes through login → sidebar → campaign list → looks for
'Create Campaign' button.  Fails because the button doesn't exist.

No direct goto, no API calls, no localStorage manipulation.
Only real UI clicks using stable #id selectors.
"""

import pytest
from conftest import (
    login_as_break_glass_admin,
    navigate_to_campaigns,
    try_find_create_campaign_button,
)
def test_uismoke__campaign_create(smoke_page):
    """Break-glass admin can create a campaign through the UI.

    Step-by-step:
    1. Login (real form — id selectors)
    2. Click 'Кампании' in sidebar
    3. Click 'Создать кампанию' button → **EXPECTED TO FAIL HERE**

    Current reality (G1): step 3 fails because no button exists.
    The page text says 'Создайте первую кампанию' but provides no
    action element. Route /campaigns/new exists and CampaignCreatePage
    renders when visited directly — but a real user cannot get there.
    """
    page = smoke_page

    # Step 1: login
    login_as_break_glass_admin(page)

    # Step 2: already on /campaigns after login — verify sidebar is visible
    page.wait_for_selector("aside nav", state="visible", timeout=5000)

    # Step 3: find 'Create Campaign' button
    # THIS IS THE GAP — will raise AssertionError
    try_find_create_campaign_button(page)
