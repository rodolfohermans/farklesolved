"""
Validate the exact race-DP solution against direct Monte Carlo, and compare
three policies head-to-head in simulated races to G:
  (a) pure turn-EV-max      — farkle_dp.py's policy, oblivious to the race entirely
  (b) turn-EV-max + patch   — same, but stop as soon as reaching G is banked
  (c) race-aware exact      — read directly from the solved (F, U_all) tables
"""
import random
import time
import numpy as np
from farkle_kcd import enumerate_actions
import farkle_dp
from farkle_dp import STEP as STEP1
from race_dp import solve_race, STEP

G = 4000
random.seed(2024)

print("Solving exact race DP (this takes ~2-3 minutes)...")
t0 = time.time()
F, U_all, N, Nx = solve_race(G, verbose=True)
print(f"Solved in {time.time()-t0:.1f}s. F[0,0] = {F[0,0]:.4f} "
      f"(exact win probability for whoever rolls first, race to {G})\n")

print("Solving single-turn EV-maximizing policy (for comparison baselines)...")
farkle_dp.N_T = farkle_dp.T_MAX // STEP1 + 1
V_turn, Tgrid_turn = farkle_dp.solve()


def roll(k):
    return tuple(random.randint(1, 6) for _ in range(k))


def stop_value(i, t_idx, j):
    if i + t_idx >= N - 1:
        return 1.0
    return 1.0 - F[j, i + t_idx]


