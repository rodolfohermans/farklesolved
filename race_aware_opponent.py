"""
Investigate "race-aware" opponent strategies (continue/stop decisions that
account for the opponent's score, not just the active player's own turn),
and export a compact table for a new in-browser opponent persona built on
the EXACT solved policy from race_dp.py, not a hand-waved heuristic.

Three things get compared here:

  1. "Naive forum heuristic" -- the version actually cited online (Method.gg's
     KCD2 guide and similar): push hard while behind, bank quickly once ahead
     or even. Implemented literally and crudely on purpose, as the strawman
     baseline this task was explicitly told not to ship.

  2. "Hybrid exact" -- the design actually shipped: which DICE to bank each
     roll is chosen via the single-turn DP value table V (farkle_dp.py,
     already embedded on the page for the Scholar persona and the player's
     own coaching), since that choice is almost entirely about this turn's
     own prospects. Whether to CONTINUE after banking is chosen via the exact
     race-aware threshold, read from race_dp.py's solved U_all -- the actual
     opponent-score-dependent decision forums are (informally) describing.
     This needs only a compact per-(own_bucket, opp_bucket, dice_remaining)
     threshold table, not the full value-function surface.

  3. "Full exact" -- both the bank-which-dice choice AND the continue
     decision read from the exact race-aware value function U_all (mirrors
     race_compare.py's play_turn_race_aware). This is the true optimum; it's
     simulated here only to check how much the Hybrid design above gives up,
     not to ship (shipping it would require embedding the full U_all value
     surface, megabytes per target, instead of a small threshold table).

Run with `python3 race_aware_opponent.py export` to also write
assets/race-data.json (the compact table for G=4000, the site's default and
only currently-offered race-aware target).
"""

import json
import pickle
import random
import sys
import time
from pathlib import Path

import numpy as np

import farkle_dp
from farkle_dp import STEP as STEP1
from farkle_kcd import enumerate_actions
from race_dp import solve_race, STEP

G = 4000
SOLUTION_CACHE = Path(__file__).parent / "race_solution_g4000.pkl"


def roll(k):
    return tuple(random.randint(1, 6) for _ in range(k))


def get_or_solve():
    if SOLUTION_CACHE.exists():
        print(f"Loading cached race solution from {SOLUTION_CACHE}...")
        with open(SOLUTION_CACHE, "rb") as f:
            d = pickle.load(f)
        return d["F"], d["U_all"], d["N"], d["Nx"]
    print(f"Solving exact race DP for G={G} (no cache found, ~2-3 min)...")
    t0 = time.time()
    F, U_all, N, Nx = solve_race(G, verbose=True)
    print(f"Solved in {time.time()-t0:.1f}s.")
    with open(SOLUTION_CACHE, "wb") as f:
        pickle.dump({"F": F, "U_all": U_all, "N": N, "Nx": Nx, "G": G}, f)
    return F, U_all, N, Nx


# ------------------------------------------------------------- Policy 1: naive
def play_turn_naive_race_aware(my_score, opp_score, target):
    """Crude literal reading of the forum advice: push while behind (stop only
    when forced), bank immediately once ahead-or-tied. No magnitude awareness
    at all -- this is the strawman, not what gets shipped."""
    k, T = 6, 0
    while True:
        dice = roll(k)
        is_bust, actions = enumerate_actions(dice)
        if is_bust:
            return 0
        bc, val = max(actions, key=lambda a: a[1])
        k = 6 if bc == k else k - bc
        T += val
        if my_score + T >= target:
            return T
        behind = (my_score + T) < opp_score
        cont = behind  # push forever while behind; bank the instant not behind
        if not cont:
            return T


