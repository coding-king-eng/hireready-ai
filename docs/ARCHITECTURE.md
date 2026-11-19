# 🧠 HireReady — AI Interview Coach System Architecture

## 1. Overview
**HireReady** is an interactive AI-powered mock interview platform where candidates select a target engineering/analyst role and experience level, answer dynamically generated interview questions, and receive structured JSON feedback (`0–10` score, strengths, gaps, ideal answer hints, and a weak-topic study roadmap).

## 2. Tech Stack
- **Backend:** Python 3, FastAPI, SQLAlchemy ORM, SQLite, Pydantic v2
- **AI Engine:** Google Gemini API with strict structured JSON evaluation + deterministic fallback rubric
- **Frontend:** HTML5, Tailwind CSS, Vanilla JavaScript (Mobile-First Glassmorphism UI)
- **Testing & Hosting:** Pytest, HTTPX, Render Cloud

## 3. End-to-End User & Data Flow
1. **Start Interview (`POST /api/sessions`):** User selects `role` (e.g., *Backend Developer, DSA / SDE-1, Frontend Engineer, Data Analyst*), `level` (*Intern, Junior, Mid-Level*), and `question_count`. Backend creates an `InterviewSession` and generates tailored questions.
2. **Question Delivery (`GET /api/sessions/{id}`):** Frontend presents one question at a time with live progress tracking and role context.
3. **Answer Submission & AI Evaluation (`POST /api/sessions/{id}/answer`):**
    - Candidate submits their typed answer.
    - AI Evaluator grades the response against a role-level rubric and returns structured JSON:
        - `score` (`0–10`)
        - `strengths` (key technical/communication positives)
        - `gaps` (missing concepts, edge cases, or clarity issues)
        - `ideal_hint` (concise model answer)
        - `topic_tag` (e.g., *REST APIs, Time Complexity, SQL Indexing*)
4. **Final Diagnostic Report (`GET /api/sessions/{id}/summary`):** Calculates overall readiness percentage, highlights top strengths, and lists weak topics for targeted revision.

## 4. Database Schema
- **`InterviewSession`**: `id`, `role`, `level`, `total_questions`, `avg_score`, `status`, `created_at`
- **`InterviewTurn`**: `id`, `session_id` (FK), `question_number`, `topic_tag`, `question_text`, `user_answer`, `score`, `strengths_json`, `gaps_json`, `ideal_hint`
