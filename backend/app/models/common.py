"""
backend/app/models/common.py
Pydantic request/response schemas shared across all subproblems.
Mirrors the dataclasses defined in Architecture.md §7-8.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


# ─── Prediction Layer ────────────────────────────────────────────────────────

class ForecastResult(BaseModel):
    predictions: Dict[str, float]           # keyed by relevant id
    lower_bound: Dict[str, float]           # 10th-percentile estimate
    upper_bound: Dict[str, float]           # 90th-percentile estimate
    mae: float
    rmse: float
    baseline_mae: float
    modelUsed: str = "Random Forest"
    explanation: str = ""
    # Legacy convenience fields for the React frontend
    predictedAttendance: Optional[int] = None
    expectedRangeMin: Optional[int] = None
    expectedRangeMax: Optional[int] = None
    utilizationPercentage: Optional[float] = None
    r2: Optional[float] = None


class MessDemandRequest(BaseModel):
    hostelPopulation: int = Field(200, ge=1, le=2000)
    date: str = "2026-08-12"
    day: str = "Wednesday"
    holiday: bool = False
    exam: bool = False
    weather: str = "Sunny"        # Sunny | Cloudy | Rainy | Cold | Stormy
    specialEvent: str = "None"    # None | Placement Drive | Campus Fest | Sports Day
    prevAttendance: int = Field(175, ge=0, le=2000)
    sevenDayAvg: int = Field(174, ge=0, le=2000)


class AttendanceRequest(BaseModel):
    course_id: str = "CS301"
    date: str = "2026-08-12"
    registered_strength: int = Field(60, ge=1)
    is_exam_week: bool = False
    weather_flag: str = "clear"   # clear | rain | extreme


# ─── Optimization Layer ───────────────────────────────────────────────────────

class SolverResult(BaseModel):
    status: Literal["OPTIMAL", "FEASIBLE", "INFEASIBLE", "ERROR"]
    objective_value: Optional[float]
    solution: Optional[Dict[str, Any]]     # None when INFEASIBLE
    runtime_seconds: float
    optimality_gap: Optional[float]
    diagnostics: List[str]


# ─── Timetable Subproblem ─────────────────────────────────────────────────────

class Course(BaseModel):
    course_id: str
    instructor_id: str
    duration_slots: int = 1
    pred_attendance: int = 40


class Room(BaseModel):
    room_id: str
    capacity: int


class TimetableRequest(BaseModel):
    n_slots: int = Field(40, ge=1, le=200)           # total time slots
    courses: List[Course] = Field(default_factory=list)
    rooms: List[Room] = Field(default_factory=list)
    use_baseline: bool = False                        # True → run greedy baseline


# ─── Hostel Subproblem ────────────────────────────────────────────────────────

class Student(BaseModel):
    student_id: str
    category: Literal["general", "reserved", "staff_quota"] = "general"
    seniority_score: float = 1.0
    pref_block_1: Optional[str] = None


class HostelRoom(BaseModel):
    room_id: str
    block_id: str
    capacity: int = 2
    category_allowed: Literal["general", "reserved", "mixed"] = "mixed"


class HostelRequest(BaseModel):
    students: List[Student] = Field(default_factory=list)
    rooms: List[HostelRoom] = Field(default_factory=list)
    force_overbook: bool = False         # stress-test: deliberately over-constrain
    use_baseline: bool = False


# ─── Mess Subproblem ──────────────────────────────────────────────────────────

class MessHall(BaseModel):
    mess_id: str
    kitchen_capacity_per_slot: int = 220
    cost_per_meal: float = 45.0


class MessPlanRequest(BaseModel):
    mess_halls: List[MessHall] = Field(default_factory=list)
    pred_demand: Dict[str, Dict[str, float]] = Field(default_factory=dict)   # {mess_id: {meal_slot: demand}}
    safety_margin: float = Field(0.05, ge=0.0, le=1.0)
    waste_penalty: float = 2.0
    shortage_penalty: float = 20.0
    use_baseline: bool = False
    hostel_population: Optional[int] = Field(None, ge=1, le=2000)  # Total student population for scaling
