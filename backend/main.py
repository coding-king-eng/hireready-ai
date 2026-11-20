from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from . import models
from .database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="HireReady 🧠 — AI Interview Coach API",
    description="Role-based mock interview generator & structured AI answer evaluator",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "HireReady AI Interview Coach"}


@app.get("/api/roles")
def get_supported_roles():
    return {
        "roles": [
            "Backend Developer (Python / FastAPI)",
            "DSA & Problem Solving (SDE-1)",
            "Frontend Engineer (React / JS)",
            "Data Analyst (SQL & Python)",
            "Android Developer (Kotlin)"
        ],
        "levels": ["Intern", "Junior (0–2 Yrs)", "Mid-Level (2–5 Yrs)"]
    }


@app.get("/api/sessions")
def list_sessions(db: Session = Depends(get_db)):
    sessions = db.query(models.InterviewSession).order_by(models.InterviewSession.id.desc()).all()
    return [
        {
            "id": s.id,
            "role": s.role,
            "level": s.level,
            "total_questions": s.total_questions,
            "avg_score": s.avg_score,
            "status": s.status,
            "created_at": s.created_at,
        }
        for s in sessions
    ]