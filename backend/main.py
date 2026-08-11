from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

CAPACITY = 200
HISTORICAL_MAE = 5
MODEL_PATH = Path(__file__).resolve().parent / "model" / "mess_attendance_model.pkl"
FEATURE_COLUMNS = [
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

app = FastAPI(
    title="CampusOpt Mess Attendance API",
    description="Predicts hostel mess lunch attendance using a pre-trained scikit-learn pipeline.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

model: Any | None = None
model_load_error: str | None = None


class PredictionRequest(BaseModel):
    date: date
    is_holiday: int = Field(ge=0, le=1)
    is_exam_period: int = Field(ge=0, le=1)
    is_rainy: int = Field(ge=0, le=1)
    is_special_event: int = Field(ge=0, le=1)
    previous_day_lunch: int = Field(ge=0, le=CAPACITY)
    lunch_7_day_avg: float = Field(ge=0, le=CAPACITY)

    @field_validator("is_holiday", "is_exam_period", "is_rainy", "is_special_event")
    @classmethod
    def validate_binary_flags(cls, value: int) -> int:
        if value not in (0, 1):
            raise ValueError("Flag values must be 0 or 1")
        return value


class PredictionResponse(BaseModel):
    prediction: int
    lower_bound: int
    upper_bound: int
    capacity: int
    utilization: int
    range_note: str
    model_status: str


@app.on_event("startup")
def load_model() -> None:
    """Load the existing trained pipeline once at application startup."""
    global model, model_load_error
    try:
        model = joblib.load(MODEL_PATH)
        model_load_error = None
    except Exception as exc:  # noqa: BLE001 - returned as explicit startup health state
        model = None
        model_load_error = f"Unable to load model from {MODEL_PATH}: {exc}"


def build_feature_frame(payload: PredictionRequest) -> pd.DataFrame:
    prediction_date = payload.date
    iso_calendar = prediction_date.isocalendar()
    features = {
        "day_of_week": prediction_date.weekday(),
        "is_weekend": int(prediction_date.weekday() >= 5),
        "is_holiday": payload.is_holiday,
        "is_exam_period": payload.is_exam_period,
        "is_rainy": payload.is_rainy,
        "is_special_event": payload.is_special_event,
        "previous_day_lunch": payload.previous_day_lunch,
        "lunch_7_day_avg": payload.lunch_7_day_avg,
        "day_of_month": prediction_date.day,
        "month": prediction_date.month,
        "day_of_year": prediction_date.timetuple().tm_yday,
        "week_of_year": iso_calendar.week,
    }
    return pd.DataFrame([[features[column] for column in FEATURE_COLUMNS]], columns=FEATURE_COLUMNS)


@app.get("/health")
def health() -> dict[str, str]:
    if model is None:
        return {
            "status": "error",
            "model_status": "not_loaded",
            "detail": model_load_error or "Model not loaded",
        }
    return {"status": "ok", "model_status": "loaded"}


@app.post("/predict", response_model=PredictionResponse)
def predict(payload: PredictionRequest) -> PredictionResponse:
    if model is None:
        raise HTTPException(status_code=503, detail=model_load_error or "Model is not loaded")

    input_dataframe = build_feature_frame(payload)
    try:
        raw_prediction = float(model.predict(input_dataframe)[0])
    except Exception as exc:  # noqa: BLE001 - provide useful API error without fake output
        raise HTTPException(status_code=500, detail=f"Prediction failed: {exc}") from exc

    prediction = round(raw_prediction)
    prediction = max(0, min(CAPACITY, prediction))
    lower_bound = max(0, round(prediction - HISTORICAL_MAE))
    upper_bound = min(CAPACITY, round(prediction + HISTORICAL_MAE))
    utilization = round((prediction / CAPACITY) * 100)

    return PredictionResponse(
        prediction=prediction,
        lower_bound=lower_bound,
        upper_bound=upper_bound,
        capacity=CAPACITY,
        utilization=utilization,
        range_note="Estimated range based on historical model error",
        model_status="loaded",
    )
