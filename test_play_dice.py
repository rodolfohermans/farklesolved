"""
Automated smoke test of play_dice.html via Playwright: starts a match,
plays several player turns (always picking the first available action and
always continuing, to exercise bust/bank/hot-dice paths), checks for JS
console errors, and verifies the review panel + scoreboard update sanely.
"""
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

PATH = (Path(__file__).parent / "play_dice.html").resolve()
errors = []

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path="/usr/bin/brave-browser", headless=True)
    page = browser.new_page()
    page.on("pageerror", lambda exc: errors.append(f"pageerror: {exc}"))
    page.on("console", lambda msg: errors.append(f"console.{msg.type}: {msg.text}") if msg.type == "error" else None)

    page.goto(f"file://{PATH}")
    page.click("#startBtn")
    page.wait_for_timeout(300)

    assert page.is_visible("#game"), "game panel did not appear"

    turns_played = 0
    max_turns = 12
    while turns_played < max_turns:
        # if game over, stop
        if page.is_visible(".banner"):
            print("Game over banner shown:", page.inner_text(".banner"))
            break

        who = page.inner_text("#turnWho")
        if "Your turn" in who:
            # roll
            roll_btn = page.query_selector("#controls button")
            if roll_btn and "Roll" in (roll_btn.inner_text() or ""):
                roll_btn.click()
                page.wait_for_timeout(150)
            # now either bust happened (handled automatically) or action buttons shown
            action_btns = page.query_selector_all(".actions button")
            if action_btns:
                action_btns[0].click()  # pick first available action
                page.wait_for_timeout(150)
                # now choose continue vs bank: alternate to exercise both paths
                buttons = page.query_selector_all("#controls button")
                texts = [b.inner_text() for b in buttons]
                if turns_played % 2 == 0 and any("Continue" in t for t in texts):
                    for b, t in zip(buttons, texts):
                        if "Continue" in t:
                            b.click()
                            break
                else:
                    for b, t in zip(buttons, texts):
                        if "Bank" in t:
                            b.click()
                            break
                page.wait_for_timeout(150)
            else:
                # bust happened -> proceed to opponent turn button
                nxt = page.query_selector("#controls button")
                if nxt:
                    nxt.click()
                    turns_played += 1
                    page.wait_for_timeout(200)
                continue
        else:
            # it's opponent's turn-trigger button state, or opponent auto-resolved
            nxt_buttons = page.query_selector_all("#controls button")
            clicked = False
            for b in nxt_buttons:
                if "Opponent" in (b.inner_text() or ""):
                    b.click()
                    clicked = True
                    page.wait_for_timeout(200)
                    break
            if not clicked:
                page.wait_for_timeout(200)

        # detect end of a player turn by checking if review area populated and we're back to opponent's turn
        if "Opponent" in page.inner_text("#turnWho") or page.is_visible(".banner"):
            turns_played += 1

    review_html = page.inner_text("#reviewArea") if page.is_visible("#reviewArea") else ""
    player_score = page.inner_text("#playerScore")
    opp_score = page.inner_text("#oppScore")
    print(f"Final (or mid-game) scores -> player: {player_score}, opponent: {opp_score}")
    print("Last review area text (truncated):", review_html[:400])

    browser.close()

if errors:
    print("\n=== JS ERRORS DETECTED ===")
    for e in errors:
        print(e)
else:
    print("\nNo JS console errors or page errors detected.")
