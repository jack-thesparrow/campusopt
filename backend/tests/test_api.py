"""
Unit & integration tests for FastAPI API endpoints.
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
from fastapi.testclient import TestClient
from backend.app.main import app


class TestAPI(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_hostel_optimize(self):
        body = {
            "students": [
                {"student_id": "S1", "category": "general", "seniority_score": 4.0},
                {"student_id": "S2", "category": "reserved", "seniority_score": 3.0},
            ],
            "rooms": [
                {"room_id": "R101", "block_id": "HB-1", "capacity": 2, "category_allowed": "mixed"},
            ],
            "force_overbook": False,
        }
        response = self.client.post("/hostel/optimize", json=body)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn(data["status"], ("OPTIMAL", "FEASIBLE"))
        self.assertIsNotNone(data["solution"])

    def test_mess_optimize(self):
        body = {
            "mess_halls": [
                {"mess_id": "MESS-1", "kitchen_capacity_per_slot": 200, "cost_per_meal": 45.0}
            ],
            "pred_demand": {
                "MESS-1": {"breakfast": 100, "lunch": 150, "snacks": 80, "dinner": 140}
            },
            "safety_margin": 0.05,
        }
        response = self.client.post("/mess/optimize", json=body)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "OPTIMAL")

    def test_timetable_optimize(self):
        body = {
            "n_slots": 16,
            "courses": [
                {"course_id": "CS101", "instructor_id": "I1", "duration_slots": 1, "pred_attendance": 30}
            ],
            "rooms": [
                {"room_id": "LH-1", "capacity": 50}
            ],
        }
        response = self.client.post("/timetable/optimize", json=body)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn(data["status"], ("OPTIMAL", "FEASIBLE"))

    def test_predict_mess_demand(self):
        body = {
            "hostelPopulation": 200,
            "date": "2026-08-12",
            "day": "Wednesday",
            "holiday": False,
            "exam": False,
            "weather": "Sunny",
            "specialEvent": "None",
            "prevAttendance": 175,
            "sevenDayAvg": 174,
        }
        response = self.client.post("/predict/mess-demand", json=body)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("predictions", data)

    def test_predict_attendance(self):
        body = {
            "course_id": "CS301",
            "date": "2026-08-12",
            "registered_strength": 60,
            "is_exam_week": False,
            "weather_flag": "clear",
        }
        response = self.client.post("/predict/attendance", json=body)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("predictions", data)


if __name__ == "__main__":
    unittest.main()
