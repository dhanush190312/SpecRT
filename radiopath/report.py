"""Console report rendering matching RadioPath's expected output format."""
from __future__ import annotations

from typing import List

import numpy as np
import pandas as pd

from .models import Isocenter


def points_table(isocenters: List[Isocenter]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Point": [iso.label for iso in isocenters],
            "X": [round(iso.x, 2) for iso in isocenters],
            "Y": [round(iso.y, 2) for iso in isocenters],
            "Z": [round(iso.z, 2) for iso in isocenters],
            "Beams": [", ".join(iso.beam_names) for iso in isocenters],
        }
    )


def cost_matrix_table(cost_matrix: np.ndarray, labels: List[str]) -> pd.DataFrame:
    return pd.DataFrame(cost_matrix, index=labels, columns=labels).round(2)


def route_to_str(route: List[int], labels: List[str], closed: bool = True) -> str:
    names = [labels[i] for i in route]
    if closed:
        names.append(labels[route[0]])
    return " -> ".join(names)


def print_input_points(isocenters: List[Isocenter]) -> None:
    print("RADIOPATH - INPUT POINTS\n")
    print(f"Number of Isocenters: {len(isocenters)}\n")
    df = points_table(isocenters).drop(columns=["Beams"])
    print(df.to_string(index=False))
    print()


def print_cost_matrix(cost_matrix: np.ndarray, labels: List[str]) -> None:
    print("COST MATRIX\n")
    print(cost_matrix_table(cost_matrix, labels).to_string())
    print()


def print_results_table(rows: List[dict]) -> None:
    df = pd.DataFrame(rows)
    print(df.to_string(index=False))
    print()


def print_before_after(
    before_route: List[int], after_route: List[int], labels: List[str], closed: bool = True
) -> None:
    print("BEFORE:")
    print(route_to_str(before_route, labels, closed))
    print()
    print("AFTER (2-opt):")
    print(route_to_str(after_route, labels, closed))
    print()
