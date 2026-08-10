# CampusOpt — Roadmap

This roadmap is organized by milestone, not by calendar date, since team
velocity varies. Each milestone lists its **exit criteria** — don't move to
the next milestone until the current one's criteria are actually met; a
half-working optimizer is worse for the final demo than a fully-working
smaller scope.

## Milestone 0 — Project scaffolding (do this first)

- [ ] Repo structure matches `Architecture.md §2`.
- [ ] `flake.nix` (or `requirements.txt` for the pip path) working — a new
      contributor can clone and run `nix develop` (or set up the venv) and
      `pytest backend/tests` passes on an empty/skeleton test suite.
- [ ] CI (`ci.yml`) runs lint + test on every push, even before there's real
      logic to test (a trivial `test_placeholder.py` is fine initially).
- [ ] `simulate.py` produces valid CSVs matching `DataModel.md` schemas for
      at least the `small` scale.

**Exit criteria:** `nix develop && pytest` (or pip equivalent) is green on a
clean clone, CI badge is green, `data/simulated/*.csv` exist and match the
documented schema.

## Milestone 1 — One subproblem end-to-end (recommend: hostel allocation)

Pick the *simplest* subproblem first to validate the whole pipeline
shape (data → solver → API → UI) before parallelizing across three. Hostel
allocation is recommended as the first vertical slice because it has no
predictive component — it isolates "can we build and solve a real CP-SAT
model correctly" from "can we also do forecasting," which is useful to
de-risk separately.

- [ ] `hostel_solver.py` implements the formulation in `Architecture.md
      §3.2`, returns `SolverResult`.
- [ ] `baselines.py` has a random and a greedy hostel baseline.
- [ ] `test_hostel_solver.py` covers: feasible case, infeasible case with
      relaxation diagnostics, and a hand-verifiable small optimality check.
- [ ] `/hostel/optimize` and `/hostel/baseline` API routes wired up.
- [ ] Streamlit hostel tab: load a scenario, adjust overbooking toggle,
      solve, see result table + objective + status.
- [ ] `scripts/stress_test_infeasible.py --subproblem hostel` passes and
      produces a clear diagnostics message.

**Exit criteria:** a judge (or teammate who's never seen the code) can open
the Streamlit hostel tab, click solve on a feasible scenario, then flip the
overbook toggle and see the infeasible case handled gracefully — end to end,
no crashes, no manual file editing required.

## Milestone 2 — Predictive component + second subproblem (mess planning)

Mess planning is the natural second slice: it exercises the
prediction-to-optimization contract (`Architecture.md §7`) that hostel
allocation doesn't need.

- [ ] `mess_demand_forecast.py`: temporal train/test split, trained model
      (start with linear regression or a simple tree-based model — this is
      explicitly acceptable per the problem statement; don't over-engineer
      before the baseline works), reports MAE/RMSE vs. naive baseline.
- [ ] `mess_solver.py` implements `Architecture.md §3.3`, consumes
      `ForecastResult.predictions` as a parameter (not hardcoded demand).
- [ ] `test_prediction.py` asserts trained MAE ≤ naive baseline MAE on the
      held-out split.
- [ ] `/predict/mess-demand`, `/mess/optimize`, `/mess/baseline` routes.
- [ ] Streamlit mess tab, following the hostel tab's pattern.

**Exit criteria:** the demand-forecast MAE beats the naive baseline on the
committed simulated dataset, and the mess solver visibly uses the
*predicted* number (not the raw registered count) — verify this by checking
the plan changes when you retrain on a modified `attendance_history.csv`
that shifts the exam-week attendance-drop pattern.

## Milestone 3 — Third subproblem (timetabling) + full benchmark report

Timetabling is left for last since it's the largest formulation (three
index sets instead of two) and benefits from the CP-SAT patterns already
proven out in Milestone 1.

- [ ] `attendance_forecast.py` + `timetable_solver.py` per
      `Architecture.md §3.1`.
- [ ] Soft-constraint objective (room-capacity slack, instructor gaps)
      implemented and documented with which weights were chosen and why.
- [ ] `scripts/run_benchmark.py` runs all three subproblems at Small/Medium/
      Large (per `Architecture.md §6`) and writes the solution-quality
      report to `reports/solution_quality/`.
- [ ] Streamlit timetable tab.

**Exit criteria:** the full solution-quality report exists, is committed,
and shows the optimizer beating both baselines at every scale tested, with
runtime numbers that fit the targets in `Architecture.md §6`. This report is
itself a required deliverable — treat generating it as a real milestone, not
an afterthought script run once at the end.

## Milestone 4 — Polish for demo

- [ ] All three Streamlit tabs consistent in layout/interaction pattern.
- [ ] A "sample scenario" preset per tab so a judge doesn't have to hand-
      construct an interesting input from scratch.
- [ ] The infeasible-case demo is a one-click toggle in the UI for all three
      subproblems, not just hostel.
- [ ] README at repo root has a 2-minute "what is this and how do I run it"
      summary linking into this `docs/` folder for detail.
- [ ] Solution-quality report and a short written summary of the
      infeasibility-handling behavior are both linked from the README, since
      these are explicit rubric deliverables — don't make a judge dig for
      them.

**Exit criteria:** someone who has never seen the project can clone the
repo, follow `Toolchain.md`, and give a live demo of all three subproblems
including one infeasible case, in under 10 minutes, without you in the room.

## Explicitly deferred (v2 / post-prototype — do not start these early)

These are real ideas but starting them before Milestone 4 is done risks the
core deliverable. Listed here so they're not lost, not so they get built
early:

- **React frontend** replacing/supplementing Streamlit — the API is already
  designed decoupled from the UI (`Architecture.md §9`) so this is additive,
  not a rewrite, when it happens.
- **Joint optimization across subproblems** — e.g. timetable-aware mess
  demand (lunch demand shifts based on which sections have back-to-back
  morning labs). Interesting, genuinely harder (couples all three models),
  explicitly out of scope for the prototype per `Description.md §3`.
- **XGBoost/stronger models** for forecasting once the linear/tree baseline
  is proven — don't reach for this before the simple model's MAE numbers
  exist to compare against; "we beat our own baseline" is a meaningless
  claim without the simple-model number on record first.
- **Rolling / online re-optimization** as new data arrives mid-semester.
- **Auth, persistence beyond CSV/SQLite, multi-tenant (multi-campus)
  support** — infra scope, not algorithmic scope, and not what this rubric
  is scoring.
- **Student preference collection UI** — currently simulated; a real
  collection flow is a product feature, not an optimization-model feature.

## How to update this roadmap

When a milestone's exit criteria are met, check its boxes in the PR that
completes it and move the "current milestone" marker (add one here, e.g. a
`> **Current: Milestone 2**` line at the top) so anyone opening this doc
knows where the project actually stands without reading every checkbox.
