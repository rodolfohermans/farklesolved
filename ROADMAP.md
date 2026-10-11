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

**Implemented (2026-10-10), the two items still open:** keyboard/ARIA support on the dice
(`role="button"`, `tabindex="0"`, `aria-pressed`, a descriptive `aria-label`, and an Enter/Space
`keydown` handler sharing the same toggle logic as the click handler, both languages), and the
CSP meta tag (`default-src 'none'; img-src 'self' data:; font-src 'self' data:; style-src
'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'; base-uri 'none';
form-action 'none';`, on all seven pages: the four game pages, both about pages, and the
strategy report). `frame-ancestors` was tried first per the usual CSP boilerplate, then
dropped: browsers ignore it entirely when delivered via `<meta>` rather than an HTTP header
(confirmed via a real console warning, not assumed), and a directive that silently does
nothing is worse than no directive, since it implies protection that isn't there. Verified via
Playwright: zero CSP console violations across all four game pages during actual play
(including the same-origin character-portrait fetch under `img-src 'self'`), keyboard
Enter-key toggle confirmed working end to end (`aria-pressed` flips, `.held` class applied).

**Not implementable from a coding session:** `www.farklesolved.com` not resolving is a DNS
record missing at the domain registrar/DNS provider, not a code change; nothing in this repo
can fix it. Left for the user to add a `www` CNAME (or A/ALIAS, per whatever the apex record
currently uses) pointing at the same target as the bare domain.

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

