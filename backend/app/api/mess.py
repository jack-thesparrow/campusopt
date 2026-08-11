"""
backend/app/api/mess.py
POST /mess/optimize  →  SolverResult
POST /mess/baseline  →  SolverResult
"""
from __future__ import annotations

from fastapi import APIRouter

from app.models.common import MessPlanRequest
from app.optimization.mess_solver import solve_mess
from app.optimization.baselines import mess_greedy_baseline
from app.prediction.mess_demand_forecast import generate_forecast
from app.models.common import MessDemandRequest

router = APIRouter()

MEAL_SLOTS = ["breakfast", "lunch", "snacks", "dinner"]
MEAL_RATIOS = {"breakfast": 0.65, "lunch": 0.85, "snacks": 0.55, "dinner": 0.78}


def _build_pred_demand(req: MessPlanRequest):
    """If pred_demand is empty, call prediction layer to build it."""
    if req.pred_demand:
        return req.pred_demand, req.mess_halls

    # Use prediction layer for MESS-1; use ratios for others
    halls = req.mess_halls
    if not halls:
        try:
            from app.data.loaders import load_mess_halls
            df = load_mess_halls().head(2)
            halls = df.to_dict("records")
        except Exception:
            halls = [{"mess_id": "MESS-1", "kitchen_capacity_per_slot": 220, "cost_per_meal": 45.0}]

    # Forecast demand for today using defaults
    # Use the hostelPopulation from the request if provided, otherwise use default
    forecast_req = MessDemandRequest()
    if hasattr(req, 'hostel_population') and req.hostel_population:
        forecast_req.hostelPopulation = req.hostel_population
    
    forecast = generate_forecast(forecast_req)
    base_demand = forecast.predictions.get("MESS-1", 175.0)

    pred: dict = {}
    for m in halls:
        mid = m["mess_id"] if isinstance(m, dict) else m.mess_id
        pred[mid] = {meal: round(base_demand * ratio) for meal, ratio in MEAL_RATIOS.items()}

    return pred, halls


@router.post("/optimize")
def optimize_mess(req: MessPlanRequest):
    pred_demand, halls = _build_pred_demand(req)
    hall_dicts = [h if isinstance(h, dict) else h.model_dump() for h in halls]
    result = solve_mess(hall_dicts, pred_demand, req.safety_margin, req.waste_penalty, req.shortage_penalty)
    return result.to_dict()


@router.post("/baseline")
def mess_baseline(req: MessPlanRequest):
    pred_demand, halls = _build_pred_demand(req)
    hall_dicts = [h if isinstance(h, dict) else h.model_dump() for h in halls]
    result = mess_greedy_baseline(hall_dicts, pred_demand, req.safety_margin)
    return result.to_dict()
