"""
backend/app/prediction/train.py
CLI entrypoint to train, evaluate, and save predictive ML models
for mess demand and course attendance using temporal train/test splits.
Usage: python -m backend.app.prediction.train --target all
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parents[2]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
project_root = Path(__file__).resolve().parents[3]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.metrics import mean_absolute_error, root_mean_squared_error

DIR_PATH = Path(__file__).resolve().parent


def train_mess_model():
    print("--- Training Mess Demand Forecasting Model ---")
    try:
        from app.data.loaders import load_mess_demand_history
        df = load_mess_demand_history()
    except Exception:
        print("Historical mess demand dataset not found. Generating small dataset first...")
        from app.data.simulate import generate_all
        generate_all(scale="small", seed=42)
        from app.data.loaders import load_mess_demand_history
        df = load_mess_demand_history()

    # Temporal split: sort by date, first 80% train, last 20% test
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
    df["day_name"] = df["date"].dt.day_name()
    df["day_of_month"] = df["date"].dt.day
    df["month"] = df["date"].dt.month
    df["day_of_year"] = df["date"].dt.dayofyear
    df["week_of_year"] = df["date"].dt.isocalendar().week.astype(int)
    df["is_rainy"] = 0
    df["is_special_event"] = 0

    # Lags for previous day / rolling avg
    df["previous_day_lunch"] = df["actual_headcount"].shift(1).fillna(df["actual_headcount"].mean())
    df["lunch_7_day_avg"] = df["actual_headcount"].rolling(7, min_periods=1).mean()

    split_idx = int(len(df) * 0.8)
    train_df = df.iloc[:split_idx]
    test_df = df.iloc[split_idx:]

    feature_cols = [
        "day_name", "is_weekend", "is_holiday", "is_exam_week", "is_rainy",
        "is_special_event", "previous_day_lunch", "lunch_7_day_avg",
        "day_of_month", "month", "day_of_year", "week_of_year"
    ]
    X_train = train_df[feature_cols].rename(columns={"day_name": "day_of_week", "is_exam_week": "is_exam_period"})
    y_train = train_df["actual_headcount"]
    X_test = test_df[feature_cols].rename(columns={"day_name": "day_of_week", "is_exam_week": "is_exam_period"})
    y_test = test_df["actual_headcount"]

    categorical_features = ["day_of_week"]
    numerical_features = [col for col in X_train.columns if col not in categorical_features]

    preprocessor = ColumnTransformer(
        transformers=[
            ("categorical", OneHotEncoder(handle_unknown="ignore"), categorical_features),
            ("numerical", "passthrough", numerical_features),
        ]
    )

    pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("model", RandomForestRegressor(n_estimators=100, random_state=42)),
        ]
    )

    pipeline.fit(X_train, y_train)
    preds = pipeline.predict(X_test)

    mae = float(mean_absolute_error(y_test, preds))
    rmse = float(root_mean_squared_error(y_test, preds))

    # Naive baseline: predicting overall training mean
    naive_preds = np.full_like(y_test, fill_value=y_train.mean())
    baseline_mae = float(mean_absolute_error(y_test, naive_preds))

    print(f"Mess Model Test MAE: {mae:.2f} | Test RMSE: {rmse:.2f} | Naive Baseline MAE: {baseline_mae:.2f}")

    out_path = DIR_PATH / "mess_attendance_model.pkl"
    joblib.dump(pipeline, out_path)
    print(f"Saved mess model to {out_path}")
    return {"mae": mae, "rmse": rmse, "baseline_mae": baseline_mae}


def train_attendance_model():
    print("--- Training Course Attendance Forecasting Model ---")
    try:
        from app.data.loaders import load_attendance_history
        df = load_attendance_history()
    except Exception:
        print("Historical course attendance dataset not found. Generating small dataset first...")
        from app.data.simulate import generate_all
        generate_all(scale="small", seed=42)
        from app.data.loaders import load_attendance_history
        df = load_attendance_history()

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    df["day_of_week"] = df["date"].dt.day_name()
    df["day_of_month"] = df["date"].dt.day
    df["month"] = df["date"].dt.month

    split_idx = int(len(df) * 0.8)
    train_df = df.iloc[:split_idx]
    test_df = df.iloc[split_idx:]

    feature_cols = ["day_of_week", "registered_strength", "is_exam_week", "weather_flag", "day_of_month", "month"]
    X_train = train_df[feature_cols]
    y_train = train_df["attended_count"]
    X_test = test_df[feature_cols]
    y_test = test_df["attended_count"]

    categorical_features = ["day_of_week", "weather_flag"]
    numerical_features = [c for c in feature_cols if c not in categorical_features]

    preprocessor = ColumnTransformer(
        transformers=[
            ("categorical", OneHotEncoder(handle_unknown="ignore"), categorical_features),
            ("numerical", "passthrough", numerical_features),
        ]
    )

    pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("model", RandomForestRegressor(n_estimators=100, random_state=42)),
        ]
    )

    pipeline.fit(X_train, y_train)
    preds = pipeline.predict(X_test)

    mae = float(mean_absolute_error(y_test, preds))
    rmse = float(root_mean_squared_error(y_test, preds))

    # Naive baseline: historical average turnout percentage * registered_strength
    hist_turnout_ratio = (y_train / train_df["registered_strength"]).mean()
    naive_preds = test_df["registered_strength"] * hist_turnout_ratio
    baseline_mae = float(mean_absolute_error(y_test, naive_preds))

    print(f"Attendance Model Test MAE: {mae:.2f} | Test RMSE: {rmse:.2f} | Naive Baseline MAE: {baseline_mae:.2f}")

    out_path = DIR_PATH / "attendance_model.pkl"
    joblib.dump({"model": pipeline, "metrics": {"mae": mae, "rmse": rmse, "baseline_mae": baseline_mae}}, out_path)
    print(f"Saved course attendance model to {out_path}")
    return {"mae": mae, "rmse": rmse, "baseline_mae": baseline_mae}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", choices=["mess", "attendance", "all"], default="all")
    args = parser.parse_args()

    if args.target in ("mess", "all"):
        train_mess_model()
    if args.target in ("attendance", "all"):
        train_attendance_model()
