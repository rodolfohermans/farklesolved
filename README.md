# farklesolved.com

**[farklesolved.com](https://farklesolved.com/)** ([en castellano](https://farklesolved.com/index.es.html)) is an exact, dynamic-programming-solved strategy for the dice minigame in *Kingdom Come: Deliverance* (the Farkle/Greed/Zilch family of "push your luck" dice games, using KCD's specific scoring table), plus a playable practice table that grades every decision you make against the exact solution.

This is an unofficial fan project. It is not affiliated with, endorsed by, or associated with Warhorse Studios or the publishers of *Kingdom Come: Deliverance* in any way.

## What's here

- **[Practice table](https://farklesolved.com/play_dice.html)**: play against a selectable opponent (six personas, each a different strategy), with turn-by-turn coaching graded against the exact optimal-stopping solution, not a heuristic.
- **[Strategy report](https://farklesolved.com/farkle_strategy_report.html)**: the full derivation, exact thresholds, a decision flowchart, and a cheat sheet, every numerical claim checked against independent Monte Carlo simulation.
- **[About / privacy audit](https://farklesolved.com/about.html)**: how this was built, what it does and does not do with your visit, and a documented audit (not just an assertion) backing the no-tracking claim.
- A full Spanish translation of all three.

No ads, no analytics, no tracking, no third-party scripts, no cookies. See the About page for the audit.

## How the math works

- `farkle_kcd.py`: the exact probability model and scoring rules for KCD's specific ruleset.
- `farkle_dp.py`: the exact optimal-stopping dynamic program for a single turn.
- `race_dp.py`: the exact solution of the full two-player race-to-target as a finite stochastic game (not just turn-level expected value), the harder problem that captures risk-seeking/risk-averse play near the finish line.
- `farkle_sim.py`, `farkle_race.py`, `race_compare.py`: Monte Carlo verification of both DP solutions and head-to-head simulated races between the exact policy and simpler heuristics.
- `farkle_report_data.py`: produces the tables used in the strategy report.

## Building the site

The shipped HTML pages are generated from real source files (templates, CSS, JS, individual sprite assets) rather than hand-edited directly; see `ROADMAP.md` for why.

```
just build   # assemble the shipped pages from assets/ + build/templates/
just test    # Playwright smoke test across every page, desktop + mobile viewports
```

## License

No license has been chosen yet for this repository. The source is public for anyone to read, verify, or challenge the math, but no reuse rights are granted. Ask if you want to use any of it.
