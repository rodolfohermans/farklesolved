"""Produce the final summary tables used in the HTML report."""
import json
import random
import numpy as np
import farkle_dp
from farkle_dp import STEP
from farkle_kcd import weighted_outcomes_for_k, bust_probability
from farkle_sim import play_turn_optimal, play_turn_threshold, play_turn_naive_bank_first, play_turn_greedy_fixed_dice

farkle_dp.T_MAX = 60000
farkle_dp.N_T = farkle_dp.T_MAX // STEP + 1

V, T_grid = farkle_dp.solve()
th = farkle_dp.thresholds(V, T_grid)
n_t = len(V[6])  # derive from the actual table, not the module global (robustness)

report = {}
report["bust_prob"] = {k: bust_probability(k) for k in range(1, 7)}
report["thresholds"] = th
report["value_fresh"] = {k: float(V[k][0]) for k in range(1, 7)}

# Opening roll (6 dice) breakdown, grouped by dice-left-after-best-action
outcomes, n = weighted_outcomes_for_k(6)
groups = {}  # kp -> {weight_sum, min_val, max_val, example_values(set), stop_weight, continue_weight}
bust_weight = 0
for weight, is_bust, actions in outcomes:
    if is_bust:
        bust_weight += weight
        continue
    best_v, best = -1, None
    for bc, val in actions:
        kp = 6 if bc == 6 else 6 - bc
        i = min(val // STEP, n_t - 1)
        v = V[kp][i]
        if v > best_v:
            best_v, best = v, (bc, val, kp)
    bc, val, kp = best
    g = groups.setdefault(kp, {"weight": 0, "vals": [], "stop_w": 0, "cont_w": 0})
    g["weight"] += weight
    g["vals"].append((val, weight))
    will_stop = V[kp][min(val // STEP, n_t - 1)] <= val + 1e-9
    if will_stop:
        g["stop_w"] += weight
    else:
        g["cont_w"] += weight

opening = []
for kp in sorted(groups.keys()):
    g = groups[kp]
    vals = sorted(set(v for v, w in g["vals"]))
    opening.append({
        "dice_left_after": kp,
        "prob": g["weight"] / n,
        "stop_prob_within_group": g["stop_w"] / g["weight"],
        "min_val": min(vals),
        "max_val": max(vals),
        "n_distinct_values": len(vals),
    })
report["opening_roll_groups"] = opening
report["opening_bust_prob"] = bust_weight / n

# Full-turn score distribution under optimal play
random.seed(123)
N = 300_000
totals = np.array([play_turn_optimal(V, T_grid) for _ in range(N)])
report["turn_stats"] = {
    "bust_rate": float((totals == 0).mean()),
    "mean": float(totals.mean()),
    "p50": float(np.percentile(totals[totals > 0], 50)),
    "p75": float(np.percentile(totals[totals > 0], 75)),
    "p90": float(np.percentile(totals[totals > 0], 90)),
    "p95": float(np.percentile(totals[totals > 0], 95)),
    "p99": float(np.percentile(totals[totals > 0], 99)),
    "max": float(totals.max()),
    "p_gt_1000": float((totals > 1000).mean()),
    "p_gt_2000": float((totals > 2000).mean()),
}

# Strategy comparison table (per turn)
strategies = {
    "DP-optimal": lambda: play_turn_optimal(V, T_grid),
    "Bank-max + DP thresholds": lambda: play_turn_threshold(th),
    "Stop after first score": lambda: play_turn_naive_bank_first(0),
    "Stop once <3 dice remain": lambda: play_turn_greedy_fixed_dice(3),
    "Stop once <2 dice remain": lambda: play_turn_greedy_fixed_dice(2),
}
strat_rows = []
random.seed(99)
for name, fn in strategies.items():
    arr = np.array([fn() for _ in range(150_000)])
    strat_rows.append({
        "name": name,
        "mean": float(arr.mean()),
        "bust_rate": float((arr == 0).mean()),
    })
report["strategy_comparison"] = strat_rows

with open("report_data.json", "w") as f:
    json.dump(report, f, indent=2)

print(json.dumps(report, indent=2))
