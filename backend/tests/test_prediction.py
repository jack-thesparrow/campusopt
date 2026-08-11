"""
Unit tests for ML prediction models (mess demand & course attendance).
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
from backend.app.models.common import MessDemandRequest, AttendanceRequest
from backend.app.prediction.mess_demand_forecast import generate_forecast
from backend.app.prediction.attendance_forecast import predict_course_attendance


class TestPredictionModels(unittest.TestCase):

    def test_mess_demand_forecast(self):
        req = MessDemandRequest(
            hostelPopulation=200,
            date="2026-08-12",
            day="Wednesday",
            holiday=False,
            exam=False,
            weather="Sunny",
            specialEvent="None",
            prevAttendance=175,
            sevenDayAvg=174,
        )
        res = generate_forecast(req)
        self.assertIsNotNone(res)
        self.assertIn("MESS-1", res.predictions)
        self.assertGreater(res.predictions["MESS-1"], 0)
        self.assertLessEqual(res.predictions["MESS-1"], 200)
        self.assertIsNotNone(res.mae)
        self.assertIsNotNone(res.rmse)
        self.assertIsNotNone(res.baseline_mae)

    def test_course_attendance_forecast(self):
        req = AttendanceRequest(
            course_id="CS101",
            date="2026-08-12",
            registered_strength=60,
            is_exam_week=False,
            weather_flag="clear",
        )
        res = predict_course_attendance(req)
        self.assertIsNotNone(res)
        self.assertIn("CS101", res.predictions)
        self.assertGreaterEqual(res.predictions["CS101"], 0)
        self.assertLessEqual(res.predictions["CS101"], 60)
        self.assertIsNotNone(res.mae)

    def test_exam_attendance_reduction(self):
        req_normal = AttendanceRequest(course_id="CS101", date="2026-08-12", registered_strength=60, is_exam_week=False)
        req_exam = AttendanceRequest(course_id="CS101", date="2026-08-12", registered_strength=60, is_exam_week=True)

        res_normal = predict_course_attendance(req_normal)
        res_exam = predict_course_attendance(req_exam)

        self.assertLessEqual(res_exam.predictions["CS101"], res_normal.predictions["CS101"])


if __name__ == "__main__":
    unittest.main()
