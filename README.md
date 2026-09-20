# SpecRt

**AI-Driven Radiotherapy Isocenter Sequence & Machine Transit Time Optimizer**

Reads a DICOM-RT treatment plan (`Modality = RTPLAN`) → extracts unique 3D target coordinates → calculates pairwise spatial distances and machine transit times based on couch speed ($\text{Time} = \frac{\text{Distance}}{\text{Speed}}$) → solves the optimal couch traversal visiting order using **Held-Karp Exact** ($N \le 13$) and **2-Opt Heuristic** algorithms → dynamically selects the sequence achieving the minimum total delivery time as **`OPTIMIZED`** → renders an interactive 3D WebGL trajectory space with real-time analytics, pairwise time/distance matrices, and exportable reports.

> **Clinical Disclaimer:** This software is an optimization and sequencing prototype. It does not modify beam dose, beam angles, machine physical limits, or clinical beam parameters, and does not replace medical physics collision verification.

---

## 1. Key Optimization Formulation

### A. Cost Metric: Machine Transit Time
Unlike traditional TSP prototypes that optimize purely for geometric distance, **SpecRt** formulates the optimization cost strictly as **Machine Transit Time**:

$$\text{Transit Time (s)} = \frac{\text{3D Euclidean Distance (mm)}}{\text{Machine Couch Speed (mm/s)}}$$

* **Couch Velocity Control**: The machine translation velocity (default: **`20 mm/s`**, customizable from 1 to 200 mm/s) is configured during plan upload or sample generation.
* **Clinical Benefit**: Translating distance into treatment delivery time allows clinical teams to evaluate real couch transition time reductions and overall linac room occupancy savings.

### B. Dynamic Algorithm Selection
* **Held-Karp Exact ($N \le 13$)**: Solves the Travelling Salesperson Problem to the guaranteed global optimum using dynamic programming ($O(n^2 2^n)$).
* **2-Opt Local Search Heuristic**: Rapidly optimizes paths for any number of isocenters by iteratively reversing sub-routes ($O(n^3)$ worst-case).
* **Dynamic `OPTIMIZED` Assignment**: Whichever method achieves the minimum delivery transit time is selected and tagged with the prominent **`OPTIMIZED`** badge:
  * When **Held-Karp** achieves lower transit time (e.g. 20.86s vs 21.30s), Held-Karp is designated as **`OPTIMIZED`**, while 2-Opt is labeled as **`2-OPT HEURISTIC`** with its own accurate savings.
  * When **2-Opt** achieves the lowest transit time (or for $N > 13$ where Held-Karp is skipped), 2-Opt is designated as **`OPTIMIZED`**.

---

## 2. Interactive Web Application Features

- **Two-Page Navigation Flow**:
  - **Home Page**: Frosted glass interface with configurable background image, machine speed control, route mode toggle (Closed Loop vs Open Path), and merge tolerance.
  - **Results Dashboard**: Dedicated second page displaying 3D WebGL trajectory, KPI cards, step-by-step legs, and data tables.
- **Top Browse & Sample Dropzone**:
  - Prominent **Browse File** button at the top for DICOM-RT files.
  - **Or Test Instantly** divider with 1-click sample plans: 6-target sample, 8-target sample, and 2D planar test cases.
- **Transit Time & Distance Analytics**:
  - **Transit Time Saved**: Primary metric reporting delivery time reduction in seconds and percentage.
  - **Optimized vs Initial Time**: Compares recommended sequence duration against the default DICOM beam definition order.
  - **Exact Global Gap**: Displays `0.00%` gap when the exact global optimum is applied.
- **Pairwise Time & Distance Matrix**:
  - Interactive sub-toggle allowing instant switching between **Machine Transit Time Matrix (seconds)** and **3D Distance Matrix (millimeters)**.
- **Step-by-Step Leg Transitions**:
  - Hop-by-hop cards showing transition order, target labels, leg transit time ($s$), and distance ($mm$).
- **Exporting Options**:
  - Download calculation results as JSON (`specrt_<plan>_results.json`) or formatted CSV (`specrt_<plan>_report.csv`).

---

## 3. Installation & Local Execution

### Prerequisites
- Python 3.9+
- pip

```bash
# 1. Clone the repository
git clone https://github.com/dhanush190312/SpecRT.git
cd SpecRT

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch the web server
python web_server.py
```

Open your browser to:
👉 **[http://localhost:8000](http://localhost:8000)** (or [http://127.0.0.1:8000](http://127.0.0.1:8000))

---

## 4. Deploying on Vercel

SpecRt includes pre-configured serverless settings for **Vercel** (`vercel.json` and `api/index.py`):

### Option A: 1-Click via Vercel Web Dashboard (Recommended)
1. Go to **[vercel.com](https://vercel.com)** and log in with your GitHub account.
2. Click **"Add New..."** → **"Project"**.
3. Select the **`dhanush190312/SpecRT`** repository.
4. Leave all build settings as default (`Root: ./`, `Framework: Other`).
5. Click **"Deploy"**. Your application will be live in 1–2 minutes with a global HTTPS URL.

### Option B: Deploy via Vercel CLI
```bash
npx vercel
# Follow the quick prompts in your terminal
```

---

## 5. Running via CLI

You can also run sequence optimization directly in your terminal:

```bash
# 1. (Optional) Generate a synthetic test plan with 6 isocenters
python generate_sample_rtplan.py --output sample_rtplan.dcm --n 6

# 2. Run optimization
python main.py sample_rtplan.dcm

# CLI Options:
python main.py plan.dcm --open              # Optimize an open path (one-way, no return leg)
python main.py plan.dcm --outdir results     # Change CSV output directory
```

---

## 6. Project Structure

```
SpecRt/
├── api/
│   └── index.py               # Vercel Serverless ASGI entrypoint
├── vercel.json                # Vercel Python runtime configuration
├── web_server.py              # FastAPI backend with transit time optimization
├── static/                    # Frontend assets
│   ├── index.html             # Multi-page layout (Home + Results Dashboard)
│   ├── style.css              # Custom design system with glassmorphism
│   ├── app.js                 # 3D Plotly space, time calculations & upload logic
│   └── logo.jpg               # SpecRt brand identity logo
├── sample_rtplan_2.dcm        # Sample 2D planar multi-isocenter plan
├── main.py                    # CLI optimization runner
├── generate_sample_rtplan.py  # Synthetic DICOM-RT plan generator
├── requirements.txt           # Python dependencies (pydicom, fastapi, uvicorn, numpy)
└── radiopath/                 # Core optimization package
    ├── models.py              # Isocenter data models
    ├── dicom_reader.py        # DICOM-RT parser & isocenter clustering
    ├── cost_matrix.py         # 3D Euclidean distance cost matrix builder
    ├── tsp_2opt.py            # 2-opt local search heuristic
    ├── tsp_held_karp.py       # Held-Karp exact dynamic programming solver
    └── report.py              # Reporting & route formatting utilities
```
