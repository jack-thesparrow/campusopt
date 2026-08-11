"""
backend/app/optimization/baselines.py
Shared SolverResult dataclass + random/greedy baselines for all three subproblems.
Per Architecture.md §4 — every solver returns this same shape.
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional


@dataclass
class SolverResult:
    status: Literal["OPTIMAL", "FEASIBLE", "INFEASIBLE", "ERROR"]
    objective_value: Optional[float]
    solution: Optional[Dict[str, Any]]   # None when INFEASIBLE
    runtime_seconds: float
    optimality_gap: Optional[float]
    diagnostics: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "objective_value": self.objective_value,
            "solution": self.solution,
            "runtime_seconds": self.runtime_seconds,
            "optimality_gap": self.optimality_gap,
            "diagnostics": self.diagnostics,
        }


# ─── Timetable Baselines ──────────────────────────────────────────────────────

def timetable_random_baseline(courses, rooms, n_slots: int) -> SolverResult:
    """Randomly assign each course to a slot/room — may produce clashes."""
    t0 = time.perf_counter()
    assignment = {}
    slots = list(range(n_slots))
    room_list = [r["room_id"] for r in rooms]

    for c in courses:
        cid = c["course_id"]
        slot = random.choice(slots)
        room = random.choice(room_list)
        assignment[cid] = {"slot": slot, "room": room}

    runtime = time.perf_counter() - t0
    return SolverResult(
        status="FEASIBLE",
        objective_value=None,
        solution={"assignments": assignment, "type": "random_baseline"},
        runtime_seconds=runtime,
        optimality_gap=None,
        diagnostics=["Random baseline: no constraint checking, may contain clashes."],
    )


def timetable_greedy_baseline(courses, rooms, n_slots: int) -> SolverResult:
    """Greedy first-fit: assign course to first slot/room that doesn't double-book instructor."""
    t0 = time.perf_counter()
    slot_room_used: Dict[tuple, str] = {}      # (slot, room_id) -> course_id
    instructor_slot: Dict[tuple, str] = {}     # (slot, instructor_id) -> course_id
    assignment = {}

    sorted_courses = sorted(courses, key=lambda c: -c.get("pred_attendance", 0))

    for c in sorted_courses:
        cid = c["course_id"]
        iid = c.get("instructor_id", cid)
        demand = c.get("pred_attendance", 0)
        placed = False

        for slot in range(n_slots):
            if (slot, iid) in instructor_slot:
                continue
            for r in rooms:
                rid = r["room_id"]
                cap = r.get("capacity", 999)
                if (slot, rid) in slot_room_used:
                    continue
                if cap < demand:
                    continue
                # Assign
                slot_room_used[(slot, rid)] = cid
                instructor_slot[(slot, iid)] = cid
                assignment[cid] = {"slot": slot, "room": rid}
                placed = True
                break
            if placed:
                break

        if not placed:
            assignment[cid] = {"slot": None, "room": None, "unplaced": True}

    runtime = time.perf_counter() - t0
    unplaced = sum(1 for v in assignment.values() if v.get("unplaced"))
    status = "INFEASIBLE" if unplaced else "FEASIBLE"
    return SolverResult(
        status=status,
        objective_value=float(unplaced),
        solution={"assignments": assignment, "type": "greedy_baseline"},
        runtime_seconds=runtime,
        optimality_gap=None,
        diagnostics=[f"Greedy baseline: {unplaced} course(s) could not be placed."] if unplaced else ["Greedy baseline: all courses placed."],
    )


# ─── Hostel Baselines ─────────────────────────────────────────────────────────

def hostel_random_baseline(students, rooms) -> SolverResult:
    """Randomly assign students to rooms (ignoring category eligibility)."""
    t0 = time.perf_counter()
    room_slots: Dict[str, int] = {r["room_id"]: r.get("capacity", 2) for r in rooms}
    assignment = {}

    shuffled = list(students)
    random.shuffle(shuffled)
    room_list = list(room_slots.keys())

    for s in shuffled:
        random.shuffle(room_list)
        placed = False
        for rid in room_list:
            if room_slots[rid] > 0:
                assignment[s["student_id"]] = rid
                room_slots[rid] -= 1
                placed = True
                break
        if not placed:
            assignment[s["student_id"]] = None

    runtime = time.perf_counter() - t0
    unassigned = sum(1 for v in assignment.values() if v is None)
    return SolverResult(
        status="FEASIBLE" if unassigned == 0 else "INFEASIBLE",
        objective_value=float(len(students) - unassigned),
        solution={"assignments": assignment, "type": "random_baseline"},
        runtime_seconds=runtime,
        optimality_gap=None,
        diagnostics=[f"Random baseline: {unassigned} student(s) unassigned."],
    )


def hostel_greedy_baseline(students, rooms) -> SolverResult:
    """Greedy: sort by seniority, assign to matching-category room with space."""
    t0 = time.perf_counter()
    room_slots: Dict[str, int] = {r["room_id"]: r.get("capacity", 2) for r in rooms}
    room_cat: Dict[str, str] = {r["room_id"]: r.get("category_allowed", "mixed") for r in rooms}
    assignment = {}

    sorted_students = sorted(students, key=lambda s: -s.get("seniority_score", 1.0))

    for s in sorted_students:
        sid = s["student_id"]
        cat = s.get("category", "general")
        placed = False
        for r in rooms:
            rid = r["room_id"]
            rcat = room_cat[rid]
            if room_slots[rid] <= 0:
                continue
            if rcat not in (cat, "mixed"):
                continue
            assignment[sid] = rid
            room_slots[rid] -= 1
            placed = True
            break
        if not placed:
            assignment[sid] = None

    runtime = time.perf_counter() - t0
    unassigned = sum(1 for v in assignment.values() if v is None)
    return SolverResult(
        status="FEASIBLE" if unassigned == 0 else "INFEASIBLE",
        objective_value=float(len(students) - unassigned),
        solution={"assignments": assignment, "type": "greedy_baseline"},
        runtime_seconds=runtime,
        optimality_gap=None,
        diagnostics=[f"Greedy baseline: {unassigned} student(s) unassigned."],
    )


# ─── Mess Baselines ───────────────────────────────────────────────────────────

def mess_greedy_baseline(mess_halls, pred_demand: Dict, safety_margin: float = 0.05) -> SolverResult:
    """Simply produce `demand * (1 + safety_margin)` up to kitchen capacity."""
    t0 = time.perf_counter()
    plan = {}
    total_cost = 0.0

    for m in mess_halls:
        mid = m["mess_id"]
        cap = m.get("kitchen_capacity_per_slot", 220)
        cost_pm = m.get("cost_per_meal", 45.0)
        plan[mid] = {}
        for meal_slot, demand in pred_demand.get(mid, {}).items():
            target = min(cap, demand * (1 + safety_margin))
            plan[mid][meal_slot] = round(target)
            total_cost += round(target) * cost_pm

    runtime = time.perf_counter() - t0
    return SolverResult(
        status="FEASIBLE",
        objective_value=total_cost,
        solution={"production_plan": plan, "type": "greedy_baseline"},
        runtime_seconds=runtime,
        optimality_gap=None,
        diagnostics=["Greedy baseline: produce demand*(1+margin), capped at kitchen capacity."],
    )
