"""
backend/app/main.py
FastAPI application entrypoint per Architecture.md §8.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import predict, timetable, hostel, mess

app = FastAPI(
    title="CampusOpt API",
    description="Hybrid optimization + prediction system for timetabling, hostel allocation, and mess planning.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(predict.router,   prefix="/predict",   tags=["Prediction"])
app.include_router(timetable.router, prefix="/timetable", tags=["Timetable"])
app.include_router(hostel.router,    prefix="/hostel",    tags=["Hostel"])
app.include_router(mess.router,      prefix="/mess",      tags=["Mess"])


@app.get("/health", tags=["System"])
def health_check():
    return {"status": "ok"}
