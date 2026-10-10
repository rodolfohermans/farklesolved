# Farkle / farklesolved.com — Development Roadmap

Everything raised across recent sessions, plus the full adversarial audit (independently
re-derived math, live network capture, source review), organized into phases with real
dependencies, not a flat backlog. Nothing below is started. Re-derive actual status from
`git log`, not this file, once work begins.

## Dependency overview

- **Tier 1 — no dependencies, start anytime:** Phase 0, Phase 1, Phase 2, Phase 8
- **Tier 2 — depends on Tier 1:** Phase 3 (needs 1, 2), Phase 4, Phase 5 (needs 2)
- **Tier 3 — depends on Tier 2:** Phase 4b (needs 4, deferred), Phase 6 (needs 5)
- **Independent track:** Phase 7 (Spanish version) — no hard dependency on the above

---

## Phase 0 — Correctness & honesty fixes

**Depends on:** nothing. **Why first:** cheap, independent, and this project's entire premise
is exactness.

The Fable audit found real defects, not nitpicks, in a site whose whole pitch is rigor. None
of these need a design decision; they're direct edits.

1. **Scholar opponent can decline a winning move** (`play_dice.html` ~432-460): give its
   action selection the same "check for a winning action first" logic the player's own
   grading already has at `winningAction` (~line 906), instead of pure race-blind
   `bestAction`.
2. **End-game-zone copy contradicts the project's own exact table**: rewrite flowchart step 5
   and `#endgameHint` (~line 580) to match what the cheat sheet already states correctly —
   bank early only when ahead with 1-3 dice left, never bank short otherwise.
