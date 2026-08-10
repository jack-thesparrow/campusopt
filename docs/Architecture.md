# CampusOpt — Architecture

## 1. System overview

```
                        ┌─────────────────────────┐
                        │        Frontend          │
                        │  Streamlit (v1) / React   │
                        │       (v2, optional)      │
                        └────────────┬──────────────┘
                                     │ HTTP (JSON)
                        ┌────────────▼──────────────┐
                        │       FastAPI backend      │
                        │  backend/app/api/*.py      │
                        └──┬───────────┬─────────┬──┘
                           │           │         │
              ┌────────────▼──┐ ┌──────▼─────┐ ┌─▼───────────────┐
              │ Prediction     │ │ Optimization│ │ Data layer      │
              │ layer          │ │ layer       │ │ (loaders/sim)   │
              │ (sklearn/      │ │ (OR-Tools   │ │ backend/app/    │
              │  xgboost)      │ │  CP-SAT,    │ │  data/*.py      │
              │                │ │  PuLP)      │ │                 │
              └────────────────┘ └─────────────┘ └─────────────────┘
```

The backend is a single FastAPI service exposing four route groups
(`/timetable`, `/hostel`, `/mess`, `/predict`). Each route group is
independent — there is no shared solver instance or global optimization
state, which keeps the prototype simple and makes each subproblem testable
in isolation.

**Data flow for a typical request (mess planning example):**

1. Frontend sends a scenario (mess capacities, menu day, historical
   attendance CSV or reference to a stored simulated dataset).
2. `/predict/mess-demand` runs the trained forecasting model to produce a
   predicted headcount per mess per meal slot, with a prediction interval.
3. `/mess/optimize` takes that predicted demand (plus a safety margin
   parameter the user can tune) as a **parameter**, builds the LP model, and
   solves it.
4. Response includes: the allocation/plan, the objective value, solver
   status (OPTIMAL / FEASIBLE / INFEASIBLE), and — if infeasible — a
   diagnostic (see §5).

## 2. Repository layout

```
campusopt/
├── docs/                      # this document set
├── backend/
│   └── app/
│       ├── main.py            # FastAPI app entrypoint
│       ├── api/                # route handlers, one file per subproblem
│       ├── core/               # config, logging, shared settings
│       ├── models/             # pydantic request/response schemas
│       ├── optimization/       # solver code — the mathematical core
│       │   ├── timetable_solver.py
│       │   ├── hostel_solver.py
│       │   ├── mess_solver.py
│       │   └── baselines.py    # random + greedy baselines for comparison
│       ├── prediction/         # forecasting models
│       │   ├── attendance_forecast.py
│       │   ├── mess_demand_forecast.py
│       │   └── train.py        # CLI entrypoint: train + evaluate + save
│       └── data/
│           ├── simulate.py     # synthetic NIT Mizoram-realistic data generator
│           └── loaders.py      # CSV/SQLite loaders, shared by API and scripts
├── backend/tests/              # pytest suite, mirrors app/ structure
├── frontend/
│   └── streamlit_app.py        # prototype UI
├── data/
│   ├── raw/                    # untouched simulated/exported data
│   ├── processed/              # cleaned/feature-engineered data
│   └── simulated/              # output of simulate.py, versioned by seed
├── notebooks/exploratory/      # throwaway analysis, not imported by app code
├── reports/solution_quality/   # generated benchmark reports (gitignored contents, kept dir)
├── scripts/
│   ├── generate_synthetic_data.py
│   ├── run_benchmark.py        # produces the solution-quality report
│   └── stress_test_infeasible.py
└── .github/workflows/ci.yml
```

**Rule of thumb for where new code goes:** if it decides something (a
constraint, an objective term, a variable), it belongs in `optimization/`.
If it estimates something uncertain from historical data, it belongs in
`prediction/`. If it's plumbing (schemas, request handling), it belongs in
`api/` or `models/`. Notebooks never get imported by application code — if
something from a notebook is worth keeping, promote it into a module.

## 3. Mathematical formulations

### 3.1 Timetabling

**Sets:**
- `C` — courses/sections to be scheduled
- `T` — time slots (e.g. 40 slots: 5 days × 8 periods)
- `R` — rooms, each with capacity `cap_r`
- `I` — instructors

**Given (parameters):**
- `pred_attendance_c` — predicted enrolled/attending headcount for course `c`
  (from the prediction layer; falls back to registered strength if no
  historical data exists for that course)
- `instructor_of[c] ∈ I`
- `duration_c` — number of consecutive slots course `c` needs (usually 1)

**Decision variables:**
- `x[c, t, r] ∈ {0, 1}` — 1 if course `c` is scheduled at time `t` in room `r`

**Constraints:**
1. Each course scheduled exactly once:
   `∀c: Σ_t Σ_r x[c,t,r] = 1`
2. No room double-booked:
   `∀t, r: Σ_c x[c,t,r] ≤ 1`
3. No instructor double-booked:
   `∀t, i: Σ_{c: instructor_of[c]=i} Σ_r x[c,t,r] ≤ 1`
