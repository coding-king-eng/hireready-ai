import json
from pathlib import Path
from typing import List
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from . import models, schemas
from .ai_engine import (
    FALLBACK_QUESTIONS,
    ask_ai_assistant,
    evaluate_answer,
    evaluate_followup,
    extract_skills_from_text,
    generate_questions,
    get_engine_status,
)
from .database import engine, get_db

models.Base.metadata.create_all(bind=engine)


def _ensure_interviewer_column():
    """Safely adds `interviewer` column if upgrading an existing SQLite database."""
    try:
        with engine.begin() as conn:
            cols = [row[1] for row in conn.execute(text("PRAGMA table_info(interview_sessions)")).fetchall()]
            if cols and "interviewer" not in cols:
                conn.execute(text("ALTER TABLE interview_sessions ADD COLUMN interviewer VARCHAR(100) DEFAULT 'Aanya Sharma'"))
    except Exception:
        pass


_ensure_interviewer_column()

app = FastAPI(
    title="HireReady 🧠 — AI Live Video & Standard Interview Coach API",
    description="Role-based live AI video & standard mock interview simulator, rubric evaluator & AI assistant",
    version="2.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

INTERVIEWER_PERSONAS = [
    {
        "id": "aanya",
        "name": "Aanya Sharma",
        "gender": "woman",
        "title": "Senior Engineering Manager",
        "style": "Warm, structured & encouraging",
        "accent_hint": "Clear Neutral English",
    },
    {
        "id": "marcus",
        "name": "Marcus Vance",
        "gender": "man",
        "title": "Principal Systems Architect",
        "style": "Deep-dive, analytical & scale-focused",
        "accent_hint": "US Deep Baritone",
    },
    {
        "id": "elena",
        "name": "Elena Rostova",
        "gender": "woman",
        "title": "Staff Frontend & Product Lead",
        "style": "Crisp, user-centric & detail-oriented",
        "accent_hint": "UK / International English",
    },
    {
        "id": "david",
        "name": "David Chen",
        "gender": "man",
        "title": "Staff Distributed Systems Lead",
        "style": "Calm, pragmatic & trade-off driven",
        "accent_hint": "US Natural Tenor",
    },
    {
        "id": "priya",
        "name": "Priya Nair",
        "gender": "woman",
        "title": "Director of AI & Data Platform",
        "style": "Strategic, inquisitive & metrics-first",
        "accent_hint": "Indian / Global English",
    },
    {
        "id": "liam",
        "name": "Liam O'Connor",
        "gender": "man",
        "title": "VP of Engineering",
        "style": "Executive, architectural & leadership-focused",
        "accent_hint": "British / Irish English",
    },
]


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
        interviewer=session.interviewer or "Aanya Sharma",
        total_questions=session.total_questions,
        answered_count=answered_count,
        avg_score=session.avg_score,
        status=session.status,
        turns=[_serialize_turn(t) for t in ordered_turns],
    )


def _build_summary_data(session: models.InterviewSession) -> schemas.SessionSummaryOut:
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


FRONTEND_INDEX = Path(__file__).resolve().parent.parent / "frontend" / "index.html"


@app.get("/")
def serve_frontend():
    return FileResponse(FRONTEND_INDEX)


@app.get("/health")
def health_check():
    ai_status = get_engine_status()
    return {
        "status": "ok",
        "service": "HireReady AI Interview Coach",
        "version": "2.1.0",
        "ai_mode": ai_status["mode"],
        "ai_model": ai_status["model"],
    }


@app.get("/api/roles")
def get_supported_roles():
    return {
        "roles": list(FALLBACK_QUESTIONS.keys()),
        "levels": [
            "Intern",
            "Junior (0–2 Yrs)",
            "Mid-Level (2–5 Yrs)",
            "Senior (5–8 Yrs)",
            "Staff / Principal (8+ Yrs)",
            "Engineering Manager / Tech Lead",
        ],
        "question_counts": [3, 5, 8, 10, 12, 15],
        "interviewers": INTERVIEWER_PERSONAS,
    }


@app.get("/api/interviewers")
def list_interviewers():
    return {"interviewers": INTERVIEWER_PERSONAS}


@app.post("/api/extract-skills", response_model=schemas.SkillExtractOut)
def extract_skills(payload: schemas.SkillExtractRequest):
    result = extract_skills_from_text(payload.raw_text)
    return schemas.SkillExtractOut(**result)


@app.post("/api/assistant", response_model=schemas.AssistantOut)
def query_ai_assistant(payload: schemas.AssistantRequest):
    result = ask_ai_assistant(payload.question, payload.context)
    return schemas.AssistantOut(**result)


