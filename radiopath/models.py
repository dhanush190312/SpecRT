"""Shared data model. Deliberately has no pydicom/pandas dependency."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import numpy as np


@dataclass
class Isocenter:
    label: str
    x: float
    y: float
    z: float
    beam_names: List[str] = field(default_factory=list)


def isocenters_to_array(isocenters: List[Isocenter]) -> np.ndarray:
    """Convert a list of Isocenter objects to an (n, 3) numpy array of X,Y,Z."""
    return np.array([[iso.x, iso.y, iso.z] for iso in isocenters], dtype=float)
