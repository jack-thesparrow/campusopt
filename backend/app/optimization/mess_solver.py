"""
backend/app/optimization/mess_solver.py
PuLP/CBC LP solver for mess production planning per Architecture.md §3.3.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from app.optimization.baselines import SolverResult

try:
    import pulp
    PULP_AVAILABLE = True
except ImportError:
    PULP_AVAILABLE = False


MEAL_SLOTS = ["breakfast", "lunch", "snacks", "dinner"]


def solve_mess(
    mess_halls: List[Dict],
    pred_demand: Dict[str, Dict[str, float]],   # {mess_id: {meal_slot: demand}}
    safety_margin: float = 0.05,
    waste_penalty: float = 2.0,
    shortage_penalty: float = 100.0,
) -> SolverResult:
    """
    minimize  Σ_{m,k} [ cost_per_meal_m * prod[m,k]
                       + waste_penalty * over[m,k]
                       + (cost_per_meal_m + shortage_penalty) * under[m,k] ]
    s.t.
        prod[m,k] ≤ capacity_m
        prod[m,k] - demand[m,k]*(1+α) = over[m,k] - under[m,k]
        prod, over, under ≥ 0
    """
    if not PULP_AVAILABLE:
        return SolverResult(
            status="ERROR",
            objective_value=None,
            solution=None,
            runtime_seconds=0.0,
            optimality_gap=None,
            diagnostics=["PuLP not installed. Run: pip install pulp"],
        )

    t0 = time.perf_counter()

    prob = pulp.LpProblem("mess_planning", pulp.LpMinimize)

    prod, over, under = {}, {}, {}

    for m in mess_halls:
        mid = m["mess_id"]
        cap = m.get("kitchen_capacity_per_slot", 220)
        prod[mid], over[mid], under[mid] = {}, {}, {}

        for meal in MEAL_SLOTS:
            demand = pred_demand.get(mid, {}).get(meal, 0) * (1 + safety_margin)

            prod[mid][meal] = pulp.LpVariable(f"prod_{mid}_{meal}", lowBound=0, upBound=cap)
            over[mid][meal] = pulp.LpVariable(f"over_{mid}_{meal}", lowBound=0)
            under[mid][meal] = pulp.LpVariable(f"under_{mid}_{meal}", lowBound=0)

            # Balance constraint
            prob += (
                prod[mid][meal] - demand == over[mid][meal] - under[mid][meal],
                f"balance_{mid}_{meal}",
            )

    # Objective
    cost_terms = []
    for m in mess_halls:
        mid = m["mess_id"]
        cost_pm = m.get("cost_per_meal", 45.0)
        for meal in MEAL_SLOTS:
            cost_terms.append(cost_pm * prod[mid][meal])
            cost_terms.append(waste_penalty * over[mid][meal])
            cost_terms.append((cost_pm + shortage_penalty) * under[mid][meal])


    prob += pulp.lpSum(cost_terms)

    # Solve (suppress CBC output)
    solver = pulp.PULP_CBC_CMD(msg=False)
    prob.solve(solver)

    runtime = time.perf_counter() - t0
    pulp_status = pulp.LpStatus[prob.status]

    if pulp_status != "Optimal":
        return SolverResult(
            status="INFEASIBLE",
            objective_value=None,
            solution=None,
            runtime_seconds=runtime,
            optimality_gap=None,
            diagnostics=[f"PuLP solver returned: {pulp_status}"],
        )

    # Extract solution
    plan: Dict[str, Any] = {}
    for m in mess_halls:
        mid = m["mess_id"]
        plan[mid] = {}
        for meal in MEAL_SLOTS:
            plan[mid][meal] = {
                "production": round(pulp.value(prod[mid][meal]) or 0),
                "over": round(pulp.value(over[mid][meal]) or 0),
                "under": round(pulp.value(under[mid][meal]) or 0),
                "demand": round(pred_demand.get(mid, {}).get(meal, 0) * (1 + safety_margin)),
            }

    obj_val = pulp.value(prob.objective)
    return SolverResult(
        status="OPTIMAL",
        objective_value=float(obj_val) if obj_val is not None else None,
        solution={"production_plan": plan},
        runtime_seconds=runtime,
        optimality_gap=0.0,
        diagnostics=[f"Optimal production plan solved. Total cost: ₹{round(obj_val, 2) if obj_val else 'N/A'}."],
    )
