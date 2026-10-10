# Farkle / farklesolved.com: Development Roadmap

Everything raised across recent sessions, plus the full adversarial audit (independently
re-derived math, live network capture, source review), organized into phases with real
dependencies, not a flat backlog. Nothing below is started. Re-derive actual status from
`git log`, not this file, once work begins.

## Dependency overview

- **Tier 1 (no dependencies, start anytime):** Phase 0, Phase 1, Phase 1b, Phase 2, Phase 8
- **Tier 2 (depends on Tier 1):** Phase 3 (needs 1, 2), Phase 4, Phase 5 (needs 2)
- **Tier 3 (depends on Tier 2):** Phase 4b (needs 4, deferred), Phase 6 (needs 5)
- **Independent track:** Phase 7 (Spanish version), no hard dependency on the above, but see
  Phase 1b's note on Phase 7 part 1's rework

Phase 1b doesn't block anything else technically (every other phase can proceed with the
current hand-rolled copy/regex-script approach), but doing Phase 3's dice rendering, Phase 4b's
character loading, and Phase 7's remaining translation work *before* Phase 1b means redoing
that work once the build system exists. Worth doing early for that reason, even though nothing
formally depends on it.

---

## Phase 0: Correctness & honesty fixes

**Depends on:** nothing. **Why first:** cheap, independent, and this project's entire premise
is exactness.

The Fable audit found real defects, not nitpicks, in a site whose whole pitch is rigor. None
of these need a design decision; they're direct edits.

1. **Scholar opponent can decline a winning move** (`play_dice.html` ~432-460): give its
   action selection the same "check for a winning action first" logic the player's own
   grading already has at `winningAction` (~line 906), instead of pure race-blind
   `bestAction`.
2. **End-game-zone copy contradicts the project's own exact table**: rewrite flowchart step 5
   and `#endgameHint` (~line 580) to match what the cheat sheet already states correctly:
   bank early only when ahead with 1-3 dice left, never bank short otherwise.
