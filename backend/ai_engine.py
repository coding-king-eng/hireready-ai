import json
import os
import random
import re
from typing import Any, Dict, List
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()

SENIOR_LEVEL_KEYWORDS = ("senior", "staff", "principal", "manager", "lead", "architect")

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
    "Full-Stack Engineer (React & Node / Python)": [
        {
            "topic_tag": "End-to-End API Contracts",
            "question_text": "How do you prevent type drift and breaking changes between a React frontend and a REST/JSON backend across rapid releases?",
            "ideal_hint": "Generate TypeScript client types directly from OpenAPI/Pydantic schemas, version breaking endpoints, and enforce contract tests in CI."
        },
        {
            "topic_tag": "Rendering Strategies",
            "question_text": "Compare Client-Side Rendering (CSR), Server-Side Rendering (SSR), and Incremental Static Regeneration (ISR) for an e-commerce app.",
            "ideal_hint": "CSR renders in browser (good for authenticated dashboards); SSR renders per request on server (SEO + fresh data); ISR statically caches pages and revalidates in background."
        },
        {
            "topic_tag": "CORS & Auth Cookies",
            "question_text": "Why do browsers send CORS preflight OPTIONS requests, and what cookie flags are needed for cross-origin authentication?",
            "ideal_hint": "Preflights verify server permission for non-simple headers/methods; cross-origin auth cookies require `HttpOnly`, `Secure`, and `SameSite=None` with explicit `Access-Control-Allow-Credentials`."
        },
        {
            "topic_tag": "Optimistic UI Updates",
            "question_text": "How do you implement optimistic UI updates safely when a user likes a post or updates a cart item, including rollback on failure?",
            "ideal_hint": "Snapshot previous state, update local UI immediately, send async mutation, and restore snapshot with an error toast if the server rejects the request."
        },
        {
            "topic_tag": "N+1 Query Bottlenecks",
            "question_text": "What is the N+1 query problem in ORM-backed APIs and how do you diagnose and eliminate it?",
            "ideal_hint": "Fetching N parent records and firing 1 query per child causes N+1 roundtrips; fix with eager loading (`joinedload`/`selectinload`) or DataLoader batching."
        },
    ],
    "Frontend Engineer (React / JS / TypeScript)": [
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
            "topic_tag": "Core Web Vitals",
            "question_text": "How do you diagnose and improve Largest Contentful Paint (LCP) and Cumulative Layout Shift (CLS) on a media-heavy page?",
            "ideal_hint": "Improve LCP via CDN caching, preloading hero images, and code-splitting; prevent CLS by reserving explicit width/height aspect ratios and avoiding late-injected banners."
        },
    ],
    "DSA & Problem Solving (SDE-1 / SDE-2)": [
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
    "System Design & Distributed Architecture": [
        {
            "topic_tag": "Rate Limiting",
            "question_text": "Design a distributed API rate limiter using Redis. Compare Token Bucket and Sliding Window Log algorithms.",
            "ideal_hint": "Token bucket allows controlled bursts using refill rate and capacity via atomic Lua scripts in Redis; Sliding Window Log tracks exact timestamps per request for strict accuracy at higher memory cost."
        },
        {
            "topic_tag": "Consistent Hashing",
            "question_text": "Why does standard `hash(key) % N` fail when scaling cache nodes, and how does Consistent Hashing with virtual nodes solve it?",
            "ideal_hint": "Modulo hashing remaps almost all keys when N changes; Consistent Hashing maps nodes and keys onto a ring so adding/removing a node only moves K/N keys, while virtual nodes balance load."
        },
        {
            "topic_tag": "Database Sharding",
            "question_text": "Compare range-based sharding and hash-based sharding. How do you handle cross-shard joins and hotspot partitions?",
            "ideal_hint": "Range sharding supports range scans but risks write hotspots; hash sharding distributes writes evenly but breaks range queries. Avoid cross-shard joins via denormalization or application-level aggregation."
        },
        {
            "topic_tag": "Event-Driven Messaging",
            "question_text": "When would you choose Apache Kafka over a traditional task queue like RabbitMQ, and how do you guarantee idempotent consumers?",
            "ideal_hint": "Kafka excels at high-throughput durable event streaming and replay via consumer offsets; ensure idempotency using deduplication IDs stored in a transactional DB or Redis."
        },
        {
            "topic_tag": "CAP & Consistency",
            "question_text": "Explain the trade-off between strong consistency and eventual consistency in a global inventory or social feed service.",
            "ideal_hint": "Inventory requires strong consistency (quorum reads/writes or pessimistic locks) to prevent overselling, whereas social feeds favor availability and low latency with eventual consistency."
        },
    ],
    "AI / Machine Learning Engineer (LLMs & RAG)": [
        {
            "topic_tag": "RAG Architecture",
            "question_text": "Walk through an end-to-end Retrieval-Augmented Generation (RAG) pipeline and how you reduce hallucinations.",
            "ideal_hint": "Chunk documents, generate dense embeddings, index in a vector DB, retrieve top-k chunks with hybrid lexical+semantic search and reranking, and ground prompts with strict citation instructions."
        },
        {
            "topic_tag": "Embeddings & Vector Search",
            "question_text": "Compare exact k-NN search with HNSW approximate nearest neighbor indexing in terms of recall, latency, and memory.",
            "ideal_hint": "Exact k-NN guarantees 100% recall at O(N) cost; HNSW builds multi-layer proximity graphs for sub-millisecond O(log N) search with >95% recall at higher RAM usage."
        },
        {
            "topic_tag": "LLM Evaluation & Guardrails",
            "question_text": "How do you evaluate an LLM application in production beyond manual spot-checking?",
            "ideal_hint": "Track deterministic schema validity, retrieval precision/recall, LLM-as-a-judge faithfulness scores on golden datasets, latency p95, and token cost per request."
        },
        {
            "topic_tag": "Fine-Tuning vs Prompting",
            "question_text": "When should you use prompt engineering or RAG instead of LoRA/QLoRA fine-tuning?",
            "ideal_hint": "Use prompting/RAG when knowledge changes frequently or citations are needed; use LoRA fine-tuning to teach domain-specific tone, strict output formatting, or specialized reasoning patterns."
        },
        {
            "topic_tag": "Inference Optimization",
            "question_text": "Explain how KV-caching and quantization (INT8/FP8) speed up autoregressive transformer inference.",
            "ideal_hint": "KV-cache stores past attention key/value tensors so tokens aren't recomputed each step; quantization shrinks weight precision to cut VRAM bandwidth bottlenecks."
        },
    ],
    "DevOps & Cloud Platform Engineer (AWS / K8s)": [
        {
            "topic_tag": "Kubernetes Scheduling",
            "question_text": "Explain the difference between Kubernetes Liveness, Readiness, and Startup probes and what happens when each fails.",
            "ideal_hint": "Startup delays other probes during slow boot; Readiness removes pod IP from Service endpoints when unready; Liveness restarts the container if deadlocked."
        },
        {
            "topic_tag": "CI/CD & Zero-Downtime",
            "question_text": "Compare Blue-Green Deployment and Canary Release strategies, including automated rollback triggers.",
            "ideal_hint": "Blue-Green switches 100% traffic between two identical environments for instant rollback; Canary shifts small traffic percentages gradually while monitoring error rates and p99 latency."
        },
        {
            "topic_tag": "Docker Optimization",
            "question_text": "How do multi-stage Docker builds reduce image size and attack surface in production?",
            "ideal_hint": "Multi-stage builds compile dependencies in a builder image and copy only runtime artifacts into a minimal distroless/slim image without compilers or build secrets."
        },
        {
            "topic_tag": "Infrastructure as Code",
            "question_text": "How does Terraform manage remote state locking, and why is state drift dangerous in team environments?",
            "ideal_hint": "Remote backends (S3 + DynamoDB) lock state during `apply` to prevent concurrent corruption; manual console edits cause drift that can trigger unintended resource recreation."
        },
        {
            "topic_tag": "Observability",
            "question_text": "Contrast Metrics, Logs, and Distributed Traces when debugging a latency spike across 10 microservices.",
            "ideal_hint": "Metrics alert on aggregate p99 latency spikes, Distributed Traces pinpoint which downstream service span caused the delay, and correlated Logs reveal the exact error stack."
        },
    ],
    "Android Developer (Kotlin / Jetpack Compose)": [
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
    "iOS Developer (Swift / SwiftUI)": [
        {
            "topic_tag": "ARC & Memory Management",
            "question_text": "Explain Automatic Reference Counting (ARC) in Swift and when to use `weak` versus `unowned` inside escaping closures.",
            "ideal_hint": "ARC frees class instances when strong reference count hits zero. Use `[weak self]` when `self` may become nil before closure runs; use `[unowned self]` only when `self` is guaranteed to outlive the closure."
        },
        {
            "topic_tag": "Swift Concurrency",
            "question_text": "How do Swift `actor` types prevent data races, and what is actor reentrancy?",
            "ideal_hint": "Actors serialize access to mutable state via isolated queues; actor reentrancy means state can change across `await` suspension points, requiring re-validation after awaiting."
        },
        {
            "topic_tag": "SwiftUI State Management",
            "question_text": "Compare `@State`, `@Binding`, `@StateObject`, and `@ObservedObject` in SwiftUI.",
            "ideal_hint": "`@State` owns local value state; `@Binding` shares two-way access; `@StateObject` instantiates and owns a reference ObservableObject across redraws, while `@ObservedObject` observes an externally owned instance."
        },
        {
            "topic_tag": "Value vs Reference Types",
            "question_text": "Why does Swift prefer `struct` over `class` by default, and how does Copy-on-Write optimize `Array` performance?",
            "ideal_hint": "Structs provide value semantics, stack allocation, and thread safety without shared mutable state; Copy-on-Write defers copying underlying buffer until a mutation occurs on a shared reference."
        },
        {
            "topic_tag": "Networking & Persistence",
            "question_text": "How do you structure clean error handling and retry logic using `URLSession` with `async/await` and `Codable`?",
            "ideal_hint": "Define typed `Error` enums, validate HTTP status codes before `JSONDecoder`, and implement exponential backoff with `Task.sleep` and cancellation checks."
        },
    ],
    "Data Engineer (Spark / Pipelines / Warehousing)": [
        {
            "topic_tag": "Apache Spark Internals",
            "question_text": "Explain the difference between narrow and wide transformations in Apache Spark, and how data skew impacts shuffle stages.",
            "ideal_hint": "Narrow transformations (`map`, `filter`) stay within partitions; wide transformations (`groupByKey`, `join`) trigger expensive network shuffles where skewed keys cause straggler tasks."
        },
        {
            "topic_tag": "Data Modeling",
            "question_text": "Compare Star Schema and Snowflake Schema in cloud data warehouses, and explain Slowly Changing Dimensions (SCD Type 2).",
            "ideal_hint": "Star schema denormalizes dimension tables for faster BI joins; Snowflake normalizes them to save space. SCD Type 2 preserves historical changes using `effective_from`, `effective_to`, and `is_current` columns."
        },
        {
            "topic_tag": "Lakehouse Formats",
            "question_text": "How do Delta Lake or Apache Iceberg bring ACID transactions and time travel on top of Parquet object storage?",
            "ideal_hint": "They maintain an atomic metadata transaction log tracking active Parquet file versions, enabling snapshot isolation, schema evolution, and time-travel queries."
        },
        {
            "topic_tag": "Pipeline Reliability",
            "question_text": "How do you design an idempotent daily ETL/ELT pipeline in Airflow so backfills never create duplicate records?",
            "ideal_hint": "Partition target tables by execution date and use atomic `DELETE + INSERT` or `MERGE` upserts keyed on deterministic natural keys."
        },
        {
            "topic_tag": "Streaming Ingestion",
            "question_text": "Compare watermarking and windowing when aggregating late-arriving events in a streaming pipeline.",
            "ideal_hint": "Windows group events by event-time intervals, while watermarks define how long the engine waits for late events before finalizing window state."
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
    "Cybersecurity & AppSec Engineer": [
        {
            "topic_tag": "OWASP Top 10",
            "question_text": "Explain how Broken Object Level Authorization (BOLA/IDOR) occurs in REST APIs and how to enforce object-level checks cleanly.",
            "ideal_hint": "BOLA happens when an API trusts a user-supplied resource ID without checking ownership; enforce policy checks in middleware/service layer verifying `resource.owner_id == current_user.id`."
        },
        {
            "topic_tag": "XSS & CSP Defense",
            "question_text": "Compare Stored XSS and Reflected XSS, and explain how a strict Content Security Policy (CSP) mitigates script execution.",
            "ideal_hint": "Stored XSS persists malicious scripts in DB; Reflected XSS echoes payload from URL/input. Strict CSP blocks inline scripts (`unsafe-inline`) and restricts script origins to trusted nonces/hashes."
        },
        {
            "topic_tag": "Cryptography & Secrets",
            "question_text": "Why should passwords be hashed with Argon2id or bcrypt instead of SHA-256, and how does per-user salting defend against rainbow tables?",
            "ideal_hint": "SHA-256 is too fast and GPU-crackable; Argon2id/bcrypt are memory-hard and intentionally slow, while unique random salts ensure identical passwords produce completely different hashes."
        },
        {
            "topic_tag": "SSRF Prevention",
            "question_text": "What is Server-Side Request Forgery (SSRF) in cloud environments, and how do you harden URL-fetching endpoints?",
            "ideal_hint": "SSRF tricks a server into calling internal services or cloud metadata IPs (`169.254.169.254`); block private IP ranges after DNS resolution, enforce domain allowlists, and require IMDSv2."
        },
        {
            "topic_tag": "Zero-Trust & mTLS",
            "question_text": "How does mutual TLS (mTLS) authenticate service-to-service traffic inside a microservice mesh?",
            "ideal_hint": "In mTLS, both client and server present X.509 certificates signed by a trusted internal CA during handshake, ensuring bidirectional cryptographic identity and encrypted transit."
        },
    ],
}

SENIOR_STAFF_QUESTIONS: List[Dict[str, str]] = [
    {
        "topic_tag": "Multi-Region Architecture",
        "question_text": "You are scaling a write-heavy global service across US, EU, and APAC regions with a 150ms p99 SLA. How do you design data partitioning, conflict resolution, and failover?",
        "ideal_hint": "Geo-partition user data to home regions to keep writes local, use asynchronous cross-region replication with CRDTs or last-write-wins vector clocks for shared state, and automate DNS/anycast health-checked failover."
    },
    {
        "topic_tag": "Incident Postmortem & Reliability",
        "question_text": "A cascading retry storm takes down your primary database during a 10x traffic surge. Walk through immediate mitigation, circuit-breaker tuning, and blameless postmortem actions.",
        "ideal_hint": "Shed non-critical load immediately, add exponential backoff with full jitter, configure circuit breakers with fallback responses, and institute load-testing and error-budget guardrails in the postmortem."
    },
    {
        "topic_tag": "Technical Leadership & Trade-offs",
        "question_text": "Your team wants to rewrite a legacy monolith into microservices, while product leadership demands shipping key features in 8 weeks. How do you make and align the architectural call?",
        "ideal_hint": "Quantify migration risk vs delivery velocity, propose the Strangler Fig pattern to extract only the highest-bottleneck domain behind clean interfaces while delivering product milestones incrementally."
    },
    {
        "topic_tag": "Zero-Downtime Schema Migration",
        "question_text": "How do you rename and split a heavily queried 500M-row production table column with zero downtime and instant rollback safety?",
        "ideal_hint": "Use the Expand-and-Contract pattern: add new columns, dual-write to both old and new schemas, backfill historical rows in throttled batches, switch reads after verification, then drop old columns later."
    },
    {
        "topic_tag": "FinOps & Latency Optimization",
        "question_text": "Your cloud infrastructure bill doubled while p95 latency crept up 40%. Walk through your systematic profiling and cost-performance optimization playbook.",
        "ideal_hint": "Correlate distributed traces with top-cost services, eliminate hot N+1 DB queries and oversized memory allocations, tune autoscaling/spot capacity, and cache high-read endpoints."
    },
    {
        "topic_tag": "Organizational Scaling & RFCs",
        "question_text": "As a Staff/Principal engineer across 4 squads, how do you establish architectural standards without becoming a review bottleneck?",
        "ideal_hint": "Introduce lightweight RFC templates for high-impact decisions, provide paved-road golden templates with built-in observability/security, and mentor squad tech leads through architecture office hours."
    },
]


def get_engine_status() -> Dict[str, str]:
    """Reports whether live Gemini AI or deterministic fallback mode is active."""
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if key and not key.startswith("your_"):
        return {"mode": "gemini", "model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()}
    return {"mode": "fallback", "model": "deterministic-rubric-v2"}


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
            config={"response_mime_type": "application/json", "temperature": 0.45},
        )
        return _extract_json(response.text or "")
    except Exception:
        return None


def _call_gemini_text(prompt: str) -> str | None:
    """Calls Google Gemini API for plain-text assistant guidance."""
    status = get_engine_status()
    if status["mode"] != "gemini":
        return None
    try:
        from google import genai
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", "").strip())
        response = client.models.generate_content(
            model=status["model"],
            contents=prompt,
            config={"temperature": 0.5},
        )
        text = (response.text or "").strip()
        return text if text else None
    except Exception:
        return None


def ask_ai_assistant(question: str, context: str | None = None) -> Dict[str, str]:
    """Provides instant AI coaching, technical explanations, and app troubleshooting help."""
    cleaned_q = (question or "").strip()
    clean_ctx = (context or "").strip()
    ctx_block = f"\nCurrent User Screen Context: {clean_ctx}" if clean_ctx else ""

    prompt = f"""
    You are the built-in AI Interview Coach & Support Assistant inside HireReady (a mock technical interview web app).
    Help the user clearly, concisely, and practically with:
    1. Technical interview concepts, system design trade-offs, coding patterns, or behavioral (STAR) answer framing.
    2. Using HireReady features: Live AI Video Call Mode vs Standard Text Mode, Voice-to-Text microphone input, Resume/JD Skill Extractor, Weak-Topic Drills, or Markdown/JSON report exports.
    {ctx_block}

    User Question: {cleaned_q}

    Keep your answer focused, structured with short bullet points where helpful, and under 180 words.
    """
    ai_reply = _call_gemini_text(prompt)
    if ai_reply:
        return {"reply": ai_reply, "mode": "gemini"}

    lower = cleaned_q.lower()
    if any(w in lower for w in ("voice", "mic", "microphone", "speak", "audio", "sound")):
        reply = (
            "• **Interviewer Voice:** In **Live Video Call Mode**, clicking any interviewer card automatically speaks their greeting. Use **Voice On / Muted** or **System Voice Accent Override** in the call panel if your browser defaults to a muted output.\n"
            "• **Your Microphone:** Click **🎙️ Speak Answer** (works best in Chrome, Safari, or Edge with mic permission allowed) to dictate answers live into the text box."
        )
    elif any(w in lower for w in ("video", "normal", "mode", "camera")):
        reply = (
            "• **🎥 Live AI Video Call Mode:** Features a real-time animated male or female interviewer with automatic voice narration, lip-sync, and optional self-camera PiP.\n"
            "• **📝 Standard Normal Mode:** Runs a quiet, text-focused mock interview without video or voice—ideal for libraries, hostels, or fast written practice."
        )
    elif any(w in lower for w in ("score", "rubric", "grade", "readiness", "export")):
        reply = (
            "• **0–10 Scoring Rubric:** Answers are graded on technical accuracy, depth, edge cases, and trade-offs. Topics scoring **7.0+** become Strong Topics; anything below **7.0** goes into your Weak-Topic Drill.\n"
            "• **Exports:** On the Readiness Report screen, download your full transcript as **Markdown (.md)**, **JSON**, or **PDF**."
        )
    elif any(w in lower for w in ("star", "behavioral", "leadership", "manager")):
        reply = (
            "Use the **STAR + Metrics** structure for senior & behavioral rounds:\n"
            "• **Situation & Task:** 1–2 sentences setting scale, SLA, or business constraint.\n"
            "• **Action:** Specific architectural trade-offs you drove and how you aligned stakeholders.\n"
            "• **Result:** Quantified impact (e.g., latency reduced by 45%, zero downtime, or incident MTTR cut)."
        )
    else:
        reply = (
            "To give a high-scoring technical answer in HireReady:\n"
            "1. **Clarify & State Core Principle:** Define the concept or architecture directly in your first 2 sentences.\n"
            "2. **Quantify Trade-offs:** Mention time/space complexity, latency, consistency, or write vs. read overhead.\n"
            "3. **Cover Edge Cases:** Explain failure handling, scaling bottlenecks, or security guardrails."
        )
    return {"reply": reply, "mode": "fallback"}


def _is_senior_level(level: str) -> bool:
    lower_lvl = (level or "").lower()
    return any(k in lower_lvl for k in SENIOR_LEVEL_KEYWORDS)


def extract_skills_from_text(raw_text: str) -> Dict[str, Any]:
    """Extracts technical skills and suggests the closest interview role from a resume or JD."""
    cleaned = (raw_text or "").strip()
    available_roles = "\n    - ".join(FALLBACK_QUESTIONS.keys())
    prompt = f"""
    Analyze this candidate resume snippet or job description:
    \"\"\"{cleaned}\"\"\"

    Extract up to 8 key technical skills/concepts and choose the single best matching role from:
    - {available_roles}

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

    known_skills = [
        "Python", "FastAPI", "Django", "SQL", "PostgreSQL", "Redis", "Docker", "Kubernetes",
        "REST API", "GraphQL", "JWT", "Microservices", "System Design", "Kafka",
        "JavaScript", "TypeScript", "React", "Next.js", "Node.js", "Tailwind CSS",
        "Kotlin", "Android", "Jetpack Compose", "Coroutines", "Room", "Retrofit",
        "Swift", "SwiftUI", "iOS", "Spark", "Airflow", "Delta Lake", "Data Warehouse",
        "Pandas", "A/B Testing", "RAG", "LLM", "Embeddings", "PyTorch",
        "OWASP", "XSS", "mTLS", "Terraform", "AWS", "CI/CD",
        "Data Structures", "Algorithms", "Dynamic Programming", "Graphs",
    ]
    lower_text = cleaned.lower()
    matched = [skill for skill in known_skills if skill.lower() in lower_text][:8]
    if not matched:
        matched = ["System Design", "Data Structures", "REST API"]

    m = {x.lower() for x in matched}
    if m & {"kotlin", "android", "jetpack compose", "coroutines", "room", "retrofit"}:
        suggested = "Android Developer (Kotlin / Jetpack Compose)"
    elif m & {"swift", "swiftui", "ios"}:
        suggested = "iOS Developer (Swift / SwiftUI)"
    elif m & {"rag", "llm", "embeddings", "pytorch"}:
        suggested = "AI / Machine Learning Engineer (LLMs & RAG)"
    elif m & {"kubernetes", "docker", "terraform", "aws", "ci/cd"}:
        suggested = "DevOps & Cloud Platform Engineer (AWS / K8s)"
    elif m & {"spark", "airflow", "delta lake", "data warehouse"}:
        suggested = "Data Engineer (Spark / Pipelines / Warehousing)"
    elif m & {"owasp", "xss", "mtls"}:
        suggested = "Cybersecurity & AppSec Engineer"
    elif m & {"react", "next.js"} and m & {"python", "fastapi", "node.js", "postgresql"}:
        suggested = "Full-Stack Engineer (React & Node / Python)"
    elif m & {"react", "javascript", "typescript", "tailwind css"}:
        suggested = "Frontend Engineer (React / JS / TypeScript)"
    elif m & {"pandas", "a/b testing"}:
        suggested = "Data Analyst (SQL & Python)"
    elif m & {"microservices", "kafka", "system design"}:
        suggested = "System Design & Distributed Architecture"
    elif m & {"dynamic programming", "graphs", "data structures", "algorithms"}:
        suggested = "DSA & Problem Solving (SDE-1 / SDE-2)"
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
    is_senior = _is_senior_level(level)

    focus_instruction = (
        f"- Specific Focus Areas / Job Description Keywords: {clean_focus} (prioritize these concepts)"
        if clean_focus
        else "- Cover a balanced mix of core and advanced topics for this role"
    )

    seniority_guidance = (
        "Ask staff/principal-level questions covering distributed trade-offs, failure modes, scalability bottlenecks, zero-downtime migrations, observability, and technical leadership."
        if is_senior
        else f"Calibrate depth appropriately for {level} candidates (practical engineering fundamentals, clean design, and edge cases)."
    )

    prompt = f"""
    You are conducting a real technical interview.
    Generate {count} distinct, realistic interview questions tailored to:
    - Role: {role}
    - Experience Level: {level}
    {focus_instruction}

    Rules:
    - Cover different angles with zero duplicate questions.
    - {seniority_guidance}
    - Phrase questions naturally as a real human interviewer would speak them in a live call.
    - Return ONLY valid JSON matching this exact schema:
    {{
      "questions": [
        {{
          "topic_tag": "Short topic label (2-4 words)",
          "question_text": "Clear, conversational interview question",
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

    role_pool = list(FALLBACK_QUESTIONS.get(role, FALLBACK_QUESTIONS["Backend Developer (Python / FastAPI)"]))
    if is_senior:
        pool = list(SENIOR_STAFF_QUESTIONS) + role_pool
    else:
        pool = role_pool

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
    is_senior = _is_senior_level(level)
    default_follow_up = (
        f"At 10x production scale, what failure mode or operational trade-off would emerge first in your {topic_tag} design?"
        if is_senior
        else f"How would your {topic_tag} solution behave under higher load or an unexpected edge case?"
    )

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

    bar_note = (
        "Apply a strict Senior/Staff engineering bar: expect trade-off analysis, failure modes, and scale awareness."
        if is_senior
        else f"Grade fairly for a {level} candidate on technical accuracy, completeness, and clarity."
    )

    prompt = f"""
    You are a seasoned technical interviewer evaluating a candidate in a live interview.
    - Role: {role} ({level})
    - Topic: {topic_tag}
    - Question: {question_text}
    - Reference Key Points: {ideal_hint}
    - Candidate Answer: {cleaned}

    {bar_note}
    Return ONLY valid JSON:
    {{
      "score": 7.5,
      "strengths": ["Specific positive point 1", "Specific positive point 2"],
      "gaps": ["Missing concept or edge case 1", "Improvement suggestion 2"],
      "ideal_hint": "Concise 2-3 sentence ideal answer",
      "follow_up": "One sharp follow-up question the interviewer would ask next out loud"
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

    hint_words = {w.lower().strip(".,():;`") for w in ideal_hint.split() if len(w) > 4}
    ans_words = {w.lower().strip(".,():;`") for w in cleaned.split()}
    overlap = len(hint_words.intersection(ans_words))
    coverage_ratio = overlap / max(1, len(hint_words))

    length_bonus = min(3.0, len(cleaned.split()) / (20.0 if is_senior else 15.0))
    base = 2.5 if is_senior else 3.0
    raw_score = base + (coverage_ratio * 5.0) + length_bonus
    final_score = round(max(2.0, min(9.5, raw_score)), 1)

    strengths = ["Addressed the core question directly."]
    if len(cleaned.split()) >= 20:
        strengths.append("Provided a structured, detailed explanation.")
    if overlap >= 2:
        strengths.append(f"Used accurate {topic_tag} terminology.")

    gaps = []
    if coverage_ratio < 0.35:
        gaps.append(f"Missed key technical concepts around {topic_tag}.")
    if len(cleaned.split()) < 25:
        gaps.append("Expand with a real-world example, failure mode, or time/space complexity.")
    if not gaps:
        gaps.append("Consider quantifying production trade-offs, SLAs, or fallback behavior.")

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