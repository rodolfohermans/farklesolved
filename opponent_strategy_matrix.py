"""
Head-to-head win-rate matrix for the five practice-table opponent personas
(Scholar/optimal, Quartermaster/thresholds, Watchman/stop3, Drunkard/stop2,
Priest/firstscore), as they are ACTUALLY implemented in build/templates/game.en.js
(playOpponentTurn), not a re-derived approximation of them.

Ports that exact per-turn logic to Python (including the win-aware override
that lets a turn stop early once it has already banked enough to reach the
match target, which none of farkle_sim.py's/farkle_race.py's existing policy
functions include, since those don't take the match target as an input).

For each ordered pair (A, B) of personas, A always rolls first; this makes the
seat-order (first-mover) effect readable directly off the matrix instead of
averaging it away.
"""

import random
import time

import numpy as np

import farkle_dp
from farkle_dp import STEP
from farkle_kcd import enumerate_actions

farkle_dp.N_T = farkle_dp.T_MAX // STEP + 1

TARGET = 4000  # the site's default match target
N_GAMES = 50_000  # per ordered pair
MAX_TURNS = 500

PERSONAS = {
    "optimal": "Scholar",
    "thresholds": "Quartermaster",
    "stop3": "Watchman",
    "stop2": "Drunkard",
    "firstscore": "Priest",
}


def roll(k):
    return tuple(random.randint(1, 6) for _ in range(k))


def play_turn(strategy, pre_turn_score, target, V, thresholds_map):
    """Exact port of playOpponentTurn() in game.en.js. Returns points banked
    this turn (0 if bust)."""
    k, T = 6, 0
    while True:
        dice = roll(k)
        is_bust, actions = enumerate_actions(dice)
        if is_bust:
            return 0

        if strategy == "optimal":
            winning = next(
                (a for a in actions if pre_turn_score + T + a[1] >= target), None
            )
            if winning is not None:
                bc, val = winning
                k = 6 if bc == k else k - bc
                T += val
                cont = False
            else:
                best_v, best = -1.0, None
                for bc, val in actions:
                    kp = 6 if bc == k else k - bc
                    idx = min((T + val) // STEP, len(V[kp]) - 1)
                    v = V[kp][idx]
                    if v > best_v:
                        best_v, best = v, (bc, val, kp)
                bc, val, kp = best
                T += val
                k = kp
                idx = min(T // STEP, len(V[k]) - 1)
                cont = V[k][idx] > T + 1e-6
        elif strategy == "thresholds":
            bc, val = max(actions, key=lambda a: a[1])
            k = 6 if bc == k else k - bc
            T += val
            cont = T <= thresholds_map[k]
        elif strategy in ("stop3", "stop2"):
            bc, val = max(actions, key=lambda a: a[1])
            k = 6 if bc == k else k - bc
            T += val
            min_dice = 3 if strategy == "stop3" else 2
            cont = k >= min_dice
        else:  # firstscore
            bc, val = max(actions, key=lambda a: a[1])
            k = 6 if bc == k else k - bc
            T += val
            cont = False

        if cont and pre_turn_score + T >= target:
            cont = False
        if not cont:
            return T


def race(strat_a, strat_b, target, V, thresholds_map, max_turns=MAX_TURNS):
    """A always rolls first. Returns 'A', 'B', or 'DRAW' (turn cap hit)."""
    a = b = 0
    for _ in range(max_turns):
        a += play_turn(strat_a, a, target, V, thresholds_map)
        if a >= target:
            return "A"
        b += play_turn(strat_b, b, target, V, thresholds_map)
        if b >= target:
            return "B"
    return "DRAW"


if __name__ == "__main__":
    random.seed(20261011)
    print("Solving exact single-turn DP (same table the Scholar/'optimal' and")
    print("Quartermaster/'thresholds' personas read from in-browser)...")
    V, T_grid = farkle_dp.solve()
    th = farkle_dp.thresholds(V, T_grid)
    print("DP thresholds (continue-while-T<=X per dice remaining):", th)
    print(f"\nRace to {TARGET}, {N_GAMES} games per ordered pair, A always starts.\n")

    keys = list(PERSONAS.keys())
    win_a = {}  # (a,b) -> A win rate
    draw_rate = {}

    t0 = time.time()
    for a_key in keys:
        for b_key in keys:
            wins_a = wins_b = draws = 0
            for _ in range(N_GAMES):
                w = race(a_key, b_key, TARGET, V, th)
                if w == "A":
                    wins_a += 1
                elif w == "B":
                    wins_b += 1
                else:
                    draws += 1
            win_a[(a_key, b_key)] = wins_a / N_GAMES
            draw_rate[(a_key, b_key)] = draws / N_GAMES
            if draws:
                print(f"  [!] {draws} draws (hit {MAX_TURNS}-turn cap) in "
                      f"{PERSONAS[a_key]} vs {PERSONAS[b_key]}")
    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.1f}s ({N_GAMES * len(keys) * len(keys):,} games total).\n")

    # ------------------------------------------------------------------ Matrix
    name_w = max(len(n) for n in PERSONAS.values())
    header = " " * (name_w + 12) + "".join(f"{PERSONAS[k]:>14s}" for k in keys)
    print("Win rate of ROW persona (rolling first) vs COLUMN persona (rolling second):\n")
    print(header)
    for a_key in keys:
        row = f"{PERSONAS[a_key]:>{name_w}s} starts  "
        for b_key in keys:
            row += f"{win_a[(a_key, b_key)]:>13.1%} "
        print(row)

    # ------------------------------------------------------- First-mover edge
    print("\nFirst-mover edge in mirror matches (same persona both seats):")
    for k in keys:
        p = win_a[(k, k)]
        se = np.sqrt(p * (1 - p) / N_GAMES)
        print(f"  {PERSONAS[k]:>14s} vs itself: starter wins {p:.2%} +/- {1.96*se:.2%} "
              f"(95% CI)  [{p-0.5:+.2%} vs a 50/50 coin flip]")

    # ---------------------------------------------------- Overall seat-balanced ranking
    print("\nOverall win rate per persona, averaged across all opponents and both seats")
    print("(seat-balanced: each pairing counted once as starter, once as second):")
    overall = {}
    for k in keys:
        total_wins = 0.0
        total_games = 0
        for opp in keys:
            total_wins += win_a[(k, opp)] * N_GAMES          # k started
            total_wins += (1 - win_a[(opp, k)] - draw_rate[(opp, k)]) * N_GAMES  # k was second
            total_games += 2 * N_GAMES
        overall[k] = total_wins / total_games
    for k in sorted(keys, key=lambda x: -overall[x]):
        print(f"  {PERSONAS[k]:>14s}: {overall[k]:.2%}")
