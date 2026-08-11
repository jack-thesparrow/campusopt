"""
backend/app/optimization/timetable_solver.py
CP-SAT timetabling solver per Architecture.md §3.1.
Supports soft constraints: room capacity slack + instructor gap penalties.
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


def solve_timetable(courses: List[Dict], rooms: List[Dict], n_slots: int = 40) -> SolverResult:
    """
    Decision vars: x[c, t, r] ∈ {0,1}
    Constraints:
        1. Each course scheduled exactly once
        2. No room double-booked
        3. No instructor double-booked
        4. Room capacity ≥ pred_attendance (variable pruning)
    Objective (soft):
        minimise w1 * capacity_slack  +  w2 * instructor_day_gaps
        where w1 = 1 (per seat waste), w2 = 50 (penalty per instructor idle gap)
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

    if not courses or not rooms:
        return SolverResult(
            status="ERROR",
            objective_value=None,
            solution=None,
            runtime_seconds=0.0,
            optimality_gap=None,
            diagnostics=["No courses or rooms provided."],
        )

    t0 = time.perf_counter()
    model = cp_model.CpModel()

    SCALE = 10  # integer scaling for objective

    x: Dict[tuple, Any] = {}   # (ci, ti, ri) → BoolVar
    n_days = max(1, n_slots // 8)
    periods_per_day = max(1, n_slots // n_days)

    # Variable pruning: only create variable if room capacity >= predicted attendance
    for ci, c in enumerate(courses):
        demand = c.get("pred_attendance", 1)
        for ti in range(n_slots):
            for ri, r in enumerate(rooms):
                if r.get("capacity", 0) >= demand:
                    x[(ci, ti, ri)] = model.NewBoolVar(f"x_{ci}_{ti}_{ri}")

    # 1. Each course scheduled exactly once
    for ci, c in enumerate(courses):
        vars_c = [v for (cii, _, __), v in x.items() if cii == ci]
        if not vars_c:
            # Infeasible: no single room large enough for course ci
            return SolverResult(
                status="INFEASIBLE",
                objective_value=None,
                solution=None,
                runtime_seconds=time.perf_counter() - t0,
                optimality_gap=None,
                diagnostics=[
                    f"Timetabling INFEASIBLE: course '{c.get('course_id')}' requires capacity {c.get('pred_attendance')} but no available room fits it.",
                    "Suggestion: add larger rooms or reduce class size.",
                ],
            )
        model.AddExactlyOne(vars_c)

    # 2. No room double-booked
    for ti in range(n_slots):
        for ri in range(len(rooms)):
            vars_tr = [v for (_, tii, rii), v in x.items() if tii == ti and rii == ri]
            if vars_tr:
                model.Add(sum(vars_tr) <= 1)

    # 3. No instructor double-booked
    instructor_courses: Dict[str, List[int]] = {}
    for ci, c in enumerate(courses):
        iid = c.get("instructor_id", f"I{ci}")
        instructor_courses.setdefault(iid, []).append(ci)

    for iid, cis in instructor_courses.items():
        for ti in range(n_slots):
            vars_it = [v for (cii, tii, _), v in x.items() if cii in cis and tii == ti]
            if vars_it:
                model.Add(sum(vars_it) <= 1)

    # ── Soft Objective ──────────────────────────────────────────────────────────
    # w1 = 1 per seat slack, w2 = 50 per instructor gap slot
    w1 = 1
    w2 = 50
    obj_terms = []

    # Seating slack term
    for (ci, ti, ri), var in x.items():
        c = courses[ci]
        r = rooms[ri]
        slack = r.get("capacity", 0) - c.get("pred_attendance", 0)
        obj_terms.append(var * int(slack * w1 * SCALE))

    # Instructor gap penalty
    for iid, cis in instructor_courses.items():
        if len(cis) < 2:
            continue
        for day in range(n_days):
            day_slots = list(range(day * periods_per_day, min(n_slots, (day + 1) * periods_per_day)))
            if len(day_slots) < 3:
                continue
            inst_busy_at_slot = {}
            for ti in day_slots:
                vars_t = [v for (cii, tii, _), v in x.items() if cii in cis and tii == ti]
                if vars_t:
                    bvar = model.NewBoolVar(f"inst_{iid}_busy_{ti}")
                    model.Add(sum(vars_t) == bvar)
                    inst_busy_at_slot[ti] = bvar
            # Linearize gap: if busy at t1 and busy at t3, penalize idle t2
            slots_list = sorted(inst_busy_at_slot.keys())
            for idx in range(len(slots_list) - 2):
                t1 = slots_list[idx]
                t2 = slots_list[idx + 1]
                t3 = slots_list[idx + 2]
                if t3 - t1 == 2 and t2 == t1 + 1:
                    gap_var = model.NewBoolVar(f"gap_{iid}_{t2}")
                    model.Add(inst_busy_at_slot[t1] + inst_busy_at_slot[t3] - inst_busy_at_slot[t2] <= 1 + gap_var)
                    obj_terms.append(gap_var * (w2 * SCALE))

    model.Minimize(sum(obj_terms))

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
        for (ci, ti, ri), var in x.items():
            cid = courses[ci]["course_id"]
            if solver.Value(var) == 1:
                day = ti // periods_per_day
                period = ti % periods_per_day
                assignment[cid] = {
                    "slot": ti,
                    "day": day,
                    "period": period,
                    "room": rooms[ri]["room_id"],
                }

        unscheduled = [c["course_id"] for c in courses if c["course_id"] not in assignment]
        obj = solver.ObjectiveValue() / SCALE
        best_bound = solver.BestObjectiveBound() / SCALE
        gap = abs(obj - best_bound)

        return SolverResult(
            status=status,
            objective_value=round(obj, 2),
            solution={"assignments": assignment, "unscheduled": unscheduled},
            runtime_seconds=round(runtime, 4),
            optimality_gap=round(gap, 2),
            diagnostics=[
                f"Scheduled {len(assignment)}/{len(courses)} courses.",
                f"Objective cost: {obj:.1f} (weighted seat slack + instructor gap penalties).",
                f"Optimality gap: {gap:.2f}.",
            ],
        )

    return SolverResult(
        status="INFEASIBLE",
        objective_value=None,
        solution=None,
        runtime_seconds=round(runtime, 4),
        optimality_gap=None,
        diagnostics=[
            "Timetabling INFEASIBLE — constraints cannot be satisfied given available slots and room capacities.",
            "Suggestion: add more time slots or increase room capacities.",
        ],
    )
