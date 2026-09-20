#!/usr/bin/env python3
"""
RadioPath Web Server
FastAPI backend for Radiotherapy Isocenter Sequence Optimization.
"""
from __future__ import annotations

import io
import time
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from generate_sample_rtplan import generate_sample_rtplan
from radiopath.cost_matrix import build_cost_matrix
from radiopath.dicom_reader import extract_isocenters, read_rtplan
from radiopath.models import isocenters_to_array
from radiopath.report import route_to_str
from radiopath.tsp_2opt import route_cost, two_opt
from radiopath.tsp_held_karp import MAX_PRACTICAL_N, held_karp

app = FastAPI(
    title="SpecRt Web API",
    description="Isocenter sequence optimization for radiotherapy treatment plans",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _process_optimization(
    ds,
    closed: bool = True,
    tolerance_mm: float = 0.1,
    filename: str = "plan.dcm",
    machine_speed_mms: float = 20.0,
):
    start_time = time.perf_counter()

    isocenters = extract_isocenters(ds, tolerance_mm=tolerance_mm)
    n = len(isocenters)
    if n == 0:
        raise ValueError("No valid isocenters could be extracted from this plan.")

    labels = [iso.label for iso in isocenters]
    coords = isocenters_to_array(isocenters)

    speed = max(0.01, float(machine_speed_mms))

    # 1. Physical 3D Euclidean distance matrix (in mm)
    distance_matrix = build_cost_matrix(coords)

    # 2. Machine Transit Time matrix (in seconds) = distance / machine_speed
    # COST IS STRICTLY TIME
    time_matrix = distance_matrix / speed
    cost_matrix = time_matrix

    # Initial route (sequential 0..n-1)
    initial_route = list(range(n))
    initial_time_s = route_cost(initial_route, time_matrix, closed)
    initial_dist_mm = route_cost(initial_route, distance_matrix, closed)

    # 2-opt optimization (minimizing machine transit time)
    two_opt_route, two_opt_time_s = two_opt(initial_route, cost_matrix, closed)
    two_opt_dist_mm = route_cost(two_opt_route, distance_matrix, closed)

    # Held-Karp exact validation for small n (minimizing machine transit time)
    held_karp_route = None
    held_karp_time_s = None
    held_karp_dist_mm = None
    held_karp_gap_pct = None

    if n <= MAX_PRACTICAL_N:
        held_karp_route, held_karp_time_s = held_karp(cost_matrix, closed)
        held_karp_dist_mm = route_cost(held_karp_route, distance_matrix, closed)
        if held_karp_time_s > 0:
            held_karp_gap_pct = round(
                100.0 * (two_opt_time_s - held_karp_time_s) / held_karp_time_s, 2
            )
        else:
            held_karp_gap_pct = 0.0

    # Determine recommended algorithm & route (Choose lowest transit time)
    if held_karp_route is not None and (held_karp_time_s <= two_opt_time_s + 1e-6):
        recommended_route = held_karp_route
        recommended_time_s = held_karp_time_s
        recommended_dist_mm = held_karp_dist_mm
        algorithm_used = "Held-Karp (Exact)"
        algorithm_tag = "(Held-Karp Exact)"
    else:
        recommended_route = two_opt_route
        recommended_time_s = two_opt_time_s
        recommended_dist_mm = two_opt_dist_mm
        algorithm_used = "2-Opt"
        algorithm_tag = "(2-Opt)"

    time_saved_s = max(0.0, initial_time_s - recommended_time_s)
    time_saved_pct = (
        round((time_saved_s / initial_time_s) * 100.0, 2) if initial_time_s > 0 else 0.0
    )
    dist_saved_mm = max(0.0, initial_dist_mm - recommended_dist_mm)
    dist_saved_pct = (
        round((dist_saved_mm / initial_dist_mm) * 100.0, 2) if initial_dist_mm > 0 else 0.0
    )

    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

    # Leg-by-leg step details (distance in mm and machine transit time in seconds)
    step_legs = []
    route_len = len(recommended_route)
    num_hops = route_len if closed and route_len > 1 else route_len - 1
    for idx in range(num_hops):
        from_idx = recommended_route[idx]
        to_idx = recommended_route[(idx + 1) % route_len] if closed else recommended_route[idx + 1]
        dist = float(distance_matrix[from_idx, to_idx])
        hop_time = float(time_matrix[from_idx, to_idx])
        step_legs.append({
            "step": idx + 1,
            "from_label": labels[from_idx],
            "from_index": from_idx,
            "to_label": labels[to_idx],
            "to_index": to_idx,
            "distance_mm": round(dist, 2),
            "time_s": round(hop_time, 2),
        })

    is_held_karp_best = held_karp_route is not None and (held_karp_time_s <= two_opt_time_s + 1e-6)

    return {
        "success": True,
        "filename": filename,
        "closed": closed,
        "n_isocenters": n,
        "tolerance_mm": tolerance_mm,
        "machine_speed_mms": speed,
        "execution_time_ms": elapsed_ms,
        "algorithm_used": algorithm_used,
        "algorithm_tag": algorithm_tag,
        "metrics": {
            # Primary time metrics
            "machine_speed_mms": speed,
            "initial_time_s": round(initial_time_s, 2),
            "optimized_time_s": round(recommended_time_s, 2),
            "time_saved_s": round(time_saved_s, 2),
            "savings_percent": time_saved_pct,
            # Physical distance metrics
            "initial_distance_mm": round(initial_dist_mm, 2),
            "optimized_distance_mm": round(recommended_dist_mm, 2),
            "distance_saved_mm": round(dist_saved_mm, 2),
            "distance_savings_percent": dist_saved_pct,
            # Algorithm optimality
            "held_karp_gap_pct": held_karp_gap_pct,
            "held_karp_eligible": n <= MAX_PRACTICAL_N,
            # Detailed algorithm comparisons
            "two_opt_time_s": round(two_opt_time_s, 2),
            "two_opt_time_saved_s": round(max(0.0, initial_time_s - two_opt_time_s), 2),
            "two_opt_time_saved_pct": round(max(0.0, (initial_time_s - two_opt_time_s) / initial_time_s * 100.0), 2) if initial_time_s > 0 else 0.0,
            "two_opt_dist_mm": round(two_opt_dist_mm, 2),
            "two_opt_dist_saved_mm": round(max(0.0, initial_dist_mm - two_opt_dist_mm), 2),
            "held_karp_time_s": round(held_karp_time_s, 2) if held_karp_time_s is not None else None,
            "held_karp_time_saved_s": round(max(0.0, initial_time_s - held_karp_time_s), 2) if held_karp_time_s is not None else None,
            "held_karp_time_saved_pct": round(max(0.0, (initial_time_s - held_karp_time_s) / initial_time_s * 100.0), 2) if (held_karp_time_s is not None and initial_time_s > 0) else None,
            "held_karp_dist_mm": round(held_karp_dist_mm, 2) if held_karp_dist_mm is not None else None,
            "held_karp_dist_saved_mm": round(max(0.0, initial_dist_mm - held_karp_dist_mm), 2) if held_karp_dist_mm is not None else None,
        },
        "routes": {
            "initial": {
                "indices": initial_route,
                "labels": [labels[i] for i in initial_route],
                "path_str": route_to_str(initial_route, labels, closed),
                "time_s": round(initial_time_s, 2),
                "distance_mm": round(initial_dist_mm, 2),
                "cost": round(initial_time_s, 2),
                "savings_time_s": 0.0,
                "savings_percent": 0.0,
                "status": "Baseline",
            },
            "optimized": {
                "indices": recommended_route,
                "labels": [labels[i] for i in recommended_route],
                "path_str": route_to_str(recommended_route, labels, closed),
                "time_s": round(recommended_time_s, 2),
                "distance_mm": round(recommended_dist_mm, 2),
                "cost": round(recommended_time_s, 2),
                "legs": step_legs,
                "algorithm_used": algorithm_used,
                "algorithm_tag": algorithm_tag,
                "savings_time_s": round(time_saved_s, 2),
                "savings_percent": time_saved_pct,
                "savings_distance_mm": round(dist_saved_mm, 2),
                "status": "Optimized",
            },
            "two_opt": {
                "indices": two_opt_route,
                "labels": [labels[i] for i in two_opt_route],
                "path_str": route_to_str(two_opt_route, labels, closed),
                "time_s": round(two_opt_time_s, 2),
                "distance_mm": round(two_opt_dist_mm, 2),
                "cost": round(two_opt_time_s, 2),
                "savings_time_s": round(max(0.0, initial_time_s - two_opt_time_s), 2),
                "savings_percent": round(max(0.0, (initial_time_s - two_opt_time_s) / initial_time_s * 100.0), 2) if initial_time_s > 0 else 0.0,
                "status": "2-Opt Heuristic" if is_held_karp_best else "Optimized",
            },
            "held_karp": {
                "indices": held_karp_route,
                "labels": [labels[i] for i in held_karp_route] if held_karp_route else [],
                "path_str": route_to_str(held_karp_route, labels, closed) if held_karp_route else None,
                "time_s": round(held_karp_time_s, 2) if held_karp_time_s is not None else None,
                "distance_mm": round(held_karp_dist_mm, 2) if held_karp_dist_mm is not None else None,
                "cost": round(held_karp_time_s, 2) if held_karp_time_s is not None else None,
                "savings_time_s": round(max(0.0, initial_time_s - held_karp_time_s), 2) if held_karp_time_s is not None else None,
                "savings_percent": round(max(0.0, (initial_time_s - held_karp_time_s) / initial_time_s * 100.0), 2) if (held_karp_time_s is not None and initial_time_s > 0) else None,
                "status": "Optimized" if is_held_karp_best else "Exact Global",
            } if held_karp_route is not None else None,
        },
        "isocenters": [
            {
                "index": i,
                "label": iso.label,
                "x": round(iso.x, 2),
                "y": round(iso.y, 2),
                "z": round(iso.z, 2),
                "beam_names": iso.beam_names,
            }
            for i, iso in enumerate(isocenters)
        ],
        "time_matrix": [
            [round(float(val), 2) for val in row] for row in time_matrix
        ],
        "distance_matrix": [
            [round(float(val), 2) for val in row] for row in distance_matrix
        ],
        "cost_matrix": [
            [round(float(val), 2) for val in row] for row in time_matrix
        ],
        "labels": labels,
    }


@app.post("/api/optimize")
async def optimize_uploaded_file(
    file: UploadFile = File(...),
    closed: bool = Form(True),
    tolerance_mm: float = Form(0.1),
    machine_speed_mms: float = Form(20.0),
):
    """Parse uploaded DICOM-RT file in-memory and return TSP optimization based on machine transit time."""
    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        buf = io.BytesIO(content)
        ds = read_rtplan(buf)
        results = _process_optimization(
            ds=ds,
            closed=closed,
            tolerance_mm=tolerance_mm,
            machine_speed_mms=machine_speed_mms,
            filename=file.filename or "uploaded_plan.dcm",
        )
        return JSONResponse(content=results)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error processing DICOM: {str(exc)}")


@app.post("/api/sample")
async def generate_and_optimize_sample(
    n: int = Form(6),
    closed: bool = Form(True),
    seed: Optional[int] = Form(None),
    machine_speed_mms: float = Form(20.0),
):
    """Generate in-memory synthetic RT plan and optimize machine transit time."""
    try:
        effective_seed = seed if seed is not None else int(time.time() * 1000) % 100000
        buf = io.BytesIO()
        generate_sample_rtplan(buf, n_isocenters=max(2, min(n, 15)), seed=effective_seed)
        buf.seek(0)
        ds = read_rtplan(buf)
        results = _process_optimization(
            ds=ds,
            closed=closed,
            tolerance_mm=0.1,
            machine_speed_mms=machine_speed_mms,
            filename=f"synthetic_{n}_isocenters.dcm",
        )
        return JSONResponse(content=results)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate sample: {str(exc)}")


@app.post("/api/sample2")
async def optimize_sample2(
    closed: bool = Form(True),
    machine_speed_mms: float = Form(20.0),
):
    """Load sample_rtplan_2.dcm (2D Planar dataset) and optimize machine transit time."""
    try:
        ds = read_rtplan("sample_rtplan_2.dcm")
        results = _process_optimization(
            ds=ds,
            closed=closed,
            tolerance_mm=0.1,
            machine_speed_mms=machine_speed_mms,
            filename="sample_rtplan_2.dcm (2D Planar)",
        )
        return JSONResponse(content=results)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load sample 2: {str(exc)}")


@app.get("/")
async def serve_index():
    return FileResponse("static/index.html")


# Mount static assets
app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web_server:app", host="127.0.0.1", port=8000, reload=True)
