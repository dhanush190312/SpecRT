"""
Read a DICOM-RT treatment plan and extract the available isocenter coordinates.

An RT Plan stores one IsocenterPosition (300A,012C) inside the first control
point of every beam in BeamSequence (300A,00B0). Several beams belonging to
the same arc/field group usually share the same physical isocenter, so this
module de-duplicates points that match to within `tolerance_mm` and keeps
track of which beam names map to each isocenter.
"""
from __future__ import annotations

from typing import List

try:
    import pydicom
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "pydicom is required to read DICOM-RT files but is not installed.\n"
        "Install it with:\n"
        "    pip install pydicom"
    ) from exc

from .models import Isocenter


def read_rtplan(source) -> "pydicom.Dataset":
    """Read a DICOM file from disk or file-like object and confirm it looks like an RT Plan."""
    ds = source if isinstance(source, pydicom.Dataset) else pydicom.dcmread(source)

    modality = getattr(ds, "Modality", None)
    source_name = getattr(source, "name", str(source)) if not hasattr(source, "read") else "uploaded file"
    if modality != "RTPLAN":
        raise ValueError(
            f"'{source_name}' does not look like a DICOM-RT Plan (Modality={modality!r}). "
            "RadioPath expects a file with Modality = RTPLAN."
        )
    if not hasattr(ds, "BeamSequence") or len(ds.BeamSequence) == 0:
        raise ValueError(f"'{source_name}' has no BeamSequence; there are no isocenters to extract.")

    return ds


def extract_isocenters(ds, tolerance_mm: float = 0.1) -> List[Isocenter]:
    """
    Walk every beam's first control point, read IsocenterPosition, and merge
    beams that share (nearly) the same isocenter into a single point.

    Parameters
    ----------
    ds : pydicom.Dataset
        A loaded RT Plan dataset (as returned by `read_rtplan`).
    tolerance_mm : float
        Two isocenters within this distance on every axis are treated as
        the same physical point.

    Returns
    -------
    List[Isocenter], labelled P1, P2, P3, ... in first-seen order.
    """
    raw_points = []  # (x, y, z, beam_name)
    for i, beam in enumerate(ds.BeamSequence):
        beam_name = str(
            getattr(beam, "BeamName", None)
            or getattr(beam, "BeamNumber", None)
            or f"Beam_{i + 1}"
        )
        control_points = getattr(beam, "ControlPointSequence", None)
        if not control_points:
            continue
        first_cp = control_points[0]
        pos = getattr(first_cp, "IsocenterPosition", None)
        if pos is None:
            continue
        x, y, z = (float(v) for v in pos)
        raw_points.append((x, y, z, beam_name))

    if not raw_points:
        raise ValueError(
            "No IsocenterPosition values were found in any beam's first "
            "control point. This RT Plan may not carry isocenter data in "
            "the expected location."
        )

    isocenters: List[Isocenter] = []
    for x, y, z, beam_name in raw_points:
        match = None
        for iso in isocenters:
            if (
                abs(iso.x - x) <= tolerance_mm
                and abs(iso.y - y) <= tolerance_mm
                and abs(iso.z - z) <= tolerance_mm
            ):
                match = iso
                break
        if match is not None:
            match.beam_names.append(beam_name)
        else:
            label = f"P{len(isocenters) + 1}"
            isocenters.append(Isocenter(label=label, x=x, y=y, z=z, beam_names=[beam_name]))

    return isocenters
