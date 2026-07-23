"""
UI-smoke: campaign.pause — pause an active campaign.
Pattern: full pipeline → approve → activate → pause → verify "Приостановлена" + reload persist.
"""
import os, pytest

if not os.environ.get("UI_SMOKE_RUN"):
    pytest.skip("UI_SMOKE_RUN not set", allow_module_level=True)

from playwright.sync_api import Page, expect
from conftest import BASE_URL

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "test-creative.png")


def test_uismoke__campaign__pause(smoke_page: Page) -> None:
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
    campaign_code = f"SMOKE-PA-{os.urandom(2).hex()}"
    page.fill("#c-code", campaign_code)
    page.fill("#c-name", f"Pause {campaign_code}")
    page.fill("#c-budget", "100000")
    page.click('button:has-text("Создать черновик")')
    page.wait_for_url(lambda url: url != BASE_URL + "/campaigns/new", timeout=15000)
    page.wait_for_load_state("networkidle")

    # ── Creative ──
    creative_code = f"PA-CR-{os.urandom(2).hex()}"
    page.click('[data-testid="tab-creatives"]')
    page.wait_for_load_state("networkidle")
    page.click('[data-testid="creative-add-library-btn"]')
    page.fill('[data-testid="creative-code"]', creative_code)
    page.fill('[data-testid="creative-name"]', "Pause CR")
    page.click('[data-testid="creative-add-submit"]')
    page.wait_for_load_state("networkidle")
    page.click('[data-testid="creative-attach-btn"]')
    opt = page.locator('[data-testid="creative-attach-select"] option').filter(has_text=creative_code)
    page.locator('[data-testid="creative-attach-select"]').select_option(value=opt.get_attribute("value"))
    page.click('[data-testid="creative-attach-submit"]')
    page.wait_for_load_state("networkidle")
    page.locator('[data-testid="creative-file-input"]').set_input_files(FIXTURE)
    expect(page.locator('[data-testid="creative-upload-done"]')).to_be_visible(timeout=20000)
    print(f"[{time.time()-t0:.1f}s] Creative uploaded")

    # ── Flights ──
    page.click('[data-testid="tab-flights"]')
    page.wait_for_load_state("networkidle")
    from datetime import datetime
    today = datetime.utcnow()
    start = today.strftime("%Y-%m-%d")
    end = today.replace(year=today.year + 1).strftime("%Y-%m-%d")
    page.fill("#f-start-date", start)
    page.fill("#f-end-date", end)
    page.fill("#f-budget", "100000")
    page.click('[data-testid="flight-add-btn"]')
    page.wait_for_load_state("networkidle")
    print(f"[{time.time()-t0:.1f}s] Flight added")

    # ── Placements ──
    page.click('[data-testid="tab-placements"]')
    page.wait_for_load_state("networkidle")
    surf_opt = page.locator("#p-surface option").first
    surf_val = surf_opt.get_attribute("value")
    page.select_option("#p-surface", value=surf_val)
    page.fill("#p-max-impressions", "10000")
    page.fill("#p-cpm", "10")
    page.click('[data-testid="placement-add-btn"]')
    page.wait_for_load_state("networkidle")
    print(f"[{time.time()-t0:.1f}s] Placement added")

    # ── Moderate creative ──
    page.click('[data-testid="sidebar-approvals"]')
    page.wait_for_url("**/approvals", timeout=10000)
    page.wait_for_load_state("networkidle")
    page.click('[data-testid="approval-tab-creatives"]')
    page.wait_for_load_state("networkidle")
    page.click('[data-testid="creative-approve-btn"]')
    page.wait_for_load_state("networkidle")
    print(f"[{time.time()-t0:.1f}s] Creative approved")

    # ── Navigate back to campaign ──
    page.click('[data-testid="sidebar-campaigns"]')
    page.wait_for_url("**/campaigns", timeout=10000)
    page.wait_for_load_state("networkidle")
    page.locator(f'tr:has-text("{campaign_code}")').click()
    page.wait_for_load_state("networkidle")

    # ── Submit ──
    expect(page.locator('[data-testid="campaign-submit-btn"]')).to_be_visible(timeout=10000)
    page.click('[data-testid="campaign-submit-btn"]')
    page.wait_for_load_state("networkidle")
    print(f"[{time.time()-t0:.1f}s] Submitted")

    # ── Approve ──
    page.click('[data-testid="sidebar-approvals"]')
    page.wait_for_url("**/approvals", timeout=10000)
    page.wait_for_load_state("networkidle")
    page.locator(f'tr:has-text("{campaign_code}")').first.click()
    page.wait_for_load_state("networkidle")
    expect(page.locator('[data-testid="campaign-approve-btn"]')).to_be_visible(timeout=10000)
    page.click('[data-testid="campaign-approve-btn"]')
    page.wait_for_load_state("networkidle")
    print(f"[{time.time()-t0:.1f}s] Approved")

    # ── Navigate back → Activate ──
    page.click('[data-testid="sidebar-campaigns"]')
    page.wait_for_url("**/campaigns", timeout=10000)
    page.wait_for_load_state("networkidle")
    page.locator(f'tr:has-text("{campaign_code}")').click()
    page.wait_for_load_state("networkidle")

    expect(page.locator('[data-testid="campaign-activate-btn"]')).to_be_visible(timeout=10000)
    page.click('[data-testid="campaign-activate-btn"]')
    page.wait_for_load_state("networkidle")
    print(f"[{time.time()-t0:.1f}s] Activated")

    # ── Pause ──
    expect(page.locator('[data-testid="campaign-pause-btn"]')).to_be_visible(timeout=10000)
    page.click('[data-testid="campaign-pause-btn"]')
    page.wait_for_load_state("networkidle")
    print(f"[{time.time()-t0:.1f}s] Paused")

    # ── Verify status "Приостановлена" ──
    badge = page.locator('[data-testid="campaign-status-badge"]')
    expect(badge).to_contain_text("Приостановлена", timeout=10000)

    # ── Reload: status persists ──
    page.reload()
    page.wait_for_load_state("networkidle")
    badge2 = page.locator('[data-testid="campaign-status-badge"]')
    expect(badge2).to_contain_text("Приостановлена", timeout=10000)

    print(f"[{time.time()-t0:.1f}s] DONE — campaign.pause reachable")
