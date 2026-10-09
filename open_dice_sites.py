"""
Open the candidate KCD dice-game web implementations in a Playwright-driven
Brave browser (non-headless), one tab each, and keep the browser alive until
the user closes it manually. Uses the system Brave binary rather than
Playwright's bundled Chromium.
"""
import time
from playwright.sync_api import sync_playwright

BRAVE_PATH = "/usr/bin/brave-browser"

URLS = [
    "https://kcddice.com/",
    "https://en.kcd-dice.com/",
    "https://kdc-dice-game.web.app",
    "https://www.nexusmods.com/kingdomcomedeliverance2/mods/2814",
    "https://www.nexusmods.com/kingdomcomedeliverance2/mods/614",
    "https://www.construct.net/en/free-online-games/farkles-medieval-dice-game-69072/play",
]

with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path=BRAVE_PATH,
        headless=False,
        args=["--start-maximized"],
    )
    context = browser.new_context(no_viewport=True)
    for url in URLS:
        page = context.new_page()
        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
        except Exception as e:
            print(f"Failed to load {url}: {e}")
    print("All tabs opened. Browser will stay open until you close it.")

    # Keep the script (and therefore the browser process) alive until every
    # tab/window has been closed by the user.
    while True:
        time.sleep(3)
        if len(context.pages) == 0:
            break
    print("All pages closed, exiting.")
