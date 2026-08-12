# CampusOpt

Smart mess attendance prediction and seating optimization for a 200-student hostel.

## Project purpose

CampusOpt has two parts:

1. **Mess attendance prediction** — predicts how many students will attend
   lunch on a given day.
2. **Mess seat capacity optimization** — takes that prediction and works out
   how many students should be seated in each available seating slot.

## How the pre-trained model is used

The application uses a pre-trained Random Forest model stored in
`mess_attendance_model.pkl`. The model is loaded for inference and is not
retrained when the application runs.

The backend loads the `.pkl` file **once**, when the FastAPI server starts,
and calls `model.predict()` on each request. No training code exists
anywhere in this application.

The seat allocation in Section 2 is **not** produced by machine learning —
it's simple deterministic logic that splits the predicted attendance as
evenly as possible across the configured number of slots, never exceeding
total capacity.

## Project structure

```
CampusOpt/
├── backend/
│   ├── main.py
│   ├── mess_attendance_model.pkl   ← place your model file here
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   └── main.jsx
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
└── README.md
```

## 1. Install backend dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate      # on Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Copy your existing `mess_attendance_model.pkl` into the `backend/` folder
(next to `main.py`) before starting the server.

## 2. Start FastAPI

```bash
cd backend
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.
Health check: `GET http://localhost:8000/health`.

## 3. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

The app will open at `http://localhost:5173`.

## 4. How the frontend talks to the backend

The frontend sends a `POST` request to
`http://localhost:8000/predict-and-optimize` with the form inputs
(date, holiday/exam/rain/event flags, previous day lunch, 7-day average,
mess capacity, and number of slots). The backend derives the date-based
features, runs `model.predict()`, performs the seat allocation, and returns
a single JSON response that the frontend renders.

If you deploy the backend somewhere other than `localhost:8000`, update
`API_URL` at the top of `frontend/src/App.jsx`.

## Notes

- The model is expected to be a saved scikit-learn (or pipeline) object
  accepting a DataFrame with these columns, in this order:
  `day_of_week, is_weekend, is_holiday, is_exam_period, is_rainy,
  is_special_event, previous_day_lunch, lunch_7_day_avg, day_of_month,
  month, day_of_year, week_of_year`.
- If your saved model object exposes a `mae_` attribute (historical mean
  absolute error), the backend will automatically include an
  "estimated range" in the response. This is optional — if it's not
  present, the range is simply omitted.
