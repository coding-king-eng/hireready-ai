import json
import os
import random
import re
from typing import Any, Dict, List
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()

# Curated role-specific fallback question bank (ensures 100% uptime even without an API key)
FALLBACK_QUESTIONS: Dict[str, List[Dict[str, str]]] = {
    "Backend Developer (Python / FastAPI)": [
        {
            "topic_tag": "REST APIs & HTTP",
            "question_text": "Explain the difference between PUT and PATCH in REST APIs, and when you would use idempotency keys in payment or order endpoints.",
            "ideal_hint": "PUT replaces the entire resource and is idempotent; PATCH applies partial updates. Idempotency keys prevent duplicate side effects when clients retry timed-out POST requests."
        },
        {
            "topic_tag": "Database Indexing",
            "question_text": "How does a B-Tree database index speed up SELECT queries, and what is the performance trade-off on INSERT/UPDATE operations?",
            "ideal_hint": "A B-Tree index keeps sorted keys for O(log n) lookups instead of full table scans, but slows down INSERT/UPDATE/DELETE because the index tree must also be updated."
        },
        {
            "topic_tag": "Async & Concurrency",
            "question_text": "In FastAPI, when should you define an endpoint with `async def` versus standard `def`?",
            "ideal_hint": "Use `async def` for non-blocking I/O operations (awaiting async DB/HTTP calls); use standard `def` for blocking/CPU-bound work so FastAPI runs it in a separate threadpool without blocking the event loop."
        },
        {
            "topic_tag": "Authentication & Security",
            "question_text": "Compare JWT stateless authentication with server-side session cookies. How do you handle token revocation with JWTs?",
            "ideal_hint": "JWTs store signed claims client-side without DB lookups per request, whereas sessions store state server-side. Revocation uses short-lived access tokens paired with rotating refresh tokens or a Redis denylist."
        },
        {
            "topic_tag": "Caching & Scalability",
            "question_text": "Describe the Cache-Aside (Lazy Loading) pattern with Redis and how you prevent cache stampedes under high traffic.",
            "ideal_hint": "App checks Redis first; on miss, reads DB and populates cache with a TTL. Prevent stampedes using mutex locks, jittered TTLs, or background refresh."
        },
    ],
    "DSA & Problem Solving (SDE-1)": [
        {
            "topic_tag": "Arrays & Hashing",
            "question_text": "How would you find the longest subarray with sum equal to K in an array containing negative numbers? State time and space complexity.",
            "ideal_hint": "Use a prefix sum running total and a hash map storing the earliest index of each prefix sum. Time: O(n), Space: O(n)."
        },
        {
            "topic_tag": "Trees & Graphs",
            "question_text": "Explain how to detect a cycle in a directed graph versus an undirected graph.",
            "ideal_hint": "Undirected graphs use DFS with a parent pointer or Union-Find. Directed graphs require tracking nodes in the current recursion stack (3-color DFS: unvisited, visiting, visited) or Kahn's topological sort."
        },
        {
            "topic_tag": "Dynamic Programming",
            "question_text": "Explain the difference between Top-Down (Memoization) and Bottom-Up (Tabulation) Dynamic Programming with an example.",
            "ideal_hint": "Memoization solves recursively from the main state and caches subproblems; Tabulation iteratively fills a DP table from base cases, avoiding recursion stack overhead and enabling space optimization."
        },
        {
            "topic_tag": "Sliding Window",
            "question_text": "Walk through finding the longest substring without repeating characters in O(n) time.",
            "ideal_hint": "Maintain a sliding window `[left, right]` and a hash map of each character's last seen index; jump `left` to `max(left, last_seen[ch] + 1)` on duplicates."
        },
        {
            "topic_tag": "Heaps & Priority Queues",
            "question_text": "How do you find the Kth largest element in a stream of numbers efficiently?",
            "ideal_hint": "Maintain a Min-Heap of size K. Push each element and pop if size > K; the root is always the Kth largest in O(log K) per insertion."
        },
    ],
    "Frontend Engineer (React / JS)": [
        {
            "topic_tag": "JavaScript Event Loop",
            "question_text": "Explain the difference between the Microtask Queue and Macrotask Queue in JavaScript with `Promise.then` and `setTimeout`.",
            "ideal_hint": "After each macrotask (e.g., setTimeout, UI events), the JS engine drains the entire microtask queue (Promises, queueMicrotask) before rendering or picking the next macrotask."
        },
        {
            "topic_tag": "React Rendering",
            "question_text": "What causes unnecessary re-renders in React, and when should you use `useMemo` or `useCallback`?",
            "ideal_hint": "State/context updates or new object/function references passed to memoized children trigger re-renders. Use `useMemo`/`useCallback` for expensive calculations or referential stability."
        },
        {
            "topic_tag": "Web Performance",
            "question_text": "Compare Debouncing and Throttling and give a real UI example for each.",
            "ideal_hint": "Debouncing delays execution until inactivity (e.g., search autocomplete input); Throttling limits execution to once every X ms (e.g., scroll or window resize listeners)."
        },
        {
            "topic_tag": "Browser Storage & Security",
            "question_text": "Compare `localStorage`, `sessionStorage`, and `HttpOnly` cookies in terms of persistence and XSS/CSRF security.",
            "ideal_hint": "localStorage persists across tabs/restarts; sessionStorage clears on tab close; both are readable by JS (vulnerable to XSS). HttpOnly cookies are inaccessible to JS and suited for auth tokens with SameSite protection."
        },
        {
            "topic_tag": "CSS & Layout",
            "question_text": "When would you choose CSS Grid over Flexbox for building a responsive dashboard?",
            "ideal_hint": "Flexbox excels at 1-dimensional alignment (navbars, button rows), while CSS Grid excels at 2-dimensional row-and-column layouts with explicit tracks."
        },
    ],
    "Data Analyst (SQL & Python)": [
        {
            "topic_tag": "SQL Window Functions",
            "question_text": "Explain the difference between `ROW_NUMBER()`, `RANK()`, and `DENSE_RANK()` when handling tied values.",
            "ideal_hint": "ROW_NUMBER assigns unique sequential integers; RANK leaves gaps after ties (1,1,3); DENSE_RANK assigns consecutive ranks without gaps (1,1,2)."
        },
        {
            "topic_tag": "SQL Joins & Optimization",
            "question_text": "Why can filtering a right-table column in the `WHERE` clause turn a `LEFT JOIN` into an `INNER JOIN`?",
            "ideal_hint": "Unmatched left rows have NULLs for right-table columns, which get eliminated by `WHERE right.col = ...` unless placed inside the `ON` condition."
        },
        {
            "topic_tag": "Pandas & Data Cleaning",
            "question_text": "How do you handle missing values and outliers in a skewed numerical dataset before reporting KPIs?",
            "ideal_hint": "Inspect missingness mechanism; impute skewed distributions with median rather than mean, flag/cap extreme outliers via IQR or domain thresholds, and report median + IQR."
        },
        {
            "topic_tag": "A/B Testing & Metrics",
            "question_text": "What is p-value and statistical power in an A/B test, and why shouldn't you stop an experiment early?",
            "ideal_hint": "p-value measures probability of observing results as extreme under the null hypothesis; peeking/early stopping inflates false-positive rates."
        },
        {
            "topic_tag": "SQL Aggregations",
            "question_text": "Write or explain a SQL approach to find users who made purchases in two consecutive months.",
            "ideal_hint": "Use `DATE_TRUNC('month', order_date)` with `LAG(order_month) OVER (PARTITION BY user_id ORDER BY order_month)` and filter where difference equals 1 month."
        },
    ],
    "Android Developer (Kotlin)": [
        {
            "topic_tag": "Kotlin Coroutines",
            "question_text": "Explain the difference between `launch` and `async` in Kotlin Coroutines, and what Structured Concurrency guarantees.",
            "ideal_hint": "`launch` returns a `Job` for fire-and-forget work; `async` returns a `Deferred<T>` with `.await()`. Structured concurrency ensures child coroutines complete or cancel with their parent scope, preventing leaks."
        },
        {
            "topic_tag": "Jetpack Compose",
            "question_text": "What is State Hoisting in Jetpack Compose and why is unidirectional data flow important?",
            "ideal_hint": "State hoisting moves state up to a caller composable by passing `value` and `onValueChange` callbacks, making UI stateless, testable, and predictable."
        },
        {
            "topic_tag": "Android Architecture (MVVM)",
            "question_text": "Compare `StateFlow` and `SharedFlow` in a ViewModel for managing UI state vs one-time events.",
            "ideal_hint": "`StateFlow` holds a single latest state value and replays it to new collectors (ideal for UI state); `SharedFlow` emits event streams without requiring an initial value (ideal for navigation/snackbars)."
        },
        {
            "topic_tag": "Lifecycle & Memory",
            "question_text": "How does a `ViewModel` survive configuration changes like screen rotation, and what must you avoid storing inside it?",
            "ideal_hint": "ViewModel is retained in `ViewModelStore` across Activity recreation. Never store Activity `Context` or `View` references inside ViewModel to avoid memory leaks."
        },
        {
            "topic_tag": "Networking & Offline Caching",
            "question_text": "How would you design an offline-first repository pattern using Retrofit and Room?",
            "ideal_hint": "Room acts as the single source of truth exposed via Flow; repository fetches from Retrofit, updates Room in a transaction, and UI reactively observes local DB updates."
        },
    ],
}

