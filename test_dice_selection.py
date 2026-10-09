"""
Test the new click-to-hold dice selection: force specific rolls via a
monkeypatched RNG (by overriding Math.random before rolling) so we can
exercise exact, known scenarios -- an invalid partial selection, a valid
selection, and the straight-with-leftover case -- and confirm the UI reacts
correctly with no console errors.
"""
from playwright.sync_api import sync_playwright

errors = []

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path="/usr/bin/brave-browser", headless=True)
    page = browser.new_page()
    page.on("pageerror", lambda exc: errors.append(f"pageerror: {exc}"))
    page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)

    page.goto("file:///home/rodo/Documents/Farkle/play_dice.html")
    page.click("#startBtn")
    page.wait_for_timeout(200)

    # Force the next roll to be [1,2,3,4,5,5] (straight + spare 5) by stubbing rollDice once.
    page.evaluate("""() => {
        window.__origRollDice = rollDice;
        rollDice = function(k){ return [1,2,3,4,5,5].slice(0,k); };
    }""")
    page.click("#controls button")  # "Roll 6 dice"
    page.wait_for_timeout(200)

    dice_texts = [d.inner_text() for d in page.query_selector_all("#diceRow .die")]
    print("Dice shown:", dice_texts)
    assert len(dice_texts) == 6

    # Click an INVALID partial selection: just the "2" die (index 1) -> should be invalid.
    page.query_selector_all("#diceRow .die")[1].click()
    page.wait_for_timeout(100)
    status1 = page.inner_text("#selectStatus")
    print("Status after selecting lone 2:", status1)
    assert "doesn't score" in status1, "expected invalid-selection message"
    assert page.get_attribute("#confirmSelectionBtn", "disabled") is not None

    # Deselect the 2, select all 6 dice (straight + spare 5) -> should be valid, 550.
    page.query_selector_all("#diceRow .die")[1].click()  # deselect
    for i in range(6):
        die = page.query_selector_all("#diceRow .die")[i]
        if "held" not in (die.get_attribute("class") or ""):
            die.click()
    page.wait_for_timeout(100)
    status2 = page.inner_text("#selectStatus")
    print("Status after selecting all 6 (straight+spare 5):", status2)
    assert "550" in status2 and "Valid" in status2, f"expected valid 550 selection, got: {status2}"
    assert page.get_attribute("#confirmSelectionBtn", "disabled") is None

    page.click("#confirmSelectionBtn")
    page.wait_for_timeout(150)
    turn_total = page.inner_text("#turnTotal")
    dice_left = page.inner_text("#diceLeft")
    print(f"After confirm: turn total={turn_total}, dice left={dice_left}")
    assert turn_total == "550"
    assert dice_left == "6"  # hot dice: all 6 were held

    # restore and bank to end turn cleanly
    page.evaluate("rollDice = window.__origRollDice;")
    buttons = page.query_selector_all("#controls button")
    for b in buttons:
        if "Bank" in (b.inner_text() or ""):
            b.click()
            break
    page.wait_for_timeout(150)
    review = page.inner_text("#reviewArea")
    print("Review panel:", review[:300])

    browser.close()

if errors:
    print("\n=== JS ERRORS ===")
    for e in errors:
        print(e)
    raise SystemExit(1)
else:
    print("\nAll checks passed, no JS errors.")
