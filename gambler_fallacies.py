"""
Research code for a possible future "Gambler" persona (ROADMAP.md Phase 12),
built on real gambling cognitive biases rather than invented behavior:

  - Gambler's fallacy: push harder than usual on the turn right after a bust,
    believing a win is "due" -- independent of the (unchanged) actual odds.
  - Hot-hand fallacy: push further than usual *within* a turn after several
    consecutive successful banks, as if recent success predicts the next roll.
  - Loss-chasing: an irrational, exaggerated cousin of the Tactician's
    race-awareness -- overcorrects when behind, pushing PAST what the exact
    math (race_dp.py) justifies, rather than the exact right amount more.

None of these are wired into the game yet (explicitly deferred). This script
only simulates each mechanic at a sweep of magnitudes, against the existing
roster, to find out which (if any) produce a behavioral signature that is
statistically distinguishable from the nearest existing persona -- per the
methodology this task was explicitly given: don't ship a fallacy that turns
out to just be a reskinned Drunkard or Priest with extra steps.

All three mechanics share the same baseline action-choice as the Quartermaster
(bank the single highest-value combo each roll) -- a "Gambler" character is
not portrayed as doing lookahead on which dice to keep, only as reasoning
(fallaciously) about whether to keep pushing. This isolates the fallacy's
effect to the continue/stop decision, the one actual behavioral difference
from the existing roster.
"""

import pickle
import random
from pathlib import Path

import numpy as np

import farkle_dp
from farkle_dp import STEP as STEP1
from farkle_kcd import enumerate_actions
from race_dp import STEP

G = 4000
SOLUTION_CACHE = Path(__file__).parent / "race_solution_g4000.pkl"


def roll(k):
    return tuple(random.randint(1, 6) for _ in range(k))


def load_race_solution():
    if not SOLUTION_CACHE.exists():
        raise SystemExit(
            f"{SOLUTION_CACHE} not found -- run `python3 race_aware_opponent.py export` "
            "first to solve and cache it (this script reuses that cache, ~2-3 min to build)."
        )
    with open(SOLUTION_CACHE, "rb") as f:
        d = pickle.load(f)
    return d["F"], d["U_all"], d["N"], d["Nx"]


def exact_race_threshold(F, U_all, N, Nx, i, j, k):
    U = U_all[i][k]
    col = U[:, j]
    idxg = np.arange(N)
    z = np.minimum(i + idxg, Nx - 1)
    win_now = (i + idxg) >= (N - 1)
    stop_vals = np.where(win_now, 1.0, 1.0 - F[j, z])
    continuing = col > stop_vals + 1e-6
    idxs = np.nonzero(continuing)[0]
    return int(idxs[-1]) * STEP if len(idxs) else -1


# --------------------------------------------------------------- Baselines
def play_turn_quartermaster(target, my_score, thresholds_map):
    k, T = 6, 0
    while True:
        dice = roll(k)
        is_bust, actions = enumerate_actions(dice)
        if is_bust:
            return 0, True
        bc, val = max(actions, key=lambda a: a[1])
        k = 6 if bc == k else k - bc
        T += val
        if my_score + T >= target:
            return T, False
        if T > thresholds_map[k]:
            return T, False


