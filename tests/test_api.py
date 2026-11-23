import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend import ai_engine
from backend.database import Base, get_db
from backend.main import app

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
    assert len(roles_body["roles"]) >= 12
    assert "Senior (5–8 Yrs)" in roles_body["levels"]
    assert "Staff / Principal (8+ Yrs)" in roles_body["levels"]
    assert len(roles_body["interviewers"]) >= 6


def test_frontend_root_serves_html():
    res = client.get("/")
    assert res.status_code == 200
    assert "HireReady" in res.text


def test_video_and_normal_interview_modes():
    video_res = client.post(
        "/api/sessions",
        json={
            "role": "Backend Developer (Python / FastAPI)",
            "level": "Intern",
            "question_count": 2,
            "interviewer": "Marcus Vance",
            "interview_mode": "video",
        },
    )
    assert video_res.status_code == 201
    video_session = video_res.json()
    assert video_session["interviewer"] == "Marcus Vance"

    normal_res = client.post(
        "/api/sessions",
        json={
            "role": "Backend Developer (Python / FastAPI)",
            "level": "Junior (0–2 Yrs)",
            "question_count": 2,
            "interview_mode": "normal",
        },
    )
    assert normal_res.status_code == 201
    assert normal_res.json()["interviewer"] == "Standard Text Mode"


def test_full_interview_lifecycle_and_summary():
    create_res = client.post(
        "/api/sessions",
        json={
            "role": "Backend Developer (Python / FastAPI)",
            "level": "Intern",
            "question_count": 2,
            "interviewer": "Marcus Vance",
        },
    )
    assert create_res.status_code == 201
    session = create_res.json()
    session_id = session["id"]
    assert session["status"] == "in_progress"
    assert session["total_questions"] == 2
    assert len(session["turns"]) == 2

    assert session["turns"][0]["ideal_hint"] is None
    assert session["turns"][0]["score"] is None

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
    assert 2.0 <= ans2.json()["score"] <= 10.0

    fetched = client.get(f"/api/sessions/{session_id}")
    assert fetched.status_code == 200
    assert fetched.json()["status"] == "completed"
    assert fetched.json()["answered_count"] == 2

    summary = client.get(f"/api/sessions/{session_id}/summary")
    assert summary.status_code == 200
    report = summary.json()
    assert report["session_id"] == session_id
    assert report["answered_count"] == 2


def test_senior_staff_questions_and_15_question_round():
    res = client.post(
        "/api/sessions",
        json={
            "role": "System Design & Distributed Architecture",
            "level": "Staff / Principal (8+ Yrs)",
            "question_count": 15,
            "interviewer": "Priya Nair",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["total_questions"] == 15
    assert len(data["turns"]) == 15
    assert data["interviewer"] == "Priya Nair"


def test_ai_assistant_endpoint():
    res = client.post(
        "/api/assistant",
        json={
            "question": "How do I structure STAR answers for senior interviews?",
            "context": "Setup Screen",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert "STAR" in data["reply"]
    assert data["mode"] == "fallback"

    bad_res = client.post("/api/assistant", json={"question": "a"})
    assert bad_res.status_code == 422


def test_error_handling_for_missing_and_invalid_inputs():
    assert client.get("/api/sessions/9999").status_code == 404
    assert client.get("/api/sessions/9999/summary").status_code == 404

    bad_create = client.post(
        "/api/sessions",
        json={"role": "DSA & Problem Solving (SDE-1 / SDE-2)", "level": "Intern", "question_count": 50},
    )
    assert bad_create.status_code == 422

    created = client.post(
        "/api/sessions",
        json={"role": "DSA & Problem Solving (SDE-1 / SDE-2)", "level": "Intern", "question_count": 1},
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
    assert ai_engine._extract_json("not valid json at all") is None


def test_analytics_and_delete_session():
    created = client.post(
        "/api/sessions",
        json={"role": "Android Developer (Kotlin / Jetpack Compose)", "level": "Intern", "question_count": 1},
    ).json()
    session_id = created["id"]
    turn_id = created["turns"][0]["id"]

    client.post(
        f"/api/sessions/{session_id}/answer",
        json={"turn_id": turn_id, "user_answer": "StateFlow holds latest UI state while SharedFlow emits one-time events cleanly in MVVM."},
    )

    analytics = client.get("/api/analytics")
    assert analytics.status_code == 200
    assert analytics.json()["total_sessions"] == 1

    deleted = client.delete(f"/api/sessions/{session_id}")
    assert deleted.status_code == 200
    assert client.get(f"/api/sessions/{session_id}").status_code == 404


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
    assert "HireReady Interview Readiness Report" in md_res.text

    json_res = client.get(f"/api/sessions/{session_id}/export?format=json")
    assert json_res.status_code == 200
    assert json_res.json()["summary"]["session_id"] == session_id


def test_demo_session_and_followup_evaluation():
    demo_res = client.post("/api/sessions/demo")
    assert demo_res.status_code == 201
    demo = demo_res.json()
    assert demo["status"] == "completed"
    assert demo["level"] == "Senior (5–8 Yrs)"

    turn_id = demo["turns"][0]["id"]
    followup_res = client.post(
        f"/api/sessions/{demo['id']}/followup",
        json={
            "turn_id": turn_id,
            "follow_up_question": "How do you prevent split-brain writes during failover?",
            "follow_up_answer": "Use monotonic fencing tokens verified by the storage layer so any stale leader attempting writes after failover is immediately rejected.",
        },
    )
    assert followup_res.status_code == 200
    assert followup_res.json()["verdict"] == "Strong Follow-Up"


def test_skill_extractor_and_openapi_routes():
    extract_res = client.post(
        "/api/extract-skills",
        json={
            "raw_text": "Built RAG pipelines with Python, LLM embeddings, PyTorch, and FastAPI."
        },
    )
    assert extract_res.status_code == 200
    assert extract_res.json()["suggested_role"] == "AI / Machine Learning Engineer (LLMs & RAG)"

    schema_res = client.get("/openapi.json")
    assert schema_res.status_code == 200
    paths = schema_res.json()["paths"]
    assert "/api/interviewers" in paths
    assert "/api/assistant" in paths