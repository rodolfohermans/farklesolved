"""
Research code for a possible future "Elder" persona (ROADMAP.md Phase 13):
near-optimal decision policy, but with a perceptual handicap rather than a
behavioral one -- misreads individual dice (low acuity / blur) and
sometimes fails to notice a straight is available (inattention), distinct
mechanisms modeled independently, grounded in real perceptual psychology
(see ROADMAP.md Phase 13 for the citations: subitizing, and the
pip-layout relationship between 2/3 and 4/5).

Not wired into the game (explicitly deferred). This script:
  1. Samples a "perceived" roll from a "true" roll via a per-die confusion
     model.
  2. Picks an action using the near-optimal single-turn policy (same
     bestAction/shouldContinue logic as the Scholar) against the PERCEIVED
     roll and the character's own (possibly already-wrong) running total.
  3. With some probability, independently, drops straight-derived actions
     from consideration even if the (possibly-already-corrupted) perceived
     roll contains one (the inattention mechanic).
  4. Checks whether the resulting intended action is actually legal against
     the TRUE roll. If not, reveals the mistake and falls back to the
     near-optimal choice on the true roll instead of silently acting on a
     fiction.
  5. Sweeps the confusion/inattention magnitudes and reports resulting win
     rate (vs the Scholar, since this is meant to be "near-optimal but
     handicapped") and bust rate, to see how costly the handicap actually is.
"""

import random
from itertools import product, combinations_with_replacement
from collections import Counter

import numpy as np

import farkle_dp
from farkle_dp import STEP as STEP1
from farkle_kcd import enumerate_actions, face_options

G = 4000


def roll(k):
    return tuple(random.randint(1, 6) for _ in range(k))


# ---------------------------------------------------- Non-straight actions
# Mirrors farkle_kcd.enumerate_actions but WITHOUT the two straight-specific
# blocks, so straight-only actions can be identified by set difference
# against the full action set (correctly keeping any (bc, val) pair that's
# ALSO reachable without forming a straight -- missing the pattern doesn't
# erase an action that didn't need the pattern in the first place).
def _combo_sums(option_lists):
    out = set()
    for combo in product(*option_lists):
        out.add((sum(c for c, _ in combo), sum(v for _, v in combo)))
    return out


def enumerate_actions_no_straight(dice):
    counts = Counter(dice)
    per_face = [face_options(f, counts.get(f, 0)) for f in range(1, 7)]
    actions = _combo_sums(per_face)
    actions.discard((0, 0))
    return actions


def straight_only_actions(dice):
    is_bust, all_actions = enumerate_actions(dice)
    non_straight = enumerate_actions_no_straight(dice)
    return set(all_actions) - non_straight


# ------------------------------------------------------------- Confusion model
# Pip-count-adjacent confusions grounded in shared layout (2<->3, 4<->5 are
# literally "add/remove one center pip"); 1 is essentially never misread
# (subitizing); 6 gets its own, much rarer, lower-confidence channel since
# it's structurally distinct (two columns, no shared-layout neighbor).
CONFUSION_PAIRS = {
    2: 3, 3: 2,
    4: 5, 5: 4,
}


def perceive_die(face, p_lose, p_gain, p_56):
    """p_lose: chance a higher-pip-count face (3 or 5) is misread as its
    lower-pip-count neighbor (losing the shared center pip, the dominant,
    blur-driven direction). p_gain: chance a lower-pip-count face (2 or 4)
    is misread as its higher neighbor (hallucinating a pip, rarer). p_56:
    separate, symmetric, low-confidence channel for 5<->6 (not grounded in a
    shared layout the way 2/3 and 4/5 are; included for sensitivity testing,
    defaults to 0 in the main sweep)."""
    r = random.random()
    if face == 3 and r < p_lose:
        return 2
    if face == 5:
        if r < p_lose:
            return 4
        if r < p_lose + p_56:
            return 6
        return 5
    if face == 2 and r < p_gain:
        return 3
    if face == 4 and r < p_gain:
        return 5
    if face == 6 and r < p_56:
        return 5
    return face


def perceive_dice(dice, p_lose, p_gain, p_56):
    return tuple(perceive_die(f, p_lose, p_gain, p_56) for f in dice)


