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


def _process_optimization(ds, closed: bool = True, tolerance_mm: float = 0.1, filename: str = "plan.dcm"):
    start_time = time.perf_counter()

    isocenters = extract_isocenters(ds, tolerance_mm=tolerance_mm)
    n = len(isocenters)
    if n == 0:
        raise ValueError("No valid isocenters could be extracted from this plan.")

    labels = [iso.label for iso in isocenters]
    coords = isocenters_to_array(isocenters)

    # Pairwise cost matrix
    cost_matrix = build_cost_matrix(coords)

    # Initial route (sequential 0..n-1)
    initial_route = list(range(n))
    initial_cost = route_cost(initial_route, cost_matrix, closed)

    # 2-opt optimization
    two_opt_route, two_opt_cost = two_opt(initial_route, cost_matrix, closed)

    # Held-Karp exact validation for small n
    held_karp_route = None
    held_karp_cost = None
    held_karp_gap_pct = None

    if n <= MAX_PRACTICAL_N:
        held_karp_route, held_karp_cost = held_karp(cost_matrix, closed)
        if held_karp_cost > 0:
            held_karp_gap_pct = round(
                100.0 * (two_opt_cost - held_karp_cost) / held_karp_cost, 2
            )
        else:
            held_karp_gap_pct = 0.0

    # Determine recommended algorithm & route (Use Held-Karp exact solution if available and equal or better than 2-opt)
    if held_karp_route is not None and (held_karp_cost <= two_opt_cost + 1e-6):
        recommended_route = held_karp_route
        recommended_cost = held_karp_cost
        algorithm_used = "Held-Karp (Exact)"
        algorithm_tag = "(Held-Karp Exact)"
    else:
        recommended_route = two_opt_route
        recommended_cost = two_opt_cost
        algorithm_used = "2-Opt"
        algorithm_tag = "(2-Opt)"

    reduction_mm = max(0.0, initial_cost - recommended_cost)
    reduction_pct = (
        round((reduction_mm / initial_cost) * 100.0, 2) if initial_cost > 0 else 0.0
    )

    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

    # Calculate leg-by-leg step details for recommended route
    step_legs = []
    route_len = len(recommended_route)
    num_hops = route_len if closed and route_len > 1 else route_len - 1
    for idx in range(num_hops):
        from_idx = recommended_route[idx]
        to_idx = recommended_route[(idx + 1) % route_len] if closed else recommended_route[idx + 1]
        dist = float(cost_matrix[from_idx, to_idx])
        step_legs.append({
            "step": idx + 1,
            "from_label": labels[from_idx],
            "from_index": from_idx,
            "to_label": labels[to_idx],
            "to_index": to_idx,
            "distance_mm": round(dist, 2),
        })

    return {
        "success": True,
        "filename": filename,
        "closed": closed,
        "n_isocenters": n,
        "tolerance_mm": tolerance_mm,
        "execution_time_ms": elapsed_ms,
        "algorithm_used": algorithm_used,
        "algorithm_tag": algorithm_tag,
        "metrics": {
            "initial_distance_mm": round(initial_cost, 2),
            "optimized_distance_mm": round(recommended_cost, 2),
            "distance_saved_mm": round(reduction_mm, 2),
            "savings_percent": reduction_pct,
            "held_karp_gap_pct": held_karp_gap_pct,
            "held_karp_eligible": n <= MAX_PRACTICAL_N,
        },
        "routes": {
            "initial": {
                "indices": initial_route,
                "labels": [labels[i] for i in initial_route],
                "path_str": route_to_str(initial_route, labels, closed),
                "cost": round(initial_cost, 2),
            },
            "optimized": {
                "indices": recommended_route,
                "labels": [labels[i] for i in recommended_route],
                "path_str": route_to_str(recommended_route, labels, closed),
                "cost": round(recommended_cost, 2),
                "legs": step_legs,
                "algorithm_used": algorithm_used,
                "algorithm_tag": algorithm_tag,
            },
            "two_opt": {
                "indices": two_opt_route,
                "labels": [labels[i] for i in two_opt_route],
                "path_str": route_to_str(two_opt_route, labels, closed),
                "cost": round(two_opt_cost, 2),
            },
            "held_karp": {
                "indices": held_karp_route,
                "labels": [labels[i] for i in held_karp_route] if held_karp_route else [],
                "path_str": route_to_str(held_karp_route, labels, closed) if held_karp_route else None,
                "cost": round(held_karp_cost, 2) if held_karp_cost is not None else None,
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
        "cost_matrix": [
            [round(float(val), 2) for val in row] for row in cost_matrix
        ],
        "labels": labels,
    }


@app.post("/api/optimize")
async def optimize_uploaded_file(
    file: UploadFile = File(...),
    closed: bool = Form(True),
    tolerance_mm: float = Form(0.1),
):
    """Parse uploaded DICOM-RT file in-memory and return TSP optimization."""
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
):
    """Generate in-memory synthetic RT plan and optimize it."""
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
            filename=f"synthetic_{n}_isocenters.dcm",
        )
        return JSONResponse(content=results)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate sample: {str(exc)}")


@app.post("/api/sample2")
async def optimize_sample2(
    closed: bool = Form(True),
):
    """Load sample_rtplan_2.dcm (2D Planar dataset) and optimize it."""
    try:
        ds = read_rtplan("sample_rtplan_2.dcm")
        results = _process_optimization(
            ds=ds,
            closed=closed,
            tolerance_mm=0.1,
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
