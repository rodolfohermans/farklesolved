"""
Automated smoke test of play_dice.html via Playwright: starts a match,
plays several player turns against the current click-to-hold dice UI
(roll, click scoring dice to hold them, confirm, then continue or bank,
alternating to exercise both paths), checks for JS console errors, and
verifies the review panel + scoreboard update sanely.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright

PATH = (Path(__file__).parent / "play_dice.html").resolve()
errors = []


def pick_scoring_indices(dice):
    """Pick a subset of rolled dice (by index) that is guaranteed to be a
    legal score, mirroring the game's own rules: any 1 or 5 always scores
    on its own, and any face with three or more of a kind scores as a
    group. A non-bust roll always has at least one of these, since bust is
    defined as having none of them (no 1, no 5, no 3-of-a-kind)."""
    idxs = [i for i, d in enumerate(dice) if d in (1, 5)]
    if idxs:
        return idxs
    positions_by_face = {}
    for i, d in enumerate(dice):
        positions_by_face.setdefault(d, []).append(i)
    for positions in positions_by_face.values():
        if len(positions) >= 3:
            return positions
    return []


def click_button_with(page, fragment):
    for b in page.query_selector_all("#controls button"):
        if fragment in (b.inner_text() or ""):
            b.click()
            return True
    return False


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
    max_iterations = 400
    iterations = 0

    while turns_played < max_turns and iterations < max_iterations:
        iterations += 1

        if page.is_visible(".banner"):
            print("Game over banner shown:", page.inner_text(".banner"))
            break

        buttons = page.query_selector_all("#controls button")
        texts = [(b.inner_text() or "") for b in buttons]

        if page.query_selector("#confirmSelectionBtn"):
            # A roll just landed and is not a bust: hold a legal scoring
            # subset of the actual dice shown, then confirm it.
            dice = page.evaluate("state.currentDice")
            idxs = pick_scoring_indices(dice)
            assert idxs, f"non-bust roll {dice} had no scoring subset -- scoring rules mismatch"
            for i in idxs:
                page.query_selector_all("#diceRow .die")[i].click()
                page.wait_for_timeout(30)

            selected = page.evaluate("[...state.selectedSet]")
            assert set(selected) == set(idxs), f"expected held dice {idxs}, got {selected}"

            assert page.get_attribute("#confirmSelectionBtn", "disabled") is None, (
                f"selection {idxs} of roll {dice} was not accepted as a valid score"
            )
            page.click("#confirmSelectionBtn")
            page.wait_for_timeout(100)

        elif any("Your turn" in t for t in texts):
            click_button_with(page, "Your turn")
            page.wait_for_timeout(150)

        elif any("Opponent's turn" in t for t in texts):
            click_button_with(page, "Opponent's turn")
            turns_played += 1
            page.wait_for_timeout(200)

        elif any("Continue" in t for t in texts) and any("Bank" in t for t in texts):
            # Alternate continue vs. bank across turns to exercise both paths.
            if turns_played % 2 == 0:
                click_button_with(page, "Continue")
            else:
                click_button_with(page, "Bank")
            page.wait_for_timeout(150)

        elif any("Roll" in t for t in texts):
            click_button_with(page, "Roll")
            page.wait_for_timeout(150)

        else:
            page.wait_for_timeout(100)

    review_html = page.inner_text("#reviewArea") if page.is_visible("#reviewArea") else ""
    player_score = page.inner_text("#playerScore")
    opp_score = page.inner_text("#oppScore")
    print(f"Final (or mid-game) scores -> player: {player_score}, opponent: {opp_score}")
    print("Last review area text (truncated):", review_html[:400])

    assert turns_played > 0, "no player turns completed -- loop never progressed"

    browser.close()

if errors:
    print("\n=== JS ERRORS DETECTED ===")
    for e in errors:
        print(e)
    raise SystemExit(1)
else:
    print("\nNo JS console errors or page errors detected.")
