
"""
CampusOpt backend

Loads the pre-trained mess_attendance_model.pkl ONCE at startup and uses it
only for inference. No training or retraining happens here.
"""

from datetime import date
from typing import List

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


HOSTEL_POPULATION = 200

# ---------------------------------------------------------------------------
# Load the pre-trained model ONCE when the server starts.
# This is inference-only. The model is never trained or modified here.
# ---------------------------------------------------------------------------

MODEL_PATH = "mess_attendance_model.pkl"

try:
    model = joblib.load(MODEL_PATH)
except Exception as exc:
    model = None
    model_load_error = str(exc)
else:
    model_load_error = None


app = FastAPI(title="CampusOpt API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class PredictRequest(BaseModel):
    date: date
    is_holiday: int = Field(ge=0, le=1)
    is_exam_period: int = Field(ge=0, le=1)
    is_rainy: int = Field(ge=0, le=1)
    is_special_event: int = Field(ge=0, le=1)
    previous_day_lunch: int = Field(ge=0)
    lunch_7_day_avg: float = Field(ge=0)
    mess_capacity: int = Field(gt=0)
    number_of_slots: int = Field(gt=0)


class PredictResponse(BaseModel):
    predicted_attendance: int
    mess_capacity: int
    utilization: int
    allocated_students: int
    unused_capacity: int
    shortage: int
    slot_allocation: List[int]
    estimated_range: List[int] | None = None


# ---------------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------------

def build_features(req: PredictRequest) -> pd.DataFrame:
    d: date = req.date

    # IMPORTANT:
    # The pretrained model was trained with day_of_week as a string:
    # "Monday", "Tuesday", ..., "Sunday".
    day_of_week = d.strftime("%A")

    # Use the numeric weekday ONLY to determine whether it is a weekend.
    # Monday = 0 ... Sunday = 6
    is_weekend = 1 if d.weekday() >= 5 else 0

    day_of_month = d.day
    month = d.month
    day_of_year = d.timetuple().tm_yday
    week_of_year = d.isocalendar()[1]

    row = {
        "day_of_week": day_of_week,
        "is_weekend": is_weekend,
        "is_holiday": req.is_holiday,
        "is_exam_period": req.is_exam_period,
        "is_rainy": req.is_rainy,
        "is_special_event": req.is_special_event,
        "previous_day_lunch": req.previous_day_lunch,
        "lunch_7_day_avg": req.lunch_7_day_avg,
        "day_of_month": day_of_month,
        "month": month,
        "day_of_year": day_of_year,
        "week_of_year": week_of_year,
    }

    # Column order matches the order used during training.
    columns = [
        "day_of_week",
        "is_weekend",
        "is_holiday",
        "is_exam_period",
        "is_rainy",
        "is_special_event",
        "previous_day_lunch",
        "lunch_7_day_avg",
        "day_of_month",
        "month",
        "day_of_year",
        "week_of_year",
    ]

    return pd.DataFrame([row], columns=columns)


# ---------------------------------------------------------------------------
# Simple deterministic seat allocation
# ---------------------------------------------------------------------------

def allocate_slots(
    students_to_seat: int,
    number_of_slots: int
) -> List[int]:

    base = students_to_seat // number_of_slots
    remainder = students_to_seat % number_of_slots

    # Distribute the remainder across the first slots.
    return [
        base + 1 if i < remainder else base
        for i in range(number_of_slots)
    ]


# ---------------------------------------------------------------------------
# Prediction + optimization endpoint
# ---------------------------------------------------------------------------

@app.post(
    "/predict-and-optimize",
    response_model=PredictResponse
)
def predict_and_optimize(req: PredictRequest):

    if model is None:
        raise HTTPException(
            status_code=500,
            detail=f"Model failed to load: {model_load_error}",
        )

    # Build features exactly as expected by the pretrained model.
    features = build_features(req)

    try:
        raw_prediction = model.predict(features)[0]
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {exc}",
        )

    predicted_attendance = max(
        0,
        round(float(raw_prediction))
    )

    # Optional model error range.
    estimated_range = None

    mae = getattr(model, "mae_", None)

    if mae is not None:
        estimated_range = [
            max(0, round(predicted_attendance - mae)),
            round(predicted_attendance + mae),
        ]

    # -----------------------------------------------------------------------
    # Seating optimization
    # -----------------------------------------------------------------------

    capacity = req.mess_capacity

    shortage = max(
        0,
        predicted_attendance - capacity
    )

    allocated_students = min(
        predicted_attendance,
        capacity
    )

    unused_capacity = max(
        0,
        capacity - allocated_students
    )

    utilization = (
        round((allocated_students / capacity) * 100)
        if capacity
        else 0
    )

    slot_allocation = allocate_slots(
        allocated_students,
        req.number_of_slots
    )

    return PredictResponse(
        predicted_attendance=predicted_attendance,
        mess_capacity=capacity,
        utilization=utilization,
        allocated_students=allocated_students,
        unused_capacity=unused_capacity,
        shortage=shortage,
        slot_allocation=slot_allocation,
        estimated_range=estimated_range,
    )


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_loaded": model is not None
    }