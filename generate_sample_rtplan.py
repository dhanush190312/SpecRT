#!/usr/bin/env python3
"""
Generate a small synthetic DICOM-RT Plan file so you can run RadioPath
end-to-end without needing a real clinical DICOM file.

This is NOT a real patient plan and must never be used or presented as one.
It only carries the fields RadioPath actually reads: Modality=RTPLAN, and a
BeamSequence where each beam's first control point has an IsocenterPosition.

USAGE
-----
    python generate_sample_rtplan.py --output sample_rtplan.dcm --n 6
"""
from __future__ import annotations

import argparse
import random

import pydicom
from pydicom.dataset import Dataset, FileDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid


def _build_beam(beam_number: int, beam_name: str, isocenter) -> Dataset:
    beam = Dataset()
    beam.BeamNumber = beam_number
    beam.BeamName = beam_name
    beam.BeamType = "STATIC"
    beam.RadiationType = "PHOTON"
    beam.TreatmentMachineName = "SIM_LINAC"

    cp = Dataset()
    cp.ControlPointIndex = 0
    cp.IsocenterPosition = [float(v) for v in isocenter]
    cp.NominalBeamEnergy = 6.0
    cp.GantryAngle = 0.0
    cp.CumulativeMetersetWeight = 0.0
    beam.ControlPointSequence = pydicom.Sequence([cp])
    beam.NumberOfControlPoints = 1
    return beam


def generate_sample_rtplan(output_path: str, n_isocenters: int = 5, seed: int = 42) -> str:
    rng = random.Random(seed)

    file_meta = Dataset()
    file_meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.481.5"  # RT Plan Storage
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    file_meta.ImplementationClassUID = generate_uid()

    ds = FileDataset(output_path, {}, file_meta=file_meta, preamble=b"\x00" * 128)
    ds.is_little_endian = True
    ds.is_implicit_VR = False

    ds.SOPClassUID = file_meta.MediaStorageSOPClassUID
    ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
    ds.Modality = "RTPLAN"
    ds.RTPlanLabel = "RadioPath_Synthetic"
    ds.RTPlanName = "Synthetic test plan - NOT for clinical use"
    ds.PatientName = "Synthetic^Test"
    ds.PatientID = "RADIOPATH-TEST-001"
    ds.PatientBirthDate = ""
    ds.PatientSex = ""
    ds.StudyInstanceUID = generate_uid()
    ds.SeriesInstanceUID = generate_uid()
    ds.StudyDate = "20260101"
    ds.StudyTime = "000000"

    # Spread synthetic isocenters over a plausible couch volume (mm).
    isocenters = [
        (
            round(rng.uniform(-100, 100), 1),
            round(rng.uniform(-100, 100), 1),
            round(rng.uniform(-150, 150), 1),
        )
        for _ in range(n_isocenters)
    ]

    beams = pydicom.Sequence()
    for i, iso in enumerate(isocenters, start=1):
        # 1-3 beams sharing each isocenter, like a real multi-field setup
        for j in range(rng.randint(1, 3)):
            beams.append(_build_beam(len(beams) + 1, f"Field_{i}_{j + 1}", iso))
    ds.BeamSequence = beams
    ds.NumberOfBeams = len(beams)

    ds.save_as(output_path, write_like_original=False)
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a synthetic RT Plan DICOM file for testing RadioPath")
    parser.add_argument("--output", default="sample_rtplan.dcm", help="Output .dcm path")
    parser.add_argument("--n", type=int, default=5, help="Number of distinct isocenters to generate")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    args = parser.parse_args()

    path = generate_sample_rtplan(args.output, args.n, args.seed)
    print(f"Synthetic RT Plan written to: {path}")
    print("This is synthetic test data only, not a real patient plan.")
