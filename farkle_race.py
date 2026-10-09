"""Head-to-head race-to-target simulations between strategies."""

import random
import farkle_dp
from farkle_dp import STEP
from farkle_sim import (
    play_turn_optimal, play_turn_threshold, play_turn_naive_bank_first,
    play_turn_greedy_fixed_dice, race_game,
)

farkle_dp.T_MAX = 60000
farkle_dp.N_T = farkle_dp.T_MAX // STEP + 1

if __name__ == "__main__":
    random.seed(7)
    V, T_grid = farkle_dp.solve()
    th = farkle_dp.thresholds(V, T_grid)

    contenders = {
        "DP-optimal": lambda: play_turn_optimal(V, T_grid),
        "Threshold-heuristic": lambda: play_turn_threshold(th),
        "Stop after first score": lambda: play_turn_naive_bank_first(0),
        "Stop once <3 dice remain": lambda: play_turn_greedy_fixed_dice(3),
    }

    N = 20_000
    for target in (1000, 4000, 10000):
        print(f"\n=== Race to {target} points, {N} games each matchup (seat order averaged) ===")
        baseline_name = "DP-optimal"
        for name, fn in contenders.items():
            if name == baseline_name:
                continue
            wins_opt = wins_other = draws = 0
            for i in range(N):
                # alternate who goes first (seat order) to remove first-mover bias
                if i % 2 == 0:
                    w = race_game(contenders[baseline_name], fn, target=target)
                    if w == "A":
                        wins_opt += 1
                    elif w == "B":
                        wins_other += 1
                    else:
                        draws += 1
                else:
                    w = race_game(fn, contenders[baseline_name], target=target)
                    if w == "A":
                        wins_other += 1
                    elif w == "B":
                        wins_opt += 1
                    else:
                        draws += 1
            print(f"  {baseline_name} vs {name:28s} -> "
                  f"{baseline_name} wins {wins_opt/N:.1%} | {name} wins {wins_other/N:.1%} | draws {draws}")
