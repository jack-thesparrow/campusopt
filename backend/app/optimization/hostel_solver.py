"""
backend/app/optimization/hostel_solver.py
CP-SAT hostel allocation solver per Architecture.md §3.2.
Supports infeasibility detection + relaxation diagnostics (§5).
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from app.optimization.baselines import SolverResult

try:
    from ortools.sat.python import cp_model
    ORTOOLS_AVAILABLE = True
except ImportError:
    ORTOOLS_AVAILABLE = False


def solve_hostel(students: List[Dict], rooms: List[Dict], force_overbook: bool = False) -> SolverResult:
    """
    Maximize:  M * Σ y[s,rm]  +  Σ y[s,rm] * pref_score(s, rm)
    Subject to:
        ∀s: Σ_rm y[s,rm] ≤ 1
        ∀rm: Σ_s y[s,rm] ≤ capacity_rm
        category eligibility enforced by variable pruning
    """
    if not ORTOOLS_AVAILABLE:
        return SolverResult(
            status="ERROR",
            objective_value=None,
            solution=None,
            runtime_seconds=0.0,
            optimality_gap=None,
            diagnostics=["OR-Tools not installed. Run: pip install ortools"],
        )

    if force_overbook:
        # Shrink all room capacities to 1 to guarantee infeasibility for demo
        rooms = [dict(r, capacity=1) for r in rooms]

    t0 = time.perf_counter()
    model = cp_model.CpModel()

    # ── Build variable grid (only eligible pairs) ──────────────────────────
    M = 10_000  # large-M to prioritise maximising assignments over preferences

    y: Dict[tuple, Any] = {}  # (student_idx, room_idx) → BoolVar

    for si, s in enumerate(students):
        s_cat = s.get("category", "general")
        pref1 = s.get("pref_block_1")
        for ri, r in enumerate(rooms):
            r_cat = r.get("category_allowed", "mixed")
            if r_cat not in (s_cat, "mixed"):
                continue          # prune ineligible pairs — no variable created
            var = model.NewBoolVar(f"y_{si}_{ri}")
            y[(si, ri)] = var

    # Each student assigned at most once (or exactly once if force_overbook)
    for si, s in enumerate(students):
        vars_for_s = [v for (sii, _), v in y.items() if sii == si]
        if vars_for_s:
            if force_overbook:
                model.Add(sum(vars_for_s) == 1)
            else:
                model.Add(sum(vars_for_s) <= 1)

    # Each room not over capacity
    for ri, r in enumerate(rooms):
        vars_for_r = [v for (_, rii), v in y.items() if rii == ri]
        if vars_for_r:
            model.Add(sum(vars_for_r) <= r.get("capacity", 2))

    # ── Objective ──────────────────────────────────────────────────────────
    obj_terms = []
    for (si, ri), var in y.items():
        s = students[si]
        r = rooms[ri]
        pref_score = 0
        if s.get("pref_block_1") and s["pref_block_1"] == r.get("block_id"):
            pref_score = 100
        obj_terms.append(var * (M + pref_score))

    model.Maximize(sum(obj_terms))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30.0
    solver.parameters.num_search_workers = 4
    status_code = solver.Solve(model)
    runtime = time.perf_counter() - t0

    status_map = {
        cp_model.OPTIMAL: "OPTIMAL",
        cp_model.FEASIBLE: "FEASIBLE",
        cp_model.INFEASIBLE: "INFEASIBLE",
        cp_model.MODEL_INVALID: "ERROR",
        cp_model.UNKNOWN: "ERROR",
    }
    status = status_map.get(status_code, "ERROR")

    if status in ("OPTIMAL", "FEASIBLE"):
        assignment = {}
        for (si, ri), var in y.items():
            if solver.Value(var) == 1:
                assignment[students[si]["student_id"]] = rooms[ri]["room_id"]

        # Students with no assignment
        assigned_ids = set(assignment.keys())
        waitlist = [s["student_id"] for s in students if s["student_id"] not in assigned_ids]
        n_assigned = len(assignment)

        return SolverResult(
            status=status,
            objective_value=float(n_assigned),
            solution={"assignments": assignment, "waitlist": waitlist},
            runtime_seconds=runtime,
            optimality_gap=solver.ObjectiveValue() - solver.BestObjectiveBound() if status == "FEASIBLE" else 0.0,
            diagnostics=[f"Assigned {n_assigned}/{len(students)} students. Waitlist: {len(waitlist)}."],
        )

    # ── Infeasible path: relaxed re-solve ─────────────────────────────────
    diagnostics = [
        f"Original model INFEASIBLE: capacity demand likely exceeds available beds.",
    ]

    # Relaxed solve: allow category violations with heavy penalty
    model2 = cp_model.CpModel()
    y2: Dict[tuple, Any] = {}
    for si, s in enumerate(students):
        for ri, r in enumerate(rooms):
            var = model2.NewBoolVar(f"y2_{si}_{ri}")
            y2[(si, ri)] = var

    for si in range(len(students)):
        vars_for_s = [v for (sii, _), v in y2.items() if sii == si]
        model2.Add(sum(vars_for_s) <= 1)

    for ri, r in enumerate(rooms):
        vars_for_r = [v for (_, rii), v in y2.items() if rii == ri]
        model2.Add(sum(vars_for_r) <= r.get("capacity", 2))

    obj2 = []
    for (si, ri), var in y2.items():
        s = students[si]
        r = rooms[ri]
        s_cat = s.get("category", "general")
        r_cat = r.get("category_allowed", "mixed")
        cat_penalty = 0 if r_cat in (s_cat, "mixed") else 500
        obj2.append(var * (M - cat_penalty))

    model2.Maximize(sum(obj2))
    solver2 = cp_model.CpSolver()
    solver2.parameters.max_time_in_seconds = 15.0
    status2 = solver2.Solve(model2)

    assignment2 = {}
    if status2 in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for (si, ri), var in y2.items():
            if solver2.Value(var) == 1:
                assignment2[students[si]["student_id"]] = rooms[ri]["room_id"]

    waitlist2 = [s["student_id"] for s in students if s["student_id"] not in assignment2]
    diagnostics.append(
        f"Relaxed solve (category violations allowed): assigned {len(assignment2)}/{len(students)}. "
        f"Waitlist: {len(waitlist2)}."
    )

    return SolverResult(
        status="INFEASIBLE",
        objective_value=None,
        solution={"assignments": assignment2, "waitlist": waitlist2, "relaxed": True},
        runtime_seconds=time.perf_counter() - t0,
        optimality_gap=None,
        diagnostics=diagnostics,
    )
