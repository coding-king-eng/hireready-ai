import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend import ai_engine
from backend.database import Base, get_db
from backend.main import app

# Isolated in-memory SQLite database for tests (never modifies hireready.db)
TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Creates fresh DB tables per test and forces deterministic fallback mode."""
    monkeypatch.setenv("GEMINI_API_KEY", "")
    Base.metadata.drop_all(bind=TEST_ENGINE)
    Base.metadata.create_all(bind=TEST_ENGINE)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()


client = TestClient(app)


def test_health_and_roles_endpoints():
    health = client.get("/health")
    assert health.status_code == 200
    body = health.json()
    assert body["status"] == "ok"
    assert body["ai_mode"] == "fallback"

    roles = client.get("/api/roles")
    assert roles.status_code == 200
    roles_body = roles.json()
    assert len(roles_body["roles"]) >= 5
    assert "Intern" in roles_body["levels"]


def test_frontend_root_serves_html():
    res = client.get("/")
    assert res.status_code == 200
    assert "HireReady" in res.text


def test_full_interview_lifecycle_and_summary():
    # 1. Start a 2-question mock session
    create_res = client.post(
        "/api/sessions",
        json={
            "role": "Backend Developer (Python / FastAPI)",
            "level": "Intern",
            "question_count": 2,
        },
    )
    assert create_res.status_code == 201
    session = create_res.json()
    session_id = session["id"]
    assert session["status"] == "in_progress"
    assert session["total_questions"] == 2
    assert len(session["turns"]) == 2

    # Unanswered turns should hide ideal_hint
    assert session["turns"][0]["ideal_hint"] is None
    assert session["turns"][0]["score"] is None

    # 2. Submit a too-short answer on Turn 1 (should trigger low-score rubric)
    turn1_id = session["turns"][0]["id"]
    ans1 = client.post(
        f"/api/sessions/{session_id}/answer",
        json={"turn_id": turn1_id, "user_answer": "Not sure"},
    )
    assert ans1.status_code == 200
    turn1_data = ans1.json()
    assert turn1_data["score"] == 1.0
    assert len(turn1_data["gaps"]) >= 1
    assert turn1_data["ideal_hint"] is not None
    assert turn1_data["follow_up"] is not None

    # 3. Submit a detailed technical answer on Turn 2
    turn2_id = session["turns"][1]["id"]
    detailed_answer = (
        "In production APIs, we design idempotent operations and handle indexing, caching, "
        "concurrency, and authentication trade-offs carefully. For example, balancing read latency "
        "against write overhead prevents bottlenecks under high traffic."
    )
    ans2 = client.post(
        f"/api/sessions/{session_id}/answer",
        json={"turn_id": turn2_id, "user_answer": detailed_answer},
    )
    assert ans2.status_code == 200
    turn2_data = ans2.json()
    assert 2.0 <= turn2_data["score"] <= 10.0
    assert len(turn2_data["strengths"]) >= 1

    # 4. Verify session automatically transitioned to completed
    fetched = client.get(f"/api/sessions/{session_id}")
    assert fetched.status_code == 200
    assert fetched.json()["status"] == "completed"
    assert fetched.json()["answered_count"] == 2

    # 5. Check diagnostic summary report
    summary = client.get(f"/api/sessions/{session_id}/summary")
    assert summary.status_code == 200
    report = summary.json()
    assert report["session_id"] == session_id
    assert report["answered_count"] == 2
    assert 0 <= report["readiness_percent"] <= 100
    assert len(report["action_plan"]) >= 1


def test_error_handling_for_missing_and_invalid_inputs():
    # Nonexistent session
    assert client.get("/api/sessions/9999").status_code == 404
    assert client.get("/api/sessions/9999/summary").status_code == 404

    # Invalid question_count (above max 10) -> 422 validation error
    bad_create = client.post(
        "/api/sessions",
        json={"role": "DSA & Problem Solving (SDE-1)", "level": "Intern", "question_count": 50},
    )
    assert bad_create.status_code == 422

    # Invalid turn_id inside a valid session -> 404
    created = client.post(
        "/api/sessions",
        json={"role": "DSA & Problem Solving (SDE-1)", "level": "Intern", "question_count": 1},
    ).json()
    bad_turn = client.post(
        f"/api/sessions/{created['id']}/answer",
        json={"turn_id": 99999, "user_answer": "Sample answer text"},
    )
    assert bad_turn.status_code == 404


def test_ai_engine_json_extractor():
    fenced = '```json\n{"score": 8.5, "strengths": ["Clear"]}\n```'
    parsed = ai_engine._extract_json(fenced)
    assert parsed is not None
    assert parsed["score"] == 8.5

    wrapped = 'Sure! Here is the JSON:\n{"questions": [{"topic_tag": "SQL"}]}'
    parsed_wrapped = ai_engine._extract_json(wrapped)
    assert parsed_wrapped is not None
    assert parsed_wrapped["questions"][0]["topic_tag"] == "SQL"

    assert ai_engine._extract_json("not valid json at all") is None


def test_analytics_and_delete_session():
    created = client.post(
        "/api/sessions",
        json={"role": "Android Developer (Kotlin)", "level": "Intern", "question_count": 1},
    ).json()
    session_id = created["id"]
    turn_id = created["turns"][0]["id"]

    client.post(
        f"/api/sessions/{session_id}/answer",
        json={"turn_id": turn_id, "user_answer": "StateFlow holds latest UI state while SharedFlow emits one-time events cleanly in MVVM."},
    )

    analytics = client.get("/api/analytics")
    assert analytics.status_code == 200
    stats = analytics.json()
    assert stats["total_sessions"] == 1
    assert stats["completed_sessions"] == 1
    assert stats["total_answered"] == 1
    assert stats["overall_avg_score"] > 0

    deleted = client.delete(f"/api/sessions/{session_id}")
    assert deleted.status_code == 200
    assert deleted.json()["deleted_id"] == session_id
    assert client.get(f"/api/sessions/{session_id}").status_code == 404


def test_custom_focus_topic_prioritization():
    res = client.post(
        "/api/sessions",
        json={
            "role": "Backend Developer (Python / FastAPI)",
            "level": "Junior (0–2 Yrs)",
            "question_count": 2,
            "focus_topic": "Redis caching",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["turns"][0]["topic_tag"] == "Caching & Scalability"


def test_session_export_markdown_and_json():
    created = client.post(
        "/api/sessions",
        json={"role": "Data Analyst (SQL & Python)", "level": "Intern", "question_count": 1},
    ).json()
    session_id = created["id"]
    turn_id = created["turns"][0]["id"]

    client.post(
        f"/api/sessions/{session_id}/answer",
        json={"turn_id": turn_id, "user_answer": "ROW_NUMBER assigns unique sequential IDs while DENSE_RANK keeps consecutive ranks on ties."},
    )

    md_res = client.get(f"/api/sessions/{session_id}/export?format=markdown")
    assert md_res.status_code == 200
    assert "text/markdown" in md_res.headers["content-type"]
    assert f"hireready-session-{session_id}.md" in md_res.headers["content-disposition"]
    assert "HireReady Interview Readiness Report" in md_res.text

    json_res = client.get(f"/api/sessions/{session_id}/export?format=json")
    assert json_res.status_code == 200
    assert f"hireready-session-{session_id}.json" in json_res.headers["content-disposition"]
    exported = json_res.json()
    assert exported["summary"]["session_id"] == session_id
    assert len(exported["transcript"]) == 1

    assert client.get("/api/sessions/9999/export?format=markdown").status_code == 404


def test_role_breakdown_and_weak_topic_drill():
    created = client.post(
        "/api/sessions",
        json={"role": "Frontend Engineer (React / JS)", "level": "Intern", "question_count": 1},
    ).json()
    session_id = created["id"]
    turn_id = created["turns"][0]["id"]

    client.post(
        f"/api/sessions/{session_id}/answer",
        json={"turn_id": turn_id, "user_answer": "Short"},
    )

    analytics = client.get("/api/analytics").json()
    assert len(analytics["role_breakdown"]) == 1
    assert analytics["role_breakdown"][0]["role"] == "Frontend Engineer (React / JS)"

    summary = client.get(f"/api/sessions/{session_id}/summary").json()
    assert len(summary["weak_topics"]) == 1

    drill = client.post(
        "/api/sessions",
        json={
            "role": summary["role"],
            "level": summary["level"],
            "question_count": 3,
            "focus_topic": ", ".join(summary["weak_topics"]),
        },
    )
    assert drill.status_code == 201
    assert drill.json()["total_questions"] == 3


def test_demo_session_and_followup_evaluation():
    demo_res = client.post("/api/sessions/demo")
    assert demo_res.status_code == 201
    demo = demo_res.json()
    assert demo["status"] == "completed"
    assert demo["total_questions"] == 3
    assert demo["avg_score"] == 7.0

    summary_res = client.get(f"/api/sessions/{demo['id']}/summary")
    assert summary_res.status_code == 200
    assert "Caching & Scalability" in summary_res.json()["weak_topics"]

    turn_id = demo["turns"][0]["id"]
    followup_res = client.post(
        f"/api/sessions/{demo['id']}/followup",
        json={
            "turn_id": turn_id,
            "follow_up_question": "What happens if you call time.sleep(5) inside an async def FastAPI endpoint?",
            "follow_up_answer": "Calling time.sleep inside an async def route blocks the single asyncio event loop thread completely, stalling all other concurrent user requests until the sleep finishes.",
        },
    )
    assert followup_res.status_code == 200
    fb = followup_res.json()
    assert fb["verdict"] == "Strong Follow-Up"
    assert len(fb["coach_note"]) > 5

    assert client.post(
        "/api/sessions/9999/followup",
        json={"turn_id": turn_id, "follow_up_question": "Test?", "follow_up_answer": "Sample answer"},
    ).status_code == 404