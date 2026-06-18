"""Paste mod-spreadsheet.tsv into the user's link-editable Google Sheet via Playwright.
Trusted Ctrl+V after writing the TSV to the browser clipboard."""
import sys, time
from playwright.sync_api import sync_playwright

URL = "https://docs.google.com/spreadsheets/d/1jzfgNdsIBM0hCbzW9J12jQWstCpec-s9Kff6VdChSYQ/edit?usp=sharing"
INST = r"C:\Users\linde\curseforge\minecraft\Instances\Ultimate vibes distant horizons version"
TSV = open(INST + r"\.uvrun\mod-spreadsheet.tsv", encoding="utf-8").read()
SHOT = INST + r"\.uvrun\sheet_after.png"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1600, "height": 900}, locale="en-US",
                              permissions=["clipboard-read", "clipboard-write"])
    page = ctx.new_page()
    page.goto(URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(8000)
    url_now = page.url
    print("landed:", url_now[:100])
    if "consent" in url_now or "accounts.google" in url_now:
        page.screenshot(path=SHOT)
        print("BLOCKED: consent/login page"); sys.exit(2)
    # detect view-only: name box exists in both; look for the "View only" mode badge
    body = page.content()
    if "View only" in body and "docs-titlebar" in body:
        print("WARNING: possible view-only banner detected (continuing, paste will fail if so)")
    # focus the grid and select A1 via the Name Box
    nb = page.locator("#t-name-box")
    nb.wait_for(state="visible", timeout=30000)
    nb.click()
    page.keyboard.press("Control+a")
    page.keyboard.type("A1")
    page.keyboard.press("Enter")
    page.wait_for_timeout(1500)
    # write clipboard in page context, then trusted paste
    page.evaluate("t => navigator.clipboard.writeText(t)", TSV)
    page.keyboard.press("Control+v")
    page.wait_for_timeout(9000)
    # verify: jump to a far cell and read content via clipboard round-trip
    nb.click(); page.keyboard.press("Control+a"); page.keyboard.type("J600"); page.keyboard.press("Enter")
    page.wait_for_timeout(1000)
    page.keyboard.press("Control+c")
    page.wait_for_timeout(1000)
    got = page.evaluate("() => navigator.clipboard.readText()")
    print("J600 readback:", repr(got[:80]))
    page.screenshot(path=SHOT)
    ctx.close()
    print("done")