3. **"Scholar" description overclaims** ("plays the mathematically optimal strategy, every
   time") — it's the race-blind policy, which loses ~5.6 points of win rate to the true
   optimum per the report's own numbers. Reword to something accurate.
4. **`about.html` factual error**: the "only external references are Wikipedia, Ko-fi,
   GitHub" line omits that page's own links to priva-c.org and 512kb.club — fix inside the
   section whose entire point is precision.
5. **`index.html` title overclaim**: retitle from bare "Farkle, Solved" to something scoped,
   e.g. "KCD Dice, Solved".
6. **Stale 55.90% headline figure** in the report, superseded by the N=50,000 rerun directly
   below it — reconcile.
7. **Two "verified against X" sentences citing artifacts not in the repo** (the 1e-9/1e-11
   reimplementation claim; the G=2,000 re-solve) — commit the artifacts or drop the
   sentences.
8. **Duplicate "commonly-cited default"** on both the 2,000 and 4,000 target options —
   remove, word each option on its own terms.
9. **Stale `test_play_dice.py`** queries UI that no longer exists and always times out — fix
   or delete, remove the matching dead `.actions` CSS.
10. **Academic grounding for the "solved" claim**: cite Allis (1994), *Searching for
    Solutions in Games and Artificial Intelligence*, for the solved-game taxonomy (this is a
    *strongly* solved game in that framing), and state the two-player-only scope explicitly
    rather than relying on it being merely never contradicted.
11. **First-mover-advantage tooltip** on "You always roll first" — pull the actual number
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

## Phase 1 — Rules-as-implemented reference

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
- Don't restate the race-blind/race-aware endgame caveat in detail here — footnote to the
  strategy report instead, to avoid the two documents drifting apart.

---

## Phase 2 — Pick one dice style

**Depends on:** nothing. **Unlocks:** simpler Phase 3 rendering, Phase 5 weight savings.

Realistic and pixel-art dice currently ship together behind a toggle. Deciding now, before
Phase 3 builds opponent dice rendering on top of both, avoids doing that rendering work
twice.

**How:**
- A judgment call on visual direction, not a technical one.
- Once decided: remove the losing sprite set from the shipped page entirely (not just hide
  the selector) — this is also one of Phase 5's concrete weight-reduction levers.

**Decision (2026-10-10): Realistic, provisional ("for now").** The case was presented with
real measured numbers rather than impressions: the realistic set is ~381KB raw versus the
pixel-art set's ~147KB, a 2.6x weight difference, worth 33% vs 13% of the page's total weight
respectively if the losing set is dropped. Weight favors pixel-art by a wide margin; visual
cohesion with the photographic table scene favors realistic (pixel-art dice visually sit on
top of that scene rather than in it); flat high-contrast pixel-art pips are more robust to
glare/low-end displays than realistic's softer shading; neither has a correctness or
mobile-legibility problem (both verified). Chose realistic, accepting the weight cost,
explicitly revisitable if page weight becomes a real problem later.

---

## Phase 3 — Opponent experience overhaul

**Depends on:** Phase 1 (terminology), benefits from Phase 2. **Status:** fully planned, zero
code written.

Opponent turns currently resolve instantly as a text log. The goal: watch the opponent
actually play, paced like a real turn, graded the same way the player is.

- **3a — Extract the review renderer.** Pull `showReview()`'s body into a parameterized
  `renderReview(decisions, preTurnScore, target, opts)`; keep a thin wrapper for the player
  so nothing visibly changes yet. Verify against current screenshots before moving on.
- **3b — Make the opponent's turn structured and analyzed (no animation yet).** Convert
  `playOpponentTurn` to async, capture the same `decisions` shape the player already produces
  (it already computes every field, just discards them into a text log), call
  `renderReview(...)` after the turn with the opponent's label swapped in. Highest-value
  single increment — shippable on its own even if animation never happens.
- **3c — Animate it.** Add `renderDice(dice, false)` calls plus `await sleep(~3000ms)`
  between roll, decision reveal, and bank/continue, fully automatic, no click required to
  advance. Add a persistent Skip control (and remember the choice) for anyone who'd rather
  not watch. Guard with a single `turnInProgress` flag so a stray click can't double-run a
  turn.
- **3d — Depth cue.** Render the opponent's dice smaller and higher in the scene than the
  player's, closer to the opponent's body, reinforcing the near/far framing the scorecards
  already imply.
- **3e — Grouped banked-dice display, for both sides.** Below the table image, show this
  turn's banked dice grouped by scoring choice with each group's point value — a 1-2-3-4-5
  straight is one group labeled "+500"; a lone 1 and a lone 5 are two separate groups, "+100"
  and "+50", never merged. Reuses the same decomposition `enumerateActions` already computes.

---

## Phase 4 — Separate background from character art

**Depends on:** nothing. **Unlocks:** Phase 4b.

The table scene is currently one baked-together photo (soldier + village flattened into a
single image). Splitting it into a reusable background layer plus a swappable character
layer is what makes per-opponent art viable at all.

**How:**
- One shared background image, reused across every opponent.
- One transparent-background character portrait per opponent, composited as a separate
  layered element (same flood-fill transparency technique already used for the dice cup).
- Reference assets already on disk for this: `..._Backgound.jpeg` (background only),
  `..._soldier-only.jpeg`, `..._priest.jpeg` — may need the same transparency cleanup pass if
  their edges aren't already clean.

---

## Phase 4b — Per-opponent character art

**Depends on:** Phase 4. **Status:** explicitly "not now."

Each opponent persona (Scholar, Priest, Drunkard, Jester, Watchman, Quartermaster) gets its
own portrait instead of sharing one soldier image.

**How:** map the already-available portraits to their matching personas. All six are now on
disk and ready to use, nothing left to source:
- `Downloads/Scholar.png` — The Scholar
- `Downloads/Drunk.png` — The Drunkard
- `Downloads/Jester.png` — The Jester
- `Downloads/QuarterMaster.png` — The Quartermaster
- `..._priest.jpeg` — The Priest
- `..._soldier-only.jpeg` — generic/fallback, or The Watchman

All six available portraits already have clean transparent backgrounds, so no flood-fill
cleanup pass is needed for those (unlike the background-only and soldier-only assets noted in
Phase 4, which may still need it). Phase 4b is now asset-complete; only Phase 4's
background/character split stands between this and being implemented.

---

## Phase 5 — Page-weight optimization

**Depends on:** Phase 2, for one specific lever. **Current state:** 1.1MB+ per page.

Attack the actual thing making the page heavy — embedded art and font — not generic page
bloat.

**How:**
- Ship only the dice style chosen in Phase 2 (realistic), not both sprite sets. Measured:
  dropping the unused pixel-art set alone removes ~147KB raw, ~13% of the current page
  weight, the single biggest lever here, now that Phase 2 has actually been decided.
- Re-compress the largest embedded images, starting with the realistic dice set itself
  (~381KB raw, 44.5% of the page) and the background scene — realistic's photographic
  shading and the AI-generated background are the more compressible assets, versus
  pixel-art's already-flat colors which compress less.
- Subset the embedded pixel font to the glyphs actually used instead of the full character
  set.
- Measure with real before/after file sizes, not estimates.

---

## Phase 6 — 512KB Club branch

**Depends on:** Phase 5's techniques. **Scope:** separate branch, not main.

An honest attempt at the club's threshold, kept off main because getting there needs real
cuts (almost certainly the photo-style dice, the embedded custom font, and a much simpler
background), not just the tuning Phase 5 does for the live site.

**How:**
- New branch, not a goal for the live site's current visual identity.
- Verify any claimed result via the club's own stated method (a Cloudflare URL Scan of total
  uncompressed weight) before claiming it qualifies.

---

## Phase 7 — Spanish version

**Depends on:** nothing outside itself. **Internal order:** architecture before content.

A full translation, not a machine-translate widget — that would reintroduce a third-party
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

## Phase 8 — Cross-device & browser testing practice

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