# --------------------------------------------------------------- Decision core
def best_action_by_value(k, T, actions, V):
    best_v, best = -1.0, None
    for bc, val in actions:
        kp = 6 if bc == k else k - bc
        idx = min((T + val) // STEP1, len(V[kp]) - 1)
        v = V[kp][idx]
        if v > best_v:
            best_v, best = v, (bc, val, kp)
    return best


def play_turn_elder(target, my_score, V, p_lose, p_gain, p_56, p_miss_straight, trace=None):
    """trace: optional list that gets an entry appended each time a
    misperception caused an attempted ILLEGAL move (the "reveal" moment).

    Note on running total: once an illegal intended move is revealed, the
    character re-decides on the true roll and that roll's cost is fully
    corrected (same T a Scholar would reach) -- by design, matching "only an
    attempt at an illegal move reveals the reality." The actual, lasting cost
    of the handicap comes entirely from the OTHER case: a misread combo that
    happens to also be a legal move on the true dice (so nothing reveals it),
    which can still be the WRONG (non-optimal) choice among what was truly
    available. There is therefore only one running total to track (T), not a
    separate "belief" vs "reality" pair -- they never actually diverge past
    a single roll by construction.
    """
    k, T = 6, 0
    while True:
        dice = roll(k)
        is_bust, real_actions = enumerate_actions(dice)
        if is_bust:
            return 0, True

        perceived_dice = perceive_dice(dice, p_lose, p_gain, p_56)
        p_is_bust, perceived_actions = enumerate_actions(perceived_dice)
        if p_is_bust:
            # Perceives a bust that isn't real: there's nothing to attempt,
            # so nothing can be "caught" as illegal -- the character simply
            # stops here, which under this game's actual rules (you must
            # bank something every roll to keep going) forfeits the turn
            # exactly like a real bust would. This IS the cost of the
            # handicap, not a bug.
            return 0, True

        if random.random() < p_miss_straight:
            without_straights = set(perceived_actions) - straight_only_actions(perceived_dice)
            if without_straights:
                perceived_actions = list(without_straights)

        bc_p, val_p, kp_p = best_action_by_value(k, T, perceived_actions, V)

        if (bc_p, val_p) in real_actions:
            # Coincidentally legal (or no misperception occurred this roll):
            # proceed exactly as intended, no reveal needed -- but this may
            # still not be the objectively best real action available.
            bc, val, kp = bc_p, val_p, kp_p
        else:
            if trace is not None:
                trace.append({"dice": dice, "perceived_dice": perceived_dice,
                              "intended": (bc_p, val_p), "real_actions": sorted(real_actions)})
            # Reveal + correct: re-decide on the TRUE roll, near-optimal.
            bc, val, kp = best_action_by_value(k, T, real_actions, V)

        T += val
        k = kp
        if my_score + T >= target:
            return T, False
        idx = min(T // STEP1, len(V[k]) - 1)
        if not (V[k][idx] > T + 1e-6):
            return T, False


def play_turn_scholar(target, my_score, V):
    k, T = 6, 0
    while True:
        dice = roll(k)
        is_bust, actions = enumerate_actions(dice)
        if is_bust:
            return 0, True
        bc, val, kp = best_action_by_value(k, T, actions, V)
        T += val
        k = kp
        if my_score + T >= target:
            return T, False
        idx = min(T // STEP1, len(V[k]) - 1)
        if not (V[k][idx] > T + 1e-6):
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


def seat_balanced_winrate(fn_a, fn_b, n, target=G):
    wins_a = 0
    for i in range(n):
        if i % 2 == 0:
            w = race(fn_a, fn_b, target=target)
            wins_a += w == "A"
        else:
            w = race(fn_b, fn_a, target=target)
            wins_a += w == "B"
    p = wins_a / n
    se = np.sqrt(p * (1 - p) / n)
    return p, se


def behavior_stats(play_fn, n=15_000):
    pts, busts = [], 0
    for _ in range(n):
        p, b = play_fn()
        pts.append(p)
        busts += b
    arr = np.array(pts)
    return {"mean": arr.mean(), "bust_rate": busts / n, "p90": float(np.percentile(arr, 90))}


if __name__ == "__main__":
    random.seed(20261012)
    farkle_dp.N_T = farkle_dp.T_MAX // STEP1 + 1
    print("Solving single-turn DP...")
    V, T_grid = farkle_dp.solve()

    N_BEHAVIOR = 15_000
    N_RACE = 10_000

    scholar_fn = lambda my, opp: play_turn_scholar(G, my, V)
    scholar_stats = behavior_stats(lambda: scholar_fn(0, 0), n=N_BEHAVIOR)
    print(f"\nScholar baseline: mean={scholar_stats['mean']:.1f}  bust_rate={scholar_stats['bust_rate']:.2%}  p90={scholar_stats['p90']:.0f}")

    print("\n=== Elder: sweep pip-confusion magnitude (p_gain fixed at p_lose/3, p_56=0, p_miss_straight=0.3) ===")
    for p_lose in [0.0, 0.03, 0.08, 0.15, 0.25]:
        p_gain = p_lose / 3
        trace = []
        elder_fn = lambda my, opp, p_lose=p_lose, p_gain=p_gain: play_turn_elder(
            G, my, V, p_lose, p_gain, 0.0, 0.3, trace=trace
        )
        stats = behavior_stats(lambda: elder_fn(0, 0), n=N_BEHAVIOR)
        reveal_rate = len(trace) / N_BEHAVIOR
        p, se = seat_balanced_winrate(elder_fn, scholar_fn, N_RACE)
        print(f"  p_lose={p_lose:.2f} (p_gain={p_gain:.3f}): mean={stats['mean']:7.1f}  "
              f"bust_rate={stats['bust_rate']:.2%}  reveal_rate={reveal_rate:.2%}  "
              f"win_vs_Scholar={p:.2%} +/- {1.96*se:.2%}")

    print("\n=== Elder: sweep straight-miss probability alone (p_lose=0.08 fixed) ===")
    for p_miss in [0.0, 0.2, 0.5, 0.8, 1.0]:
        elder_fn = lambda my, opp, p_miss=p_miss: play_turn_elder(
            G, my, V, 0.08, 0.08 / 3, 0.0, p_miss
        )
        stats = behavior_stats(lambda: elder_fn(0, 0), n=N_BEHAVIOR)
        p, se = seat_balanced_winrate(elder_fn, scholar_fn, N_RACE)
        print(f"  p_miss_straight={p_miss:.2f}: mean={stats['mean']:7.1f}  "
              f"bust_rate={stats['bust_rate']:.2%}  win_vs_Scholar={p:.2%} +/- {1.96*se:.2%}")

    print("\n=== Sample revealed mistakes (p_lose=0.15) ===")
    trace = []
    elder_fn = lambda my, opp: play_turn_elder(G, my, V, 0.15, 0.05, 0.0, 0.3, trace=trace)
    for _ in range(2000):
        elder_fn(0, 0)
        if len(trace) >= 5:
            break
    for t in trace[:5]:
        print(f"  real={t['dice']} perceived={t['perceived_dice']} intended={t['intended']} "
              f"real_actions_available={t['real_actions']}")
