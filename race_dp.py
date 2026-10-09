"""
Exact solution of the full two-player race-to-target game as a finite
stochastic game (not just the single-turn EV-maximizing MDP from farkle_dp.py).

State for the OUTER game: (x, y) = (active player's banked score, other
player's banked score), both < target G. Define

    F[x, y] = P(the player about to roll wins the race | scores x, y)

F is a fixed point: within a turn, the active player chooses actions to
maximize their OWN win probability, where:
  - stopping with new total z = x+T wins outright if z >= G, else hands the
    turn to the opponent, who then faces F[y, z] — so the active player's
    win prob from stopping is 1 - F[y, z].
  - busting reverts to x and also hands the turn over: value 1 - F[y, x].
  - continuing recurses into the same per-turn action space as before.

This couples every (x,y) to every other (y,x') pair, so it's solved by
Gauss-Seidel value iteration over the whole (x,y) grid simultaneously; the
inner per-turn recursion is vectorized over ALL opponent scores y at once
(not just at one y), so one inner solve for a given x yields an entire row
of F. All scores are multiples of 50 (STEP), so the grid is exact up to the
target G itself (no truncation-ceiling approximation needed this time: the
natural absorbing boundary is "reached G", not an arbitrary cutoff).
"""

import numpy as np
from farkle_kcd import weighted_outcomes_for_k

STEP = 50


def solve_race(G, outer_iters=200, inner_iters=6, tol=1e-7, verbose=False):
    N = G // STEP + 1          # z/T grid: indices 0..N-1, index N-1 == "reached G"
    Nx = N - 1                 # valid in-progress scores: 0..N-2
    cache = {k: weighted_outcomes_for_k(k) for k in range(1, 7)}
    idx = np.arange(N)

    F = np.full((Nx, Nx), 0.5)
    # Persistent, warm-started per-i inner tables: each outer round only runs a
    # few more Bellman sweeps on top of where it left off, instead of
    # resolving each i's inner MDP from scratch every round.
    U_all = [{k: np.full((N, Nx), 0.5) for k in range(1, 7)} for _ in range(Nx)]
    for i in range(Nx):
        for k in range(1, 7):
            U_all[i][k][N - 1, :] = 1.0

    for outer in range(outer_iters):
        max_change = 0.0
        for i in range(Nx):
            z_idx = np.minimum(i + idx, N - 1)             # (N,)
            win_now = (z_idx == N - 1)
            gathered = F[:, np.minimum(z_idx, Nx - 1)].T   # (N, Nx), safe gather
            STOP = 1.0 - gathered
            STOP[win_now, :] = 1.0

            BUST = 1.0 - F[:, i]  # (Nx,)

            U = U_all[i]
            for _ in range(inner_iters):
                newU = {}
                for k in range(1, 7):
                    outcomes, n = cache[k]
                    cont = np.zeros((N, Nx))
                    for weight, is_bust, actions in outcomes:
                        if is_bust:
                            cont += weight * BUST[np.newaxis, :]
                            continue
                        best = None
                        for bc, val in actions:
                            kp = 6 if bc == k else k - bc
                            shift = val // STEP
                            shifted = np.minimum(idx + shift, N - 1)
                            cand = U[kp][shifted, :]
                            best = cand if best is None else np.maximum(best, cand)
                        cont += weight * best
                    cont /= n
                    v = np.maximum(STOP, cont)
                    v[N - 1, :] = 1.0  # keep absorbing boundary exact
                    newU[k] = v
                U = newU
            U_all[i] = U

            row = U[6][0, :]  # fresh turn (k=6, T=0) win-prob for every y
            max_change = max(max_change, float(np.max(np.abs(row - F[i, :]))))
            F[i, :] = row  # Gauss-Seidel: used immediately by later i's this round

        if verbose and outer % 5 == 0:
            print(f"outer {outer}: max_change={max_change:.6f}")
        if max_change < tol:
            if verbose:
                print(f"converged at outer={outer}, max_change={max_change:.2e}")
            break

    return F, U_all, N, Nx


if __name__ == "__main__":
    import time
    for G in (300, 1000):
        t0 = time.time()
        F, U_all, N, Nx = solve_race(G, verbose=True)
        print(f"G={G}: solved in {time.time()-t0:.2f}s, F[0,0]={F[0,0]:.4f} "
              f"(win prob for whoever rolls first)")
