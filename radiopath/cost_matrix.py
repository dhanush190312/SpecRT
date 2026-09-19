"""
Build the pairwise 3D Euclidean distance / cost matrix for isocenter points.

C_ij = sqrt( (xi-xj)^2 + (yi-yj)^2 + (zi-zj)^2 )
"""
from __future__ import annotations

import numpy as np


def build_cost_matrix(coordinates: np.ndarray) -> np.ndarray:
    """
    Build an (n x n) cost matrix of pairwise 3D Euclidean distances.

    Parameters
    ----------
    coordinates : np.ndarray of shape (n, 3)
        X, Y, Z coordinates of each isocenter (mm).

    Returns
    -------
    np.ndarray of shape (n, n)
        C[i, j] = 3D Euclidean distance between point i and point j.
        The diagonal is zero and the matrix is symmetric.
    """
    coordinates = np.asarray(coordinates, dtype=float)
    if coordinates.ndim != 2 or coordinates.shape[1] != 3:
        raise ValueError(f"coordinates must have shape (n, 3), got {coordinates.shape}")

    diff = coordinates[:, np.newaxis, :] - coordinates[np.newaxis, :, :]
    dist = np.sqrt(np.sum(diff ** 2, axis=-1))
    return dist
