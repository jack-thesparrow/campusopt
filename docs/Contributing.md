# Contributing to CampusOpt

Welcome. This doc is written for someone joining the project with zero
context — if you follow it top to bottom you should be able to get a PR
merged without needing to ask "how do I even start."

## 1. Before you write any code

1. Read `Description.md` and `Architecture.md` — at minimum, the section
   for the subproblem you're touching. Don't start writing a solver
   constraint you haven't first found in the formulation in `Architecture.md
   §3` — if it's not there, the model description is out of date and that's
   its own PR (update the doc first, get it reviewed, then implement).
2. Set up your environment per `Toolchain.md` (Nix flake or pip venv) and
   confirm `pytest backend/tests` passes on a clean clone before you change
   anything — this tells you the baseline is green and any future red is
   yours to fix.
3. Check open issues / the project board for something already scoped
   before inventing new work — especially early on, avoid parallel effort on
   the same solver module.

## 2. Branching and workflow

- `main` is always green (CI passing) and always demoable.
- Branch naming: `feature/<short-description>`, `fix/<short-description>`,
  `docs/<short-description>`. E.g. `feature/hostel-relaxation-diagnostics`.
- No direct commits to `main` — even for the project lead. Everything goes
  through a PR, even a one-line docs fix, so there's a review trail and CI
  runs before merge.
- Rebase on `main` before opening a PR if your branch has drifted; don't
  merge `main` into your feature branch repeatedly (keeps history readable).

## 3. Making a change — step by step

1. Create your branch off latest `main`.
2. If your change affects the data schema, update `DataModel.md` **in the
   same PR** as the code change — schema and docs must never drift apart.
   Same rule for `Architecture.md` if you're changing a constraint or
   objective term.
3. Write the code following `CodingStyle.md`.
4. Write/update tests. A PR that adds solver logic without a corresponding
   test in `backend/tests/` will be asked to add one before merge — this
   isn't optional even under time pressure, because the infeasibility and
   correctness guarantees are the actual deliverable of this project, not
   the UI.
5. Run locally, in order:
   ```bash
   ruff format .
   ruff check --fix .
   pytest backend/tests -v
   ```
6. Push, open a PR against `main`. Fill in the PR template (see §4).
7. Address review comments as new commits (don't force-push over review
   history until the PR is approved and you're doing a final cleanup
   squash).

## 4. PR checklist (paste this into your PR description)

```markdown
## What
<one or two sentences: what does this PR do>

## Why
<link an issue if one exists, or explain the motivation>

## Checklist
- [ ] Code follows CodingStyle.md (ruff format + check pass locally)
- [ ] Tests added/updated, `pytest backend/tests` passes locally
- [ ] If schema changed: DataModel.md updated in this PR
- [ ] If a constraint/objective changed: Architecture.md updated in this PR
- [ ] If infeasibility handling touched: stress test still passes
      (`python scripts/stress_test_infeasible.py --subproblem <name>`)
- [ ] No commented-out code, no stray print() debugging left in
```

## 5. Review expectations

- At least one approving review before merge, even on a small team — a
  second pair of eyes on constraint logic specifically catches real bugs
  (off-by-one on slot indices, a constraint that's accidentally soft when it
  should be hard, etc.) that are easy to miss reading your own code.
- Reviewers should actually run the test suite locally on the branch for
  any PR touching `optimization/` or `prediction/`, not just read the diff —
  solver correctness bugs frequently look fine in a diff and fail on an
  actual instance.
- If you're reviewing and don't understand *why* a constraint is formulated
  a certain way, ask — don't approve on trust. Referencing back to
  `Architecture.md §3` should resolve most "why" questions; if it doesn't,
  that's a sign the doc needs updating.

## 6. Data handling rule

This project only ever uses **simulated** data for the prototype (see
`DataModel.md §1`). If at any point real student data (attendance rolls,
actual hostel rosters) is introduced for a later milestone:
- It goes in `data/raw/`, which must be `.gitignore`'d — never commit real
  student records to the repo, public or private.
- Strip/hash any direct identifier (name, roll number) before it touches
  any code path outside a clearly-marked `data/raw/` ingestion script.
- Flag this explicitly in the PR description if a change touches real-data
  handling, so it gets extra review attention.

This isn't yet a live concern for the prototype phase (all data is
synthetic per `simulate.py`), but the rule exists now so it's not
retrofitted under deadline pressure later.

## 7. Issue labels

- `good-first-issue` — scoped, doesn't require deep OR-Tools/PuLP
  familiarity (e.g. a Streamlit UI tweak, a docs fix, adding a new feature
  column to the simulator).
- `solver` — touches `optimization/`, needs the reviewer expectations in §5.
- `prediction` — touches `prediction/`.
- `infra` — CI, Nix flake, dependency bumps.
- `docs` — this `docs/` folder.

## 8. Getting unstuck

- If you're new to OR-Tools CP-SAT: read the constraint you're implementing
  in `Architecture.md §3` first, then look at an existing similar
  constraint already in the codebase (e.g. if you're adding a new
  hostel constraint, look at how the existing capacity constraint is
  written in `hostel_solver.py`) before reaching for OR-Tools' own docs —
  matching the existing pattern in this repo is usually faster than
  re-deriving the idiom from scratch.
- If a solver test is failing and you can't tell if it's your constraint
  logic or your test fixture that's wrong: shrink the fixture further (2–3
  entities, not 5–10) until you can verify the expected answer by hand.
- Genuinely stuck for more than ~30 minutes: open a draft PR with what you
  have and a comment describing where you're stuck, rather than sitting on
  an uncommitted branch — someone can usually spot the issue faster looking
  at a diff than a description.
