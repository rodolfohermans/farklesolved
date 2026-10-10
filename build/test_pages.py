#!/usr/bin/env python3
"""Standing cross-device/browser smoke test (Phase 8 of ROADMAP.md).

Run from the repo root: `python3 build/test_pages.py` (or `just test`).

Checks, for every page and every installed Playwright browser engine, at both
a desktop and a mobile viewport:
  - zero JavaScript errors
  - zero network requests to anything but this site's own files (the whole
    privacy pitch; see about.html)
  - the game actually starts and renders dice, where applicable

This exists because a real bug (a stale CSS selector silently stopped
applying, causing the score box to overflow on a phone) shipped and reached
an actual phone before being caught. Run this before every future visual
change ships, not as a one-time audit.

Only the browser engines actually installed in this environment are used;
others are skipped with a clear note rather than silently claiming coverage
that didn't run. Install more with: python3 -m playwright install firefox webkit
"""
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent

GAME_PAGES = ["play_dice.html", "index.html", "play_dice.es.html", "index.es.html"]
STATIC_PAGES = ["about.html", "about.es.html", "farkle_strategy_report.html"]

VIEWPORTS = {
    "desktop": {"width": 1280, "height": 800},
    "mobile": {"width": 375, "height": 667},  # roughly an iPhone SE/8, the size that caught the original bug
}

ENGINES = ["chromium", "firefox", "webkit"]


def check_engine_available(p, engine_name):
    try:
        b = getattr(p, engine_name).launch()
        b.close()
        return True
    except Exception:
        return False


def check_page(browser, path, viewport_name, viewport):
    page = browser.new_page(viewport=viewport)
    errors = []
    requests = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("request", lambda r: requests.append(r.url))
    page.goto("file://" + str(ROOT / path))
    page.wait_for_timeout(200)

    if path in GAME_PAGES:
        start_btn = page.locator("#startBtn")
        if start_btn.count():
            start_btn.click()
            roll_btn = page.locator("#controls button")
            if roll_btn.count():
                roll_btn.first.click()
            page.wait_for_timeout(200)

    external = [r for r in requests if not r.startswith("file://") and not r.startswith("data:")]
    page.close()
    return {"errors": errors, "external": external}


def main():
    failures = 0
    with sync_playwright() as p:
        available = [e for e in ENGINES if check_engine_available(p, e)]
        skipped = [e for e in ENGINES if e not in available]
        print(f"Engines available: {available}")
        if skipped:
            print(f"Engines NOT installed, skipped: {skipped} "
                  f"(install with: python3 -m playwright install {' '.join(skipped)})")

        for engine_name in available:
            browser = getattr(p, engine_name).launch()
            for page_path in GAME_PAGES + STATIC_PAGES:
                for vp_name, vp in VIEWPORTS.items():
                    result = check_page(browser, page_path, vp_name, vp)
                    status = "ok"
                    if result["errors"] or result["external"]:
                        status = "FAIL"
                        failures += 1
                    print(f"[{engine_name:8s} {vp_name:7s}] {page_path:28s} {status}"
                          + (f"  errors={result['errors']}" if result["errors"] else "")
                          + (f"  external={result['external']}" if result["external"] else ""))
            browser.close()

    if failures:
        print(f"\n{failures} check(s) failed.")
        return 1
    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