4. Room capacity respected:
   `∀c,t,r: x[c,t,r] = 1 ⟹ cap_r ≥ pred_attendance_c`
   (implemented as `x[c,t,r] * pred_attendance_c ≤ x[c,t,r] * cap_r`, or more
   directly by only creating the variable `x[c,t,r]` when `cap_r ≥
   pred_attendance_c` — this is the preferred CP-SAT pattern since it shrinks
   the model instead of adding a constraint per variable)
5. (Soft) Instructor slot preferences / no-gap preference — implemented as
   penalty terms in the objective, not hard constraints, so the model stays
   feasible even when preferences conflict.

**Objective:** minimize a weighted sum of soft-constraint violations —
primarily **room-capacity slack** (avoid seating a 40-person section in a
120-seat room when a 45-seat room is free elsewhere at that slot) and
**instructor gap count** (idle periods between an instructor's classes on the
same day). Formally:

```
minimize   w1 * Σ_{c,t,r} x[c,t,r] * (cap_r - pred_attendance_c)
         + w2 * Σ_i gaps(i)
```

where `gaps(i)` is linearized with auxiliary boolean variables marking
"instructor i is idle at slot t but has classes both before and after that
slot on the same day."

### 3.2 Hostel allocation

**Sets:**
- `S` — students to allocate
- `B` — hostel blocks
- `Rm` — rooms, each in exactly one block, with `capacity_rm` and
  `category_rm` (e.g. general / reserved)

**Given:**
- `category_s` — the student's eligibility category
- `pref_s` — ranked list of preferred blocks (optional; degrades to
  unweighted if absent)
- `seniority_s` — used for tie-breaking / weighting priority

**Decision variables:**
- `y[s, rm] ∈ {0, 1}` — 1 if student `s` is assigned to room `rm`

**Constraints:**
1. Each student assigned to exactly one room (or zero, if we allow
   waitlisting — see infeasibility handling in §5):
   `∀s: Σ_rm y[s,rm] ≤ 1`
2. Room capacity: `∀rm: Σ_s y[s,rm] ≤ capacity_rm`
3. Category eligibility: `y[s,rm] = 0` if `category_s` is not eligible for
   `category_rm` (again, enforced by not creating the variable at all)

**Objective:** maximize total assigned students, then (secondary,
lexicographic or weighted) maximize preference satisfaction:

```
maximize   M * Σ_{s,rm} y[s,rm]
         + Σ_{s,rm} y[s,rm] * pref_score(s, rm)
```

`M` is set large enough that the model always prefers assigning one more
student over improving preference score — this is how we encode
"maximize allocation first, preferences second" without a two-stage solve.
Document the exact value of `M` in code next to where it's set (it must be
provably larger than the maximum possible total preference score in the
instance — see the comment in `hostel_solver.py`).

### 3.3 Mess planning

**Sets:**
- `M` — mess halls
- `K` — meal slots (breakfast/lunch/snacks/dinner) for the planning horizon
  (typically one day, extendable to a week)

**Given:**
- `pred_demand[m,k]` — predicted headcount for mess `m`, meal `k` (from the
  prediction layer, with a configurable safety margin `α`, e.g. plan for
  `pred_demand * (1 + α)`)
- `capacity_m` — max meals mess `m` can produce per slot (kitchen throughput)
- `cost_per_meal_m` — cost to produce one meal at mess `m`
- `waste_penalty` — cost per unit of over-production
- `shortage_penalty` — cost per unit of under-production (much higher than
  waste_penalty, since running out of food is worse than minor waste)

**Decision variables:**
- `prod[m,k] ≥ 0` (continuous or integer) — meals planned for mess `m`,
  slot `k`
- `over[m,k] ≥ 0`, `under[m,k] ≥ 0` — slack variables for
  over/under-production relative to predicted demand

**Constraints:**
1. `∀m,k: prod[m,k] ≤ capacity_m`
2. `∀m,k: prod[m,k] - pred_demand[m,k] = over[m,k] - under[m,k]`
   (standard slack decomposition so `over`/`under` are both ≥ 0 and exactly
   one is nonzero at the optimum)

**Objective:**
```
minimize   Σ_{m,k} [ cost_per_meal_m * prod[m,k]
                    + waste_penalty * over[m,k]
                    + shortage_penalty * under[m,k] ]
```

This is a straightforward LP (no integer variables strictly required unless
you want meal counts to be integral — recommended for realism, at the cost
of switching from pure LP to MIP, which is still trivial at this scale).

## 4. Solver choice rationale

- **Timetabling and hostel allocation** are combinatorial with natural
  boolean structure (assignment-type problems) — **CP-SAT** is the right
  tool: it handles boolean/integer variables natively, is very fast on
  assignment-shaped problems, and gives a proof of optimality or a
  provable gap directly.
- **Mess planning** is a continuous resource-allocation LP with a clean
  cost-minimization structure — **PuLP with CBC** is sufficient and keeps
  the dependency footprint lighter for that module. CP-SAT would also work
  if you want everything on one solver library; document whichever you pick
  in `Toolchain.md` and stay consistent.