def play_turn_scholar(target, my_score, V):
    k, T = 6, 0
    while True:
        dice = roll(k)
        is_bust, actions = enumerate_actions(dice)
        if is_bust:
            return 0, True
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
            return T, False
        idx = min(T // STEP1, len(V[k]) - 1)
        if not (V[k][idx] > T + 1e-6):
            return T, False


def play_turn_stop_k(target, my_score, min_dice):
    k, T = 6, 0
    while True:
        dice = roll(k)
        is_bust, actions = enumerate_actions(dice)
        if is_bust:
            return 0, True
        bc, val = max(actions, key=lambda a: a[1])
        k = 6 if bc == k else k - bc
        T += val
        if my_score + T >= target:
            return T, False
        if k < min_dice:
            return T, False


def play_turn_firstscore(target, my_score):
    k, T = 6, 0
    dice = roll(k)
    is_bust, actions = enumerate_actions(dice)
    if is_bust:
        return 0, True
    bc, val = max(actions, key=lambda a: a[1])
    T += val
    return T, False


# --------------------------------------------------------- Fallacy policies
class GamblersFallacyPolicy:
    """Stateful across one match's turns: pushes harder than the Quartermaster
    only on the turn right after a bust. magnitude=0.0 is identical to the
    Quartermaster (no fallacy effect at all); call .reset() between matches."""

    def __init__(self, thresholds_map, magnitude):
        self.thresholds_map = thresholds_map
        self.magnitude = magnitude
        self.last_busted = False

    def reset(self):
        self.last_busted = False

    def __call__(self, my_score, opp_score, target=G):
        k, T = 6, 0
        boosted = self.last_busted
        while True:
            dice = roll(k)
            is_bust, actions = enumerate_actions(dice)
            if is_bust:
                self.last_busted = True
                return 0, True
            bc, val = max(actions, key=lambda a: a[1])
            k = 6 if bc == k else k - bc
            T += val
            if my_score + T >= target:
                self.last_busted = False
                return T, False
            th = self.thresholds_map[k] * (1 + self.magnitude) if boosted else self.thresholds_map[k]
            if T > th:
                self.last_busted = False
                return T, False


def play_turn_hot_hand(target, my_score, thresholds_map, magnitude):
    """magnitude: fractional threshold inflation PER consecutive successful
    bank this turn (0.0 = identical to Quartermaster)."""
    k, T = 6, 0
    streak = 0
    while True:
        dice = roll(k)
        is_bust, actions = enumerate_actions(dice)
        if is_bust:
            return 0, True
        bc, val = max(actions, key=lambda a: a[1])
        k = 6 if bc == k else k - bc
        T += val
        streak += 1
        if my_score + T >= target:
            return T, False
        th = thresholds_map[k] * (1 + magnitude * streak)
        if T > th:
            return T, False


def play_turn_loss_chasing(target, my_score, opp_score, V, thresholds_map, F, U_all, N, Nx, exaggeration):
    """Same hybrid design as the Tactician (bank-which-dice via the
    score-blind V table), but the continue threshold is the Scholar's blind
    threshold shifted toward the exact race-aware threshold by `exaggeration`
    times the gap between them, instead of exactly 1x: shifted = blind +
    exaggeration*(exact - blind). exaggeration=0 reproduces the Scholar
    exactly; =1 reproduces the Tactician exactly; >1 overshoots PAST the
    exact threshold in whichever direction the race-aware signal already
    points (further when it says push harder, further still when it says
    play safer) -- an "emotionally reactive" overcorrection in general, of
    which loss-chasing (overreacting specifically while behind) is the most
    recognizable special case, not the only state where this fires."""
    i = min(my_score // STEP, Nx - 1)
    j = min(opp_score // STEP, Nx - 1)
    k, T = 6, 0
    while True:
        dice = roll(k)
        is_bust, actions = enumerate_actions(dice)
        if is_bust:
            return 0, True
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
            return T, False
        blind_th = thresholds_map[k]
        exact_th = max(exact_race_threshold(F, U_all, N, Nx, i, j, k), 0)
        shifted_th = blind_th + exaggeration * (exact_th - blind_th)
        if T > shifted_th:
            return T, False


def race(policy_a, policy_b, target=G, max_turns=500):
    a = b = 0
    for _ in range(max_turns):
        pa, _ = policy_a(a, b)
        a += pa
        if a >= target:
            return "A"
        pb, _ = policy_b(b, a)
        b += pb
        if b >= target:
            return "B"
    return "DRAW"


def seat_balanced_winrate(fn_a, fn_b, n):
    wins_a = 0
    for i in range(n):
        if i % 2 == 0:
            w = race(fn_a, fn_b)
            wins_a += w == "A"
        else:
            w = race(fn_b, fn_a)
            wins_a += w == "B"
    p = wins_a / n
    se = np.sqrt(p * (1 - p) / n)
    return p, se


def behavior_stats(play_fn, n=20_000):
    pts = []
    busts = 0
    for _ in range(n):
        p, b = play_fn()
        pts.append(p)
        busts += b
    arr = np.array(pts)
    return {
        "mean": arr.mean(),
        "bust_rate": busts / n,
        "p90": float(np.percentile(arr, 90)),
    }


def race_with_reset(fn_a, fn_b, n, target=G):
    """Seat-balanced win rate, resetting any .reset() the policies expose
    (stateful ones like GamblersFallacyPolicy) at the start of every match."""
    wins_a = 0
    for i in range(n):
        if hasattr(fn_a, "reset"):
            fn_a.reset()
        if hasattr(fn_b, "reset"):
            fn_b.reset()
        if i % 2 == 0:
            w = race(fn_a, fn_b, target=target)
            wins_a += w == "A"
        else:
            w = race(fn_b, fn_a, target=target)
            wins_a += w == "B"
    p = wins_a / n
    se = np.sqrt(p * (1 - p) / n)
    return p, se


def nearest_roster_match(candidate_winrates, roster_matrix_row):
    """candidate_winrates / roster_matrix_row: dict {opp_name: (p, se)}.
    Returns the roster member whose own win-rate vector vs the same roster
    is closest (sum of squared differences), to check whether a candidate's
    whole behavioral profile just reproduces an existing persona."""
    best_name, best_dist = None, float("inf")
    for name, row in roster_matrix_row.items():
        dist = sum((candidate_winrates[opp][0] - row[opp][0]) ** 2 for opp in candidate_winrates)
        if dist < best_dist:
            best_name, best_dist = name, dist
    return best_name, best_dist


if __name__ == "__main__":
    random.seed(20261012)
    F, U_all, N, Nx = load_race_solution()
    farkle_dp.N_T = farkle_dp.T_MAX // STEP1 + 1
    print("Solving single-turn DP...")
    V, T_grid = farkle_dp.solve()
    th = farkle_dp.thresholds(V, T_grid)

    ROSTER = {
        "Scholar": lambda my, opp: play_turn_scholar(G, my, V),
        "Quartermaster": lambda my, opp: play_turn_quartermaster(G, my, th),
        "Watchman": lambda my, opp: play_turn_stop_k(G, my, 3),
        "Drunkard": lambda my, opp: play_turn_stop_k(G, my, 2),
        "Priest": lambda my, opp: play_turn_firstscore(G, my),
    }

    N_RACE = 30_000
    N_BEHAVIOR = 75_000

    print(f"\n=== Baseline behavior stats (standalone turns, n={N_BEHAVIOR}) ===")
    for name, fn in ROSTER.items():
        stats = behavior_stats(lambda fn=fn: fn(0, 0), n=N_BEHAVIOR)
        print(f"  {name:15s} mean={stats['mean']:7.1f}  bust_rate={stats['bust_rate']:.2%}  p90={stats['p90']:6.0f}")

    print("\nBuilding roster-vs-roster reference matrix (for distinguishability checks)...")
    roster_matrix = {}
    for name_a, fn_a in ROSTER.items():
        roster_matrix[name_a] = {}
        for name_b, fn_b in ROSTER.items():
            if name_a == name_b:
                roster_matrix[name_a][name_b] = (0.5, 0.0)
                continue
            roster_matrix[name_a][name_b] = race_with_reset(fn_a, fn_b, N_RACE)

    print("\n=== Gambler's fallacy: sweep magnitude ===")
    for magnitude in [0.0, 0.3, 0.75, 1.5, 3.0]:
        probe = GamblersFallacyPolicy(th, magnitude)

        def gf_standalone_turn(probe=probe):
            probe.reset()
            return probe(0, 0)

        stats = behavior_stats(gf_standalone_turn, n=N_BEHAVIOR)
        print(f"\n  magnitude={magnitude}: mean={stats['mean']:7.1f}  bust_rate={stats['bust_rate']:.2%}  p90={stats['p90']:6.0f}")
        policy = GamblersFallacyPolicy(th, magnitude)
        winrates = {}
        for opp_name, opp_fn in ROSTER.items():
            p, se = race_with_reset(policy, opp_fn, N_RACE)
            winrates[opp_name] = (p, se)
            print(f"    vs {opp_name:15s} -> wins {p:.2%} +/- {1.96*se:.2%}")
        nearest, dist = nearest_roster_match(winrates, roster_matrix)
        print(f"    nearest existing persona by win-rate profile: {nearest} (sum-sq dist={dist:.4f})")

    print("\n=== Hot-hand fallacy: sweep magnitude ===")
    for magnitude in [0.0, 0.15, 0.4, 1.0]:
        hh_fn = lambda my, opp, magnitude=magnitude: play_turn_hot_hand(G, my, th, magnitude)
        stats = behavior_stats(lambda fn=hh_fn: fn(0, 0), n=N_BEHAVIOR)
        print(f"\n  magnitude={magnitude}: mean={stats['mean']:7.1f}  bust_rate={stats['bust_rate']:.2%}  p90={stats['p90']:6.0f}")
        winrates = {}
        for opp_name, opp_fn in ROSTER.items():
            p, se = race_with_reset(hh_fn, opp_fn, N_RACE)
            winrates[opp_name] = (p, se)
            print(f"    vs {opp_name:15s} -> wins {p:.2%} +/- {1.96*se:.2%}")
        nearest, dist = nearest_roster_match(winrates, roster_matrix)
        print(f"    nearest existing persona by win-rate profile: {nearest} (sum-sq dist={dist:.4f})")

    print("\n=== Loss-chasing / emotional-reactivity: sweep exaggeration ===")
    for exaggeration in [0.0, 1.0, 1.5, 2.5, 4.0]:
        lc_fn = lambda my, opp, exaggeration=exaggeration: play_turn_loss_chasing(
            G, my, opp, V, th, F, U_all, N, Nx, exaggeration
        )
        stats = behavior_stats(lambda fn=lc_fn: fn(0, 0), n=N_BEHAVIOR)
        print(f"\n  exaggeration={exaggeration}: mean={stats['mean']:7.1f}  bust_rate={stats['bust_rate']:.2%}  p90={stats['p90']:6.0f}")
        winrates = {}
        for opp_name, opp_fn in ROSTER.items():
            p, se = race_with_reset(lc_fn, opp_fn, N_RACE)
            winrates[opp_name] = (p, se)
            print(f"    vs {opp_name:15s} -> wins {p:.2%} +/- {1.96*se:.2%}")
        nearest, dist = nearest_roster_match(winrates, roster_matrix)
        print(f"    nearest existing persona by win-rate profile: {nearest} (sum-sq dist={dist:.4f})")
