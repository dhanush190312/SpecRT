"""
2-opt local-search heuristic — the main route-optimization algorithm.

Takes an existing route, removes two edges, reconnects the route the other
way, and keeps the change whenever it lowers total cost. Repeats until no
single 2-opt move improves the route further (a local optimum).

Complexity: roughly O(n^3) worst case for the straightforward iterative
version used here (O(n^2) candidate moves per pass, repeated until no
improving pass is found). Does NOT guarantee the global optimum.
"""
from __future__ import annotations

from typing import List, Tuple

import numpy as np


def route_cost(route: List[int], cost_matrix: np.ndarray, closed: bool = True) -> float:
    """Total cost of visiting `route` in order (optionally closing the tour)."""
    total = 0.0
    for i in range(len(route) - 1):
        total += cost_matrix[route[i], route[i + 1]]
    if closed and len(route) > 1:
        total += cost_matrix[route[-1], route[0]]
    return float(total)


def two_opt(route: List[int], cost_matrix: np.ndarray, closed: bool = True) -> Tuple[List[int], float]:
    """
    Improve `route` with 2-opt until no further improving move exists.

    Parameters
    ----------
    route : list[int]
        Initial visiting order, as indices into cost_matrix.
    cost_matrix : np.ndarray
        (n x n) pairwise cost matrix.
    closed : bool
        If True, optimizes a closed tour (returns to the start).
        If False, optimizes an open path (no return leg).

    Returns
    -------
    (best_route, best_cost)
    """
    best = list(route)
    best_cost = route_cost(best, cost_matrix, closed)
    n = len(best)

    improved = True
    while improved:
        improved = False
        for i in range(0, n - 1):
            for k in range(i + 1, n):
                candidate = best[:i] + best[i:k + 1][::-1] + best[k + 1:]
                candidate_cost = route_cost(candidate, cost_matrix, closed)
                if candidate_cost < best_cost - 1e-9:
                    best = candidate
                    best_cost = candidate_cost
                    improved = True
    return best, best_cost
