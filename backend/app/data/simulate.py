"""
backend/app/data/simulate.py
Synthetic NIT Mizoram-realistic data generator.
Usage: python -m app.data.simulate --scale small --seed 42
"""
from __future__ import annotations

import argparse
import os
import random
from pathlib import Path

import numpy as np
import pandas as pd

DEPARTMENTS = ["CSE", "ECE", "ME", "CE", "EE", "MCA", "PhD"]
INSTRUCTORS_PER_DEPT = 5

SCALE_CONFIGS = {
    "small": {"n_courses": 20, "n_rooms": 10, "n_students": 100, "n_beds": 120, "n_mess": 2, "n_days": 30},
    "medium": {"n_courses": 80, "n_rooms": 25, "n_students": 600, "n_beds": 650, "n_mess": 4, "n_days": 90},
    "large": {"n_courses": 200, "n_rooms": 40, "n_students": 2000, "n_beds": 2100, "n_mess": 6, "n_days": 365},
}


def generate_all(scale: str = "small", seed: int = 42, out_dir: str = "data/simulated", force_overbook: bool = False):
    rng = np.random.default_rng(seed)
    random.seed(seed)
    cfg = SCALE_CONFIGS[scale]
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # ── Instructors ────────────────────────────────────────────────────────
    instructors = []
    for dept in DEPARTMENTS:
        for i in range(INSTRUCTORS_PER_DEPT):
            instructors.append({
                "instructor_id": f"{dept}-I{i+1:02d}",
                "name": f"Prof. {dept}{i+1}",
                "department": dept,
                "max_load_per_week": 4,
            })
    inst_df = pd.DataFrame(instructors)
    inst_df.to_csv(out / "instructors.csv", index=False)

    # ── Rooms ──────────────────────────────────────────────────────────────
    room_caps = list(rng.integers(30, 150, size=cfg["n_rooms"]))
    rooms = []
    for i, cap in enumerate(room_caps):
        rtype = "lecture_hall" if cap > 60 else ("lab" if cap < 40 else "seminar_room")
        rooms.append({"room_id": f"LH-{i+1:03d}", "room_type": rtype, "capacity": int(cap)})
    pd.DataFrame(rooms).to_csv(out / "rooms.csv", index=False)

    # ── Courses ────────────────────────────────────────────────────────────
    courses = []
    dept_cycle = (DEPARTMENTS * 10)[:cfg["n_courses"]]
    for i, dept in enumerate(dept_cycle):
        strength = int(rng.integers(15, 120))
        iid = f"{dept}-I{rng.integers(1, INSTRUCTORS_PER_DEPT+1):02d}"
        courses.append({
            "course_id": f"{dept}{100+i}",
            "course_name": f"{dept} Course {i+1}",
            "department": dept,
            "semester": int(rng.integers(1, 9)),
            "instructor_id": iid,
            "registered_strength": strength,
            "duration_slots": 1,
            "session_type": rng.choice(["lecture", "lab", "tutorial"]),
        })
    pd.DataFrame(courses).to_csv(out / "courses.csv", index=False)

    # ── Attendance history ─────────────────────────────────────────────────
    dates = pd.date_range("2026-01-01", periods=cfg["n_days"])
    att_rows = []
    for c in courses[:min(len(courses), 20)]:       # keep CSV small for prototype
        for date in dates:
            dow = date.dayofweek
            is_exam = int(date.month in [4, 11])
            weather = rng.choice(["clear", "rain", "extreme"], p=[0.6, 0.3, 0.1])
            base_rate = rng.beta(7, 3)              # centred ~0.7
            if is_exam:
                base_rate *= 0.85
            if weather == "extreme":
                base_rate *= 0.75
            attended = int(c["registered_strength"] * base_rate)
            att_rows.append({
                "course_id": c["course_id"],
                "date": date.date(),
                "day_of_week": dow,
                "registered_strength": c["registered_strength"],
                "attended_count": attended,
                "is_exam_week": is_exam,
                "weather_flag": weather,
            })
    pd.DataFrame(att_rows).to_csv(out / "attendance_history.csv", index=False)

    # ── Hostel blocks & rooms ─────────────────────────────────────────────
    blocks = [
        {"block_id": f"HB-{i+1}", "gender": "boys" if i < 3 else "girls",
         "category_allowed": ["general", "reserved", "mixed"][i % 3]}
        for i in range(6)
    ]
    pd.DataFrame(blocks).to_csv(out / "hostel_blocks.csv", index=False)

    n_beds = cfg["n_beds"]
    if force_overbook:
        n_beds = max(1, n_beds // 2)      # deliberately under-provision

    hostel_rooms = []
    rid = 1
    for b in blocks:
        n_rooms_in_block = n_beds // len(blocks)
        for _ in range(n_rooms_in_block):
            hostel_rooms.append({
                "room_id": f"R-{rid:04d}",
                "block_id": b["block_id"],
                "capacity": int(rng.integers(2, 5)),
            })
            rid += 1
    pd.DataFrame(hostel_rooms).to_csv(out / "hostel_rooms.csv", index=False)

    # ── Students ──────────────────────────────────────────────────────────
    students = []
    cats = ["general"] * 60 + ["reserved"] * 30 + ["staff_quota"] * 10
    random.shuffle(cats)
    for i in range(cfg["n_students"]):
        year = int(rng.integers(1, 5))
        dept = rng.choice(DEPARTMENTS)
        cat = cats[i % len(cats)]
        students.append({
            "student_id": f"STU{i+1:04d}",
            "department": dept,
            "year": year,
            "category": cat,
            "seniority_score": round(year + rng.uniform(0, 0.5), 3),
            "pref_block_1": f"HB-{rng.integers(1, 7)}",
            "pref_block_2": None,
        })
    pd.DataFrame(students).to_csv(out / "students.csv", index=False)

    # ── Mess halls ────────────────────────────────────────────────────────
    mess_halls = []
    for i in range(cfg["n_mess"]):
        mess_halls.append({
            "mess_id": f"MESS-{i+1}",
            "serves_blocks": f"HB-{i*2+1},HB-{i*2+2}",
            "kitchen_capacity_per_slot": int(rng.integers(180, 280)),
            "cost_per_meal": round(float(rng.uniform(40, 60)), 2),
        })
    pd.DataFrame(mess_halls).to_csv(out / "mess_halls.csv", index=False)

    # ── Mess demand history ───────────────────────────────────────────────
    demand_rows = []
    meal_base = {"breakfast": 0.65, "lunch": 0.80, "snacks": 0.55, "dinner": 0.78}
    for m in mess_halls:
        mid = m["mess_id"]
        n_diners = cfg["n_students"] // cfg["n_mess"]
        for date in dates:
            dow = date.dayofweek
            is_exam = int(date.month in [4, 11])
            is_holiday = int(dow >= 5)
            for meal, base_turn in meal_base.items():
                weekday_adj = -0.1 if is_holiday else 0.0
                exam_adj = -0.05 if is_exam else 0.0
                popularity = round(float(rng.uniform(0, 1)), 2)
                turnout = max(0.1, base_turn + weekday_adj + exam_adj + rng.uniform(-0.05, 0.05))
                demand_rows.append({
                    "mess_id": mid,
                    "date": date.date(),
                    "meal_slot": meal,
                    "registered_diners": n_diners,
                    "actual_headcount": int(n_diners * turnout),
                    "day_of_week": dow,
                    "is_exam_week": is_exam,
                    "is_holiday": is_holiday,
                    "menu_popularity_score": popularity,
                })
    pd.DataFrame(demand_rows).to_csv(out / "mess_demand_history.csv", index=False)

    print(f"Generated {scale} dataset (seed={seed}) -> {out}/")
    return str(out)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scale", choices=["small", "medium", "large"], default="small")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default="data/simulated")
    parser.add_argument("--force-overbook", action="store_true")
    args = parser.parse_args()
    generate_all(args.scale, args.seed, args.out, args.force_overbook)
