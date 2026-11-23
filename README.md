# 🧠 HireReady — AI Technical Interview Coach

HireReady is a full-stack AI mock interview platform that generates role- and seniority-specific technical questions, grades answers against a strict `0–10` rubric using **Google Gemini**, asks interviewer follow-up probes, and produces a diagnostic readiness report with a personalized revision plan.

## ✨ Core Features
- **Role & Seniority Question Engine:** Supports Backend (Python/FastAPI), DSA/SDE-1, Frontend (React/JS), Data Analyst (SQL/Python), and Android (Kotlin) across Intern, Junior, and Mid-Level tracks.
- **Structured AI Grading (`Gemini 2.5 Flash` + Offline Rubric Fallback):** Returns strict JSON feedback containing score (`0–10`), strengths, technical gaps, an ideal answer hint, and an interviewer follow-up probe.
- **Live Interview Arena:** Dark glassmorphism UI with per-question timer, live word counter, `Cmd/Ctrl + Enter` quick submit, and resumeable sessions.
- **Readiness Report & Analytics:** Aggregates strong vs. weak topics, computes interview readiness percentage, builds a revision plan, and tracks overall KPIs across sessions.
- **Automated Test Suite:** Isolated `pytest` suite covering the full session lifecycle, validation errors, analytics, deletion, and LLM JSON extraction.

## 🛠️ Tech Stack
- **Backend:** Python, FastAPI, SQLAlchemy, SQLite, Pydantic
- **AI Layer:** Google GenAI SDK (`gemini-2.5-flash`) with deterministic fallback engine
- **Frontend:** HTML5, Tailwind CSS, Vanilla JavaScript
- **Testing & Deployment:** Pytest, HTTPX, Render

## 📡 API Endpoints
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Serves the HireReady web application |
| `GET` | `/health` | Service health + active AI engine status (`gemini` / `fallback`) |
| `GET` | `/api/roles` | Lists supported engineering roles and seniority levels |
| `POST` | `/api/sessions` | Starts a new mock interview session with generated questions |
| `GET` | `/api/sessions` | Lists recent mock interview sessions |
| `GET` | `/api/sessions/{id}` | Fetches full session state and turns |
| `POST` | `/api/sessions/{id}/answer` | Grades a candidate's answer and returns rubric feedback + follow-up |
| `GET` | `/api/sessions/{id}/summary` | Generates the diagnostic readiness report and revision plan |
| `DELETE` | `/api/sessions/{id}` | Deletes a session and its turns |
| `GET` | `/api/analytics` | Returns aggregate KPIs (total mocks, graded questions, avg & best score) |

## 🚀 Run Locally
```bash
git clone [https://github.com/coding-king-eng/hireready-ai.git](https://github.com/coding-king-eng/hireready-ai.git)
cd hireready-ai
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Optional: enable live Gemini AI
cp .env.example .env
# Add your GEMINI_API_KEY inside .env

uvicorn backend.main:app --reload