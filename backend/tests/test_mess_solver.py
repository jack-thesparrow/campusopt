"""
Unit tests for mess production planning LP solver and baseline.
"""
import sys
from pathlib import Path

# Add backend and project root to sys.path
root = Path(__file__).resolve().parents[2]
backend_dir = root / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

import unittest
from backend.app.optimization.mess_solver import solve_mess
from backend.app.optimization.baselines import mess_greedy_baseline


class TestMessSolver(unittest.TestCase):

    def setUp(self):
        self.mess_halls = [
            {"mess_id": "MESS-1", "kitchen_capacity_per_slot": 250, "cost_per_meal": 45.0},
            {"mess_id": "MESS-2", "kitchen_capacity_per_slot": 200, "cost_per_meal": 50.0},
        ]
        self.pred_demand = {
            "MESS-1": {"breakfast": 150, "lunch": 200, "snacks": 100, "dinner": 180},
            "MESS-2": {"breakfast": 120, "lunch": 160, "snacks": 90, "dinner": 150},
        }

    def test_optimal_mess_plan(self):
        res = solve_mess(self.mess_halls, self.pred_demand, safety_margin=0.05)
        self.assertEqual(res.status, "OPTIMAL")
        self.assertIsNotNone(res.solution)
        plan = res.solution["production_plan"]
        self.assertIn("MESS-1", plan)
        self.assertIn("MESS-2", plan)

        # Check safety margin application for MESS-1 lunch: demand 200 * 1.05 = 210
        mess1_lunch = plan["MESS-1"]["lunch"]
        self.assertEqual(mess1_lunch["demand"], 210)
        self.assertEqual(mess1_lunch["production"], 210)

    def test_kitchen_capacity_limit(self):
        # Demand exceeds capacity (200 * 1.05 = 210 > capacity 150)
        constrained_halls = [{"mess_id": "MESS-1", "kitchen_capacity_per_slot": 150, "cost_per_meal": 45.0}]
        res = solve_mess(constrained_halls, self.pred_demand, safety_margin=0.05)
        self.assertEqual(res.status, "OPTIMAL")
        plan = res.solution["production_plan"]
        mess1_lunch = plan["MESS-1"]["lunch"]
        self.assertEqual(mess1_lunch["production"], 150)
        self.assertEqual(mess1_lunch["under"], 60)

    def test_mess_greedy_baseline(self):
        res = mess_greedy_baseline(self.mess_halls, self.pred_demand, safety_margin=0.05)
        self.assertEqual(res.status, "FEASIBLE")
        self.assertIsNotNone(res.solution)


if __name__ == "__main__":
    unittest.main()
