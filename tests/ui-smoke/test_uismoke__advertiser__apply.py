"""
UI-smoke: advertiser.apply — public application form.
No auth required. Public entry route /become-advertiser.
"""
import os
import pytest

if not os.environ.get("UI_SMOKE_RUN"):
    pytest.skip("UI_SMOKE_RUN not set", allow_module_level=True)

from playwright.sync_api import Page, expect

# Must match conftest BASE_URL (admin-web :3000)
BASE_URL = os.environ.get("UI_SMOKE_BASE_URL", "http://localhost:3000")
APPLY_URL = f"{BASE_URL}/become-advertiser"

TS = "2026-07-20T21-00-00"


def test_uismoke__advertiser__apply(page: Page):
    """Public user submits advertiser application form without auth."""
    # 1. Open public entry route
    page.goto(APPLY_URL)
    page.wait_for_load_state("networkidle")

    # 2. Verify form is visible (public, no login redirect)
    expect(page.get_by_test_id("advertiser-apply-company-name")).to_be_visible()

    # 3. Fill required fields
    page.get_by_test_id("advertiser-apply-company-name").fill(f"ООО Тест-{TS}")
    page.get_by_test_id("advertiser-apply-contact-name").fill("Петров Пётр")
    page.get_by_test_id("advertiser-apply-email").fill(f"test-{TS}@example.com")
    page.get_by_test_id("advertiser-apply-phone").fill("+7-999-000-0001")
    page.get_by_test_id("advertiser-apply-website").fill("https://test.example.com")
    page.get_by_test_id("advertiser-apply-comment").fill("Тестовая заявка — smoke")

    # 4. Consent checkbox
    page.get_by_test_id("advertiser-apply-consent").check()

    # 5. Submit
    page.get_by_test_id("advertiser-apply-submit").click()

    # 6. Success message
    expect(page.locator("text=Заявка отправлена")).to_be_visible(timeout=10000)
    expect(page.locator("text=Это не даёт немедленного доступа")).to_be_visible()
