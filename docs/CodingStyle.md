# CampusOpt — Coding Style

This document is deliberately opinionated so contributors don't have to
guess. If something isn't covered here, match the surrounding code and raise
it in the PR if you think the convention should change.

## 1. Language & formatting baseline

- Python 3.11+, type-hinted throughout. Every function signature has
  parameter and return types. Use `from __future__ import annotations` is
  **not** needed at 3.11+ (native support for most patterns), but prefer
  `list[int]` / `dict[str, float]` / `X | None` (PEP 604) over `List`,
  `Dict`, `Optional` from `typing`.
- Formatting and linting via **ruff** (`ruff format` for formatting,
  `ruff check` for linting) — no `black`/`flake8`/`isort` mix, one tool.
  Config lives in `pyproject.toml`:

  ```toml
  [tool.ruff]
  line-length = 100
  target-version = "py311"

  [tool.ruff.lint]
  select = ["E", "F", "W", "I", "UP", "B", "SIM", "N"]
  # E/W: pycodestyle, F: pyflakes, I: isort rules, UP: pyupgrade,
  # B: bugbear (catches real bugs, not just style), SIM: simplify, N: naming
  ```
- Run `ruff format . && ruff check --fix .` before every commit. CI fails on
  lint errors — don't rely on CI to catch formatting; run it locally.

## 2. Naming conventions

- `snake_case` for functions, variables, modules.
- `PascalCase` for classes (including pydantic models and dataclasses).
- Constants in `UPPER_SNAKE_CASE`, defined near top of module or in
  `core/config.py` if shared across modules.
- Solver decision variables keep their **mathematical names** from
  `Architecture.md` where practical — e.g. `x[c, t, r]` in the model
  description becomes `x = {}` / `x[(c, t, r)]` in code, not renamed to
  something generic like `assignment_var`. This keeps code and the math
  formulation in `Architecture.md` cross-referenceable at a glance. Add a
  one-line comment linking back to the constraint number, e.g.:

  ```python
  # Constraint (2): no room double-booked — Architecture.md §3.1
  for t in range(num_slots):
      for r in range(num_rooms):
          model.Add(sum(x[c, t, r] for c in eligible_courses(t, r)) <= 1)
  ```

## 3. Module boundaries (don't cross these)

- `optimization/*.py` must **never** import from `sklearn`, `xgboost`, or
  anything in `prediction/`. It receives predictions as plain data
  (`ForecastResult.predictions`, a `pandas.Series`) via function arguments.
- `prediction/*.py` must **never** import `ortools` or `pulp`.
- Neither layer calls `pd.read_csv`/`pd.read_sql` directly — all I/O goes
  through `data/loaders.py`. This is what makes both layers testable with
  in-memory fixtures (see §5).
- `api/*.py` route handlers are thin: parse request → call one function in
  `optimization/` or `prediction/` → serialize response. No business logic,
  no constraint-building, in a route handler. If a route handler is more
  than ~20 lines excluding the pydantic model definitions, that's a signal
  logic leaked into the wrong layer.

## 4. Solver code conventions

- Every solver function has this signature shape:

  ```python
  def solve_hostel_allocation(
      students: pd.DataFrame,
      rooms: pd.DataFrame,
      blocks: pd.DataFrame,
      *,
      time_limit_seconds: float = 30.0,
      num_search_workers: int = 8,
  ) -> SolverResult:
      """Solve the hostel room-assignment CSP.

      See Architecture.md §3.2 for the full mathematical formulation.
      """
      ...
  ```

  Keyword-only args after `*` for anything that's a solver tuning knob, not
  problem data — this makes call sites self-documenting
  (`solve_hostel_allocation(students, rooms, blocks, time_limit_seconds=5)`
  reads clearly; positional tuning args don't).

- Always set an explicit `time_limit_seconds` on CP-SAT
  (`solver.parameters.max_time_in_seconds = time_limit_seconds`) — an
  unbounded solve on a bad/adversarial instance (e.g. the stress test) must
  still return within a predictable time, not hang the API.
- Always set `num_search_workers` explicitly (don't rely on CP-SAT's
  default) so benchmark runtime numbers in the solution-quality report are
  reproducible across machines with different core counts — document the
  value used in the report itself.
- Never silently swallow an `INFEASIBLE` status. Every solver function must
  hit the relaxation/diagnostics path described in `Architecture.md` §5 —
  don't add a bare `except Exception: return None` anywhere in solver code.
- Baseline functions (`optimization/baselines.py`) return the **same**
  `SolverResult` shape as the real solvers, with `optimality_gap` left as
  `None` (baselines don't have a meaningful gap concept) — this keeps the
  benchmark script's comparison logic uniform.

## 5. Testing conventions

- One test file per solver/predictor module:
  `test_timetable_solver.py`, `test_hostel_solver.py`, etc.
- Tests build small, hand-written `pd.DataFrame` fixtures inline (5–10 rows)
  rather than loading from `data/simulated/` — keeps tests fast and makes
  the exact scenario being tested legible in the test file itself.
- Every solver test file includes at minimum:
  - One feasible-instance test asserting `status == "OPTIMAL"` and checking
    at least one hard constraint is actually respected in the returned
    solution (not just that a status string came back).
  - One infeasible-instance test (see `Architecture.md` §5) asserting
    graceful degradation, not a crash.
  - One test comparing the solver's objective against a hand-computed
    baseline on a tiny instance where you can verify optimality by hand.
- Predictor tests assert `mae <= baseline_mae` on the test fixture (the
  model should beat the naive baseline on held-out data — if it doesn't,
  that's a real bug, not a style nit, and the test should fail loudly).
- Run `pytest -v` locally before pushing; don't rely on CI as your first
  signal.

## 6. Docstrings and comments

- Every public function (anything importable from outside its own module)
  gets a docstring: one-line summary, then `Args`/`Returns` if the type
  hints alone don't make usage obvious. Google-style docstrings, not
  NumPy-style or reST — pick one, this project uses Google-style, be
  consistent.
- Comment the *why*, not the *what* — the code already says what it does.
  Reserve comments for: linking a constraint back to `Architecture.md`,
  explaining a non-obvious linearization trick (e.g. the `M`-large-constant
  pattern in hostel allocation), or flagging a known limitation.
- No commented-out code in commits. If it's worth keeping, it's worth a git
  branch or an issue, not a dead block in the file.

## 7. Frontend (Streamlit) conventions

- Keep `streamlit_app.py` thin — it should call the FastAPI backend over
  HTTP, never import `optimization/` or `prediction/` directly. This keeps
  the "prototype UI vs. real backend" boundary honest and means the UI can
  be swapped for React later (see `Roadmap.md`) without touching solver
  code.
- One function per tab (`render_timetable_tab()`, `render_hostel_tab()`,
  `render_mess_tab()`) — don't build one 400-line linear script.

## 8. Commit hygiene

- Commits are scoped to one logical change. "Add hostel CP-SAT model" and
  "Add hostel allocation tests" can be separate commits in the same PR; "Add
  hostel model AND fix an unrelated typo in Toolchain.md" should be two
  commits, not one.
- Commit messages: imperative mood, short summary line (~50 chars), blank
  line, then body if needed explaining *why* not *what* (the diff already
  shows what). E.g. `Add relaxation fallback for infeasible hostel model`,
  not `updates`.
