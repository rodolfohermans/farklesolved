"""
Monte Carlo verification of the DP, plus full two-player game simulation
comparing the optimal policy against simpler heuristic strategies.
"""

import random
import numpy as np
from farkle_kcd import enumerate_actions
import farkle_dp
from farkle_dp import STEP

farkle_dp.N_T = farkle_dp.T_MAX // STEP + 1


def roll(k):
    return tuple(random.randint(1, 6) for _ in range(k))


def play_turn_optimal(V, T_grid):
    """Play one turn using the exact DP-optimal policy. Returns points banked."""
    k = 6
    T = 0
    n_t = len(V[6])  # derive the clip bound from the actual table, not a module
    # global that some other caller could have left set to a different T_MAX.
    while True:
        dice = roll(k)
        is_bust, actions = enumerate_actions(dice)
        if is_bust:
            return 0
        best_val, best_action = -1, None
        for bc, val in actions:
            kp = 6 if bc == k else k - bc
            i = min((T + val) // STEP, n_t - 1)
            v = V[kp][i]
            if v > best_val:
                best_val = v
                best_action = (bc, val, kp)
        bc, val, kp = best_action
        T += val
        k = kp
        i = min(T // STEP, n_t - 1)
        if T >= V[k][i] - 1e-9:  # stopping at least as good as continuing
            return T


def play_turn_threshold(thresholds_map):
    """Simplified heuristic: bank ALL scoring dice always; stop once T exceeds
    thresholds_map[k] for the CURRENT dice-remaining count."""
    k = 6
    T = 0
    while True:
        dice = roll(k)
        is_bust, actions = enumerate_actions(dice)
        if is_bust:
            return 0
        bc, val = max(actions, key=lambda a: a[1])  # bank everything scoring
        T += val
        k = 6 if bc == k else k - bc
        if T > thresholds_map[k]:
            return T


def play_turn_naive_bank_first(max_rerolls=0):
    """Baseline: bank all scoring dice, stop as soon as you have ANY points
    (i.e. never push your luck). max_rerolls=0 means stop immediately after
    first successful scoring roll."""
    k = 6
    T = 0
    rerolls = 0
    while True:
        dice = roll(k)
        is_bust, actions = enumerate_actions(dice)
        if is_bust:
            return 0
        bc, val = max(actions, key=lambda a: a[1])
        T += val
        k = 6 if bc == k else k - bc
        if rerolls >= max_rerolls:
            return T
        rerolls += 1


def play_turn_greedy_fixed_dice(min_dice_to_stop):
    """Heuristic some players use: keep rolling until dice_remaining would
    drop below min_dice_to_stop, then bank. Always take max scoring dice."""
    k = 6
    T = 0
    while True:
        dice = roll(k)
        is_bust, actions = enumerate_actions(dice)
        if is_bust:
            return 0
        bc, val = max(actions, key=lambda a: a[1])
        T += val
        k = 6 if bc == k else k - bc
        if k < min_dice_to_stop:
            return T


def simulate_strategy(play_fn, n=200_000):
    totals = [play_fn() for _ in range(n)]
    arr = np.array(totals)
    return {
        "mean_turn_score": arr.mean(),
        "bust_rate": (arr == 0).mean(),
        "median_nonzero": np.median(arr[arr > 0]) if (arr > 0).any() else 0,
        "p90": np.percentile(arr, 90),
    }


def race_game(play_fn_a, play_fn_b, target=4000, max_turns=500):
    """Simulate a full race-to-target game; return 'A' or 'B' for winner."""
    scoreA = scoreB = 0
    for _ in range(max_turns):
        scoreA += play_fn_a()
        if scoreA >= target:
            return "A"
        scoreB += play_fn_b()
        if scoreB >= target:
            return "B"
    return "DRAW"


if __name__ == "__main__":
    print("Solving exact DP...")
    V, T_grid = farkle_dp.solve()
    th = farkle_dp.thresholds(V, T_grid)
    print("Thresholds:", th)

    random.seed(42)
    print("\n--- Per-turn strategy comparison (200k simulated turns each) ---")
    strategies = {
        "DP-optimal (exact)": lambda: play_turn_optimal(V, T_grid),
        "Threshold-heuristic (bank-max, DP thresholds)": lambda: play_turn_threshold(th),
        "Naive: stop after first score": lambda: play_turn_naive_bank_first(0),
        "Naive: one extra reroll then stop": lambda: play_turn_naive_bank_first(1),
        "Greedy: stop once <3 dice remain": lambda: play_turn_greedy_fixed_dice(3),
        "Greedy: stop once <2 dice remain": lambda: play_turn_greedy_fixed_dice(2),
        "Reckless: stop once <1 die remains (push to the edge)": lambda: play_turn_greedy_fixed_dice(1),
    }
    results = {}
    for name, fn in strategies.items():
        stats = simulate_strategy(fn, n=200_000)
        results[name] = stats
        print(f"{name:55s} mean={stats['mean_turn_score']:7.1f}  "
              f"bust_rate={stats['bust_rate']:.3%}  p90={stats['p90']:6.0f}")
