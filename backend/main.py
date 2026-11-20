import json
from typing import List
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import models, schemas
from .ai_engine import evaluate_answer, generate_questions
from .database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="HireReady 🧠 — AI Interview Coach API",
    description="Role-based mock interview generator & structured AI answer evaluator",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _serialize_turn(turn: models.InterviewTurn, hide_hint_if_unanswered: bool = True) -> schemas.TurnOut:
    answered = turn.user_answer is not None and turn.score is not None
    return schemas.TurnOut(
        id=turn.id,
        question_number=turn.question_number,
        topic_tag=turn.topic_tag,
        question_text=turn.question_text,
        user_answer=turn.user_answer,
        score=turn.score,
        strengths=json.loads(turn.strengths_json or "[]"),
        gaps=json.loads(turn.gaps_json or "[]"),
        ideal_hint=turn.ideal_hint if (answered or not hide_hint_if_unanswered) else None,
    )


def _serialize_session(session: models.InterviewSession) -> schemas.SessionDetailOut:
    ordered_turns = sorted(session.turns, key=lambda t: t.question_number)
    answered_count = sum(1 for t in ordered_turns if t.score is not None)
    return schemas.SessionDetailOut(
        id=session.id,
        role=session.role,
        level=session.level,
        total_questions=session.total_questions,
        answered_count=answered_count,
        avg_score=session.avg_score,
        status=session.status,
        turns=[_serialize_turn(t) for t in ordered_turns],
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
            "Android Developer (Kotlin)",
        ],
        "levels": ["Intern", "Junior (0–2 Yrs)", "Mid-Level (2–5 Yrs)"],
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


@app.post("/api/sessions", response_model=schemas.SessionDetailOut, status_code=201)
def create_interview_session(payload: schemas.SessionCreate, db: Session = Depends(get_db)):
    questions = generate_questions(payload.role, payload.level, payload.question_count)

    session = models.InterviewSession(
        role=payload.role,
        level=payload.level,
        total_questions=len(questions),
        avg_score=0.0,
        status="in_progress",
    )
    db.add(session)
    db.flush()

    for idx, q in enumerate(questions, start=1):
        turn = models.InterviewTurn(
            session_id=session.id,
            question_number=idx,
            topic_tag=q.get("topic_tag", "Core Concepts"),
            question_text=q["question_text"],
            ideal_hint=q.get("ideal_hint", ""),
        )
        db.add(turn)

    db.commit()
    db.refresh(session)
    return _serialize_session(session)


@app.get("/api/sessions/{session_id}", response_model=schemas.SessionDetailOut)
def get_interview_session(session_id: int, db: Session = Depends(get_db)):
    session = db.query(models.InterviewSession).filter(models.InterviewSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")
    return _serialize_session(session)


@app.post("/api/sessions/{session_id}/answer", response_model=schemas.TurnOut)
def submit_turn_answer(session_id: int, payload: schemas.AnswerSubmit, db: Session = Depends(get_db)):
    session = db.query(models.InterviewSession).filter(models.InterviewSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")

    turn = (
        db.query(models.InterviewTurn)
        .filter(models.InterviewTurn.id == payload.turn_id, models.InterviewTurn.session_id == session_id)
        .first()
    )
    if not turn:
        raise HTTPException(status_code=404, detail="Interview question turn not found")

    result = evaluate_answer(
        role=session.role,
        level=session.level,
        topic_tag=turn.topic_tag,
        question_text=turn.question_text,
        user_answer=payload.user_answer,
        ideal_hint=turn.ideal_hint or "",
    )

    turn.user_answer = payload.user_answer.strip()
    turn.score = result["score"]
    turn.strengths_json = json.dumps(result["strengths"])
    turn.gaps_json = json.dumps(result["gaps"])
    turn.ideal_hint = result["ideal_hint"]

    db.flush()

    scored_turns = [t.score for t in session.turns if t.score is not None]
    session.avg_score = round(sum(scored_turns) / len(scored_turns), 2) if scored_turns else 0.0
    if len(scored_turns) >= session.total_questions:
        session.status = "completed"

    db.commit()
    db.refresh(turn)
    return _serialize_turn(turn, hide_hint_if_unanswered=False)


@app.get("/api/sessions/{session_id}/summary", response_model=schemas.SessionSummaryOut)
def get_session_summary(session_id: int, db: Session = Depends(get_db)):
    session = db.query(models.InterviewSession).filter(models.InterviewSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")

    ordered_turns = sorted(session.turns, key=lambda t: t.question_number)
    answered_turns = [t for t in ordered_turns if t.score is not None]
    avg_score = session.avg_score
    readiness = int(round(avg_score * 10))

    if avg_score >= 8.0:
        verdict = "Strong Hire — Interview Ready"
    elif avg_score >= 6.0:
        verdict = "Solid Foundation — Polish Edge Cases"
    elif avg_score >= 4.0:
        verdict = "Developing — Focused Topic Revision Needed"
    else:
        verdict = "Needs Practice — Review Core Fundamentals"

    strong_topics: List[str] = [t.topic_tag for t in answered_turns if (t.score or 0) >= 7.0]
    weak_topics: List[str] = [t.topic_tag for t in answered_turns if (t.score or 0) < 7.0]

    action_plan: List[str] = []
    for t in answered_turns:
        if (t.score or 0) < 7.0:
            gaps = json.loads(t.gaps_json or "[]")
            tip = gaps[0] if gaps else f"Revise core concepts of {t.topic_tag}"
            action_plan.append(f"[{t.topic_tag}] {tip}")

    if not action_plan:
        action_plan.append(f"Attempt a {session.role} mock session at the next seniority tier.")

    return schemas.SessionSummaryOut(
        session_id=session.id,
        role=session.role,
        level=session.level,
        status=session.status,
        total_questions=session.total_questions,
        answered_count=len(answered_turns),
        avg_score=avg_score,
        readiness_percent=readiness,
        verdict=verdict,
        strong_topics=list(dict.fromkeys(strong_topics)),
        weak_topics=list(dict.fromkeys(weak_topics)),
        action_plan=action_plan,
    )