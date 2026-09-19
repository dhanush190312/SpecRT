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


def held_karp(cost_matrix: np.ndarray, closed: bool = True) -> Tuple[List[int], float]:
    """
    Solve TSP exactly with Held-Karp, starting and (optionally) ending at
    node 0.

    Parameters
    ----------
    cost_matrix : np.ndarray
        (n x n) pairwise cost matrix.
    closed : bool
        If True, solves the closed-tour TSP (return to node 0).
        If False, solves the open shortest Hamiltonian path from node 0.

    Returns
    -------
    (best_route, best_cost) — best_route always starts at node 0.
    """
    n = cost_matrix.shape[0]
    if n > MAX_PRACTICAL_N:
        raise ValueError(
            f"Held-Karp is only practical for small n (<= {MAX_PRACTICAL_N}); "
            f"got n={n}. Use the 2-opt result for larger cases."
        )
    if n <= 1:
        return list(range(n)), 0.0
    if n == 2:
        cost = cost_matrix[0, 1] + (cost_matrix[1, 0] if closed else 0.0)
        return [0, 1], float(cost)

    # C[(subset_bitmask_excluding_0, last_node)] = (cost, path_from_0)
    C: Dict[Tuple[int, int], Tuple[float, List[int]]] = {}
    for k in range(1, n):
        C[(1 << k, k)] = (float(cost_matrix[0][k]), [0, k])

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
                        cand_cost = prev_cost + cost_matrix[m][k]
                        if best is None or cand_cost < best[0]:
                            best = (cand_cost, prev_path + [k])
                if best is not None:
                    C[(bits, k)] = best

    full_bits = (1 << n) - 2  # all nodes 1..n-1 visited (excludes bit 0)
    best_total = None
    for k in range(1, n):
        key = (full_bits, k)
        if key in C:
            cost, path = C[key]
            total = cost + (cost_matrix[k][0] if closed else 0.0)
            if best_total is None or total < best_total[0]:
                best_total = (total, path)

    if best_total is None:
        raise RuntimeError("Held-Karp failed to find a solution (unexpected).")

    best_cost, best_path = best_total
    return best_path, float(best_cost)
