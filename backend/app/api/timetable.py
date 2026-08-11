"""
backend/app/api/timetable.py
POST /timetable/optimize  →  SolverResult
POST /timetable/baseline  →  SolverResult
"""
from __future__ import annotations

from fastapi import APIRouter

from app.models.common import TimetableRequest
from app.optimization.timetable_solver import solve_timetable
from app.optimization.baselines import timetable_greedy_baseline, timetable_random_baseline

router = APIRouter()


def _sample_courses_rooms(req: TimetableRequest):
    """Fall back to auto-generated sample data when request lists are empty."""
    if req.courses and req.rooms:
        courses = [c.model_dump() for c in req.courses]
        rooms = [r.model_dump() for r in req.rooms]
        return courses, rooms

    # Load from simulated CSVs if available, else generate inline
    try:
        from app.data.loaders import load_courses, load_rooms
        c_df = load_courses()
        r_df = load_rooms()
        courses = c_df.rename(columns={"registered_strength": "pred_attendance"}).to_dict("records")[:20]
        rooms = r_df.to_dict("records")[:10]
    except Exception:
        courses = [{"course_id": f"C{i}", "instructor_id": f"I{i%5}", "duration_slots": 1, "pred_attendance": 30 + i * 2} for i in range(10)]
        rooms = [{"room_id": f"R{i}", "capacity": 40 + i * 10} for i in range(5)]

    return courses, rooms


@router.post("/optimize")
def optimize_timetable(req: TimetableRequest):
    courses, rooms = _sample_courses_rooms(req)
    result = solve_timetable(courses, rooms, req.n_slots)
    return result.to_dict()


@router.post("/baseline")
def timetable_baseline(req: TimetableRequest):
    courses, rooms = _sample_courses_rooms(req)
    if req.use_baseline:
        result = timetable_random_baseline(courses, rooms, req.n_slots)
    else:
        result = timetable_greedy_baseline(courses, rooms, req.n_slots)
    return result.to_dict()
