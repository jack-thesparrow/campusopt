"""
backend/app/data/loaders.py
Single place that knows file paths and CSV parsing.
Nothing in optimization/ or prediction/ calls pd.read_csv directly.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "simulated"
RAW_DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "raw"


def _load(filename: str, dtype: Optional[dict] = None) -> pd.DataFrame:
    path = DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found: {path}. "
            f"Run: python -m app.data.simulate --scale small"
        )
    return pd.read_csv(path, dtype=dtype)


def load_courses() -> pd.DataFrame:
    return _load("courses.csv")


def load_rooms() -> pd.DataFrame:
    return _load("rooms.csv")


def load_instructors() -> pd.DataFrame:
    return _load("instructors.csv")


def load_attendance_history() -> pd.DataFrame:
    df = _load("attendance_history.csv")
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)


def load_students() -> pd.DataFrame:
    return _load("students.csv")


def load_hostel_rooms() -> pd.DataFrame:
    return _load("hostel_rooms.csv")


def load_hostel_blocks() -> pd.DataFrame:
    return _load("hostel_blocks.csv")


def load_mess_halls() -> pd.DataFrame:
    return _load("mess_halls.csv")


def load_mess_demand_history() -> pd.DataFrame:
    df = _load("mess_demand_history.csv")
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)


def load_mess_attendance_raw() -> pd.DataFrame:
    """Load real mess attendance data from raw dataset."""
    path = RAW_DATA_DIR / "mess_attendance_200_students_365_days.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"Raw dataset not found: {path}. "
            f"Please add the mess attendance CSV to data/raw/"
        )
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)
