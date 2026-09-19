#!/usr/bin/env python3
"""
RadioPath — Isocenter Sequence Optimization for Radiotherapy Treatment Plans
==============================================================================
Reads a DICOM-RT plan, extracts isocenters, builds a 3D-distance cost matrix,
optimizes the visiting order with 2-opt, and (for small cases) validates the
result against the exact Held-Karp solution.

This is a sequencing prototype only. It does not change dose, beam
parameters, treatment technique, or the clinical plan, and it does not
perform collision detection (see project spec, sections 2 and 11).

USAGE
-----
    python main.py path/to/plan.dcm
    python main.py path/to/plan.dcm --open              # open path, no return leg
    python main.py path/to/plan.dcm --outdir my_results  # change output folder

Don't have a DICOM-RT file to test with? Run generate_sample_rtplan.py first:
    python generate_sample_rtplan.py --output sample_rtplan.dcm --n 6
    python main.py sample_rtplan.dcm
"""
from __future__ import annotations

import argparse
import os
import sys

import pandas as pd

from radiopath.dicom_reader import read_rtplan, extract_isocenters
from radiopath.models import isocenters_to_array
from radiopath.cost_matrix import build_cost_matrix
from radiopath.tsp_2opt import two_opt, route_cost
from radiopath.tsp_held_karp import held_karp, MAX_PRACTICAL_N
from radiopath import report


def run(input_path: str, outdir: str, closed: bool) -> None:
    if not os.path.isfile(input_path):
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    # 1-3: read DICOM-RT, extract + organize isocenters
    ds = read_rtplan(input_path)
    isocenters = extract_isocenters(ds)
    labels = [iso.label for iso in isocenters]
    coords = isocenters_to_array(isocenters)
    n = len(isocenters)

    report.print_input_points(isocenters)

    # 4-5: pairwise distances + cost matrix
    cost_matrix = build_cost_matrix(coords)
    report.print_cost_matrix(cost_matrix, labels)

    # 6: initial route (extraction order)
    initial_route = list(range(n))
    initial_cost = route_cost(initial_route, cost_matrix, closed)

    # 7: improve with 2-opt
    two_opt_route, two_opt_cost_val = two_opt(initial_route, cost_matrix, closed)

    rows = [
        {
            "Method": "Initial",
            "Total Cost": round(initial_cost, 2),
            "Route": report.route_to_str(initial_route, labels, closed),
        },
        {
            "Method": "2-opt",
            "Total Cost": round(two_opt_cost_val, 2),
            "Route": report.route_to_str(two_opt_route, labels, closed),
        },
    ]

    # 8: exact Held-Karp validation for small n only
    held_karp_cost_val = None
    if n <= MAX_PRACTICAL_N:
        held_karp_route, held_karp_cost_val = held_karp(cost_matrix, closed)
        rows.append(
            {
                "Method": "Held-Karp*",
                "Total Cost": round(held_karp_cost_val, 2),
                "Route": report.route_to_str(held_karp_route, labels, closed),
            }
        )
    else:
        print(f"(Held-Karp skipped: n={n} exceeds the practical limit of {MAX_PRACTICAL_N} points)\n")

    # 9-10: compare + display
    report.print_results_table(rows)
    report.print_before_after(initial_route, two_opt_route, labels, closed)

    if held_karp_cost_val is not None and held_karp_cost_val > 0:
        gap_pct = 100.0 * (two_opt_cost_val - held_karp_cost_val) / held_karp_cost_val
        print(f"2-opt vs Held-Karp gap: {gap_pct:.2f}%\n")

    print("* Held-Karp is shown only for small datasets where the exact solution is computationally practical.")
    print("NOTE: sequencing only — dose, beams, and collision safety are unchanged (see project spec).\n")

    # Save output files
    os.makedirs(outdir, exist_ok=True)
    points_path = os.path.join(outdir, "input_points.csv")
    matrix_path = os.path.join(outdir, "cost_matrix.csv")
    results_path = os.path.join(outdir, "results.csv")

    report.points_table(isocenters).to_csv(points_path, index=False)
    report.cost_matrix_table(cost_matrix, labels).to_csv(matrix_path)
    pd.DataFrame(rows).to_csv(results_path, index=False)

    print(f"Saved: {points_path}")
    print(f"Saved: {matrix_path}")
    print(f"Saved: {results_path}")


def main():
    parser = argparse.ArgumentParser(description="RadioPath isocenter sequence optimizer")
    parser.add_argument("input", help="Path to a DICOM-RT Plan (.dcm) file")
    parser.add_argument(
        "--open",
        action="store_true",
        help="Optimize an open path instead of a closed tour (no return leg to the start)",
    )
    parser.add_argument("--outdir", default="output", help="Directory to write report CSV files into")
    args = parser.parse_args()

    run(args.input, args.outdir, closed=not args.open)


if __name__ == "__main__":
    main()
