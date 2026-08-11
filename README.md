# CampusOpt

CampusOpt is a minimal web application for predicting hostel mess lunch attendance for a 200-student hostel. The production app uses the existing pre-trained `mess_attendance_model.pkl` scikit-learn Pipeline and never trains, retrains, replaces, or fakes the ML model at runtime.

## Project structure

```text
backend/
  main.py
  model/
    mess_attendance_model.pkl   # place the existing trained Pipeline here
  requirements.txt
frontend/
  src/
  package.json
README.md
```

## Model placement

Place your existing model file at:

```text
backend/model/mess_attendance_model.pkl
```

The FastAPI service loads that file once during startup with `joblib.load(...)`. The saved object is expected to be the complete scikit-learn Pipeline containing preprocessing and the Random Forest model.

## Backend setup and startup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload
```

The API will run at `http://localhost:8000` by default.

### API endpoints

- `GET /health` reports whether the model is loaded.
- `POST /predict` accepts prediction inputs from the frontend and calls `model.predict(input_dataframe)`.

Example request:

```json
{
  "date": "2026-08-12",
  "is_holiday": 0,
  "is_exam_period": 0,
  "is_rainy": 0,
  "is_special_event": 0,
  "previous_day_lunch": 180,
  "lunch_7_day_avg": 175
}
```

The backend derives the date-based features internally and builds the exact training feature structure:

```text
day_of_week, is_weekend, is_holiday, is_exam_period, is_rainy,
is_special_event, previous_day_lunch, lunch_7_day_avg,
day_of_month, month, day_of_year, week_of_year
```

Predictions are clamped to the valid hostel capacity range of 0 to 200 students. The returned range is `prediction ± historical MAE` and is labeled as an estimated range based on historical model error, not a guaranteed confidence interval.

## Frontend setup and startup

```bash
cd frontend
npm install
npm run dev
```

The Vite frontend runs at `http://localhost:5173` by default and sends requests to `http://localhost:8000/predict`. To point it at another backend URL, set:

```bash
VITE_API_URL=http://your-backend-host:8000 npm run dev
```

## Important ML behavior

- The model is pre-trained and is **not retrained** when the application runs.
- The backend loads only `backend/model/mess_attendance_model.pkl`.
- No second ML model is created in the application.
- The frontend does not generate predictions; it only sends inputs to `/predict` and displays the backend response.
- If the model cannot be loaded or prediction fails, the backend returns a clear error instead of fake or random values.