3. **"Scholar" description overclaims** ("plays the mathematically optimal strategy, every
   time"): it's the race-blind policy, which loses ~5.6 points of win rate to the true
   optimum per the report's own numbers. Reword to something accurate.
4. **`about.html` factual error**: the "only external references are Wikipedia, Ko-fi,
   GitHub" line omits that page's own links to priva-c.org and 512kb.club. Fix inside the
   section whose entire point is precision.
5. **`index.html` title overclaim**: retitle from bare "Farkle, Solved" to something scoped,
   e.g. "KCD Dice, Solved".
6. **Stale 55.90% headline figure** in the report, superseded by the N=50,000 rerun directly
   below it, reconcile.
7. **Two "verified against X" sentences citing artifacts not in the repo** (the 1e-9/1e-11
   reimplementation claim; the G=2,000 re-solve), commit the artifacts or drop the
   sentences.
8. **Duplicate "commonly-cited default"** on both the 2,000 and 4,000 target options: remove, word each option on its own terms.
9. **Stale `test_play_dice.py`** queries UI that no longer exists and always times out: fix
   or delete, remove the matching dead `.actions` CSS.
10. **Academic grounding for the "solved" claim**: cite Allis (1994), *Searching for
    Solutions in Games and Artificial Intelligence*, for the solved-game taxonomy (this is a
    *strongly* solved game in that framing), and state the two-player-only scope explicitly
    rather than relying on it being merely never contradicted.
11. **First-mover-advantage tooltip** on "You always roll first": pull the actual number
    from the existing race-simulation data, don't estimate fresh.
12. **Smaller hygiene items**:
    - Vestigial `farkle_dp.T_MAX` override lines across several `.py` files (no-ops)
    - Unused `const k, T` in `finishPlayerTurn`
    - Two unrelated competitor-scraping scripts committed to, and publicly served from, the
      repo
    - Missing `<meta name="description">` on `play_dice.html`
    - No keyboard/ARIA support on the clickable dice
    - `www.farklesolved.com` doesn't resolve
    - Optional: a CSP meta tag making the no-external-loads commitment browser-enforced, not
      just documented

---

## Phase 1: Rules-as-implemented reference

**Depends on:** nothing. **Unlocks:** Phase 3's analysis panel.

A precise, exhaustive scoring reference transcribed directly from the code, not a generic
description of Farkle. Doing this before Phase 3 matters: the opponent-analysis panel will
want to cite the exact same terms and values, so writing them once here avoids the two
drifting apart.

**How:**
- Transcribe directly from `enumerateActions`/`evaluateSelection`: single 1 = 100, single 5 =
  50 (nothing else scores alone); the three-of-a-kind base value per face as a table, not
  just the doubling formula; both straight bonuses and how leftover dice compose with them;
  the exact bust definition; the hot-dice/re-roll-all-six rule with a worked example.
- Add as an expandable section on the existing About card (matches the "Customize match"
  disclosure pattern already in use), not a separate page.
- Don't restate the race-blind/race-aware endgame caveat in detail here: footnote to the
  strategy report instead, to avoid the two documents drifting apart.

---

## Phase 1b: Build system and asset architecture

**Depends on:** nothing. **Why now:** three separate problems converged on the same root
cause this session (a corrupted line from a heredoc-quoting bug while hand-editing a 1.1MB
file, near-useless git diffs on embedded base64, and a 4-way file-sync burden that's about to
grow a 5th dimension). Hand-rolled regex-surgery Python scripts have been the stopgap all
session; this is about replacing the stopgap, not adding new capability.

**How:**
- Real source assets as real files: individual sprite PNGs, the JS game logic as its own
  `.js` file, CSS as its own `.css` file, each HTML page as a template with placeholders.
  Actually diffable in git for the first time.
- A small build script (Python or Node, not a dependency-graph tool like Make) that
  assembles each final static HTML file from the shared template plus assets, base64-embedding
  images/fonts as it does today.
- A `justfile` wrapping it (`just build`), matching this user's own established tooling
  convention, not a second build-tool paradigm.
- One real decision needed: commit the built HTML (simple, no CI, but a "two sources of
  truth" risk if someone edits the built file directly) versus a GitHub Actions build-on-push
  (single source of truth, but new infrastructure for a solo project). Leaning toward
  committing the build output given the project's size, but this needs the user's sign-off,
  it's a judgment call like Phase 2's.
- **Language text** (unblocks cleaning up Phase 7's duplication): build-time templating, not
  a runtime fetch. One shared template/assets, a small per-language strings file, combined at
  build time. The shipped page stays exactly as self-contained as today (this project's
  "works with zero network connectivity at all" property is worth keeping), only the *source*
  stops being two full 1.1MB files hand-kept in sync. Phase 7 part 1 (already shipped via the
  duplicate-file approach) would get reworked onto this once it exists, not redone from
  scratch, since the actual translated strings are already written.
- **Dice sprite sets** (resolves the "don't ship both styles" request): the default style's
  sprites stay embedded; the alternative style's sprites move to a small sibling asset file,
  fetched on demand only if the visitor actually switches styles. This is a same-origin
  fetch, not a third-party request, so it doesn't touch the no-tracking commitment, but it
  does add the site's first runtime network call, which means updating the privacy audit's
  "zero fetch() calls" line in about.html to be accurate ("same-origin only, no third party")
  rather than letting the documentation drift from reality.
- **Character portraits** (Phase 4b, once it exists): unlike language or dice style, this
  needs a genuine runtime fetch, not a build-time trick, because which portrait is needed can
  change mid-session (a new match, or the Jester revealing a different persona turn to turn),
  not just once per page load. Fetch the one portrait actually needed at the moment an
  opponent is selected or revealed, same-origin, same privacy-audit update as above applies.
  Whether this is worth the added complexity depends on how heavy the portraits actually are
  after cropping to content; measure before committing to lazy-loading them specifically, they
  may be cheap enough to just embed all six.

**Sequencing note:** do not start this concurrently with other in-flight edits to the HTML
files, for the same reason the dice-compression work earlier this session was carefully
staged around a running background workflow. A structural refactor racing against other
edits to the same files is how things get corrupted.

**Implemented (2026-10-10):** the asset-extraction and build-script core of this phase.
Real files now exist under `assets/` (`dice/{face}_{variant}.png` ×24, `background.jpg`,
`pixelfont.woff2`, `dp-data.json`) and `build/templates/` (`template.en.html`,
`template.es.html`, `game.en.js`, `game.es.js`), plus `build/pages.json` and `build/build.py`.
`just build` assembles the 4 shipped pages from these; verified byte-identical to the
pre-refactor committed files, and re-verified via Playwright (dice render, zero JS errors,
zero external requests) after the switch. Decision made per the roadmap's own lean: built
HTML is committed (single `just build` command, no CI needed for a solo static site), not
built on push.

**Deferred, not yet done:** the language-string unification this phase's "How" section also
called for (`game.en.js`/`game.es.js` are still two separate ~32KB files, not one `game.js`
plus a `strings.en.json`/`strings.es.json` pair): the two files differ by only ~400 bytes of
translated text, so this is tractable later but wasn't done now to keep this change a pure,
verifiably-safe refactor rather than risk the text-extraction introducing a subtle bug.
`about.html`/`about.es.html` are also not yet templated (still hand-duplicated as before);
smaller and lower-risk than the game pages, worth folding in later.

---

## Phase 2: Pick one dice style

**Depends on:** nothing. **Unlocks:** simpler Phase 3 rendering, Phase 5 weight savings.

Realistic and pixel-art dice currently ship together behind a toggle. Deciding now, before
Phase 3 builds opponent dice rendering on top of both, avoids doing that rendering work
twice.

**How:**
- A judgment call on visual direction, not a technical one.
- Once decided: remove the losing sprite set from the shipped page entirely (not just hide
  the selector), this is also one of Phase 5's concrete weight-reduction levers.

**Decision (2026-10-10): Realistic, provisional ("for now").** The case was presented with
real measured numbers rather than impressions: the realistic set is ~381KB raw versus the
pixel-art set's ~147KB, a 2.6x weight difference, worth 33% vs 13% of the page's total weight
respectively if the losing set is dropped. Weight favors pixel-art by a wide margin; visual
cohesion with the photographic table scene favors realistic (pixel-art dice visually sit on
top of that scene rather than in it); flat high-contrast pixel-art pips are more robust to
glare/low-end displays than realistic's softer shading; neither has a correctness or
mobile-legibility problem (both verified). Chose realistic, accepting the weight cost,
explicitly revisitable if page weight becomes a real problem later.

**Implemented (2026-10-10):** pixel-art sprite set and the dice-style selector removed from
all four pages. Each page dropped from ~1.1MB to ~930KB. `DICE_SPRITES_REALISTIC` renamed to
`DICE_SPRITES` since it's now the only set.

---

## Phase 3: Opponent experience overhaul

**Depends on:** Phase 1 (terminology), benefits from Phase 2. **Status:** fully planned, zero
code written.

Opponent turns currently resolve instantly as a text log. The goal: watch the opponent
actually play, paced like a real turn, graded the same way the player is.

- **3a: Extract the review renderer.** Pull `showReview()`'s body into a parameterized
  `renderReview(decisions, preTurnScore, target, opts)`; keep a thin wrapper for the player
  so nothing visibly changes yet. Verify against current screenshots before moving on.
- **3b: Make the opponent's turn structured and analyzed (no animation yet).** Convert
  `playOpponentTurn` to async, capture the same `decisions` shape the player already produces
  (it already computes every field, just discards them into a text log), call
  `renderReview(...)` after the turn with the opponent's label swapped in. Highest-value
  single increment, shippable on its own even if animation never happens.
- **3c: Animate it.** Add `renderDice(dice, false)` calls plus `await sleep(~3000ms)`
  between roll, decision reveal, and bank/continue, fully automatic, no click required to
  advance. Add a persistent Skip control (and remember the choice) for anyone who'd rather
  not watch. Guard with a single `turnInProgress` flag so a stray click can't double-run a
  turn.
- **3d: Depth cue.** Render the opponent's dice smaller and higher in the scene than the
  player's, closer to the opponent's body, reinforcing the near/far framing the scorecards
  already imply.
- **3e: Grouped banked-dice display, for both sides.** Below the table image, show this
  turn's banked dice grouped by scoring choice with each group's point value: a 1-2-3-4-5
  straight is one group labeled "+500"; a lone 1 and a lone 5 are two separate groups, "+100"
  and "+50", never merged. Reuses the same decomposition `enumerateActions` already computes.

**Implemented (2026-10-10), all five sub-phases:** `showReview()` became a thin wrapper
around a parameterized `renderReview(decisions, preTurnScore, otherScore, target, subj)`,
`subj` supplying the English/Spanish pronoun and verb forms so the identical grading logic
produces correct text for either side ("you chose" vs "the opponent chose"; Spanish needed
real verb-conjugation swaps, not just pronoun substitution, e.g. `tenías`/`tenía`).
`playOpponentTurn` now records the same `{kBefore, TBefore, dice, actionsAvailable,
actionChosen, continued, resultingK, resultingT}` shape per roll the player's own
`recordDecision` does, so the opponent gets graded by the exact same table. `runOpponentTurn`
is now `async`, animating each roll (`renderDice` + a 1.5s pace between roll and decision
reveal) with a persistent "Skip animation" control that also remembers the choice in a plain
JS variable for the rest of the session (never `localStorage`, per this site's own no-storage
commitment) and a `state.turnInProgress` re-entrancy guard. The opponent's dice render at 72%
scale, shifted up, via a `.dice-row.opponent-row` CSS class toggled in `renderDice` based on
`state.turnOwner`, measured via bounding box (309×146 vs 222×105, correctly smaller and
higher) since the visual difference alone was hard to judge from a screenshot. Grouped banked
dice: a new `decomposeAction()` parses a chosen action's label back into its separate scoring
groups (e.g. "straight 1–5 + one 5" -> the 500 group and the 50 group, never merged) using the
same per-face value rules that built the label in the first place, rendered as chips below the
table scene for both sides, reset at each side's turn start. All verified via Playwright
across multiple simulated rounds on all four pages: zero JS errors, zero external requests,
correct score tracking through busts and banks.

---

## Phase 4: Separate background from character art

**Depends on:** nothing. **Unlocks:** Phase 4b.

The table scene is currently one baked-together photo (soldier + village flattened into a
single image). Splitting it into a reusable background layer plus a swappable character
layer is what makes per-opponent art viable at all.

**How:**
- One shared background image, reused across every opponent.
- One transparent-background character portrait per opponent, composited as a separate
  layered element (same flood-fill transparency technique already used for the dice cup).
- Reference assets already on disk for this: `..._Backgound.jpeg` (background only),
  `..._soldier-only.jpeg`, `..._priest.jpeg`. May need the same transparency cleanup pass if
  their edges aren't already clean.

---

## Phase 4b: Per-opponent character art

**Depends on:** Phase 4. **Status:** explicitly "not now."

Each opponent persona (Scholar, Priest, Drunkard, Jester, Watchman, Quartermaster) gets its
own portrait instead of sharing one soldier image.

**How:** map the already-available portraits to their matching personas. All six are now on
disk and ready to use, nothing left to source:
- `Downloads/Scholar.png`: The Scholar
- `Downloads/Drunk.png`: The Drunkard
- `Downloads/Jester.png`: The Jester
- `Downloads/QuarterMaster.png`: The Quartermaster
- `..._priest.jpeg`: The Priest
- `..._soldier-only.jpeg`: generic/fallback, or The Watchman

All six available portraits already have clean transparent backgrounds, so no flood-fill
cleanup pass is needed for those (unlike the background-only and soldier-only assets noted in
Phase 4, which may still need it). Phase 4b is now asset-complete; only Phase 4's
background/character split stands between this and being implemented.

**Implemented (2026-10-10), both phases together:** the four persona PNGs (Scholar, Drunk,
Jester, QuarterMaster) really did already have clean alpha transparency (verified: 80-84%
transparent pixels, no fringing). The soldier-only and priest JPEGs did not (plain JPEG, no
alpha at all, contrary to what this roadmap entry claimed): flood-filled via a
border-connected near-white region mask (numpy + `scipy.ndimage.label`), verified clean on a
checkerboard test backdrop. All six resized to the background's resolution (1100x821, so they
align with it with zero positioning math needed) and palette-quantized; total 607KB for all
six, too heavy to embed all at once, so they ship as real files under `assets/characters/`
and load via a genuine same-origin runtime request (`updateCharacterLayer()` in
`game.{en,es}.js`, hooked into the existing opponent-selection code path), exactly the
lazy-loading behavior Phase 1b's own notes anticipated for this asset type. The baked-together
background+soldier photo is replaced by a real background-only image (freshly generated, not
the old composite) plus a `.character-layer` div stacked between it and the dice/score-box
layers via z-index. `about.html`/`about.es.html` updated to disclose the one same-origin image
request this adds, rather than leaving the "zero network requests" claim to drift from
reality. Verified via Playwright: all six portraits load with zero failed requests and zero
external domains, across all four pages, with correct visual alignment.

Also fixed in the course of this: `build.py` wasn't actually reading `assets/style.css` or
`build/templates/game.{en,es}.js`, despite both existing on disk since the original Phase 1b
work. The build read literal CSS/JS baked directly into the two HTML templates instead, so
those two "extracted" files were silent dead weight, any edit to them had zero effect. Fixed
by wiring real `{{CSS}}` and `{{GAME_JS}}` placeholders through `build.py`, so they're now the
actual source of truth they were always meant to be.

---

## Phase 5: Page-weight optimization

**Depends on:** Phase 2, for one specific lever. **Current state:** 1.1MB+ per page.

Attack the actual thing making the page heavy: embedded art and font, not generic page
bloat.

**How:**
- Ship only the dice style chosen in Phase 2 (realistic), not both sprite sets. Measured:
  dropping the unused pixel-art set alone removes ~147KB raw, ~13% of the current page
  weight, the single biggest lever here, now that Phase 2 has actually been decided.
- Re-compress the largest embedded images, starting with the realistic dice set itself
  (~381KB raw, 44.5% of the page) and the background scene: realistic's photographic
  shading and the AI-generated background are the more compressible assets, versus
  pixel-art's already-flat colors which compress less.
- Subset the embedded pixel font to the glyphs actually used instead of the full character
  set.
- Measure with real before/after file sizes, not estimates.

**Implemented (2026-10-10):** all three levers, measured. Realistic dice: 381KB raw across 24
PNGs reduced to 75KB via 128-color palette quantization (`Image.quantize`, `FASTOCTREE`);
checked side-by-side at both 84px (actual display size) and 168px (2x/retina) and found no
visible difference. Background JPEG: 175KB reduced to 101KB at quality 55 (the AI-generated
pixel-art-style scene compresses unusually well; it stayed visually identical even at quality
25 in testing, but 55 was kept as a safety margin rather than riding the edge). Pixel font:
30KB reduced to 7.6KB by subsetting to the exact character set used across both languages'
templates and game logic (`pyftsubset`), verified visually (Spanish accented characters
render correctly). Combined with Phase 2's pixel-art-sprite removal, each shipped page went
from ~1.1MB (session start) to ~416KB, a 62% reduction. Verified via Playwright after each
step: dice render, zero JS errors, zero external requests, all four pages.

---

## Phase 6: 512KB Club branch

**Depends on:** Phase 5's techniques. **Scope:** separate branch, not main.

An honest attempt at the club's threshold, kept off main because getting there needs real
cuts (almost certainly the photo-style dice, the embedded custom font, and a much simpler
background), not just the tuning Phase 5 does for the live site.

**How:**
- New branch, not a goal for the live site's current visual identity.
- Verify any claimed result via the club's own stated method (a Cloudflare URL Scan of total
  uncompressed weight) before claiming it qualifies.

---

## Phase 7: Spanish version

**Depends on:** nothing outside itself. **Internal order:** architecture before content.

A full translation, not a machine-translate widget: that would reintroduce a third-party
script, which conflicts with the privacy commitment.

**How:**
1. Decide the storage approach first: separate pre-translated static files (e.g.
   `play_dice.es.html`) with a plain language-switcher link, with translatable strings
   factored out of the shared HTML/JS/CSS structure so language-independent assets (art,
   font) aren't duplicated per language.
2. Then translate: a substantial job on its own, covering every embedded UI string in the
   game plus the full report prose.
3. Add `hreflang` alternate tags once both versions exist.

---

## Phase 8: Cross-device & browser testing practice

**Depends on:** nothing. **Why early:** this exact gap already caused a real mobile bug.

The mobile score-overflow bug (a stale CSS selector that silently stopped applying) shipped
and reached a real phone before being caught. Worth fixing the practice, not just that one
bug.

**How:**
- Research lightweight device/browser-matrix options (a real local device bank already
  partly exists; Playwright's multi-engine support is already in use locally; evaluate
  whether a hosted service's free tier adds enough over that).
- Apply as a standing check before every future visual change ships, starting with Phase 3's
  new rendering work, not as a one-time audit.
