"""
Exact optimal-stopping DP for the KCD dice game.

State: (k = dice remaining to roll, T = points already banked THIS turn).
V(k, T) = expected total points earned this turn under optimal play
        = max( T,                                   # stop now
               sum_outcomes p(o) * [ 0 if bust else max_action V(k', T+val) ] )
Busting forfeits T entirely, which is why the continue branch scores a bust
as 0, not T — that asymmetry is what produces a finite stop/continue threshold.

All scores are multiples of 50, so a step-50 grid is exact (no discretization
error) up to the truncation ceiling T_MAX, a forced-stop boundary. This is an
approximation, not a true boundary (unlike race_dp.py, where the target score
itself is a natural absorbing boundary and needs no truncation at all): checked
by re-solving at increasing T_MAX until thresholds stop moving. k=1-5 are
stable from T_MAX=4000 on at 250/200/400/1000/3350. k=6 converges more slowly:
12850 at T_MAX=15000, settling at its final value of 12900 only from T_MAX=30000
onward (smaller ceilings like 4000 or 8000 visibly truncate it further, see the
__main__ sweep below). T_MAX is set well above that here so the truncation is
inconsequential (V(6,0) is identical to 6 decimal places across T_MAX=15000/
30000/60000, even though the k=6 threshold itself hadn't fully settled at the
low end of that range).

Multisets (not raw permutations) are used so each k has only C(k+5,5)
distinct states; the T-grid sweep for each outcome/action is a vectorized
index shift, since value is always a multiple of STEP.
"""

import numpy as np
from farkle_kcd import weighted_outcomes_for_k

STEP = 50
T_MAX = 60000
N_T = T_MAX // STEP + 1  # grid indices 0..N_T-1, T = i*STEP


def solve(tol=1e-9, max_iters=3000, verbose=False):
    T_grid = np.arange(N_T) * STEP
    V = {k: T_grid.astype(np.float64).copy() for k in range(1, 7)}

    cache = {k: weighted_outcomes_for_k(k) for k in range(1, 7)}
    idx = np.arange(N_T)

    for it in range(max_iters):
        newV = {}
        max_delta = 0.0
        for k in range(1, 7):
            outcomes, n = cache[k]
            cont = np.zeros(N_T, dtype=np.float64)
            for weight, is_bust, actions in outcomes:
                if is_bust:
                    continue  # contributes 0 to cont
                best = None
                for bc, val in actions:
                    kp = 6 if bc == k else k - bc
                    shift = val // STEP
                    shifted_idx = np.minimum(idx + shift, N_T - 1)
                    candidate = V[kp][shifted_idx]
                    best = candidate if best is None else np.maximum(best, candidate)
                cont += weight * best
            cont /= n
            val_here = np.maximum(T_grid, cont)
            max_delta = max(max_delta, float(np.max(np.abs(val_here - V[k]))))
            newV[k] = val_here
        V = newV
        if verbose and it % 25 == 0:
            print(f"iter {it}: max_delta={max_delta:.8f}")
        if max_delta < tol:
            if verbose:
                print(f"converged at iter {it}, max_delta={max_delta:.2e}")
            break
    return V, T_grid


def thresholds(V, T_grid):
    """Largest T at which continuing still (weakly) beats stopping, per k."""
    out = {}
    for k in range(1, 7):
        continue_mask = V[k] > T_grid + 1e-6
        idxs = np.nonzero(continue_mask)[0]
        out[k] = int(T_grid[idxs[-1]]) if len(idxs) else -1
    return out


if __name__ == "__main__":
    V, T_grid = solve(verbose=True)
    th = thresholds(V, T_grid)
    print("\nOptimal continue/stop thresholds (bank once accumulated turn score exceeds this):")
    for k in range(1, 7):
        print(f"  dice remaining = {k}: continue while T <= {th[k]:5d},  E[V(k,0)] = {V[k][0]:.2f}")
