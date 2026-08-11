"""
Unit tests for timetabling CP-SAT solver and baselines.
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
from backend.app.optimization.timetable_solver import solve_timetable
from backend.app.optimization.baselines import timetable_greedy_baseline, timetable_random_baseline


class TestTimetableSolver(unittest.TestCase):

    def setUp(self):
        self.courses = [
            {"course_id": "CS101", "instructor_id": "ProfA", "duration_slots": 1, "pred_attendance": 40},
            {"course_id": "CS102", "instructor_id": "ProfB", "duration_slots": 1, "pred_attendance": 30},
            {"course_id": "CS103", "instructor_id": "ProfA", "duration_slots": 1, "pred_attendance": 50},
        ]
        self.rooms = [
            {"room_id": "LH-1", "capacity": 60},
            {"room_id": "LH-2", "capacity": 40},
        ]
        self.n_slots = 16

    def test_feasible_timetable(self):
        res = solve_timetable(self.courses, self.rooms, self.n_slots)
        self.assertIn(res.status, ("OPTIMAL", "FEASIBLE"))
        self.assertIsNotNone(res.solution)
        assignments = res.solution["assignments"]
        self.assertEqual(len(assignments), 3)

        # Check instructor ProfA double-booking constraint
        slot_cs101 = assignments["CS101"]["slot"]
        slot_cs103 = assignments["CS103"]["slot"]
        self.assertNotEqual(slot_cs101, slot_cs103)

    def test_infeasible_no_large_room(self):
        large_courses = self.courses + [
            {"course_id": "CS999", "instructor_id": "ProfC", "duration_slots": 1, "pred_attendance": 100}
        ]
        res = solve_timetable(large_courses, self.rooms, self.n_slots)
        self.assertEqual(res.status, "INFEASIBLE")
        self.assertIn("Timetabling INFEASIBLE", res.diagnostics[0])

    def test_greedy_baseline(self):
        res = timetable_greedy_baseline(self.courses, self.rooms, self.n_slots)
        self.assertIn(res.status, ("OPTIMAL", "FEASIBLE"))

    def test_random_baseline(self):
        res = timetable_random_baseline(self.courses, self.rooms, self.n_slots)
        self.assertEqual(res.status, "FEASIBLE")


if __name__ == "__main__":
    unittest.main()