KNOWN_TECH_SKILLS = [
    "Python", "FastAPI", "Django", "Flask", "SQL", "PostgreSQL", "MySQL", "SQLite",
    "Redis", "Docker", "Kubernetes", "REST API", "GraphQL", "JWT", "Microservices",
    "JavaScript", "TypeScript", "React", "Next.js", "Node.js", "Tailwind CSS", "HTML", "CSS",
    "Kotlin", "Android", "Jetpack Compose", "Coroutines", "Room", "Retrofit", "MVVM",
    "Pandas", "NumPy", "A/B Testing", "Power BI", "Tableau",
    "Data Structures", "Algorithms", "Dynamic Programming", "Graphs", "Trees", "System Design",
    "Git", "Linux", "AWS", "LLM", "Gemini API",
]


def get_engine_status() -> Dict[str, str]:
    """Reports whether live Gemini AI or deterministic fallback mode is active."""
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if key and not key.startswith("your_"):
        return {"mode": "gemini", "model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()}
    return {"mode": "fallback", "model": "deterministic-rubric-v1"}


def _extract_json(raw_text: str) -> Dict[str, Any] | None:
    """Safely strips markdown fences and parses JSON returned by an LLM."""
    if not raw_text:
        return None
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            return None
        try:
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None


def _clean_str_list(items: Any, fallback: List[str], limit: int = 3) -> List[str]:
    if not isinstance(items, list):
        return fallback
    cleaned = [str(x).strip() for x in items if str(x).strip()]
    return cleaned[:limit] if cleaned else fallback


def _call_gemini_json(prompt: str) -> Dict[str, Any] | None:
    """Calls Google Gemini API when GEMINI_API_KEY is configured and parses JSON safely."""
    status = get_engine_status()
    if status["mode"] != "gemini":
        return None
    try:
        from google import genai
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", "").strip())
        response = client.models.generate_content(
            model=status["model"],
            contents=prompt,
            config={"response_mime_type": "application/json", "temperature": 0.4},
        )
        return _extract_json(response.text or "")
    except Exception:
        return None


def extract_skills_from_text(raw_text: str) -> Dict[str, Any]:
    """Extracts technical skills and suggests the closest interview role from a resume or JD."""
    cleaned = (raw_text or "").strip()
    prompt = f"""
    Analyze this candidate resume snippet or job description:
    \"\"\"{cleaned}\"\"\"

    Extract up to 8 key technical skills/concepts and choose the single best matching role from:
    - Backend Developer (Python / FastAPI)
    - DSA & Problem Solving (SDE-1)
    - Frontend Engineer (React / JS)
    - Data Analyst (SQL & Python)
    - Android Developer (Kotlin)

    Return ONLY valid JSON:
    {{
      "suggested_role": "Backend Developer (Python / FastAPI)",
      "extracted_skills": ["Python", "FastAPI", "Redis", "SQL"]
    }}
    """
    ai_res = _call_gemini_json(prompt)
    if ai_res and isinstance(ai_res.get("extracted_skills"), list):
        skills = [str(s).strip() for s in ai_res["extracted_skills"] if str(s).strip()][:8]
        role = str(ai_res.get("suggested_role") or "Backend Developer (Python / FastAPI)").strip()
        if skills:
            return {
                "suggested_role": role,
                "extracted_skills": skills,
                "focus_query": ", ".join(skills[:6]),
            }

    lower_text = cleaned.lower()
    matched = [skill for skill in KNOWN_TECH_SKILLS if skill.lower() in lower_text][:8]
    if not matched:
        matched = ["System Design", "Data Structures", "REST API"]

    matched_lower = {m.lower() for m in matched}
    if matched_lower & {"kotlin", "android", "jetpack compose", "coroutines", "room", "retrofit"}:
        suggested = "Android Developer (Kotlin)"
    elif matched_lower & {"react", "javascript", "typescript", "next.js", "tailwind css", "css"}:
        suggested = "Frontend Engineer (React / JS)"
    elif matched_lower & {"pandas", "numpy", "a/b testing", "power bi", "tableau"}:
        suggested = "Data Analyst (SQL & Python)"
    elif matched_lower & {"dynamic programming", "graphs", "trees", "data structures", "algorithms"}:
        suggested = "DSA & Problem Solving (SDE-1)"
    else:
        suggested = "Backend Developer (Python / FastAPI)"

    return {
        "suggested_role": suggested,
        "extracted_skills": matched,
        "focus_query": ", ".join(matched[:6]),
    }


def generate_questions(
        role: str,
        level: str,
        count: int = 5,
        focus_topic: str | None = None,
) -> List[Dict[str, str]]:
    """Generates `count` distinct, seniority-calibrated interview questions."""
    clean_focus = (focus_topic or "").strip()
    focus_instruction = (
        f"- Specific Focus Areas / Job Description Keywords: {clean_focus} (prioritize these concepts)"
        if clean_focus
        else "- Cover a balanced mix of core topics for this role"
    )

    prompt = f"""
    You are a senior staff engineer conducting a real technical interview.
    Generate {count} distinct, practical interview questions tailored to:
    - Role: {role}
    - Seniority Level: {level}
    {focus_instruction}

    Rules:
    - Cover different angles (no duplicate questions).
    - Calibrate depth to the {level} level (fundamentals + edge cases for Intern/Junior; system trade-offs for Mid-Level).
    - Return ONLY valid JSON matching this exact schema:
    {{
      "questions": [
        {{
          "topic_tag": "Short topic label (2-4 words)",
          "question_text": "Clear, focused interview question",
          "ideal_hint": "Concise 2-sentence model answer covering key expected concepts"
        }}
      ]
    }}
    """
    ai_data = _call_gemini_json(prompt)
    if ai_data and isinstance(ai_data.get("questions"), list):
        valid_qs = [
            {
                "topic_tag": str(q.get("topic_tag", "Core Concepts")).strip()[:80],
                "question_text": str(q.get("question_text", "")).strip(),
                "ideal_hint": str(q.get("ideal_hint", "")).strip(),
            }
            for q in ai_data["questions"]
            if isinstance(q, dict) and str(q.get("question_text", "")).strip()
        ]
        if len(valid_qs) >= count:
            return valid_qs[:count]

    pool = list(FALLBACK_QUESTIONS.get(role, FALLBACK_QUESTIONS["Backend Developer (Python / FastAPI)"]))
    if clean_focus:
        keywords = {w.lower().strip(",.;:") for w in clean_focus.split() if len(w) > 2}
        pool.sort(
            key=lambda q: sum(
                1 for kw in keywords if kw in q["topic_tag"].lower() or kw in q["question_text"].lower()
            ),
            reverse=True,
        )
        selected = pool[: min(count, len(pool))]
    else:
        selected = random.sample(pool, min(count, len(pool)))

    while len(selected) < count:
        selected.append(pool[len(selected) % len(pool)])
    return selected


def evaluate_answer(
        role: str,
        level: str,
        topic_tag: str,
        question_text: str,
        user_answer: str,
        ideal_hint: str,
) -> Dict[str, Any]:
    """Evaluates a candidate's answer and returns structured score, strengths, gaps, ideal_hint, and follow_up."""
    cleaned = (user_answer or "").strip()
    default_follow_up = f"How would your {topic_tag} solution behave under 10x scale or an unexpected edge case?"

    if len(cleaned) < 10:
        return {
            "score": 1.0,
            "strengths": ["Attempted the question promptly."],
            "gaps": [
                "Answer is too brief to demonstrate technical depth.",
                f"Include core principles of {topic_tag} and a concrete trade-off or example.",
            ],
            "ideal_hint": ideal_hint,
            "follow_up": f"Can you walk through a concrete example of {topic_tag} step by step?",
        }

    prompt = f"""
    You are a strict yet constructive technical interviewer evaluating a candidate.
    - Role: {role} ({level})
    - Topic: {topic_tag}
    - Question: {question_text}
    - Reference Key Points: {ideal_hint}
    - Candidate Answer: {cleaned}

    Grade the candidate fairly from 0.0 to 10.0 based on technical accuracy, completeness, and clarity.
    Return ONLY valid JSON:
    {{
      "score": 7.5,
      "strengths": ["Specific positive point 1", "Specific positive point 2"],
      "gaps": ["Missing concept or edge case 1", "Improvement suggestion 2"],
      "ideal_hint": "Concise 2-3 sentence ideal answer",
      "follow_up": "One sharp follow-up question an interviewer would ask next based on this answer"
    }}
    """
    ai_eval = _call_gemini_json(prompt)
    if ai_eval and "score" in ai_eval:
        try:
            score = max(0.0, min(10.0, float(ai_eval.get("score", 5.0))))
        except (TypeError, ValueError):
            score = 5.0
        return {
            "score": round(score, 1),
            "strengths": _clean_str_list(ai_eval.get("strengths"), ["Clear structure in response."]),
            "gaps": _clean_str_list(ai_eval.get("gaps"), ["Add concrete complexity or edge-case analysis."]),
            "ideal_hint": str(ai_eval.get("ideal_hint") or ideal_hint).strip(),
            "follow_up": str(ai_eval.get("follow_up") or default_follow_up).strip(),
        }

    # Deterministic keyword & structure rubric fallback when offline / no API key
    hint_words = {w.lower().strip(".,():;`") for w in ideal_hint.split() if len(w) > 4}
    ans_words = {w.lower().strip(".,():;`") for w in cleaned.split()}
    overlap = len(hint_words.intersection(ans_words))
    coverage_ratio = overlap / max(1, len(hint_words))

    length_bonus = min(3.0, len(cleaned.split()) / 15.0)
    raw_score = 3.0 + (coverage_ratio * 5.0) + length_bonus
    final_score = round(max(2.0, min(9.5, raw_score)), 1)

    strengths = ["Addressed the core prompt directly."]
    if len(cleaned.split()) >= 20:
        strengths.append("Provided a structured, detailed explanation.")
    if overlap >= 2:
        strengths.append(f"Used accurate {topic_tag} terminology.")

    gaps = []
    if coverage_ratio < 0.35:
        gaps.append(f"Missed key technical concepts around {topic_tag}.")
    if len(cleaned.split()) < 25:
        gaps.append("Expand with a real-world example, edge case, or time/space complexity.")
    if not gaps:
        gaps.append("Consider mentioning production trade-offs or scalability limits.")

    return {
        "score": final_score,
        "strengths": strengths,
        "gaps": gaps,
        "ideal_hint": ideal_hint,
        "follow_up": default_follow_up,
    }


def evaluate_followup(
        role: str,
        level: str,
        topic_tag: str,
        follow_up_question: str,
        follow_up_answer: str,
) -> Dict[str, str]:
    """Evaluates a candidate's response to an interviewer follow-up probe."""
    cleaned = (follow_up_answer or "").strip()
    if len(cleaned.split()) < 6:
        return {
            "verdict": "Too Brief",
            "coach_note": f"Your follow-up reply needs more concrete reasoning around {topic_tag}.",
            "bonus_tip": "Mention a specific bottleneck, failure mode, or trade-off in 2–3 sentences.",
        }

    prompt = f"""
    You are a senior technical interviewer reviewing a candidate's follow-up response.
    - Role: {role} ({level})
    - Topic: {topic_tag}
    - Follow-Up Question: {follow_up_question}
    - Candidate Follow-Up Answer: {cleaned}

    Return ONLY valid JSON:
    {{
      "verdict": "Strong Follow-Up | Solid Attempt | Needs Depth",
      "coach_note": "1-2 sentence evaluation of how well they handled the follow-up probe",
      "bonus_tip": "1 concrete senior-level detail that would elevate this answer further"
    }}
    """
    ai_res = _call_gemini_json(prompt)
    if ai_res and "coach_note" in ai_res:
        return {
            "verdict": str(ai_res.get("verdict") or "Solid Attempt").strip(),
            "coach_note": str(ai_res.get("coach_note") or "").strip(),
            "bonus_tip": str(ai_res.get("bonus_tip") or f"Quantify latency, memory, or complexity impact in {topic_tag}.").strip(),
        }

    words = len(cleaned.split())
    if words >= 18:
        return {
            "verdict": "Strong Follow-Up",
            "coach_note": f"Clear, well-reasoned handling of the {topic_tag} follow-up scenario with practical depth.",
            "bonus_tip": "In live interviews, briefly mention monitoring or fallback metrics to sound production-ready.",
        }
    return {
        "verdict": "Solid Attempt",
        "coach_note": f"Good direction on {topic_tag}, though adding one concrete edge case or metric would make it sharper.",
        "bonus_tip": "Anchor follow-ups with: Bottleneck -> Mitigation -> Trade-off.",
    }