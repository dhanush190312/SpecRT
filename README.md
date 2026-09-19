# SpecRt

Isocenter sequence optimization for radiotherapy treatment plans.

Reads a DICOM-RT plan → extracts isocenter coordinates → builds a 3D-distance cost matrix → optimizes the visiting order with **2-opt** → validates against the exact **Held-Karp** solution on small cases → renders an interactive 3D Web visualization and generates comparison reports.

> **Note:** This is a sequencing prototype only. It does not change dose, beam parameters, treatment technique, or the clinical plan, and it does not perform collision detection.

---

## 1. Installation

```bash
pip install -r requirements.txt
```

---

## 2. Running the Web Application

Launch the modern interactive web application with 3D WebGL trajectory visualization and drag-and-drop DICOM-RT upload:

```bash
python web_server.py
```

Then open your browser to:
**http://localhost:8000**

Features:
- **Two-Page Navigation Flow**: Home page with custom background image support and dedicated Results Dashboard.
- **Drag & Drop DICOM-RT**: Upload any clinical `.dcm` plan with `Modality = RTPLAN`.
- **1-Click Synthetic Sample Testing**: Test immediately with 6 or 8 target plans without needing patient files.
- **Interactive 3D WebGL Visualizer**: Inspect 3D coordinates, rotate, pan, zoom, and compare baseline vs 2-opt trajectory.
- **Exact Held-Karp Comparison**: Validates 2-opt against the exact global optimum ($N \le 13$) with real-time percentage gap metrics.
- **Export Data**: Download results as JSON or CSV reports.

---

## 3. Running via CLI

You can also run sequence optimization directly in the terminal:

```bash
# 1. (Optional) Generate a synthetic plan with 6 isocenters
python generate_sample_rtplan.py --output sample_rtplan.dcm --n 6

# 2. Run optimization
python main.py sample_rtplan.dcm
```

### CLI Options
```bash
python main.py plan.dcm --open              # optimize an open path (no return leg)
python main.py plan.dcm --outdir results     # change where CSV files are saved
```

---

## 4. Project Structure

```
SpecRt/
├── web_server.py              # FastAPI server for the web application
├── static/                    # Web frontend assets
│   ├── index.html             # Multi-page layout
│   ├── style.css              # Custom design system with glassmorphism
│   ├── app.js                 # Interactive 3D Plotly visualizer & upload logic
│   └── home_bg.jpg            # Default background image for home page
├── main.py                    # CLI entry point
├── generate_sample_rtplan.py  # Synthetic test .dcm generator
├── requirements.txt           # Python dependencies
└── radiopath/                 # Core optimization algorithms
    ├── models.py              # Isocenter data class
    ├── dicom_reader.py        # DICOM-RT reader & isocenter extraction
    ├── cost_matrix.py         # 3D Euclidean distance cost matrix
    ├── tsp_2opt.py            # 2-opt local search heuristic
    ├── tsp_held_karp.py       # Held-Karp exact dynamic programming solver
    └── report.py              # Console & CSV formatting
```

---

## 5. Algorithm Details

- **2-opt** (Main): Reverses sub-routes iteratively to find shorter traversal paths. O(n³) worst case.
- **Held-Karp** (Exact Validation): Dynamic programming TSP solver providing exact global optimum for $N \le 13$ targets ($O(n^2 2^n)$).
