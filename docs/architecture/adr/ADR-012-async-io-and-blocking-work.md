# ADR-012: Async I/O and Blocking Work

**Status:** Accepted
**Date:** 2026-07-04
**Phase:** 4.0a+ (Architecture Lock)
**Deciders:** Sergey Paschenko (project owner), Hermes Agent

## Context

ADR-001 establishes FastAPI as the async-first service framework for the
Control API and all backend services.  ADR-006 mandates LDAPS
integration for internal staff authentication.  ADR-005 requires
observability with latency metrics, timeout counts, and correlation ID
propagation.

A single blocking call inside an async request handler — an LDAP bind,
a synchronous HTTP request, a file read — blocks the entire event loop
for all concurrent requests on that worker.  One slow LDAP server can
degrade every endpoint, not just the auth endpoint that called it.

This ADR defines what constitutes blocking work, where it is allowed,
and what patterns replace it.

## Decision

### 1. Async-first, blocking-forbidden

**FastAPI services are async-first.**  Blocking calls are forbidden
inside async request handlers, FastAPI dependencies, and background
task coroutines unless explicitly wrapped in an approved offloading
mechanism.

A blocking call is any operation that:

| Category | Examples |
|----------|----------|
| **Sync network I/O** | `requests.get()`, `httpx` sync client, `ldap3` sync bind/search, `smtplib`, sync DNS resolution |
| **Sync file I/O** | `open().read()` on large files, `shutil.copy()`, `os.listdir()` blocking, `zipfile` extraction |
| **Sync S3/MinIO** | `minio-py` sync client (`client.fput_object()`, `client.get_object()`) |
| **CPU-heavy work** | PDF generation (reportlab/weasyprint), Excel generation (openpyxl), image processing (Pillow), video transcoding, cryptographic batch operations |
| **Database** | Sync `psycopg2`/`sqlite3` in async handler (SQLAlchemy async is fine) |
| **Subprocess** | `subprocess.run()` without timeout, `os.system()` |

**Non-blocking operations that are fine:**
- `asyncpg`, SQLAlchemy async (`await session.execute(...)`)
- `httpx.AsyncClient`, `aiohttp`
- `aiofiles` for async file I/O
- `aiobotocore` / async MinIO SDK
- `bcrypt` / `hashlib` for password hashing / JWT signing (O(ms), not sustained)
- `json.dumps()` / `json.loads()` (CPU-bound but O(μs) per call)

### 2. Approved Offloading Patterns

#### Pattern A: Native async library (preferred)

Use the async-native equivalent.  Always the first choice.

```python
# ❌  sync — blocks event loop
import requests
resp = requests.get("https://external-api/status")

# ✅  async — cooperatively yields
import httpx
async with httpx.AsyncClient() as client:
    resp = await client.get("https://external-api/status")
```

#### Pattern B: `run_in_threadpool` (short blocking work)

For blocking calls that complete in **< 5 seconds** and have no
async-native alternative:

```python
from fastapi.concurrency import run_in_threadpool

def _ldap_bind_sync(username, password):
    # ldap3 sync bind — no async equivalent exists
    conn = ldap3.Connection(server, user=dn, password=password)
    conn.bind()
    return conn

# In FastAPI handler:
conn = await run_in_threadpool(_ldap_bind_sync, username, password)
```

**Constraints on `run_in_threadpool`:**
- Maximum duration: 5 seconds (enforced by caller timeout).
- Used only when no async-native library exists AND the work is
  short-lived.
- The threadpool is shared across the process — do not use for I/O that
  can saturate it (e.g., 50 concurrent LDAP binds each taking 10s =
  pool exhaustion).

#### Pattern C: Background worker (long-running jobs)

For work that exceeds 5 seconds, is CPU-heavy, or needs retry/queue
semantics:

```
Request Handler          outbox_events / job table        Worker Process
     │                         │                              │
     │ INSERT job (status=pending)                             │
     │ return 202 Accepted    │                              │
     │                         │  poll pending jobs           │
     │                         ├─────────────────────────────►│
     │                         │                              │ process job
     │                         │◄─────────────────────────────│
     │                         │  UPDATE status=done          │
```

**Examples:** manifest generation, report PDF rendering, media
transcoding, bulk data import.

The outbox relay from ADR-011 is one instance of this pattern.  A
separate `job_worker` or dedicated worker process handles CPU/IO-heavy
tasks that are not event-delivery.

#### Pattern D: Streaming (large payloads)

Upload/download endpoints that handle files > 1 MB MUST stream:

```python
# ❌  loads entire file into memory
content = await request.body()
await minio_client.put_object("bucket", "key", io.BytesIO(content), len(content))

# ✅  streams chunk-by-chunk
async with minio_async_client.put_object("bucket", "key", length=content_length) as writer:
    async for chunk in request.stream():
        await writer.write(chunk)
```

**Streaming rules:**
- Request body: use `request.stream()` not `await request.body()` or
  `await request.json()` for payloads > 1 MB.
- Response body: use `StreamingResponse` for file downloads, never
  `FileResponse` with the entire file in memory.
- S3/MinIO: use multipart upload with async client.
- Timeout: streaming endpoints get longer timeouts (configurable, default
  300s for uploads, 120s for downloads).

### 3. Timeouts Are Mandatory

Every external I/O call MUST have a timeout.  No timeout = indefinite
block.

```python
# ❌  no timeout — blocks forever
resp = await httpx.AsyncClient().get(url)

# ✅  explicit timeout
async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
    resp = await client.get(url)
```