- Both choices are swappable behind a thin interface — see
  `optimization/baselines.py` for the shared `SolverResult` shape every
  solver function returns, regardless of backend.

## 5. Infeasibility handling (required deliverable)

Every solver function returns a `SolverResult` (defined once, reused across
all three subproblems):

```python
@dataclass
class SolverResult:
    status: Literal["OPTIMAL", "FEASIBLE", "INFEASIBLE", "ERROR"]
    objective_value: float | None
    solution: dict | None          # None if INFEASIBLE
    runtime_seconds: float
    optimality_gap: float | None   # None if not applicable
    diagnostics: list[str]         # human-readable explanation, esp. for INFEASIBLE
```

When a CP-SAT model is infeasible, we do **not** just report "infeasible."
The solver module re-solves a *relaxed* version — either by:
- Dropping soft constraints first (if the original had any that were
  incorrectly marked hard), or
- Using CP-SAT's assumption/relaxation pattern: temporarily convert one
  class of hard constraint into a penalized soft constraint (e.g. allow
  category violations in hostel allocation at a heavy objective penalty) and
  re-solve, then report *which* constraint class had to be relaxed and by
  how much.

This relaxed re-solve is what produces the `diagnostics` list, e.g.:

```
["Original model INFEASIBLE: reserved-category demand (58) exceeds
  reserved-category capacity (50) by 8 beds in Block C.",
 "Relaxed solve: allocated all 50 reserved seats; 8 reserved-category
  students placed on waitlist. General-category allocation unaffected."]
```

The stress test in `scripts/stress_test_infeasible.py` and
`backend/tests/test_hostel_solver.py::test_infeasible_overbooking`
deliberately construct an over-booked instance and assert that:
1. The system never raises an unhandled exception.
2. `status == "INFEASIBLE"` on the strict model.
3. `diagnostics` is non-empty and names the specific violated constraint.
4. The relaxed solve still respects all *other* constraints exactly.

## 6. Scale targets and runtime expectations

The solution-quality report (`scripts/run_benchmark.py`) must run each
solver at three sizes and log wall-clock runtime:

| Subproblem | Small | Medium | Large |
|---|---|---|---|
| Timetabling | 20 courses / 10 rooms / 40 slots | 80 courses / 25 rooms / 40 slots | 200 courses / 40 rooms / 40 slots |
| Hostel allocation | 100 students / 120 beds | 600 students / 650 beds | 2000 students / 2100 beds |
| Mess planning | 2 messes × 4 meals (1 day) | 4 messes × 4 meals × 7 days | 6 messes × 4 meals × 30 days |

Expected runtime on a 4–8 GB dev machine: sub-second for Small, low single
digits of seconds for Medium, under 30s for Large (CP-SAT default worker
count; set `num_search_workers` explicitly and document the value used, since
this materially affects reproducibility of timing numbers).

## 7. Prediction ↔ optimization contract

To keep the two layers decoupled and independently testable, prediction
outputs are **plain data**, never solver objects. A prediction function
returns:

```python
@dataclass
class ForecastResult:
    predictions: pd.Series          # indexed by the relevant key (course_id, or (mess_id, meal_slot))
    lower_bound: pd.Series          # e.g. 10th percentile, for safety-margin use
    upper_bound: pd.Series
    mae: float                      # on the held-out test split
    rmse: float
    baseline_mae: float             # naive baseline, for comparison in the report
```

The optimization layer imports `ForecastResult.predictions` (and optionally
`upper_bound` for the safety-margin parameter) as plain parameters. This
means: (a) you can unit-test the optimizer with hand-written fake predictions
without touching sklearn, and (b) you can unit-test the predictor without
touching OR-Tools/PuLP.

## 8. API surface (v1)

```
POST /predict/attendance          -> ForecastResult (per course)
POST /predict/mess-demand         -> ForecastResult (per mess, per meal slot)

POST /timetable/optimize          -> SolverResult (timetable assignment)
POST /timetable/baseline          -> SolverResult (greedy/random, for comparison)

POST /hostel/optimize             -> SolverResult (room assignment)
POST /hostel/baseline             -> SolverResult

POST /mess/optimize               -> SolverResult (production plan)
POST /mess/baseline               -> SolverResult

GET  /health                      -> {"status": "ok"}
```

Request/response schemas are pydantic models in `backend/app/models/` — see
`DataModel.md` for the exact fields.

## 9. Frontend

Prototype UI is a single Streamlit app (`frontend/streamlit_app.py`) with
three tabs (Timetable / Hostel / Mess), each with:
- A form to adjust key parameters (dataset size, safety margin, a toggle to
  intentionally overbook and trigger the infeasible path).
- A "Solve" button that calls the FastAPI backend.
- A result panel: the allocation/schedule as a table, objective value,
  solver status, runtime, and — for the infeasible demo — the diagnostics
  list rendered clearly.
- A Plotly chart comparing optimizer objective vs. baseline objective for
  the currently selected scenario.

A React frontend is listed in `Roadmap.md` as an optional v2 upgrade; it is
not required for the prototype deliverable and the API is designed so it can
be swapped in without backend changes.
