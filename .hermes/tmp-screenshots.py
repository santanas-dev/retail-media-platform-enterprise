"""A1b after-screenshots — capture 5 pages."""
import asyncio, os
from playwright.async_api import async_playwright

BASE = "http://localhost:3000"
PAGES = [
    "campaigns",
    "advertisers",
    "users",
    "commerce/tariffs",
    "commerce/orders",
]

out_dir = "/home/cobalt/retail-media-platform-enterprise/.hermes/screenshots/a1b-after"

async def main():
    os.makedirs(out_dir, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1440, "height": 900})

        # Login
        await page.goto(f"{BASE}/login", wait_until="networkidle")
        await page.select_option("#login-provider", "local_break_glass")
        await page.fill("#login-username", "break_glass_admin")
        await page.fill("#login-password", "break-glass-dev-only")
        await page.click('button[type="submit"]')
        await page.wait_for_url(f"{BASE}/campaigns", timeout=15000)
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(1000)
        print("  login OK")

        for slug in PAGES:
            url = f"{BASE}/{slug}"
            await page.goto(url, wait_until="networkidle")
            await page.wait_for_timeout(1500)
            name = slug.replace("/", "-")
            path = f"{out_dir}/{name}.png"
            await page.screenshot(path=path, full_page=True)
            print(f"  {slug}: {path}")

        await browser.close()
        print(f"\nDone — {len(PAGES)} screenshots in {out_dir}")

asyncio.run(main())
