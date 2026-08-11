"""
backend/app/api/hostel.py
POST /hostel/optimize  →  SolverResult
POST /hostel/baseline  →  SolverResult
"""
from __future__ import annotations

from fastapi import APIRouter

from app.models.common import HostelRequest
from app.optimization.hostel_solver import solve_hostel
from app.optimization.baselines import hostel_greedy_baseline, hostel_random_baseline

router = APIRouter()


def _sample_students_rooms(req: HostelRequest):
    if req.students and req.rooms:
        return [s.model_dump() for s in req.students], [r.model_dump() for r in req.rooms]

    try:
        from app.data.loaders import load_students, load_hostel_rooms
        s_df = load_students()
        r_df = load_hostel_rooms()
        if "category_allowed" not in r_df.columns:
            r_df["category_allowed"] = "mixed"
        students = s_df.head(50).to_dict("records")
        rooms = r_df.head(35).to_dict("records")
    except Exception:
        students = [{"student_id": f"S{i}", "category": "general" if i % 3 != 0 else "reserved", "seniority_score": float(i)} for i in range(20)]
        rooms = [{"room_id": f"R{i}", "block_id": f"HB-{i%3+1}", "capacity": 2, "category_allowed": "mixed"} for i in range(15)]

    return students, rooms


@router.post("/optimize")
def optimize_hostel(req: HostelRequest):
    students, rooms = _sample_students_rooms(req)
    result = solve_hostel(students, rooms, force_overbook=req.force_overbook)
    return result.to_dict()


@router.post("/baseline")
def hostel_baseline(req: HostelRequest):
    students, rooms = _sample_students_rooms(req)
    if req.use_baseline:
        result = hostel_random_baseline(students, rooms)
    else:
        result = hostel_greedy_baseline(students, rooms)
    return result.to_dict()
