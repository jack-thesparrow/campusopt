# CampusOpt — Toolchain & Environment Setup

## 1. What you need

| Tool | Version | Why |
|---|---|---|
| Python | 3.11+ | backend, solver code, ML |
| Google OR-Tools | latest via pip | CP-SAT solver (timetabling, hostel) |
| PuLP | latest via pip | LP solver via CBC (mess planning) |
| pandas | latest | data wrangling |
| scikit-learn | latest | attendance / demand forecasting |
| xgboost | optional | swap-in for stronger forecasting once linear/tree baseline is working |
| FastAPI + uvicorn | latest | backend API |
| Streamlit | latest | prototype frontend |
| Plotly | latest | charts in Streamlit and in the benchmark report |
| pytest | latest | test suite |
| ruff | latest | linting + formatting (see `CodingStyle.md`) |
| Node.js | 20+ | only needed if/when the optional React frontend (Roadmap v2) is built |

Two supported ways to get this environment: **Nix flake** (recommended,
fully reproducible, no "works on my machine") or **plain pip + venv**
(simpler if you've never used Nix). Both are documented below — pick one,
don't mix them for the same working copy.

## 2. Option A — Nix flake (recommended)

A `flake.nix` is provided at the repo root. It pins Python and every solver
dependency exactly, and gives you `rust-analyzer`-style zero-setup tooling:
one `nix develop` and everything is on `PATH`, including `ruff`, `pytest`,
and a pre-built virtualenv for anything not packaged in nixpkgs.

```bash
# from repo root
nix develop
# you're now in a shell with python, or-tools, pulp, fastapi, streamlit,
# ruff, pytest all available
```

Because `ortools` and some ML packages (e.g. `xgboost`) have compiled
native extensions that aren't always cleanly packaged in nixpkgs, the flake
uses the same pattern as the CloudFree-LISS-IV and rust-lang setups: a
`shellHook` that provisions a `.venv-nix-extras` for pip-only packages,
layered on top of the Nix-provided interpreter, so you get reproducible
system-level deps (Python itself, any C libraries CBC/OR-Tools need) plus
normal `pip install` for anything nixpkgs doesn't package well.

```nix
# flake.nix (abridged — see the actual file at repo root)
{
  description = "CampusOpt dev environment";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  inputs.flake-utils.url = "github:numtide/flake-utils";

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let pkgs = import nixpkgs { inherit system; };
      in {
        devShells.default = pkgs.mkShell {
          buildInputs = [
            pkgs.python311
            pkgs.python311Packages.pip
            pkgs.python311Packages.virtualenv
            pkgs.nodejs_20   # only needed for the optional React v2 frontend
          ];
          shellHook = ''
            if [ ! -d .venv-nix-extras ]; then
              python -m venv .venv-nix-extras
            fi
            source .venv-nix-extras/bin/activate
            pip install -q -r backend/requirements.txt
          '';
        };
      });
}
```

First run will take a minute (venv creation + pip install); subsequent
`nix develop` calls are fast since the venv persists on disk (it's
gitignored — see `.gitignore`).

If you use direnv, add a `.envrc` with `use flake` so the shell activates
automatically on `cd`.

## 3. Option B — plain pip + venv

```bash
git clone <repo-url> campusopt
cd campusopt
python3.11 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
```

`backend/requirements.txt` (create this file if it doesn't exist yet, keep
it pinned with `==` once the dependency set stabilizes):

```
fastapi
uvicorn[standard]
ortools
pulp
pandas
scikit-learn
xgboost
streamlit
plotly
pydantic
pytest
ruff
python-multipart
```

## 4. Running things

**Backend API:**
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```
Visit `http://localhost:8000/docs` for the auto-generated Swagger UI — this
is the fastest way to manually exercise an endpoint while developing without
needing the frontend up.

**Frontend (Streamlit):**
```bash
cd frontend
streamlit run streamlit_app.py
```
Defaults to `http://localhost:8501`; it expects the backend at
`http://localhost:8000` (configurable via `CAMPUSOPT_API_URL` env var — see
`backend/app/core/config.py` for the equivalent backend-side settings
pattern).

**Generate simulated data:**
```bash
python scripts/generate_synthetic_data.py --scale medium --seed 42
```

**Train predictive models:**
```bash
python -m backend.app.prediction.train --target attendance
python -m backend.app.prediction.train --target mess-demand
```
Both print MAE/RMSE against the naive baseline to stdout and save the
trained model under `backend/app/prediction/artifacts/` (gitignored — models
are regenerated from data, not committed).

**Run the solution-quality benchmark:**
```bash
python scripts/run_benchmark.py --subproblem all --sizes small medium large
```
Writes a report to `reports/solution_quality/` (Markdown + a Plotly HTML
chart) comparing optimizer vs. baseline objective and runtime at each size.

**Run the infeasibility stress test:**
```bash
python scripts/stress_test_infeasible.py --subproblem hostel
```

**Run tests:**
```bash
pytest backend/tests -v
```

**Lint / format:**
```bash
ruff check .
ruff format .
```

## 5. Editor setup

The project doesn't mandate an editor, but if you're using Neovim with an
LSP-based Python setup: point `pyright` or `basedpyright` (or `ruff-lsp` for
diagnostics) at the venv/`.venv-nix-extras` interpreter explicitly — Nix
shells sometimes confuse editor auto-detection of the active Python. A
minimal `pyrightconfig.json` at the repo root pinning
`"venvPath": ".", "venv": ".venv-nix-extras"` (or `.venv` for the pip path)
avoids "import not found" false positives for `ortools`/`pulp` in the
editor even though the code runs fine from the CLI.

Enable format-on-save via `ruff format` the same way you'd wire up
`clang-format` on save for a C++ project — an LSP-agnostic `ruff-lsp` (or
`ruff server` in newer versions) attaches like any other language server.

## 6. CI

`.github/workflows/ci.yml` runs on every push/PR:
1. Set up Python 3.11.
2. `pip install -r backend/requirements.txt`.
3. `ruff check .` (lint gate — must pass).
4. `pytest backend/tests` (test gate — must pass).
5. `python scripts/generate_synthetic_data.py --scale small --seed 42` then
   `python scripts/run_benchmark.py --subproblem all --sizes small` as a
   smoke test that the solvers actually run end-to-end, not just import
   cleanly.

CI does **not** run the `medium`/`large` benchmark sizes (too slow for a
per-PR gate) — those are run manually before a milestone/demo and the report
committed to `reports/solution_quality/` deliberately, in its own commit.

## 7. Common issues

- **`ortools` import error inside a Nix shell**: usually means the
  `.venv-nix-extras` wasn't activated — check `which python` points inside
  `.venv-nix-extras/bin`, not the Nix store's bare interpreter.
- **CBC not found (PuLP)**: PuLP ships a bundled CBC binary via pip on most
  platforms; if it's missing, `pip install pulp --force-reinstall` or install
  `coinor-cbc` via your system package manager / nixpkgs as a fallback.
- **Streamlit can't reach the backend**: confirm `uvicorn` is actually
  running on port 8000 and `CAMPUSOPT_API_URL` isn't pointing elsewhere;
  CORS is permissive in dev (`backend/app/core/config.py`) so this is almost
  always just "the backend isn't up yet."
