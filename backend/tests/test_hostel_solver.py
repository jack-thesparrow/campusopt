"""
Unit tests for hostel allocation CP-SAT solver and baselines.
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
from backend.app.optimization.hostel_solver import solve_hostel
from backend.app.optimization.baselines import hostel_greedy_baseline, hostel_random_baseline


class TestHostelSolver(unittest.TestCase):

    def setUp(self):
        self.students = [
            {"student_id": "S1", "category": "general", "seniority_score": 4.0, "pref_block_1": "HB-1"},
            {"student_id": "S2", "category": "reserved", "seniority_score": 3.0, "pref_block_1": "HB-2"},
            {"student_id": "S3", "category": "general", "seniority_score": 2.0, "pref_block_1": "HB-1"},
            {"student_id": "S4", "category": "staff_quota", "seniority_score": 1.0, "pref_block_1": "HB-3"},
        ]
        self.rooms = [
            {"room_id": "R101", "block_id": "HB-1", "capacity": 2, "category_allowed": "general"},
            {"room_id": "R102", "block_id": "HB-2", "capacity": 2, "category_allowed": "reserved"},
            {"room_id": "R103", "block_id": "HB-3", "capacity": 2, "category_allowed": "mixed"},
        ]

    def test_feasible_hostel_allocation(self):
        res = solve_hostel(self.students, self.rooms, force_overbook=False)
        self.assertIn(res.status, ("OPTIMAL", "FEASIBLE"))
        self.assertIsNotNone(res.solution)
        self.assertEqual(len(res.solution["assignments"]), 4)
        self.assertEqual(len(res.solution["waitlist"]), 0)

    def test_force_overbook_infeasible(self):
        res = solve_hostel(self.students, self.rooms, force_overbook=True)
        self.assertEqual(res.status, "INFEASIBLE")
        self.assertTrue(len(res.diagnostics) >= 1)
        self.assertIn("Original model INFEASIBLE", res.diagnostics[0])

    def test_greedy_baseline(self):
        res = hostel_greedy_baseline(self.students, self.rooms)
        self.assertIn(res.status, ("OPTIMAL", "FEASIBLE"))
        self.assertIsNotNone(res.solution)

    def test_random_baseline(self):
        res = hostel_random_baseline(self.students, self.rooms)
        self.assertIsNotNone(res.solution)


if __name__ == "__main__":
    unittest.main()
