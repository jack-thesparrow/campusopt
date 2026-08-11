"""
backend/app/api/predict.py
POST /predict/mess-demand  →  ForecastResult
POST /predict/attendance   →  ForecastResult (per course)
"""
from __future__ import annotations

from fastapi import APIRouter

from app.models.common import MessDemandRequest, AttendanceRequest
from app.prediction.mess_demand_forecast import generate_forecast
from app.prediction.attendance_forecast import predict_course_attendance

router = APIRouter()


@router.post("/mess-demand")
def predict_mess_demand(request: MessDemandRequest):
    result = generate_forecast(request)
    return result.model_dump()


@router.post("/attendance")
def predict_attendance(request: AttendanceRequest):
    result = predict_course_attendance(request)
    return result.model_dump()
