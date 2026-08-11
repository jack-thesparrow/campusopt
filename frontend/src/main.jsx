import React, { useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function today() {
  return new Date().toISOString().slice(0, 10);
}

function App() {
  const [form, setForm] = useState({
    date: today(),
    is_holiday: 0,
    is_exam_period: 0,
    is_rainy: 0,
    is_special_event: 0,
    previous_day_lunch: 180,
    lunch_7_day_avg: 175,
  });
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const derived = useMemo(() => {
    const date = new Date(`${form.date}T00:00:00`);
    const start = new Date(date.getFullYear(), 0, 1);
    const dayOfYear = Math.floor((date - start) / 86400000) + 1;
    return {
      day_of_week: date.getDay() === 0 ? 6 : date.getDay() - 1,
      is_weekend: [0, 6].includes(date.getDay()) ? 1 : 0,
      day_of_month: date.getDate(),
      month: date.getMonth() + 1,
      day_of_year: dayOfYear,
      week_of_year: Math.ceil(dayOfYear / 7),
    };
  }, [form.date]);

  const update = (event) => {
    const { name, value, type, checked } = event.target;
    setForm((current) => ({ ...current, [name]: type === 'checkbox' ? Number(checked) : value }));
  };

  const submit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const response = await fetch(`${API_URL}/predict`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...form,
          previous_day_lunch: Number(form.previous_day_lunch),
          lunch_7_day_avg: Number(form.lunch_7_day_avg),
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Prediction failed');
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return <main className="shell">
    <section className="hero">
      <div className="brand"><span aria-hidden="true">◦</span> CampusOpt</div>
      <h1>Smart Mess Attendance Prediction</h1>
      <p>AI-powered lunch attendance forecasting for a 200-student hostel.</p>
    </section>

    <section className="panel">
      <form onSubmit={submit} className="form">
        <label>Prediction Date<input name="date" type="date" value={form.date} onChange={update} required /></label>
        <div className="toggles">
          {[
            ['is_holiday', 'Holiday'], ['is_exam_period', 'Exam Period'], ['is_rainy', 'Rainy Day'], ['is_special_event', 'Special Event'],
          ].map(([name, label]) => <label className="toggle" key={name}><input name={name} type="checkbox" checked={Boolean(form[name])} onChange={update} />{label}</label>)}
        </div>
        <label>Previous Day Lunch Attendance<input name="previous_day_lunch" type="number" min="0" max="200" value={form.previous_day_lunch} onChange={update} required /></label>
        <label>7-Day Average Lunch Attendance<input name="lunch_7_day_avg" type="number" min="0" max="200" step="0.1" value={form.lunch_7_day_avg} onChange={update} required /></label>
        <p className="derived">Date features are derived automatically: weekday {derived.day_of_week}, weekend {derived.is_weekend}, day {derived.day_of_month}, month {derived.month}, day-of-year {derived.day_of_year}, week {derived.week_of_year}.</p>
        <button type="submit" disabled={loading}>{loading ? 'Predicting...' : 'Predict Attendance'}</button>
      </form>

      <aside className="result" aria-live="polite">
        {error && <p className="error">{error}</p>}
        {result ? <>
          <span>Predicted Lunch Attendance</span>
          <strong>{result.prediction} students</strong>
          <div className="metrics"><p><b>Expected Range</b><br />{result.lower_bound} – {result.upper_bound} students</p><p><b>Mess Capacity</b><br />{result.capacity} students</p><p><b>Expected Utilization</b><br />{result.utilization}%</p></div>
          <small>{result.range_note}</small>
        </> : <p className="placeholder">Enter attendance context to receive a model-backed forecast.</p>}
      </aside>
    </section>

    <section className="info"><b>Model Information</b><span>Model: Random Forest</span><span>Dataset: 200-student hostel</span><span>Target: Lunch Attendance</span><span>Model status: Loaded by backend</span></section>
  </main>;
}

createRoot(document.getElementById('root')).render(<App />);