def play_turn_race_aware(i, j):
    """i = active player's permanent score index, j = opponent's. Returns
    points actually banked this turn (0 if busted)."""
    k, t_idx = 6, 0
    U = U_all[i]
    while True:
        dice = roll(k)
        is_bust, actions = enumerate_actions(dice)
        if is_bust:
            return 0
        best_v, best = -1, None
        for bc, val in actions:
            kp = 6 if bc == k else k - bc
            tp_idx = min(t_idx + val // STEP, N - 1)
            v = U[kp][tp_idx, j]
            if v > best_v:
                best_v, best = v, (kp, tp_idx)
        k, t_idx = best
        cur_v = U[k][t_idx, j]
        sv = stop_value(i, t_idx, j)
        # Tolerance must be >= the solver's own convergence tolerance (race_dp's
        # default tol=1e-7, actual final max_change ~8.5e-8), not an arbitrarily
        # tight 1e-9: U_all is Gauss-Seidel and was computed against F as it stood
        # mid-round, which can differ from the final converged F by ~1e-7. A too-
        # tight tolerance here makes this function occasionally "continue" at
        # states where the converged policy says "stop" (found by audit: ~7000
        # grid states affected, each a large-magnitude wrong decision, though the
        # net effect on win rates was small since it occurs rarely per race).
        if cur_v <= sv + 1e-6:
            return t_idx * STEP


def play_turn_ev_max(cap=None):
    """Pure single-turn EV-max policy, oblivious to the race (cap=None), or
    patched to stop once `cap` points would be reached/exceeded this turn."""
    k, T = 6, 0
    n_t = len(V_turn[6])  # derive from the actual table, not the module global
    while True:
        dice = roll(k)
        is_bust, actions = enumerate_actions(dice)
        if is_bust:
            return 0
        best_val, best = -1, None
        for bc, val in actions:
            kp = 6 if bc == k else k - bc
            i_ = min((T + val) // STEP1, n_t - 1)
            v = V_turn[kp][i_]
            if v > best_val:
                best_val, best = v, (kp, val)
        kp, val = best
        T += val
        k = kp
        if cap is not None and T >= cap:
            return T
        i_ = min(T // STEP1, n_t - 1)
        if T >= V_turn[k][i_] - 1e-9:
            return T


def race(policy_a, policy_b, g_target=G):
    """policy_a/b(my_score, opp_score) -> points banked this turn."""
    a = b = 0
    while True:
        a += policy_a(a, b)
        if a >= g_target:
            return "A"
        b += policy_b(b, a)
        if b >= g_target:
            return "B"


# ---------------------------------------------------------------- Part 1:
# Validate F against direct Monte Carlo from several representative states.
print("=== Part 1: exact F[i,j] vs direct Monte Carlo (race-aware vs race-aware) ===")
STEPg = STEP
test_states = [(0, 0), (2000, 0), (0, 2000), (3500, 0), (1000, 1500), (3000, 3500)]
N_SIM = 10000
for x0, y0 in test_states:
    i0, j0 = x0 // STEPg, y0 // STEPg
    exact = F[i0, j0]
    wins = 0
    for _ in range(N_SIM):
        a, b = x0, y0
        active_is_a = True
        while True:
            if active_is_a:
                i, j = a // STEPg, b // STEPg
                a += play_turn_race_aware(i, j)
                if a >= G:
                    wins += 1
                    break
            else:
                i, j = b // STEPg, a // STEPg
                b += play_turn_race_aware(i, j)
                if b >= G:
                    break
            active_is_a = not active_is_a
    empirical = wins / N_SIM
    se = np.sqrt(empirical * (1 - empirical) / N_SIM)
    print(f"  (x={x0:5d}, y={y0:5d}): exact F={exact:.4f}   "
          f"MC estimate={empirical:.4f}  (N={N_SIM}, 95% CI ±{1.96*se:.4f})")

# ---------------------------------------------------------------- Part 2:
# Head-to-head: race-aware exact vs. the two EV-max baselines, seat-balanced.
print("\n=== Part 2: race-aware exact vs turn-EV-max baselines (seat-order balanced) ===")
N_RACE = 300000


def policy_b_patched(my_score, opp_score):
    return play_turn_ev_max(cap=G - my_score)


def policy_raceaware(my_score, opp_score):
    i, j = my_score // STEPg, min(opp_score // STEPg, Nx - 1)
    return play_turn_race_aware(i, j)


def policy_a_pure(my_score, opp_score):
    return play_turn_ev_max(cap=None)


matchups = {
    "(a) pure turn-EV-max (race-blind)": policy_a_pure,
    "(b) turn-EV-max + endgame-stop patch": policy_b_patched,
}

matchup_results = {}
for name, opp_fn in matchups.items():
    wins_opt = wins_other = 0
    for n in range(N_RACE):
        if n % 2 == 0:
            w = race(policy_raceaware, opp_fn)
            wins_opt += (w == "A")
            wins_other += (w == "B")
        else:
            w = race(opp_fn, policy_raceaware)
            wins_opt += (w == "B")
            wins_other += (w == "A")
    p = wins_opt / N_RACE
    se = np.sqrt(p * (1 - p) / N_RACE)
    matchup_results[name] = (p, se)
    print(f"  race-aware-exact vs {name:38s} -> "
          f"race-aware wins {p:.2%} +/- {1.96*se:.2%} (95% CI) | other wins {wins_other/N_RACE:.2%}")

pa, sea = matchup_results["(a) pure turn-EV-max (race-blind)"]
pb, seb = matchup_results["(b) turn-EV-max + endgame-stop patch"]
diff = pa - pb
se_diff = np.sqrt(sea**2 + seb**2)
print(f"\n  Patch effect: (a)->(b) moved race-aware's win rate from {pa:.2%} to {pb:.2%}, "
      f"a change of {diff:.2%} +/- {1.96*se_diff:.2%} (95% CI on the difference). "
      f"{'This IS statistically distinguishable from zero.' if abs(diff) > 1.96*se_diff else 'This is NOT statistically distinguishable from zero at this N.'}")

# ---------------------------------------------------------------- Part 3:
# How do race-aware thresholds (continue-while-T<=X) shift vs the fixed
# single-player table, depending on how far behind/ahead you are?
print("\n=== Part 3: race-aware thresholds vs fixed single-player thresholds ===")
single_th = farkle_dp.thresholds(V_turn, Tgrid_turn)
print("Fixed single-player thresholds (score-blind):", single_th)


def race_aware_threshold(i, j, k):
    U = U_all[i][k]
    col = U[:, j]
    t_idx_grid = np.arange(N)
    stop_vals = np.array([stop_value(i, t, j) for t in range(N)])
    continuing = col > stop_vals + 1e-6  # same staleness tolerance fix as play_turn_race_aware
    idxs = np.nonzero(continuing)[0]
    return int(idxs[-1]) * STEP if len(idxs) else -1


scenarios = {
    "tied, early (x=0,y=0)": (0, 0),
    "far behind (x=0, y=3000)": (0, 3000),
    "far ahead (x=3000, y=0)": (3000, 0),
    "both near finish, tied (x=3500,y=3500)": (3500, 3500),
    "behind near finish (x=3000,y=3900)": (3000, 3900),
    "ahead near finish (x=3900,y=3000)": (3900, 3000),
}
print(f"{'scenario':42s}" + "".join(f"k={k:<7d}" for k in range(1, 7)))
for name, (x, y) in scenarios.items():
    i, j = x // STEP, min(y // STEP, Nx - 1)
    ths = [race_aware_threshold(i, j, k) for k in range(1, 7)]
    print(f"{name:42s}" + "".join(f"{t:<9d}" for t in ths))

import pickle
with open("race_solution.pkl", "wb") as f:
    pickle.dump({"F": F, "U_all": U_all, "N": N, "Nx": Nx, "G": G, "STEP": STEP}, f)
print("\n(F matrix and U_all pickled to race_solution.pkl for reuse without re-solving)")
