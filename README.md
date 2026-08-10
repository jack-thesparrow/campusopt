# CampusOpt

AI-assisted resource optimizer for timetables, hostel allocation, and mess
planning — a hybrid system combining formal optimization (OR-Tools CP-SAT /
PuLP) with predictive ML (attendance and mess-demand forecasting) over
simulated NIT Mizoram data.

## Quick start

```bash
nix develop                     # or: python -m venv .venv && pip install -r backend/requirements.txt
python scripts/generate_synthetic_data.py --scale small --seed 42
python -m backend.app.prediction.train --target mess-demand
cd backend && uvicorn app.main:app --reload &
cd frontend && streamlit run streamlit_app.py
```

## Documentation

Full documentation lives in [`docs/`](docs/) — start with
[`docs/Description.md`](docs/Description.md) for what this is and why, then
[`docs/Architecture.md`](docs/Architecture.md) for the actual math and
system design.

| Doc | Covers |
|---|---|
| [Description.md](docs/Description.md) | Problem framing, scope, success criteria |
| [Architecture.md](docs/Architecture.md) | System design, formal model formulations, infeasibility handling |
| [DataModel.md](docs/DataModel.md) | Schemas, simulated data generation rules |
| [Toolchain.md](docs/Toolchain.md) | Environment setup (Nix flake or pip), running everything |
| [CodingStyle.md](docs/CodingStyle.md) | Code conventions |
| [Contributing.md](docs/Contributing.md) | Branching, PR workflow, review expectations |
| [Roadmap.md](docs/Roadmap.md) | Milestones, exit criteria, deferred work |

## Deliverables status

- [ ] Formal solver-based model (OR-Tools / PuLP) for all three subproblems
- [ ] Solution-quality report vs. naive baseline, 3 dataset sizes
- [ ] Predictive component with temporal train/test split + MAE/RMSE
- [ ] Infeasibility stress test with graceful degradation
- [ ] Working prototype UI

See [`docs/Roadmap.md`](docs/Roadmap.md) for the milestone breakdown behind
this checklist.
