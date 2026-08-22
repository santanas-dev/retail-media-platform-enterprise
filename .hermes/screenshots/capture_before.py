"""STYLE-TOKENS-001A1a — before screenshots."""
import os
from playwright.sync_api import sync_playwright

OUT = "/home/cobalt/retail-media-platform-enterprise/.hermes/screenshots/before"
BASE = "http://localhost:3000"
PW = os.environ.get("UI_SMOKE_BG_PASSWORD", "break-glass-dev-only")

PAGES = [
    ("campaigns", "/campaigns"),
    ("advertisers", "/advertisers"),
    ("users", "/users"),
    ("commerce", "/commerce/tariffs"),
    ("devices", "/devices"),
]

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width":1440,"height":900}, locale="ru-RU")
    pg = ctx.new_page()
    pg.goto(f"{BASE}/login"); pg.wait_for_load_state("networkidle")
    pg.select_option("#login-provider", "local_break_glass")
    pg.fill("#login-username", "break_glass_admin")
    pg.fill("#login-password", PW)
    pg.click('button[type="submit"]')
    pg.wait_for_url("**/campaigns", timeout=15000)
    pg.wait_for_load_state("networkidle")
    for name, path in PAGES:
        pg.goto(f"{BASE}{path}")
        pg.wait_for_load_state("networkidle")
        pg.wait_for_timeout(1000)
        pg.screenshot(path=f"{OUT}/{name}.png", full_page=False)
        print(f"  OK {name}")
    b.close()
print("Done")