**Findings (2026-10-10), premise revised after verifying against the real rules:** this
phase's "Cloudflare URL Scan" guess for the verification method was wrong; fetched the actual
current rules at 512kb.club. Real tiers: Green under 100KB, Orange under 250KB, Blue under
512KB, all uncompressed. Real stated method: Firefox's Network tab, "total size (not
transferred)", on the homepage. Phase 2 and Phase 5's weight work (done for other reasons,
not this one) happened to already bring index.html to ~437KB raw, comfortably inside the Blue
tier on its own. But measuring the actual homepage load (not just the HTML file's byte count)
surfaced a real separate bug: the default-selected opponent's portrait (The Jester, 119KB) was
being fetched automatically on idle page load, via `renderIdle()` calling
`updateCharacterLayer()`, pushing genuine total homepage weight to ~553KB, over the Blue
threshold. Fixed on main (not worth a separate branch for): `renderIdle()` now only hides the
character layer (`classList.remove('visible')`, no fetch) instead of loading a portrait before
a match has actually started; the fetch still happens, just deferred to `startMatch()`, which
is also exactly the "needs a genuine runtime fetch... because which portrait is needed can
change" design Phase 1b already called for. Verified via Playwright: idle page load now fires
exactly one request (the HTML document itself) on all four pages; the portrait request fires
only after "Start match" is clicked.

With that fixed, `index.html` measures 447,326 bytes (436.7 KiB) at idle load, under the 512KB
Blue tier threshold with real headroom. This was not the original goal (Blue tier was assumed
to need a separate, uglier branch with real visual cuts), so no separate branch was created.
Whether to actually submit to the club (a public PR to their `_data/sites.yml` plus a mailing
list patch, per their real submission process) is a judgment call for the user, not made here;
measuring and fixing the underlying weight bug stands on its own regardless of that decision.
Green or Orange tier would still need the cuts this phase originally anticipated (dropping the
photo-style dice and the custom font); not attempted, since Blue tier was the only threshold
actually at stake once the idle-load bug was fixed.

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

**Implemented (2026-10-10):** `build/test_pages.py` (`just test`), a standing smoke test
across every page (the 4 game pages plus both about pages and the strategy report), at both
a desktop and a 375x667 mobile viewport (the size class that caught the original bug), using
whichever Playwright browser engines are actually installed. Checked this environment
specifically: only Chromium is installed here, not Firefox or WebKit, so the roadmap's
"multi-engine support is already in use locally" line was optimistic, not actual, when this
was written. The script reports which engines ran and which were skipped rather than silently
claiming coverage that didn't happen, and prints the install command for the missing ones.
Evaluating a hosted cross-browser service is left for whenever Firefox/WebKit testing is
actually needed locally and isn't available. Every phase of this session's work (Phase 2
through Phase 4b) was checked this same way manually before this script existed; it now
codifies that practice as a real, repeatable command instead of ad hoc one-off scripts.

---

## Phase 9: Unicode die-face glyphs in the log text

This was requested early in the session that produced this roadmap ("replace the text that
says 'You roll [2, 5, 1, 2, 1, 5]' with Unicode die-face glyphs") but got dropped when
everything was consolidated into phases here: it never made it into any phase above, so it
sat unimplemented until the user noticed the game still showed bracketed numbers and asked
directly. Recorded here now specifically so a dropped item is visible and traceable instead
of silently vanishing a second time.

**Attempted, then reverted (2026-10-10).** First pass: added `DIE_GLYPH` (U+2680-U+2685, the
standard Unicode die-face block) and a `diceGlyphs(dice)` helper, replacing the bracketed-number
roll display, then extended the same idea to action labels ("three 5s" -> "three ⚄"). My own
verification of this was wrong twice over: I confirmed legibility by rendering the glyphs at
60px on an isolated test page, which doesn't reflect the site's real ~15px log text size or its
real font stack, and I later screenshotted the actual game believing I'd confirmed both broken
and (after a fix attempt) fixed, without re-running `just build` first, so at least one of those
checks was against a stale page.

When the user caught the glyphs still weren't rendering as dice, a focused independent review
(Fable 5, scoped to only this issue) corrected the diagnosis: it was never a missing-glyph or
font-fallback problem (DejaVu Sans genuinely has these glyphs, and Chromium's own per-character
font resolution, checked via `CSS.getPlatformFontsForNode`, confirmed it was actually selected
and used). The real problem is device pixel density: at standard 1x desktop scaling the glyphs'
internal pip detail is sub-pixel and unreadable; a size-sweep test showed legibility only
starting around 32-40px, far too large for inline log text. At 2x-3x (phones, Retina displays)
the same glyphs render cleanly. Since a large share of desktop visitors run at 1x, this is a
real cross-platform limitation, not an artifact of the sandboxed test environment, and no
practical font-size bump fixes it.

Reverted both the roll-line and action-label glyph changes back to plain numerals, keeping one
real improvement that came out of the attempt: the roll display now shows dice sorted (e.g.
"[1, 1, 2, 4, 4, 5]" instead of roll order), so pairs and triples are visually grouped, which
doesn't depend on glyph rendering at all. The `.log` font-size bump from this same work (0.86rem
to 0.94rem) also stands independently and was kept.

A same-origin inline `<img>` approach, reusing the site's own dice sprite PNGs instead of
relying on font glyph coverage, would sidestep this entirely and was noted as a sound future
option by the reviewer, scoped only to the roll line (never the tiny action-label contexts,
where even a 40px requirement is unworkable) and built with real DOM nodes rather than switching
`logLine()` to `innerHTML`. Not attempted here; recorded as a legitimate follow-up, not a
silent drop.

## Phase 10: Race-aware opponent ("The Tactician")

Requested 2026-10-11 after the opponent-strategy win-rate matrix and forum research (below)
surfaced a real gap: Method.gg's KCD2 guide and others independently recommend conditioning the
continue/bank decision on the live score gap ("push when behind, bank when ahead"), which is
exactly what `race_dp.py`'s exact race-to-target solve already proves optimal, but none of the
five existing opponent personas use it. All five only ever read the score-blind single-turn table
(`farkle_dp.py`) or simpler heuristics; the only score-awareness any of them has is the universal
"stop once this turn already secures the match" override.

**Investigated multiple flavors before implementing anything (explicit instruction: find a good
version, don't strawman it):**

1. **Naive forum heuristic**, implemented literally ("push while behind, bank the instant not
   behind," no magnitude awareness): loses badly to the Scholar, 26.7% win rate, seat-balanced.
   Confirmed strawman, not shipped. The failure mode: early in a race, being behind by one turn's
   worth of points is nearly meaningless, since both sides have many turns left; playing reckless
   the whole match on that signal is just worse banking, it ignores that the real exact policy's
   deviation from score-blind play is concentrated almost entirely near the endgame.
2. **Full exact** (bank-which-dice AND continue/stop both read from the solved race value
   function `U_all`, mirroring `race_compare.py`'s `play_turn_race_aware`): the true optimum, but
   would require embedding the full value-function surface (megabytes per target) to ship,
   ruled out on page-weight grounds alone.
3. **Hybrid exact (shipped)**: which dice to bank each roll stays on the single-turn DP table
   (same choice the Scholar already makes — this is almost entirely about the turn's own
   prospects); only the continue/stop decision reads the opponent's score, via a compact
   per-(own-score-bucket, opponent-score-bucket, dice-remaining) exact threshold table derived
   from `U_all`. Verified by simulation to be statistically indistinguishable from the full exact
   policy head-to-head (49.87% vs 50.13% over 20,000 games) — the simplification costs nothing
   measurable, at a fraction of the data size (44.8KB raw / ~60KB base64 vs megabytes).
4. **A zero-table calibrated heuristic was also explored and rejected.** Queried the exact
   threshold table directly across representative (own score, opponent score, dice-remaining)
   states before attempting any formula. Found the opponent-dependence is highly non-uniform (huge
   at low dice-remaining/high bust-risk states, often negligible at a fresh 6-dice roll regardless
   of score gap) and NOT reducible to a function of the score gap alone (sharp, nonlinear jumps at
   specific gap values, not a smooth relationship) — see `race_aware_opponent.py`'s exploratory
   output. A hand-tuned formula would itself need real iterative calibration to avoid becoming a
   second strawman, for an already-modest prize (next point): decided not worth it, shipped the
   table-based hybrid instead.

**Headline result**: the shipped Tactician beats the Scholar 52.3% of the time, seat-balanced —
a real, measured, but modest edge, not a dramatic one. This is the correct and expected size of
the effect, not a sign of a weak implementation: most of a race happens far from the target,
where score-blind and score-aware play agree almost every turn.

**Scope limit, disclosed rather than silently approximated**: the exact threshold table is solved
and embedded only for the site's default 4,000-point target (the target already used for this
site's other published race-DP statistic, the 55.71%/44.29% first-mover split). Embedding exact
tables for every preset target (1500/2000/4000/5000) plus arbitrary custom targets was rejected:
each target's table scales with the target itself (the 4,000 table alone is 44.8KB raw), and
`race_dp.py`'s solve itself takes ~2-3 minutes even in vectorized Python/numpy, nowhere near fast
enough to solve on-demand in the browser for a custom target. At any match target other than
4,000, the Tactician falls back to playing identically to the Scholar, and this is stated directly
in its selector description in the UI, not hidden.

**Page-weight impact**: measured before/after, not assumed. Game pages grew from ~434KB to
~508KB (headroom inside the 512KB Club's Blue tier shrank from comfortable to thin). `about.html`,
`about.es.html`, and `README.md`'s size claims were updated to the re-measured figures as part of
this change, per this project's standing practice of not leaving a stale measurement once the
underlying fact changes.

Named "The Tactician" rather than "The Gambler" (the obvious first choice) after noticing the
name mismatch: this persona is a cold, exact, score-tracking optimizer, the opposite of the
superstition/myth associations "Gambler" carries (gambler's fallacy, hot-hand fallacy). "Gambler"
was left open for a future myth-driven persona instead -- see Phase 12.

Portrait is a placeholder (`assets/characters/tactician.png`, plain text label, not real art) by
explicit agreement with the project owner, who will supply real art later on this feature branch.

Built on branch `feature/gambler-race-aware`, not master, by explicit instruction, pending that art.

## Phase 11 (future, not scheduled): Loaded-dice bias measurement

Raised 2026-10-11 while researching opponent strategies and other sites' dice-game content:
forum/guide discussion of this minigame is dominated by *loaded dice selection* (which of the
game's biased/trick dice to carry), not turn-by-turn play strategy, the thing farklesolved.com
actually solves. The site's model deliberately excludes loaded dice entirely (standard fair
6-sided dice only), which is correct for the exact single-turn and race DP as published, but
leaves an open question worth quantifying rather than just asserting is "probably small":

- How much does giving ONE side a biased/loaded die set shift the race win probability, holding
  both players' play strategy fixed?
- Does a strictly better play strategy (e.g. the exact race-aware policy, once implemented, or
  even just the Scholar) still beat a weaker strategy (e.g. Drunkard, Priest) when the weaker
  side is the one using loaded dice? i.e. how large a dice-bias advantage would it take to
  overcome a given strategy-skill gap?

Not implemented. Would need: a biased per-face roll distribution (not uniform 1/6 per face,
calibrated to whatever bias magnitude is being tested) substituted into the Monte Carlo roll
step of `farkle_sim.py`/`farkle_race.py`-style simulations (the exact DP tables themselves
assume fair dice and would need their own re-derivation to stay exact under bias, out of scope
for a quick measurement), run head-to-head at a few bias magnitudes and a few strategy-skill
gaps, and reported as win-rate shift vs. bias magnitude. This is a measurement/report question,
not necessarily a new opponent persona or site feature.

## Phase 12 (future, not scheduled): myth-driven opponent persona

Raised 2026-10-11 during the Phase 10 race-aware opponent work: the name "Gambler" evokes
classic gambling cognitive biases (gambler's fallacy, hot-hand fallacy, loss-chasing), which are
the mirror opposite of what Phase 10 actually built (a cold, exact, score-tracking optimizer).
Decided to name Phase 10's persona "The Tactician" instead and leave "Gambler" open for this.

A myth-driven persona would need to track history no current persona tracks at all (every
existing persona, including the Tactician, decides purely from the current k/T and, now, the
live score gap — none have memory of past rolls or past turns):

- **Gambler's fallacy**: push harder than justified on the turn right after a bust, believing
  a win is "due" — independent of the (unchanged) actual odds.
- **Hot-hand fallacy**: push further than optimal *within* a turn after several consecutive
  successful banks, as if recent success predicts the next roll.
- **Loss-chasing**: a superstitious cousin of the Tactician's race-awareness — overcorrects when
  behind (pushes past what the math justifies), rather than the exact right amount more.

Not implemented. Would need: per-match streak/history state (last turn's outcome, this turn's
consecutive successful-bank count) threaded into a new strategy branch in `playOpponentTurn`,
and its own portrait/name once scoped.

**Research-and-testing methodology (added 2026-10-11, don't skip straight to implementation):**
before writing any shipped persona, implement each fallacy mechanic above as its own standalone
simulatable policy (same pattern as `race_aware_opponent.py`'s three-way naive/hybrid/full-exact
comparison), then:

1. Sweep the fallacy's magnitude parameter (e.g. how much the gambler's-fallacy push intensifies
   per consecutive bust, or how many consecutive successful banks trigger the hot-hand escalation)
   across a range, not one guessed value — a too-weak setting is indistinguishable from an
   existing persona, a too-strong one degenerates into something the Drunkard already covers.
2. Simulate each candidate against the full existing roster (Scholar through Tactician) and
   measure whether its win-rate profile and, ideally, its qualitative behavior (bust rate,
   mean turn score, how its results differ turn-by-turn) are STATISTICALLY DISTINGUISHABLE from
   the nearest existing persona, not just a renamed Drunkard/Priest with extra steps.
3. Only ship the specific fallacy mechanic(s) that clear that bar. If gambler's-fallacy and
   hot-hand both turn out statistically indistinguishable from existing personas at every
   magnitude tried, that's a legitimate negative result worth recording, not a reason to force
   a persona into existence anyway.
4. This mirrors the Phase 10 lesson directly: the "naive race-aware" heuristic was tested and
   found to be a strawman (26.7% vs Scholar) before anything was shipped; the same discipline
   applies here, given these are explicitly *irrational* mechanics being deliberately added, not
   mathematically-grounded ones like Phase 10's.

**Findings (2026-10-12, research code only -- `gambler_fallacies.py` -- nothing wired into the
game):** all baseline action-choices are the Quartermaster's (bank the single highest-value
combo, no DP lookahead), isolating each mechanic's effect to the continue/stop call. Results at
target 4,000, seat-balanced, against the full Scholar-through-Priest roster:

- **Gambler's fallacy** (push harder only on the turn right after a bust): stays statistically
  indistinguishable from the Quartermaster across the ENTIRE magnitude range tested, 0% to 300%
  threshold inflation (nearest-persona sum-sq distance 0.0003-0.0012, only drifting slightly
  toward the Watchman at the extreme 300% setting). **This is the predicted negative result**:
  the trigger (one single post-bust turn) is too rare (busts happen ~17-20% of turns) and too
  short-lived (resets immediately) to shift the overall profile much, no matter how strongly it
  pushes while active. As modeled, this mechanic does not clear the distinguishability bar. A
  stronger version (escalating with CONSECUTIVE busts, or a longer decay window after one) was
  not tested and is the obvious next thing to try before concluding gambler's fallacy can't work
  as a persona at all.
- **Hot-hand fallacy** (push further within a turn per consecutive successful bank): DOES clear
  the bar, clearly. At magnitude=1.0 the bust rate hits 66.3%, higher than every existing
  persona including the Drunkard (44%), driven by a genuinely different mechanism (escalating
  greed tied to this turn's own success, not a fixed dice-count cutoff). This is the strongest
  candidate of the three for an actual future persona.
- **Loss-chasing / "emotional reactivity"** (amplify the Tactician's exact race-threshold
  deviation by a multiplier past 1.0x): produces a striking, well-explained result rather than a
  smooth dial. exaggeration=1.0 reproduces the Tactician (50.98% vs Scholar); exaggeration=1.1 (a
  mere 10% overshoot) already drops to 41.6%, and it keeps falling sharply from there (28.4% by
  1.5x, worse than the Priest's own baseline by 4.0x). This isn't a modeling artifact: the exact
  race threshold is BY DEFINITION the indifference point where continuing and stopping have equal
  win probability, so any overshoot past it, in either direction, is stepping into objectively
  net-negative territory with no gentle buffer zone. A shippable "loss-chasing" persona would need
  a deliberately chosen exaggeration level (not "more is more superstitious"), since the failure
  mode is a cliff, not a slope.

**Verification pass (2026-10-12, same session, 5x the evidence):** re-ran with N_RACE 6,000->
30,000 and N_BEHAVIOR 15,000->75,000 (now the scripts' committed defaults), plus a finer
exaggeration sweep (1.0/1.1/1.2/1.3/1.4/1.5) at the same 5x scale to see the loss-chasing cliff's
actual shape instead of just its endpoints. All three conclusions above held with roughly half
the confidence-interval width (~0.4-0.6pp vs ~1.1-1.3pp): gambler's-fallacy stayed statistically
glued to the Quartermaster at every magnitude (nearest-persona distance 0.0000-0.0031, if
anything tighter than before); hot-hand's bust rate came back at 66.9% (vs 66.3%); the fine sweep
confirmed the cliff is immediate and sharp, not a sampling artifact of the original coarse
sweep: 51.5% (exag=1.0) -> 41.8% (1.1) -> 36.9% (1.2) -> 32.7% (1.3) -> 30.3% (1.4) -> 28.7% (1.5),
a ~9.7-point drop from just a 10% overshoot, reproducing the original run's 51.0%->41.6% step
almost exactly.

## Phase 13 (future, not scheduled): "The Elder" -- near-optimal play with misread dice

Raised 2026-10-11: a character with a near-optimal decision policy but a perceptual handicap
(poor eyesight), as opposed to every existing persona's flaws being purely behavioral/decision-
based. Researched and grounded in real perceptual psychology rather than invented arbitrarily:

- **Pip-misreading pairs.** Dice layouts aren't arbitrary: 3's layout is 2's diagonal pair plus
  one added center pip; 5 is 4's four corners plus one added center pip. Under blur/low acuity,
  that added center pip is exactly the low-contrast fine detail that disappears first, so 2<->3
  and 4<->5 are the well-grounded confusion pairs (same "add/remove one center pip" relationship
  in both cases). 6 is structurally different (two parallel columns, no center dot) rather than
  "5 plus something," so it's more robustly distinguishable; a 5<->6 confusion channel, if
  modeled at all, should be much rarer than 2<->3/4<->5, not equally likely.
- **1 is essentially never misread.** This follows from subitizing (Kaufman et al. 1949 and a
  large literature since): humans perceive 1-3 items instantly and accurately without counting;
  4+ requires actual serial counting, which is where acuity loss and fatigue cause errors. This
  also means 2 should misread less often than 3 does (2 is still within/at the edge of the
  subitizing range).
- **Missing a straight (1-5, 2-6, full 1-6) is a separate, unrelated mechanism** worth modeling
  independently: not a per-die misread but a failure to perform the extra integration step of
  scanning all 5-6 dice for a consecutive run. Closer to inattentional blindness (missing a
  fully-visible but unattended-to pattern) than to low acuity, and should be an independent
  probability, not derived from the pip-confusion model.
- **Decision: a new character, not layered onto the Drunkard.** The Drunkard already fully
  occupies the behavioral-flaw niche (poor stopping discipline); stacking a perceptual flaw onto
  it conflates two different phenomena and risks reading as piling impairments onto one trope.
  It would also silently change the Drunkard's already-measured behavior from the Phase 10
  win-rate matrix (opponent_strategy_matrix.py) without that matrix being re-run, an honesty
  problem this project takes seriously elsewhere. Proposed name: "The Elder" (age-related vision
  decline -- presbyopia/cataracts -- a sympathetic, extremely common, and distinct real
  phenomenon from the drinking angle already covered).

Requested design constraint: the misperception should mostly be invisible, surfacing only when
it would cause an illegal move, at which point it's revealed/corrected narratively. This was NOT
wired into the game in this session (explicitly deferred, first to keep the Phase 10 Tactician
work from being left half-wired, then by explicit instruction to keep this at the research/code
stage only). Research code was written and validated (`elder_perception.py`); the design below
reflects what it actually implements, not just what was proposed:

1. A "perceived dice" array: sample a confusion draw per die (each face has a small chance of
   being misread as its confusion-paired neighbor; 1 essentially never misreads).
2. Run the decision logic (near-optimal, i.e. close to the Scholar/Tactician's action choice)
   against the PERCEIVED dice to pick an intended action.
3. Check whether that intended (bc, val) action is actually legal against the REAL dice (i.e.
   present in `enumerate_actions(real_dice)`'s output) -- not guaranteed, since the perceived
   combo may not exist on the real roll.
4. If illegal: reveal narratively (a log line, e.g. "He reaches for two 3s, squints -- only one
   was actually a 3.") and substitute the nearest legal action on the real dice, rather than
   silently proceeding on a fiction.
5. If legal (misperception happened not to change the outcome): proceed silently, no reveal.
6. Independently, with some probability, drop straight-based actions from the considered action
   set entirely (the inattention mechanic), regardless of whether any pip-misread occurred.

One consequence of this design worth stating explicitly: the running turn total never actually
diverges from reality for more than a single roll, since every reveal re-syncs it immediately.
The lasting cost of the handicap therefore comes entirely from misreads that happen to ALSO be
legal on the true dice (so nothing reveals them) but weren't the objectively best choice -- not
from the illegal-and-caught case, which self-corrects to the same decision the Scholar would make.

**Findings (2026-10-12, research code only -- `elder_perception.py` -- nothing wired into the
game):** both mechanisms produce smooth, well-behaved, independently tunable cost curves (no
instability, unlike the Gambler's loss-chasing cliff above), making either a plausible difficulty
knob. Win rate measured seat-balanced against the Scholar at target 4,000:

- **Pip-confusion alone** (p_lose swept 0 to 0.25, p_gain fixed at p_lose/3, per the grounded
  "losing a detail is more likely than hallucinating one" asymmetry): win rate vs Scholar falls
  smoothly from 45.5% to 32.9%, bust rate rises from 20.2% to 29.5%, and the reveal rate (how
  often a misread is actually caught as an illegal move) rises from 0% to 21.3% -- exactly the
  expected shape, more confusion means more frequent, more consequential mistakes, some of which
  get self-corrected and some of which don't.
- **Straight-miss alone** (p_lose fixed at a moderate 0.08, p_miss_straight swept 0 to 1.0): a
  separate, smaller but real cost, win rate falling from 44.2% to 33.0% over the full range.
- Sample caught mistakes read as intended, e.g. a true `(6,4,4,5,3,3)` misperceived as
  `(6,4,4,4,3,3)` (one 5 misread as a 4), intending to bank three 4s for 400 -- illegal on the
  real dice, correctly caught and corrected to the only real legal move (banking the 5 alone).

**Verification pass (2026-10-12, same session, 5x the evidence):** re-ran with N_BEHAVIOR 15,000->
75,000 and N_RACE 10,000->50,000 (now the script's committed defaults). Both curves reproduced
closely and stayed monotonic and smooth (confidence intervals tightened from ~0.9-1.0pp to
~0.4pp): pip-confusion win rate vs Scholar 46.4%->32.9% (vs the original 45.5%->32.9%, same
endpoints within noise), reveal rate 0%->20.7% (vs 0%->21.3%); straight-miss-alone win rate
44.4%->33.5% (vs the original 44.2%->33.0%). No instability or non-monotonicity appeared at the
larger sample size that the smaller run's confidence intervals could have been masking.

---
