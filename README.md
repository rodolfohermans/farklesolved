# farklesolved.com

**[farklesolved.com](https://farklesolved.com/)** ([en castellano](https://farklesolved.com/index.es.html)) is an exact, dynamic-programming-solved strategy for the dice minigame in *Kingdom Come: Deliverance* (the Farkle/Greed/Zilch family of "push your luck" dice games, using KCD's specific scoring table).

It is primarily a strategy reference and a practice tool: the point is to learn the exact optimal play and see your own decisions graded against it, not to be a game in its own right. It does turn out to be fun to play anyway.

This is an unofficial fan project. It is not affiliated with, endorsed by, or associated with Warhorse Studios or the publishers of *Kingdom Come: Deliverance* in any way.

## No tracking, no ads, lightweight

No analytics, no tracking pixels, no third-party scripts, no cookies, nothing that identifies you. This is checked, not just claimed: the About page documents a real audit, including captured browser network traffic, not just a source-code read-through.

Each page is a single self-contained file, about 490KB, comfortably inside the [512KB Club](https://512kb.club/)'s Blue tier. Everything, including the dice art, the background, and the custom font, is embedded in that one file; nothing else loads over the network except an opponent portrait fetched from this same site once you pick or change one.

## What's here

- **[Practice table](https://farklesolved.com/play_dice.html)**: play against a selectable opponent (six personas, each a different strategy), with turn-by-turn coaching graded against the exact optimal-stopping solution, not a heuristic.
- **[Strategy report](https://farklesolved.com/farkle_strategy_report.html)**: the full derivation, exact thresholds, a decision flowchart, and a cheat sheet, every numerical claim checked against independent Monte Carlo simulation. Start here if you just want the strategy, not the practice table.
- **[About / privacy audit](https://farklesolved.com/about.html)**: how this was built, what it does and does not do with your visit, and the documented audit backing that.
- A full Spanish translation of all three.

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

[CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/): free to share and adapt with attribution, for non-commercial use only. Not authorized for commercial use or resale.
