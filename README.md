# 🧠 HireReady — AI Technical Interview Coach

**HireReady** is a full-stack AI mock interview platform built with **Python, FastAPI, SQLAlchemy, Tailwind CSS, and Google Gemini**. It generates role- and seniority-calibrated technical questions, grades spoken or typed responses against a `0–10` rubric, conducts interactive follow-up probes, and produces exportable interview readiness reports.

## ✨ Key Features
- **Resume / JD Skill Extractor & Custom Role Mode:** Paste any resume bio or job description (`POST /api/extract-skills`) to auto-match the target role and extract focus keywords—or enter any custom role track.
- **Voice-to-Text Interview Arena:** Hands-free answer dictation via the browser **Web Speech API**, paired with per-question timers, live word counters, question jump pills, and `Cmd/Ctrl + Enter` quick submit.
- **Structured AI Rubric Grading (`Gemini 2.5 Flash` + Deterministic Fallback):** Grades responses `0–10` in strict JSON with concrete strengths, missing edge cases/concepts, an ideal answer hint, and an interactive **Interviewer Follow-Up Probe** (`POST /api/sessions/{id}/followup`).
- **Diagnostic Readiness Report & Smart Retakes:** Separates strong vs. weak topics, generates a personalized revision plan, launches 1-click **Weak-Topic Drill** sessions, and exports full transcripts as **Markdown (`.md`)**, **JSON (`.json`)**, or **PDF**.
- **Analytics & 1-Click Sample Demo:** Tracks aggregate KPIs and role mastery bars across sessions (`GET /api/analytics`) and provides a 1-click pre-graded sample report (`POST /api/sessions/demo`).

## 🛠️ Tech Stack
- **Backend:** Python 3.12, FastAPI, SQLAlchemy, SQLite, Pydantic v2
- **AI Engine:** Google GenAI SDK (`gemini-2.5-flash`) with deterministic keyword/structure fallback
- **Frontend:** HTML5, Tailwind CSS, Vanilla JavaScript, Web Speech API
- **Testing & Cloud Deployment:** Pytest, HTTPX, Render (`render.yaml` auto-deploy)

## 📡 API Reference
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Serves the HireReady web application |
| `GET` | `/health` | Service health & active AI engine mode (`gemini` / `fallback`) |
| `GET` | `/api/roles` | Lists built-in engineering roles and seniority levels |
| `POST` | `/api/extract-skills` | Extracts technical skills & matches target role from resume/JD text |
| `POST` | `/api/sessions` | Starts a new mock interview session with generated questions |
| `POST` | `/api/sessions/demo` | Creates a pre-graded sample mock session for instant report preview |
| `GET` | `/api/sessions` | Lists recent mock interview sessions |
| `GET` | `/api/sessions/{id}` | Fetches full session state and question turns |
| `POST` | `/api/sessions/{id}/answer` | Grades a candidate's answer and returns rubric feedback + follow-up |
| `POST` | `/api/sessions/{id}/followup` | Evaluates the candidate's response to the follow-up probe |
| `GET` | `/api/sessions/{id}/summary` | Computes readiness percentage, verdict, weak topics & revision plan |
| `GET` | `/api/sessions/{id}/export` | Downloads full report & transcript (`?format=markdown` or `?format=json`) |
| `DELETE` | `/api/sessions/{id}` | Deletes a session and its turns |
| `GET` | `/api/analytics` | Returns aggregate KPIs and per-role mastery breakdown |

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