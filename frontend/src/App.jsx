import { useState } from "react";
import "./App.css";

const API_URL = "http://localhost:8001/predict-and-optimize";

const initialForm = {
  date: new Date().toISOString().slice(0, 10),
  is_holiday: 0,
  is_exam_period: 0,
  is_rainy: 0,
  is_special_event: 0,
  previous_day_lunch: 180,
  lunch_7_day_avg: 175,
  mess_capacity: 200,
  number_of_slots: 3,
};

function YesNoField({ label, name, value, onChange }) {
  return (
    <div className="field">
      <label>{label}</label>
      <select name={name} value={value} onChange={onChange}>
        <option value={0}>No</option>
        <option value={1}>Yes</option>
      </select>
    </div>
  );
}

export default function App() {
  const [form, setForm] = useState(initialForm);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  function handleChange(e) {
    const { name, value } = e.target;
    setForm((prev) => ({
      ...prev,
      [name]: name === "date" ? value : Number(value),
    }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setResult(null);

    if (form.number_of_slots <= 0) {
      setError("Number of slots must be greater than zero.");
      return;
    }
    if (form.mess_capacity <= 0) {
      setError("Mess capacity must be greater than zero.");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || "Request failed.");
      }

      const data = await res.json();
      setResult(data);
    } catch (err) {
      setError(
        err.message === "Failed to fetch"
          ? "Could not reach the backend. Make sure the FastAPI server is running."
          : err.message
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page">
      <header className="header">
        <h1>CampusOpt</h1>
        <p>Smart Mess Attendance &amp; Seating Optimization</p>
      </header>

      <form className="card" onSubmit={handleSubmit}>
        <div className="field">
          <label>Prediction Date</label>
          <input
            type="date"
            name="date"
            value={form.date}
            onChange={handleChange}
          />
        </div>

        <YesNoField label="Holiday" name="is_holiday" value={form.is_holiday} onChange={handleChange} />
        <YesNoField label="Exam Period" name="is_exam_period" value={form.is_exam_period} onChange={handleChange} />
        <YesNoField label="Rainy Day" name="is_rainy" value={form.is_rainy} onChange={handleChange} />
        <YesNoField label="Special Event" name="is_special_event" value={form.is_special_event} onChange={handleChange} />

        <div className="field">
          <label>Previous Day Lunch Attendance</label>
          <input
            type="number"
            name="previous_day_lunch"
            min="0"
            value={form.previous_day_lunch}
            onChange={handleChange}
          />
        </div>

        <div className="field">
          <label>7-Day Average Lunch Attendance</label>
          <input
            type="number"
            name="lunch_7_day_avg"
            min="0"
            value={form.lunch_7_day_avg}
            onChange={handleChange}
          />
        </div>

        <div className="field">
          <label>Mess Capacity</label>
          <input
            type="number"
            name="mess_capacity"
            min="1"
            value={form.mess_capacity}
            onChange={handleChange}
          />
        </div>

        <div className="field">
          <label>Number of Slots</label>
          <input
            type="number"
            name="number_of_slots"
            min="1"
            value={form.number_of_slots}
            onChange={handleChange}
          />
        </div>

        <button type="submit" disabled={loading}>
          {loading ? "Predicting..." : "Predict & Optimize"}
        </button>
      </form>

      {error && <div className="card error">{error}</div>}

      {result && (
        <>
          <section className="card result">
            <h2>Predicted Lunch Attendance</h2>
            <p className="big-number">{result.predicted_attendance} students</p>

            <div className="stat-row">
              <span>Hostel Population</span>
              <span>{200} students</span>
            </div>
            <div className="stat-row">
              <span>Predicted Seat Utilization</span>
              <span>{result.utilization}%</span>
            </div>

            {result.estimated_range && (
              <p className="note">
                Estimated range based on historical model error:{" "}
                {result.estimated_range[0]}–{result.estimated_range[1]} students
              </p>
            )}
          </section>

          <section className="card result">
            <h2>Seating Plan</h2>

            {result.shortage > 0 && (
              <p className="warning">
                Capacity Insufficient — shortage of {result.shortage} students
              </p>
            )}

            <ul className="slot-list">
              {result.slot_allocation.map((count, i) => (
                <li key={i}>
                  <span>Slot {i + 1}</span>
                  <span>{count} students</span>
                </li>
              ))}
            </ul>

            <div className="stat-row">
              <span>Total Seating Capacity</span>
              <span>{result.mess_capacity}</span>
            </div>
            <div className="stat-row">
              <span>Allocated Seats</span>
              <span>{result.allocated_students}</span>
            </div>
            <div className="stat-row">
              <span>Unused Capacity</span>
              <span>{result.unused_capacity}</span>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
