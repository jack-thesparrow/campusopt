# CampusOpt — Project Description

## 1. What this project is

CampusOpt is a hybrid **optimization + prediction** system for three coupled
resource-allocation problems that show up on every residential campus:

1. **Timetabling** — assigning courses/sections to time slots and rooms
   without clashes, subject to instructor and room capacity constraints.
2. **Hostel allocation** — assigning students to hostel rooms subject to
   capacity, category (e.g. reserved quota), and preference constraints.
3. **Mess planning** — deciding how much food to prepare per meal per mess,
   driven by a **predicted** headcount rather than a fixed or guessed number.

The unifying idea: **prediction feeds optimization**. The ML component doesn't
make decisions — it estimates uncertain inputs (how many students will
actually show up to breakfast, how attendance trends affect classroom
capacity planning). The optimizer then makes the actual allocation decision
against hard constraints, using those predictions as parameters or as a
signal to size buffers.

This is *not* a CRUD app with a scheduling UI bolted on. The grading rubric
explicitly penalizes hardcoded if/else "scheduling logic" — the core
deliverable is a real mathematical program (decision variables, constraints,
objective) solved by a real solver (OR-Tools CP-SAT or PuLP/CBC).

## 2. Why this is hard (and why it's worth doing properly)

Naive approaches fail in specific, predictable ways:

- **Greedy/first-fit allocation** (assign the first available room, then the
  next) produces clashes as soon as constraints interact (an instructor
  double-booked across two "independently greedy" assignments) and wastes
  capacity (small sections sitting in large rooms while big sections get
  split).
- **Fixed demand assumptions** (mess always cooks for 80% of registered
  strength) systematically over- or under-produce because actual attendance
  varies by day-of-week, weather, exam proximity, and menu — this is a
  forecasting problem, not a constant.
- **No infeasibility handling** — real constraint sets *will* occasionally be
  over-constrained (more students than hostel beds in a category, more
  sections than available room-hours). A system that crashes or silently
  drops constraints is worse than useless in front of a warden or academic
  office. CampusOpt must detect infeasibility, explain *why*, and propose a
  relaxation.

## 3. Scope for the prototype phase

In scope:
- A formal CP/LP model for each of the three subproblems, independently
  solvable (they *can* be composed later, but the prototype treats them as
  three services sharing infrastructure).
- One predictive model per subproblem where a genuine forecasting need
  exists (attendance forecasting for timetabling capacity, mess demand
  forecasting for mess planning). Hostel allocation is a pure CSP/assignment
  problem for the prototype — no meaningful time-series signal to forecast,
  so no predictive component is forced onto it artificially.
- Realistic **simulated** NIT Mizoram data (department list, class strength
  ranges, hostel block/room counts, mess capacity) — see `DataModel.md` for
  the exact schema and generation rules.
- A working prototype UI (Streamlit first, optionally a React frontend later)
  where a judge can input constraints/demand and see the optimized output,
  including a deliberately infeasible case.
- A solution-quality report comparing solver output against a naive baseline
  (random or greedy) at 2–3 dataset sizes, with runtime.

Out of scope for the prototype (documented in `Roadmap.md` as future work):
- Multi-campus/multi-semester rolling optimization.
- Real-time re-optimization on the fly (e.g. mid-semester room changes).
- Student-facing preference collection UI (we simulate preferences).
- Authentication/RBAC, production deployment, persistence beyond SQLite/CSV.

## 4. The three subproblems at a glance

| Subproblem | Type | Solver | Predictive input |
|---|---|---|---|
| Timetabling | Constraint Satisfaction / CSP with soft objective | OR-Tools CP-SAT | Predicted attendance per course (affects room-size assignment) |
| Hostel allocation | Assignment problem (bipartite, capacitated) | OR-Tools CP-SAT or PuLP | — (deterministic inputs: applicants, quotas, capacities) |
| Mess planning | Resource/production planning (LP) | PuLP (CBC) or OR-Tools | Predicted meal headcount per mess per meal-slot |

Full mathematical formulations for each live in `Architecture.md` §3.

## 5. Success criteria (how we know it works)

1. The optimizer produces **zero hard-constraint violations** on feasible
   instances, and the objective value is reported alongside the optimality
   gap (CP-SAT reports this natively; for PuLP we log the LP relaxation
   bound).
2. On the same instance, the optimizer's objective is measurably better than
   a random and a greedy baseline (this comparison is the "solution quality
   report" deliverable).
3. The predictive model has a genuine train/test split (temporal split, not
   random shuffle, since this is forecasting) and reports MAE/RMSE against a
   naive baseline (e.g. "predict yesterday's count" or "predict the
   7-day rolling average").
4. Feeding the system a deliberately over-constrained instance (e.g. more
   hostel applicants in a quota than beds available) produces a structured
   infeasibility report, not a crash or a silent partial allocation.
5. A judge with no prior context can open the UI, load a sample scenario,
   change one or two constraints, and see the optimizer re-solve and explain
   the result within a few seconds, for the dataset sizes we target (see
   `Architecture.md` §6 for scale targets).

## 6. Who this document set is for

This `docs/` folder is written so that a new contributor — including someone
who has never touched OR-Tools or PuLP before — can go from "cloned the repo"
to "opened a PR" without needing a synchronous walkthrough. Read order:

1. `Description.md` (this file) — what and why.
2. `Architecture.md` — system design and the actual math.
3. `DataModel.md` — schemas, simulated data generation.
4. `Toolchain.md` — environment setup (Nix flake, pip, running things).
5. `CodingStyle.md` — how code should look.
6. `Contributing.md` — workflow, branching, PR checklist.
7. `Roadmap.md` — what's built, what's next, what's explicitly deferred.