| Operation | Default timeout | Rationale |
|-----------|----------------|-----------|
| LDAP bind | 5s | AD on same network/VPN; longer = degraded |
| LDAP search | 3s | Group membership lookup is fast |
| External HTTP API | 10s | Third-party SLA; circuit breaker at 30s |
| Internal service HTTP | 5s | Same network; longer = cascading failure |
| S3/MinIO upload (per part) | 60s | Large files, multipart |
| S3/MinIO download | 30s | Media/manifest retrieval |
| Redis | 2s | In-memory, same network |
| NATS publish | 5s | JetStream ack timeout |
| PostgreSQL query | 30s | OLTP queries; reports use read replica |

Timeouts are environment-configurable.  Production values may differ
from dev.  Every timeout is exposed as a metric label
(`timeout_target="ldap:bind"`).

### 4. Where Each Pattern Applies

| Operation | Pattern | Why |
|-----------|---------|-----|
| AD/LDAPS authentication | **B** (`run_in_threadpool`) | `ldap3` has no async equivalent; bind is <1s on healthy AD |
| External ad verification API | **A** (async httpx) | HTTP calls have async clients |
| Campaign report PDF | **C** (background worker) | CPU-heavy, >5s, user polls for result |
| Media file upload to MinIO | **D** (streaming) | Files up to hundreds of MB; multipart |
| Manifest media package download | **D** (streaming) | Large packages; device streams to disk |
| Bulk Excel export (audit log) | **C** (background worker) | Can be 100K+ rows; async job with download link |
| Password hashing (bcrypt) | **inline async** | O(100ms), cost factor 12, single user — not blocking |
| JWT sign/verify | **inline async** | O(μs), non-blocking |
| Cryptographic batch work | **C** (background worker) | Sustained CPU; e.g., re-signing 1000 manifests |

### 5. Observability

Every offloaded operation emits metrics:

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `rmp_blocking_ops_total` | Counter | `pattern` (A/B/C/D), `target` | Offloaded operations |
| `rmp_blocking_op_duration_ms` | Histogram | `pattern`, `target` | Duration of offloaded work |
| `rmp_threadpool_active` | Gauge | — | Active threadpool threads |
| `rmp_threadpool_available` | Gauge | — | Idle threadpool threads |
| `rmp_streaming_bytes_total` | Counter | `direction` (up/down) | Bytes streamed |
| `rmp_streaming_duration_ms` | Histogram | `direction` | Streaming session duration |
| `rmp_timeout_total` | Counter | `target` | Timeout count by I/O target |
| `rmp_worker_queue_age_seconds` | Gauge | `queue_name` | Oldest pending job age |

Alert thresholds:
- `rmp_threadpool_available == 0` for > 60s → critical (threadpool exhausted)
- `rate(rmp_timeout_total[5m]) > 5` → warning (external dependency degraded)
- `rmp_worker_queue_age_seconds > 600` → warning (worker backlog)

Correlation IDs propagate through `run_in_threadpool` (contextvars),
background workers (job metadata), and streaming chunk metadata.

### 6. Testing Requirements

Every external I/O integration MUST have a behavioral or integration
test proving the failure path before acceptance:

| Test | What it proves |
|------|---------------|
| **Timeout triggers correctly** | I/O target unreachable → call returns within timeout window, not hung |
| **Blocking call NOT on event loop** | `run_in_threadpool` or background worker used; no `asyncio` warning |
| **Threadpool exhaustion handled** | All threads busy → new request gets 503 with retry-after, not queued silently |
| **Streaming recovers from mid-stream failure** | MinIO unreachable mid-upload → partial upload cleaned up, error propagated |

**Source-inspection alone is not sufficient** for I/O safety.  A test
that actually blocks the target (mock server that sleeps past timeout)
is required.

### 7. Non-Goals / Deferred

- **Greenlet/gevent-based async:** not approved.  Stick to `asyncio`
  native.
- **Celery/RQ task queues:** background workers are Docker containers
  polling job tables or NATS.  No external task-queue infrastructure
  yet.
- **`loop.run_in_executor()` raw usage:** always use
  `run_in_threadpool` (which is a thin wrapper) — it preserves
  contextvars for correlation ID propagation.
- **GIL-bound CPU work in threadpool:** Python threads don't bypass
  the GIL.  True CPU-bound work (video transcoding, ML inference)
  belongs in a separate worker PROCESS (Pattern C), not threadpool.

## Consequences

- **Positive:** No single slow LDAP bind degrades all endpoints.  Large
  file uploads don't OOM the process.  Timeouts prevent cascading
  failures.  Observability surfaces blocking-work hotspots before they
  become incidents.

- **Negative:** Developers must think about I/O boundaries.  Some
  libraries (notably `ldap3`) have no async equivalent — threadpool is
  mandatory, which adds complexity.  Streaming endpoints require
  different FastAPI patterns than simple `response_model` returns.

- **Risk:** A developer unfamiliar with asyncio may call
  `requests.get()` inside a handler.  Mitigation: CI lint rule (e.g.,
  `blocking-http-call-in-async-function` or ruff rule `ASYNC10x`).  If
  the only available SDK for an integration is sync, the threadpool is
  a legitimate fallback — but must be documented and tested.

## References

- ADR-001 — FastAPI service framework, deployment model
- ADR-005 — Observability (metrics, correlation IDs)
- ADR-006 — User identity (LDAPS integration)
- ADR-008 — Testing strategy (behavioral test gates)
- ADR-011 — Transactional outbox (background worker pattern)
- FastAPI docs: [Concurrency and async](https://fastapi.tiangolo.com/async/)
- Python docs: [Developing with asyncio](https://docs.python.org/3/library/asyncio-dev.html)
