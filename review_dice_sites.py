"""
Independent headless pass over the candidate dice-game sites: screenshot the
landing page, try to click through to actual gameplay (common button text),
screenshot that too, and dump visible text + any JS bundle URLs seen, for a
critical review. Runs in its own browser process -- does not touch the
already-open interactive Brave window.
"""
import json
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

BRAVE_PATH = "/usr/bin/brave-browser"
OUT = Path("/tmp/claude-1000/-home-rodo-Documents-Farkle/b09a2a93-5ec6-4b86-bb34-948c9e85aa30/scratchpad/dice_review")
OUT.mkdir(parents=True, exist_ok=True)

SITES = {
    "kcddice": "https://kcddice.com/",
    "kcd_dice_en": "https://en.kcd-dice.com/",
    "toss_toss": "https://kdc-dice-game.web.app",
    "nexus_2814": "https://www.nexusmods.com/kingdomcomedeliverance2/mods/2814",
    "nexus_614": "https://www.nexusmods.com/kingdomcomedeliverance2/mods/614",
    "construct_farkle": "https://www.construct.net/en/free-online-games/farkles-medieval-dice-game-69072/play",
}

PLAY_BUTTON_TEXTS = [
    "Start Game", "Play Now", "Play", "Start", "New Game", "Click and Play",
    "PLAY", "Begin", "Roll", "Enter",
]

results = {}

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=BRAVE_PATH, headless=True)
    for name, url in SITES.items():
        entry = {"url": url, "error": None, "title": None, "js_files": [], "text_sample": None}
        js_files = []
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.on("response", lambda r: js_files.append(r.url) if r.url.endswith(".js") else None)
        try:
            page.goto(url, timeout=25000, wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            entry["title"] = page.title()
            shot1 = OUT / f"{name}_1_landing.png"
            page.screenshot(path=str(shot1), full_page=False)
            entry["screenshot_landing"] = str(shot1)
            body_text = page.inner_text("body")[:3000]
            entry["text_sample"] = body_text

            clicked = False
            for txt in PLAY_BUTTON_TEXTS:
                try:
                    loc = page.get_by_text(txt, exact=False).first
                    if loc.is_visible(timeout=1000):
                        loc.click(timeout=3000)
                        clicked = True
                        break
                except Exception:
                    continue
            if clicked:
                page.wait_for_timeout(3000)
                shot2 = OUT / f"{name}_2_ingame.png"
                page.screenshot(path=str(shot2), full_page=False)
                entry["screenshot_ingame"] = str(shot2)
                entry["clicked_play"] = True
            else:
                entry["clicked_play"] = False

            entry["js_files"] = list(dict.fromkeys(js_files))[:20]
        except Exception as e:
            entry["error"] = str(e)
        finally:
            page.close()
        results[name] = entry
        print(f"{name}: title={entry.get('title')!r} clicked_play={entry.get('clicked_play')} error={entry.get('error')}")
    browser.close()

with open(OUT / "results.json", "w") as f:
    json.dump(results, f, indent=2)
print("\nDone. Results + screenshots in", OUT)