@app.get("/api/sessions")
def list_sessions(db: Session = Depends(get_db)):
    sessions = db.query(models.InterviewSession).order_by(models.InterviewSession.id.desc()).all()
    return [
        {
            "id": s.id,
            "role": s.role,
            "level": s.level,
            "interviewer": s.interviewer or "Aanya Sharma",
            "total_questions": s.total_questions,
            "avg_score": s.avg_score,
            "status": s.status,
            "created_at": s.created_at,
        }
        for s in sessions
    ]


@app.post("/api/sessions/demo", response_model=schemas.SessionDetailOut, status_code=201)
def create_demo_session(db: Session = Depends(get_db)):
    """Creates a realistic pre-graded 3-question Senior mock session so visitors can preview reports immediately."""
    demo_turns = [
        {
            "topic_tag": "Multi-Region Architecture",
            "question_text": "You are scaling a write-heavy global service across US, EU, and APAC regions with a 150ms p99 SLA. How do you design data partitioning, conflict resolution, and failover?",
            "user_answer": "Geo-partition user records into home regions so writes stay local under 150ms, use async cross-region replication with CRDTs for shared counters, and configure automated DNS health-checked failover.",
            "score": 9.0,
            "strengths": [
                "Identified regional data locality to satisfy the 150ms p99 write SLA.",
                "Applied CRDTs and automated health-checked failover cleanly.",
            ],
            "gaps": ["Mention split-brain fencing tokens during primary region failover."],
            "ideal_hint": "Geo-partition user data to home regions to keep writes local, use asynchronous cross-region replication with CRDTs or last-write-wins vector clocks for shared state, and automate DNS/anycast health-checked failover.",
        },
        {
            "topic_tag": "Zero-Downtime Schema Migration",
            "question_text": "How do you rename and split a heavily queried 500M-row production table column with zero downtime and instant rollback safety?",
            "user_answer": "Follow Expand-and-Contract: add new columns first, dual-write to both old and new columns, backfill old rows in small batches, verify parity, then switch reads.",
            "score": 8.0,
            "strengths": [
                "Structured the rollout with Expand-and-Contract and throttled batch backfills.",
                "Maintained backward compatibility for zero-downtime deployment.",
            ],
            "gaps": ["Include lock-timeout guardrails during initial DDL column creation."],
            "ideal_hint": "Use the Expand-and-Contract pattern: add new columns, dual-write to both old and new schemas, backfill historical rows in throttled batches, switch reads after verification, then drop old columns later.",
        },
        {
            "topic_tag": "Caching & Scalability",
            "question_text": "Describe the Cache-Aside (Lazy Loading) pattern with Redis and how you prevent cache stampedes under high traffic.",
            "user_answer": "We check Redis first and if missing we query the database and save it back to Redis.",
            "score": 4.5,
            "strengths": ["Captured the basic read-through flow of Cache-Aside."],
            "gaps": [
                "Did not explain TTL expiration or cache stampede mitigations (mutex locks, jittered TTLs).",
                "Include how stale data is invalidated on writes.",
            ],
            "ideal_hint": "App checks Redis first; on miss, reads DB and populates cache with a TTL. Prevent stampedes using mutex locks, jittered TTLs, or background refresh.",
        },
    ]

    avg = round(sum(t["score"] for t in demo_turns) / len(demo_turns), 2)
    session = models.InterviewSession(
        role="System Design & Distributed Architecture",
        level="Senior (5–8 Yrs)",
        interviewer="Marcus Vance",
        total_questions=len(demo_turns),
        avg_score=avg,
        status="completed",
    )
    db.add(session)
    db.flush()

    for idx, item in enumerate(demo_turns, start=1):
        db.add(
            models.InterviewTurn(
                session_id=session.id,
                question_number=idx,
                topic_tag=item["topic_tag"],
                question_text=item["question_text"],
                user_answer=item["user_answer"],
                score=item["score"],
                strengths_json=json.dumps(item["strengths"]),
                gaps_json=json.dumps(item["gaps"]),
                ideal_hint=item["ideal_hint"],
            )
        )

    db.commit()
    db.refresh(session)
    return _serialize_session(session)


