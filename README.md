# 🧠 HireReady v2.1 — Live AI Video & Standard Interview Coach

**Live App:** [https://hireready-ai-jk3i.onrender.com/](https://hireready-ai-jk3i.onrender.com/)  
**Interactive API Docs:** [https://hireready-ai-jk3i.onrender.com/docs](https://hireready-ai-jk3i.onrender.com/docs)

**HireReady** is a full-stack AI mock interview platform built with **Python, FastAPI, SQLAlchemy, Tailwind CSS, and Google Gemini**. Candidates can choose between a face-to-face **Live AI Video Call** (with realistic male and female interviewer personas, neural voice synthesis, and lip-sync) or a quiet **Standard Text Interview** across **12 engineering roles** and **6 experience levels** (Intern up to Staff/Principal & Engineering Manager).

## ✨ Key Features
- **🎥 Live AI Video Call Mode vs. 📝 Standard Mode:** Switch seamlessly between a live simulated video call (6 male & female interviewer personas with instant auto-voice preview, lip-sync, and optional self-webcam PiP) or a distraction-free text interview mode.
- **🎯 12 Engineering Tracks & Senior/Staff Calibration:** Covers Backend, Full-Stack, Frontend, DSA, System Design, AI/ML (LLMs & RAG), DevOps/K8s, Android, iOS, Data Engineering, Data Analytics, and Cybersecurity—plus Custom Roles and rounds up to **15 questions**.
- **📄 Resume / JD Skill Extractor:** Paste any resume bio or job description (`POST /api/extract-skills`) to auto-extract technical skills and match the closest role track.
- **🎙️ Voice-to-Text Arena & Structured `0–10` Rubric (`Gemini 2.5 Flash`):** Speak or type answers to receive instant strengths, missing edge cases, an ideal answer hint, and an interactive **Live Follow-Up Probe** (`POST /api/sessions/{id}/followup`).
- **💬 Built-in HireReady AI Assistant:** Floating coach drawer (`POST /api/assistant`) for instant technical clarifications, STAR behavioral framing tips, and app guidance.
- **📊 Readiness Report, Weak-Topic Drills & Exports:** Identifies strong vs. weak topics, launches 1-click **Weak-Topic Drills**, and exports full transcripts in **Markdown (`.md`)**, **JSON (`.json`)**, or **PDF**.

## 🛠️ Tech Stack
- **Backend:** Python 3.12, FastAPI, SQLAlchemy, SQLite, Pydantic v2
- **AI & Speech:** Google GenAI SDK (`gemini-2.5-flash` + deterministic fallback), Web Speech API (`SpeechRecognition` & `SpeechSynthesis`), WebRTC Webcam PiP
- **Frontend:** HTML5, Tailwind CSS, Vanilla JavaScript, Animated SVG Portraits
- **Testing & Deployment:** Pytest (12 automated tests), Render Cloud, UptimeRobot 24/7 Health Monitoring

## 📡 API Reference
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Serves the HireReady web application |
| `GET` | `/health` | Service health & active AI engine mode (`gemini` / `fallback`) |
| `GET` | `/api/roles` | Lists 12 engineering roles, 6 experience levels, question counts & personas |
| `GET` | `/api/interviewers` | Lists available male & female interviewer personas |
| `POST` | `/api/extract-skills` | Extracts technical skills & matches role from resume/JD text |
| `POST` | `/api/assistant` | Built-in AI interview coach & troubleshooting assistant |
| `POST` | `/api/sessions` | Starts a new Video Call or Standard mock interview session |
| `POST` | `/api/sessions/demo` | Creates a pre-graded Senior sample report for instant preview |
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
```
Open `http://127.0.0.1:8000` for the web app or `http://127.0.0.1:8000/docs` for Swagger API docs.

## 🧪 Automated Test Suite
```bash
python3 -m pytest -v
```
Runs 12 isolated tests against an in-memory SQLite database covering Video & Standard modes, Senior/Staff 15-question rounds, rubric scoring, follow-up probes, skill extraction, AI Assistant queries, Markdown/JSON exports, and OpenAPI schema validation.