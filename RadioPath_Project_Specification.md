# RadioPath — Project Specification

## 1. Project Title
**RadioPath: Isocenter Sequence Optimization for Radiotherapy Treatment Plans**

## 2. Project Idea
RadioPath is a Python-based prototype that reads a DICOM-RT treatment plan, extracts the available treatment isocenter coordinates, calculates the movement cost between the points, and uses TSP optimization to find a shorter visiting sequence.

The project focuses only on **sequence optimization**. It does not change radiation dose, beam parameters, treatment technique, or the clinical treatment plan.

## 3. Main Objective
Given a set of treatment isocenters:

> Find a visiting order that reduces the total distance between consecutive isocenters.

For the prototype, **3D Euclidean distance is used as the movement-cost proxy**.

## 4. Input
- A DICOM-RT / RT Plan file.
- Isocenter coordinates available in the treatment plan.

Example:

| Point | X | Y | Z |
|---|---:|---:|---:|
| P1 | x1 | y1 | z1 |
| P2 | x2 | y2 | z2 |
| P3 | x3 | y3 | z3 |

The actual values must come from the supplied DICOM file; example values must not be presented as real results.

## 5. Technologies
| Technology | Purpose |
|---|---|
| Python | Main implementation |
| pydicom | Read and extract information from DICOM-RT |
| Pandas | Organize isocenter data in tabular form |
| NumPy | Numerical calculations and distance/cost matrix |
| 2-opt | Main TSP route-improvement algorithm |
| Held-Karp | Exact TSP solution for small test cases / validation |

No GUI, machine-learning model, 3D visualization, or NetworkX is required for the core version.

## 6. Processing Pipeline

1. Read the DICOM-RT plan using `pydicom`.
2. Extract the required isocenter coordinates.
3. Store and organize the coordinates.
4. Calculate pairwise 3D Euclidean distances.
5. Build the cost matrix.
6. Generate an initial route.
7. Improve the route using **2-opt**.
8. For small datasets, solve the same TSP using **Held-Karp**.
9. Compare the 2-opt result with the exact Held-Karp result.
10. Display the final result table and routes.

## 7. Cost Function

For two isocenters:

\[
C_{ij} = \sqrt{(x_i-x_j)^2 + (y_i-y_j)^2 + (z_i-z_j)^2}
\]

The total route cost is the sum of the costs of all consecutive movements, including the return to the starting point if a closed TSP tour is used.

**Important:** This is a simplified distance-based movement-cost model, not a validated real-machine movement-time model.

## 8. 2-opt — Main Algorithm

2-opt is a TSP local-search heuristic.

It takes an existing route, removes two edges, reconnects the route in another way, and keeps the change when the total cost improves. It repeats this until no further 2-opt improvement is found.

### Why 2-opt?
- Simple to implement.
- Fast compared with exact TSP methods.
- Suitable for larger test cases.
- Provides a practical optimized route.

### Complexity
A straightforward iterative implementation is commonly described as having approximately **O(n³) worst-case time**, depending on implementation and stopping behavior. Route storage is **O(n)**, excluding the cost matrix.

### Limitation
2-opt is a heuristic. It **does not guarantee the globally optimal TSP route** and can stop at a local optimum.

## 9. Held-Karp — Validation Algorithm

Held-Karp is an **exact dynamic-programming algorithm for TSP**.

It systematically considers subsets of points and stores the best partial solutions.

### Why Held-Karp?
It guarantees the optimal TSP solution for the small test cases where it is computationally practical.

We use it mainly as a **benchmark/validation method**, not as the main algorithm for large datasets.

### Complexity
- Time: **O(n² 2ⁿ)**
- Space: **O(n 2ⁿ)**

### Limitation
The exponential `2ⁿ` term makes it impractical as the number of points becomes large.

## 10. Why Use Both?

They have different purposes:

| | 2-opt | Held-Karp |
|---|---|---|
| Type | Heuristic | Exact dynamic programming |
| Main purpose | Practical optimization | Validation / benchmark |
| Optimality guarantee | No | Yes |
| Complexity | ~O(n³) basic iterative version | O(n²2ⁿ) |
| Larger datasets | More suitable | Not suitable |
| Project role | **Main algorithm** | **Small-case validation** |

For a small dataset, we can compare:

```text
2-opt cost      = X
Held-Karp cost  = Y (exact optimum)
```

and calculate the percentage gap between the heuristic and the exact solution.

## 11. Collision Handling

**Collision detection is NOT part of the core implementation.**

It is a **future-scope extension**.

The current project only uses the distance-based cost matrix and TSP sequence optimization.

Possible future work:
- Machine-geometry constraints
- Gantry/couch movement constraints
- Collision-safe transition checking
- More realistic machine movement-time models

Do not implement or claim collision detection in the current version.

## 12. Expected Output

The first successful output should show the extracted isocenters:

```text
RADIOPATH - INPUT POINTS

Number of Isocenters: N

P1    X    Y    Z
P2    X    Y    Z
...
```

Then the cost matrix:

```text
COST MATRIX

       P1     P2     P3    ...
P1    0.00   ...    ...
P2    ...    0.00   ...
P3    ...    ...    0.00
```

Final output should contain a concise result table and route comparison:

| Method | Total Cost | Route |
|---|---:|---|
| Initial | X | P1 → P2 → P3 → ... |
| 2-opt | X | P1 → P3 → P2 → ... |
| Held-Karp* | X | P1 → P3 → P2 → ... |

`* Held-Karp is shown only for small datasets where the exact solution is computationally practical.`

Also display:

```text
BEFORE:
P1 → P2 → P3 → P4 → ...

AFTER (2-opt):
P1 → P3 → P2 → P4 → ...
```

## 13. Complete Flowchart

```text
┌──────────────────────┐
│      DICOM-RT        │
│     Treatment Plan   │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│       pydicom        │
│      Read File       │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Extract Isocenter    │
│     Coordinates      │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│      Pandas          │
│ Organize Point Data  │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│       NumPy          │
│ Calculate Pairwise   │
│      Distances       │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│     COST MATRIX      │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│    Initial Route     │
└──────────┬───────────┘
           │
           ▼
      ┌────┴─────┐
      │          │
      ▼          ▼
┌──────────┐ ┌──────────────┐
│  2-OPT   │ │ HELD-KARP    │
│  Main    │ │ Exact small  │
│  Route   │ │ case /       │
│Optimization││ Validation  │
└────┬─────┘ └──────┬───────┘
     │              │
     └──────┬───────┘
            ▼
┌──────────────────────┐
│   Compare Results    │
│ Cost + Route         │
└──────────┬───────────┘
           │
           ▼
┌─────────────────────────────┐
│       FINAL OUTPUT           │
│                             │
│  Result Table               │
│  Before Route               │
│  Optimized Route            │
└─────────────────────────────┘

NOTE:
Collision detection is future scope and is NOT
included in the current implementation.
```

## 14. Final Project Statement

**RadioPath is a prototype that extracts treatment isocenters from a DICOM-RT plan and formulates their sequencing as a distance-based Travelling Salesman Problem. 2-opt is used as the practical route-optimization method, while Held-Karp is used on small datasets to obtain the exact optimum and validate the heuristic result.**

The project does **not** claim clinical validation or real-machine collision safety.