@app.post("/api/sessions", response_model=schemas.SessionDetailOut, status_code=201)
def create_interview_session(payload: schemas.SessionCreate, db: Session = Depends(get_db)):
    questions = generate_questions(
        payload.role,
        payload.level,
        payload.question_count,
        payload.focus_topic,
    )

    interviewer_label = (
        "Standard Text Mode"
        if payload.interview_mode == "normal"
        else (payload.interviewer or "Aanya Sharma").strip()
    )

    session = models.InterviewSession(
        role=payload.role,
        level=payload.level,
        interviewer=interviewer_label,
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

    turn_out = _serialize_turn(turn, hide_hint_if_unanswered=False)
    turn_out.follow_up = result.get("follow_up")
    return turn_out


@app.post("/api/sessions/{session_id}/followup", response_model=schemas.FollowUpFeedbackOut)
def submit_followup_answer(session_id: int, payload: schemas.FollowUpSubmit, db: Session = Depends(get_db)):
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

    feedback = evaluate_followup(
        role=session.role,
        level=session.level,
        topic_tag=turn.topic_tag,
        follow_up_question=payload.follow_up_question,
        follow_up_answer=payload.follow_up_answer,
    )
    return schemas.FollowUpFeedbackOut(**feedback)


@app.get("/api/sessions/{session_id}/summary", response_model=schemas.SessionSummaryOut)
def get_session_summary(session_id: int, db: Session = Depends(get_db)):
    session = db.query(models.InterviewSession).filter(models.InterviewSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")
    return _build_summary_data(session)


@app.get("/api/sessions/{session_id}/export")
def export_session_report(
        session_id: int,
        format: str = Query(default="markdown", pattern="^(markdown|json)$"),
        db: Session = Depends(get_db),
):
    session = db.query(models.InterviewSession).filter(models.InterviewSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")

    summary = _build_summary_data(session)
    detail = _serialize_session(session)

    if format == "json":
        payload = {
            "summary": summary.model_dump(),
            "interviewer": detail.interviewer,
            "transcript": [t.model_dump() for t in detail.turns],
        }
        return JSONResponse(
            content=payload,
            headers={"Content-Disposition": f'attachment; filename="hireready-session-{session_id}.json"'},
        )

    lines = [
        f"# HireReady Interview Readiness Report — Session #{session.id}",
        "",
        f"- **Mode / Interviewer:** {detail.interviewer}",
        f"- **Role:** {summary.role}",
        f"- **Level:** {summary.level}",
        f"- **Status:** {summary.status}",
        f"- **Average Score:** {summary.avg_score} / 10",
        f"- **Readiness:** {summary.readiness_percent}%",
        f"- **Verdict:** {summary.verdict}",
        "",
        "## Personalized Revision Plan",
    ]
    for item in summary.action_plan:
        lines.append(f"- {item}")

    lines.extend(["", "## Question-by-Question Transcript"])
    for turn in detail.turns:
        score_str = f"{turn.score}/10" if turn.score is not None else "Not answered"
        lines.extend([
            "",
            f"### Q{turn.question_number}. [{turn.topic_tag}] ({score_str})",
            f"**Question:** {turn.question_text}",
            "",
            f"**Your Answer:** {turn.user_answer or '_Unanswered_'}",
            "",
            "**Strengths:**",
        ])
        for s in (turn.strengths or ["N/A"]):
            lines.append(f"- {s}")
        lines.append("")
        lines.append("**Gaps to Improve:**")
        for g in (turn.gaps or ["N/A"]):
            lines.append(f"- {g}")
        if turn.ideal_hint:
            lines.extend(["", f"**Ideal Answer Hint:** {turn.ideal_hint}"])

    markdown_body = "\n".join(lines) + "\n"
    return PlainTextResponse(
        content=markdown_body,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="hireready-session-{session_id}.md"'},
    )


@app.get("/api/analytics")
def get_analytics(db: Session = Depends(get_db)):
    sessions = db.query(models.InterviewSession).all()
    answered_turns = (
        db.query(models.InterviewTurn)
        .filter(models.InterviewTurn.score.isnot(None))
        .all()
    )

    total_sessions = len(sessions)
    completed_sessions = sum(1 for s in sessions if s.status == "completed")
    scored_sessions = [s.avg_score for s in sessions if s.avg_score and s.avg_score > 0]
    overall_avg = round(sum(scored_sessions) / len(scored_sessions), 2) if scored_sessions else 0.0
    best_score = round(max(scored_sessions), 2) if scored_sessions else 0.0

    role_scores = {}
    for s in sessions:
        if s.avg_score and s.avg_score > 0:
            role_scores.setdefault(s.role, []).append(s.avg_score)

    role_breakdown = sorted(
        [
            {"role": role, "sessions": len(scores), "avg_score": round(sum(scores) / len(scores), 2)}
            for role, scores in role_scores.items()
        ],
        key=lambda item: item["avg_score"],
        reverse=True,
    )

    return {
        "total_sessions": total_sessions,
        "completed_sessions": completed_sessions,
        "total_answered": len(answered_turns),
        "overall_avg_score": overall_avg,
        "best_score": best_score,
        "role_breakdown": role_breakdown,
    }


@app.delete("/api/sessions/{session_id}")
def delete_interview_session(session_id: int, db: Session = Depends(get_db)):
    session = db.query(models.InterviewSession).filter(models.InterviewSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")

    db.query(models.InterviewTurn).filter(models.InterviewTurn.session_id == session_id).delete()
    db.delete(session)
    db.commit()
    return {"deleted_id": session_id, "status": "deleted"}