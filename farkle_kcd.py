"""
Kingdom Come: Deliverance dice game ("Farkle"-family) — exact probability model
and optimal-stopping dynamic program.

Rules encoded (from the KCD wiki scoring table, standard 6 regular dice, no
special/Devil's-head dice):
  - Single 1  = 100, single 5 = 50 (only these two faces score alone).
  - Three of a kind: 1s=1000, 2s=200, 3s=300, 4s=400, 5s=500, 6s=600.
  - Each additional die of the same kind beyond three DOUBLES the value
    (4-of-a-kind = x2, 5-of-a-kind = x4, 6-of-a-kind = x8 the three-of-a-kind value).
  - Straight 1-5 = 500, straight 2-6 = 750, full straight 1-6 = 1500.
  - A roll "busts" if none of the above are present at all.
  - After a non-bust roll you must bank >=1 scoring die/combo; sets of <3
    identical 2/3/4/6 dice never score and can never be banked.
  - Banking all currently-rolled dice ("hot dice") lets you re-roll all 6.
  - Busting on a continuation wipes every point earned so far *this turn*.

All achievable scores are multiples of 50, so a DP grid in steps of 50 is exact
(no discretization error) up to the truncation ceiling T_MAX, which is set far
above any threshold that actually matters.
"""

from __future__ import annotations
from itertools import product, combinations_with_replacement
from functools import lru_cache
from collections import Counter
from math import factorial

THREE_KIND_VALUE = {1: 1000, 2: 200, 3: 300, 4: 400, 5: 500, 6: 600}


def group_value(face: int, count: int) -> int:
    """Value of `count` (>=3) identical dice of `face`."""
    base = THREE_KIND_VALUE[face]
    return base * (2 ** (count - 3))


def face_options(face: int, count: int) -> list[tuple[int, int]]:
    """
    All legal (dice_banked, value) choices for how many of this face's
    `count` available dice to bank, including (0, 0) = bank none of them.
    Faces 1 and 5 score as individual dice (so any 0..count is legal, with
    the >=3 group formula kicking in once banked count reaches 3). Faces
    2/3/4/6 only ever score in a 3-or-more group — and a group need not be
    taken in full: with 5 of a kind you may bank only 3 or 4 of them and
    leave the rest in the pool, since they still individually score 0 either
    way and the choice is purely about how many dice stay active to re-roll.
    """
    opts = [(0, 0)]
    if face in (1, 5):
        single = 100 if face == 1 else 50
        for b in range(1, count + 1):
            opts.append((b, single * b if b < 3 else group_value(face, b)))
    else:
        for b in range(3, count + 1):
            opts.append((b, group_value(face, b)))
    return opts


def _combo_sums(option_lists: list[list[tuple[int, int]]]) -> set[tuple[int, int]]:
    out = set()
    for combo in product(*option_lists):
        out.add((sum(c for c, _ in combo), sum(v for _, v in combo)))
    return out


def enumerate_actions(dice: tuple[int, ...]) -> tuple[bool, list[tuple[int, int]]]:
    """
    Given a rolled multiset of dice, return (is_bust, actions): actions is the
    full set of distinct (dice_banked_count, points_value) choices legally
    available for THIS roll, including partial takes (e.g. banking only one
    of two 5s, or only 3 of 4 like-kind dice) and straights-with-leftovers
    (e.g. {1,2,3,4,5,5} can bank the 1-5 straight plus the spare 5).
    """
    k = len(dice)
    counts = Counter(dice)

    per_face = [face_options(f, counts.get(f, 0)) for f in range(1, 7)]
    actions = _combo_sums(per_face)

    def leftover_counts(exclude_faces):
        c = Counter(counts)
        for f in exclude_faces:
            c[f] -= 1
        return c

    if all(counts.get(v, 0) >= 1 for v in (1, 2, 3, 4, 5)):
        lc = leftover_counts((1, 2, 3, 4, 5))
        lopts = [face_options(f, lc.get(f, 0)) for f in range(1, 7)]
        for bc, val in _combo_sums(lopts):
            actions.add((5 + bc, 500 + val))

    if all(counts.get(v, 0) >= 1 for v in (2, 3, 4, 5, 6)):
        lc = leftover_counts((2, 3, 4, 5, 6))
        lopts = [face_options(f, lc.get(f, 0)) for f in range(1, 7)]
        for bc, val in _combo_sums(lopts):
            actions.add((5 + bc, 750 + val))

    if k == 6 and sorted(dice) == [1, 2, 3, 4, 5, 6]:
        actions.add((6, 1500))

    actions.discard((0, 0))
    is_bust = len(actions) == 0
    return is_bust, sorted(actions)


@lru_cache(maxsize=None)
def outcomes_for_k(k: int):
    """All 6^k equally-likely outcomes for rolling k dice, pre-scored."""
    n = 6 ** k
    results = []
    for combo in product(range(1, 7), repeat=k):
        is_bust, actions = enumerate_actions(combo)
        results.append((is_bust, tuple(actions)))
    return results, n


def bust_probability(k: int) -> float:
    results, n = outcomes_for_k(k)
    busts = sum(1 for is_bust, _ in results if is_bust)
    return busts / n


@lru_cache(maxsize=None)
def weighted_outcomes_for_k(k: int):
    """
    Distinct dice multisets for rolling k dice, with their multinomial weight
    (number of equally-likely permutations), pre-scored. Collapses 6^k raw
    permutations down to C(k+5,5) distinct multisets — identical probability
    model, far fewer states to evaluate per DP sweep.
    Returns (outcomes, n) where outcomes = [(weight, is_bust, actions), ...]
    and n = 6**k (total permutations, i.e. sum of weights).
    """
    n = 6 ** k
    outcomes = []
    for combo in combinations_with_replacement(range(1, 7), k):
        counts = Counter(combo)
        weight = factorial(k)
        for c in counts.values():
            weight //= factorial(c)
        is_bust, actions = enumerate_actions(combo)
        outcomes.append((weight, is_bust, tuple(actions)))
    assert sum(w for w, _, _ in outcomes) == n
    return outcomes, n