# ------------------------------------------------- Policy 2: hybrid (SHIPPED)
def play_turn_hybrid_exact(my_score, opp_score, target, V, U_all, N, Nx):
    """Bank-which-dice via single-turn V (turn-internal choice). Continue
    decision via the exact race-aware threshold for (i=my bucket, j=opp
    bucket, k=dice remaining). This is what race-data.json encodes."""
    i = min(my_score // STEP, Nx - 1)
    j = min(opp_score // STEP, Nx - 1)
    U = U_all[i]
    k, T = 6, 0
    while True:
        dice = roll(k)
        is_bust, actions = enumerate_actions(dice)
        if is_bust:
            return 0
        best_v, best = -1.0, None
        for bc, val in actions:
            kp = 6 if bc == k else k - bc
            idx = min((T + val) // STEP1, len(V[kp]) - 1)
            v = V[kp][idx]
            if v > best_v:
                best_v, best = v, (bc, val, kp)
        bc, val, kp = best
        T += val
        k = kp
        if my_score + T >= target:
            return T
        t_idx = min(T // STEP, N - 1)
        col = U[k][:, j]
        # Stop value at the CURRENT t_idx only (cheaper than the full-column
        # sweep race_compare.py's race_aware_threshold does, since we only
        # need one decision point here, not the whole threshold curve):
        z = min(i + t_idx, Nx - 1)
        win_now = (i + t_idx) >= (N - 1)
        sv = 1.0 if win_now else 1.0 - F_GLOBAL[j, z]
        cur_v = col[t_idx]
        cont = cur_v > sv + 1e-6
        if not cont:
            return T


# --------------------------------------------------- Policy 3: full exact
def play_turn_full_exact(my_score, opp_score, target, U_all, N, Nx):
    i = min(my_score // STEP, Nx - 1)
    j = min(opp_score // STEP, Nx - 1)
    U = U_all[i]
    k, t_idx = 6, 0
    while True:
        dice = roll(k)
        is_bust, actions = enumerate_actions(dice)
        if is_bust:
            return 0
        best_v, best = -1.0, None
        for bc, val in actions:
            kp = 6 if bc == k else k - bc
            shift = val // STEP
            tp = min(t_idx + shift, N - 1)
            v = U[kp][tp, j]
            if v > best_v:
                best_v, best = v, (kp, tp)
        k, t_idx = best
        T = t_idx * STEP
        if my_score + T >= target:
            return T
        z = min(i + t_idx, Nx - 1)
        win_now = (i + t_idx) >= (N - 1)
        sv = 1.0 if win_now else 1.0 - F_GLOBAL[j, z]
        cur_v = U[k][t_idx, j]
        cont = cur_v > sv + 1e-6
        if not cont:
            return T


def play_turn_scholar(my_score, target, V):
    """The existing 'optimal' persona: score-blind single-turn DP, plus the
    universal win-now override."""
    k, T = 6, 0
    while True:
        dice = roll(k)
        is_bust, actions = enumerate_actions(dice)
        if is_bust:
            return 0
        best_v, best = -1.0, None
        for bc, val in actions:
            kp = 6 if bc == k else k - bc
            idx = min((T + val) // STEP1, len(V[kp]) - 1)
            v = V[kp][idx]
            if v > best_v:
                best_v, best = v, (bc, val, kp)
        bc, val, kp = best
        T += val
        k = kp
        if my_score + T >= target:
            return T
        idx = min(T // STEP1, len(V[k]) - 1)
        if not (V[k][idx] > T + 1e-6):
            return T


def race(policy_a, policy_b, target=G, max_turns=500):
    a = b = 0
    for _ in range(max_turns):
        a += policy_a(a, b)
        if a >= target:
            return "A"
        b += policy_b(b, a)
        if b >= target:
            return "B"
    return "DRAW"


if __name__ == "__main__":
    random.seed(99)
    F, U_all, N, Nx = get_or_solve()
    F_GLOBAL = F  # used by the module-level closures above

    farkle_dp.N_T = farkle_dp.T_MAX // STEP1 + 1
    print("Solving single-turn DP (for the Scholar baseline and hybrid's action choice)...")
    V, T_grid = farkle_dp.solve()

    N_RACE = 20_000

    print(f"\n=== Flavor comparison, race to {G}, {N_RACE} games each matchup, seat-balanced ===\n")

    def seat_balanced(name_a, fn_a, name_b, fn_b):
        wins_a = wins_b = draws = 0
        for n in range(N_RACE):
            if n % 2 == 0:
                w = race(fn_a, fn_b)
                wins_a += w == "A"
                wins_b += w == "B"
            else:
                w = race(fn_b, fn_a)
                wins_b += w == "A"
                wins_a += w == "B"
            draws += w == "DRAW"
        p = wins_a / N_RACE
        se = np.sqrt(p * (1 - p) / N_RACE)
        print(f"  {name_a:30s} vs {name_b:30s} -> {name_a} wins {p:.2%} +/- {1.96*se:.2%} (95% CI)")
        return p

    scholar = lambda my, opp: play_turn_scholar(my, G, V)
    naive = lambda my, opp: play_turn_naive_race_aware(my, opp, G)
    hybrid = lambda my, opp: play_turn_hybrid_exact(my, opp, G, V, U_all, N, Nx)
    full_exact = lambda my, opp: play_turn_full_exact(my, opp, G, U_all, N, Nx)

    print("-- Is the naive forum heuristic actually good, or a strawman? --")
    seat_balanced("naive-race-aware", naive, "Scholar", scholar)
    seat_balanced("full-exact-race-aware", full_exact, "naive-race-aware", naive)

    print("\n-- Does the hybrid (shipped) design give up much vs full exact? --")
    seat_balanced("full-exact-race-aware", full_exact, "hybrid-exact (shipped)", hybrid)

    print("\n-- Headline: shipped design vs the current best opponent (Scholar) --")
    seat_balanced("hybrid-exact (shipped)", hybrid, "Scholar", scholar)

    if len(sys.argv) > 1 and sys.argv[1] == "export":
        print("\nExporting compact race-aware threshold table for G=4000...")
        # thr[i][j][k] = highest t_idx at which continuing still beats stopping,
        # or 0 if stopping immediately is always at least as good (sentinel:
        # stored value 0 means "never continue"; stored value v>0 means
        # "continue while T <= (v-1)*STEP").
        thr = np.zeros((Nx, Nx, 7), dtype=np.uint8)  # k=1..6, index 0 unused
        idxg = np.arange(N)
        for i in range(Nx):
            U = U_all[i]
            for k in range(1, 7):
                col_all_j = U[k]  # shape (N, Nx)
                z_idx = np.minimum(i + idxg, N - 1)
                win_now = (z_idx == N - 1)
                for j in range(Nx):
                    gathered = F[j, np.minimum(z_idx, Nx - 1)]
                    stop_vals = np.where(win_now, 1.0, 1.0 - gathered)
                    col = col_all_j[:, j]
                    continuing = col > stop_vals + 1e-6
                    idxs = np.nonzero(continuing)[0]
                    thr[i, j, k] = (int(idxs[-1]) + 1) if len(idxs) else 0
            if i % 10 == 0:
                print(f"  exported row i={i}/{Nx}")
        packed = thr.tobytes()
        import base64
        b64 = base64.b64encode(packed).decode("ascii")
        out = {
            "G": G,
            "STEP": STEP,
            "Nx": Nx,
            "note": "thr[i*Nx*7 + j*7 + k] (k=1..6, index 0 unused), uint8: "
                    "0 = never continue; v>0 = continue while this-turn T <= (v-1)*STEP",
            "data_b64": b64,
        }
        out_path = Path(__file__).parent / "assets" / "race-data.json"
        out_path.write_text(json.dumps(out), encoding="utf-8")
        print(f"Wrote {out_path} ({out_path.stat().st_size:,} bytes, "
              f"{len(packed):,} raw bytes before base64)")
