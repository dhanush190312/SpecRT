"""
Held-Karp — exact dynamic-programming TSP solver used only for small-case
validation / benchmarking of the 2-opt result.

Complexity: O(n^2 * 2^n) time, O(n * 2^n) space. The exponential term makes
this impractical for large n, so it is intentionally gated behind
MAX_PRACTICAL_N and is NOT the main algorithm.
"""
from __future__ import annotations

import itertools
from typing import Dict, List, Tuple

import numpy as np

# Guard rail: 2^n subsets get expensive fast. 13 points is already ~1M subsets.
MAX_PRACTICAL_N = 13


def _held_karp_from_start(cost_matrix: np.ndarray, closed: bool = True, start_node: int = 0) -> Tuple[List[int], float]:
    n = cost_matrix.shape[0]
    if n <= 1:
        return list(range(n)), 0.0
    if n == 2:
        other = 1 if start_node == 0 else 0
        cost = cost_matrix[start_node, other] + (cost_matrix[other, start_node] if closed else 0.0)
        return [start_node, other], float(cost)

    perm = [start_node] + [i for i in range(n) if i != start_node]
    cm_perm = cost_matrix[np.ix_(perm, perm)]

    C: Dict[Tuple[int, int], Tuple[float, List[int]]] = {}
    for k in range(1, n):
        C[(1 << k, k)] = (float(cm_perm[0][k]), [0, k])

    for subset_size in range(2, n):
        for subset in itertools.combinations(range(1, n), subset_size):
            bits = 0
            for b in subset:
                bits |= (1 << b)
            for k in subset:
                prev_bits = bits & ~(1 << k)
                best = None
                for m in subset:
                    if m == k:
                        continue
                    key = (prev_bits, m)
                    if key in C:
                        prev_cost, prev_path = C[key]
                        cand_cost = prev_cost + cm_perm[m][k]
                        if best is None or cand_cost < best[0]:
                            best = (cand_cost, prev_path + [k])
                if best is not None:
                    C[(bits, k)] = best

    full_bits = (1 << n) - 2
    best_total = None
    for k in range(1, n):
        key = (full_bits, k)
        if key in C:
            cost, path = C[key]
            total = cost + (cm_perm[k][0] if closed else 0.0)
            if best_total is None or total < best_total[0]:
                best_total = (total, path)

    if best_total is None:
        raise RuntimeError("Held-Karp failed to find a solution.")

    best_cost, best_perm_path = best_total
    real_path = [perm[idx] for idx in best_perm_path]
    return real_path, float(best_cost)


def held_karp(cost_matrix: np.ndarray, closed: bool = True) -> Tuple[List[int], float]:
    """
    Solve TSP exactly with Held-Karp algorithm.

    Parameters
    ----------
    cost_matrix : np.ndarray
        (n x n) pairwise cost matrix.
    closed : bool
        If True, solves closed-tour TSP (returns to start).
        If False, solves open path TSP across all possible start/end nodes.

    Returns
    -------
    (best_route, best_cost)
    """
    n = cost_matrix.shape[0]
    if n > MAX_PRACTICAL_N:
        raise ValueError(
            f"Held-Karp is only practical for small n (<= {MAX_PRACTICAL_N}); "
            f"got n={n}. Use the 2-opt result for larger cases."
        )
    if closed:
        return _held_karp_from_start(cost_matrix, closed=True, start_node=0)
    else:
        best_route = None
        best_cost = float('inf')
        for s in range(n):
            route, cost = _held_karp_from_start(cost_matrix, closed=False, start_node=s)
            if cost < best_cost - 1e-9:
                best_cost = cost
                best_route = route
        return best_route, best_cost
