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