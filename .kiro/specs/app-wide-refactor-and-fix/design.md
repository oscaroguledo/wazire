# Wazire App-Wide Refactor and Fix — Bugfix Design

## Overview

Wazire is a production-grade multi-tenant online exam platform for Nigerian tertiary institutions. This design document formalises the fix approach for all 156 defects catalogued in `bugfix.md`. The defects span ten domains: backend startup crashes, Docker/infrastructure misconfiguration, frontend type and logic errors, exam data-flow architecture gaps, production resilience gaps, OLAP/OLTP separation violations, onboarding and billing gaps, analytics and AI grading engine bugs, advanced grading engine improvements, and missing test/CI infrastructure.

The fix strategy is **targeted and additive**: every change is the minimum required to satisfy the stated requirement without altering unaffected behaviour. New columns are nullable or have safe defaults. New files are placed in existing module directories. No existing API contract is broken.

---

## Glossary

- **Bug_Condition (C)**: The set of inputs or states that trigger a defect — e.g. calling `Invoice.to_dict()` when `status` column is absent.
- **Property (P)**: The desired correct behaviour for inputs in C — e.g. `Invoice.to_dict()` returns a dict that includes `status`.
- **Preservation**: All existing behaviours for inputs outside C that must remain unchanged after the fix.
- **F**: The original (unfixed) function or system state.
- **F'**: The fixed function or system state.
- **Tenant**: A single Nigerian tertiary institution (school) registered on the platform.
- **tenant_code**: A 6-character uppercase alphanumeric join code auto-generated per tenant, used by lecturers and students to self-register.
- **KafkaManager**: A facade class wrapping `KafkaProducerService`, providing a clean `emit(event, data, partition_key)` API for routes and tasks.
- **Worker**: The class-based background process (`class Worker`) that manages `KafkaConsumerService` lifecycle.
- **Dispatcher**: The pattern by which each `tasks/` module exports a `HANDLERS` dict; `KafkaConsumerService` merges all dicts at startup.
- **GroqKeyRotator**: A Redis-backed singleton that manages a pool of up to four Groq API keys with round-robin selection, per-key cooldown, and cross-process coordination.
- **PRELOAD_QUESTIONS**: Kafka event emitted by the scheduler ~15 min before exam start; worker writes questions to Redis.
- **UPSERT_STUDENT_ANSWER**: Kafka event emitted by the answer PATCH endpoint; worker performs DB UPSERT.
- **FORCE_SUBMIT_EXAM**: Kafka event emitted by the scheduler when an exam expires; worker auto-submits unsubmitted students.
- **INITIATE_BILLING**: Kafka event emitted by the end-of-semester billing scheduler job; worker calls Paystack/Monnify.
- **OLTP**: Online Transaction Processing — the PostgreSQL tables used for live reads/writes by the API.
- **OLAP**: Online Analytical Processing — the `analytics.*` dashboard tables, written only by the Kafka worker.
- **grading_in_progress**: New `SubmissionStatus` enum value set when grading begins.
- **isBugCondition(input)**: Pseudocode function that returns `true` when an input triggers a known defect.
- **expectedBehavior(result)**: Pseudocode function that returns `true` when the result satisfies the correct specification.

---

## Bug Details

### Bug Condition

The system contains 156 discrete defects across ten domains. They share a common structure: a code path is invoked with a valid input, but the implementation is missing a required element (column, yield, import, handler, constraint, etc.), causing a crash, silent data loss, or incorrect behaviour.

**Formal Specification:**

```
FUNCTION isBugCondition(input)
  INPUT: input of type SystemCall (API request, Kafka event, scheduler tick, Docker build, etc.)
  OUTPUT: boolean

  RETURN (
    -- Domain 1: Backend crashes
    (input.target IN ['lifespan', 'register', 'models.__init__', 'scheduler',
                      'SubmissionService', 'Invoice.to_dict', 'BillingPlan.to_dict',
                      'Tenant.start_date', 'Exam.end_time', 'Submission.submitted_at',
                      'StudentAnswer.upsert'])
    AND defectPresent(input.target)
  ) OR (
    -- Domain 2: Docker/infrastructure
    (input.target IN ['docker-compose.yml', 'frontend/Dockerfile', 'backend/Dockerfile'])
    AND structuralDefectPresent(input.target)
  ) OR (
    -- Domain 3: Frontend
    (input.target IN ['UserManagement.tsx', 'AuthContext.register', 'answer.ts',
                      'auth.ts', 'tenant.ts', 'enrollment.ts', 'dashboard.ts'])
    AND (missingImport(input.target) OR wrongURL(input.target) OR wrongMethod(input.target)
         OR typeMismatch(input.target))
  ) OR (
    -- Domain 4: Exam data flow
    (input.target IN ['scheduler.PRELOAD_QUESTIONS', 'worker.PRELOAD_QUESTIONS',
                      'question.GET', 'answer.PUT', 'worker.UPSERT_STUDENT_ANSWER'])
    AND architectureDeviationPresent(input.target)
  ) OR (
    -- Domains 5-10: resilience, OLAP, onboarding, analytics, grading, CI
    deviationFromSpec(input.target)
  )
END FUNCTION
```

### Examples of Bug Manifestation

- **1.1** `uvicorn main:app` starts, runs startup code, immediately runs shutdown code, never serves a request — because `lifespan` has no `yield`.
- **1.9** `GET /api/v1/billing/invoices` returns HTTP 500 with `AttributeError: 'Invoice' object has no attribute 'status'`.
- **1.12** `docker compose up` silently ignores `pgbouncer` and `scheduler` services; `backend` fails to start because its `depends_on: pgbouncer` target does not exist.
- **1.22** Student answers are written directly to PostgreSQL on every keystroke, bypassing Kafka; a DB spike during an exam causes answer loss.
- **1.30** Two concurrent PATCH requests for the same `(student_id, exam_id, question_id)` produce two rows in `student_answers` because there is no UNIQUE constraint.
- **1.52** `GET /api/v1/analytics/dashboard/` performs `db.add()` + `db.commit()` inside a GET handler, violating OLAP/OLTP separation.
- **1.142** A 20-question theory exam triggers 20 sequential Groq API calls instead of one batched call.
- **1.152** Twenty worker replicas each independently select the same Groq API key because key usage counters are in-process only.

---

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviours (must not regress):**
- All existing API endpoint paths that are already correct continue to be served at the same URLs.
- All existing Kafka event handlers (`GRADE_SUBMISSION_ATTEMPT`, `REFRESH_DASHBOARD`, `DETECT_ANSWER`, `PARSE_AND_CREATE`, `SEND_EMAIL`, `UPDATE_EXAM_STATUS`, `SEND_QUEUED_EMAILS`) continue to function identically.
- All existing model columns and their `to_dict()` output shapes are preserved; new columns are additive.
- The `postgres`, `redis` Docker services retain their current image versions, volumes, health checks, and resource limits.
- The `KafkaProducerService` and `KafkaConsumerService` classes retain their manual-commit, dead-letter-logging, and reconnect-on-error behaviour.
- MCQ and FITB grading continue to use direct comparison with no Groq API call.
- The `GroqEngineBase._init_client()` method remains the single place where the Groq client is initialised.
- All existing frontend page components continue to function after type corrections.

**Scope of Non-Buggy Inputs:**
All inputs that do NOT match `isBugCondition` — i.e. all currently working API calls, Kafka events, scheduler jobs, and Docker operations — must produce exactly the same result after the fix as before.

---

## Hypothesized Root Cause

The defects cluster into six root-cause categories:

1. **Missing implementation stubs**: Columns indexed but never declared (`Invoice.status`, `BillingPlan.is_active`, `Tenant.start_date/end_date`); `yield` omitted from lifespan; `apscheduler` missing from requirements.
2. **Architectural shortcuts taken during initial development**: Direct DB writes where Kafka buffering was intended (answer upsert); OLAP writes inside GET handlers; scheduler jobs not yet wired to new event types.
3. **YAML indentation errors**: `pgbouncer` and `scheduler` services nested one level too deep under sibling services in `docker-compose.yml`.
4. **Frontend/backend contract drift**: Frontend types, URLs, and HTTP methods written against an earlier API design that was later changed on the backend.
5. **Missing cross-process coordination**: Groq key usage counters are per-process; no Redis-backed global balancer; no per-tenant semaphore for grading concurrency.
6. **Missing infrastructure**: No nginx, no gunicorn, no health endpoint, no CI pipeline, no test files, no Postman collection.

---

## Correctness Properties

Property 1: Bug Condition — All 156 Defects Produce Correct Behaviour

_For any_ system call where `isBugCondition(input)` returns `true`, the fixed system SHALL produce the behaviour specified in the corresponding `2.x` requirement in `bugfix.md` — no crash, no data loss, no silent discard, no wrong HTTP method, no missing column, no YAML parse error, no missing import.

**Validates: Requirements 2.1–2.156 (all Expected Behavior clauses)**

Property 2: Preservation — Non-Buggy Inputs Unchanged

_For any_ system call where `isBugCondition(input)` returns `false` (i.e. all currently working paths), the fixed system SHALL produce exactly the same result as the original system, preserving all existing API contracts, Kafka event handling, model shapes, Docker service behaviour, and frontend functionality.

**Validates: Requirements 3.1–3.93 (all Unchanged Behavior clauses)**

---

## Fix Implementation

### System Architecture Overview

```
                        ┌─────────────────────────────────────────────────────┐
                        │                   nginx (port 80/443)               │
                        │  /api/v1/ → upstream backend  /  → static /app/dist │
                        └──────────────┬──────────────────────────────────────┘
                                       │ internal Docker network (wazire-network)
              ┌────────────────────────┼────────────────────────┐
              ▼                        ▼                        ▼
   ┌──────────────────┐   ┌──────────────────────┐   ┌──────────────────┐
   │  backend (x2)    │   │  worker (x2)          │   │  scheduler (x1)  │
   │  gunicorn+uvicorn│   │  class Worker         │   │  APScheduler     │
   │  FastAPI app     │   │  KafkaConsumerService │   │  KafkaProducer   │
   └────────┬─────────┘   └──────────┬────────────┘   └────────┬─────────┘
            │                        │                          │
            ▼                        ▼                          ▼
   ┌──────────────────┐   ┌──────────────────────┐   ┌──────────────────┐
   │  PostgreSQL       │   │  Kafka (KRaft)        │   │  Redis           │
   │  (via PgBouncer)  │   │  tenant-tasks topic   │   │  exam cache      │
   │  schemas:         │   │  answers topic        │   │  key balancer    │
   │  account/academic │   │  dead-letter topic    │   │  rate limits     │
   │  billings/analytics│  └──────────────────────┘   └──────────────────┘
   └──────────────────┘
```

### Data Flow Diagrams

#### Exam Lifecycle

```
Lecturer creates exam (POST /academic/exams)
  → direct PostgreSQL write (no Kafka)

Scheduler tick (every 1-5 min)
  → query exams WHERE start_time BETWEEN now() AND now()+15min
  → emit PRELOAD_QUESTIONS {exam_id, duration_seconds}

Worker: PRELOAD_QUESTIONS handler
  → fetch questions from PostgreSQL
  → SET exam:{exam_id}:questions = JSON(questions)  TTL = duration + 1800s
  → Redis key: exam:{exam_id}:preloaded = "1"

Student fetches questions (GET /academic/questions/?exam_id=X)
  → try Redis GET exam:{exam_id}:questions
  → on miss: fallback to PostgreSQL SELECT

Student answers (PATCH /academic/answers/{question_id})
  → API emits UPSERT_STUDENT_ANSWER {student_id, exam_id, question_id, answer}
  → returns HTTP 200 immediately (optimistic)

Worker: UPSERT_STUDENT_ANSWER handler
  → INSERT INTO student_answers ... ON CONFLICT (student_id,exam_id,question_id)
    DO UPDATE SET answer=EXCLUDED.answer, updated_at=now()

Scheduler tick (every 1-5 min)
  → query exams WHERE start_time+duration <= now() AND status='in_progress'
  → emit FORCE_SUBMIT_EXAM {exam_id}

Worker: FORCE_SUBMIT_EXAM handler
  → find enrolled students with no Submission record
  → INSERT Submission(status='submitted', submitted_at=exam.end_time)
  → emit GRADE_SUBMISSION_ATTEMPT per new submission

Worker: GRADE_SUBMISSION_ATTEMPT handler
  → set Submission.status = 'grading_in_progress'
  → set SubmissionAttempt.grading_started_at = now()
  → batch all theory questions → single Groq API call
  → bulk INSERT StudentAnswer results
  → set Submission.status = 'graded', graded_at = now()
  → emit REFRESH_DASHBOARD

Worker: REFRESH_DASHBOARD handler
  → compute metrics from OLTP tables
  → UPSERT analytics.admin_dashboard, lecturer_dashboard, student_dashboard
```

#### Answer Autosave Flow

```
Frontend (TakeExam page)
  PATCH /api/v1/academic/answers/{question_id}
  body: {exam_id, answer}
        │
        ▼
  answer route handler
  → KafkaManager.emit("UPSERT_STUDENT_ANSWER", {student_id, exam_id, question_id, answer},
                       partition_key=tenant_id)
  → return Response(success=True, message="Answer saved", data=optimistic_payload)
        │
        ▼ (async, Kafka)
  Worker: UPSERT_STUDENT_ANSWER
  → acquire per-tenant semaphore (max 2 concurrent per tenant)
  → INSERT INTO academic.student_answers(student_id, exam_id, question_id, answer, ...)
    ON CONFLICT (student_id, exam_id, question_id)
    DO UPDATE SET answer=EXCLUDED.answer, updated_at=now()
  → commit offset only after successful DB write
```

#### Grading Pipeline

```
GRADE_SUBMISSION_ATTEMPT event consumed
  → idempotency check: if attempt.graded_at IS NOT NULL → skip, commit offset
  → acquire per-tenant semaphore (GRADING_CONCURRENCY_PER_TENANT, default 2)
  → set Submission.status = 'grading_in_progress'
  → set SubmissionAttempt.grading_started_at = now()
  → separate MCQ/FITB (direct compare) from theory questions
  → for theory questions: build batch prompt → GroqKeyRotator.get_key()
    → single Groq API call with all theory questions
    → parse JSON response keyed by question_id
    → apply jitter: asyncio.sleep(random.uniform(0.1, 0.5)) between submissions
  → bulk INSERT: session.execute(insert(StudentAnswer).values([...]))
  → UPDATE submission_attempts SET score=X, graded_at=now() WHERE id IN (...)
  → set Submission.status = 'graded', latest_score = computed_score
  → emit REFRESH_DASHBOARD
  → commit Kafka offset
```

#### Billing Flow

```
Scheduler tick (hourly/daily)
  → query Semester WHERE end_date <= now() AND is_billed=False AND status='ended'
  → count active students for tenant
  → INSERT Invoice(status='pending', student_count, amount_per_student, total_amount)
  → emit INITIATE_BILLING {invoice_id, tenant_id, semester_id, payment_gateway}

Worker: INITIATE_BILLING handler
  → PaymentGatewayService.initiate(invoice)
    → Paystack: POST https://api.paystack.co/transaction/initialize
      → store authorization_url → Invoice.payment_url
      → store reference → Invoice.payment_reference
    → Monnify: equivalent direct-debit endpoint

POST /api/v1/billing/webhooks/paystack
  → verify HMAC(PAYSTACK_SECRET_KEY, request.body)
  → on charge.success: Invoice.status='paid', Invoice.paid_at=now()
  → SemesterService.mark_billed(semester_id, now())
  → return HTTP 200
```


---

## Database Schema Changes

### New Columns (additive — no existing column removed except Exam.student_id)

#### `account.tenants`
| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `tenant_code` | `String(6)` | NOT NULL | auto-generated | 6-char uppercase alphanumeric; UNIQUE index |
| `start_date` | `DateTime(tz=True)` | NULL | — | Tenant contract start |
| `end_date` | `DateTime(tz=True)` | NULL | — | Tenant contract end |
| `paystack_customer_code` | `String(100)` | NULL | — | Paystack customer reference |
| `monnify_account_reference` | `String(100)` | NULL | — | Monnify account reference |

#### `academic.exams`
| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `end_time` | `DateTime(tz=True)` | NULL | — | Computed: `start_time + duration`; persisted |
| ~~`student_id`~~ | — | — | — | **REMOVED** — student participation via Enrollment/Submission |

#### `academic.submissions`
| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `submitted_at` | `DateTime(tz=True)` | NULL | — | UTC moment of submission receipt |

#### `academic.submission_attempts`
| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `grading_started_at` | `DateTime(tz=True)` | NULL | — | Set when grading begins |

#### `academic.student_answers`
| Constraint | Type | Columns | Notes |
|-----------|------|---------|-------|
| `uq_student_answer_student_exam_question` | UNIQUE | `(student_id, exam_id, question_id)` | Enables atomic ON CONFLICT UPSERT |

#### `billings.invoices`
| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `status` | `SAEnum(InvoiceStatus)` | NOT NULL | `'pending'` | Values: `pending`, `paid`, `overdue`, `cancelled` |
| `payment_reference` | `String(100)` | NULL | — | Gateway transaction reference |
| `payment_gateway` | `SAEnum('paystack','monnify')` | NULL | — | Which gateway was used |
| `paid_at` | `DateTime(tz=True)` | NULL | — | Confirmed payment timestamp |
| `payment_url` | `String(500)` | NULL | — | Checkout/redirect URL from gateway |

#### `billings.billing_plans`
| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `is_active` | `Boolean` | NOT NULL | `True` | Plan active flag |

### Enum Changes

#### `SubmissionStatus` (new value)
```python
class SubmissionStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    GRADING_IN_PROGRESS = "grading_in_progress"   # NEW
    GRADED = "graded"
```

### New Alembic Migration
A single migration file `backend/alembic/versions/YYYYMMDD_app_wide_refactor.py` covers all schema changes above in one transaction.

---

## API Route Structure

All routes follow the pattern `/api/v1/{domain}/{resource}`.

### `/api/v1/auth` — Authentication (unchanged paths)
| Method | Path | Handler |
|--------|------|---------|
| POST | `/api/v1/auth/register` | `users.register` (fixed: add `request` param, add `tenant_code` lookup) |
| POST | `/api/v1/auth/login` | `users.login` |
| GET | `/api/v1/auth/me` | `users.me` |
| POST | `/api/v1/auth/refresh` | `users.refresh` |

### `/api/v1/account` — Account Management (renamed from `/api/v1/auth` for CRUD)
| Method | Path | Handler | File |
|--------|------|---------|------|
| GET | `/api/v1/account/users` | `users.list_users` | `routes/account/users.py` |
| GET | `/api/v1/account/users/{id}` | `users.get_user` | |
| PUT | `/api/v1/account/users/{id}` | `users.update_user` | |
| DELETE | `/api/v1/account/users/{id}` | `users.delete_user` | |
| GET | `/api/v1/account/tenants` | `tenants.list_tenants` | `routes/account/tenants.py` |
| POST | `/api/v1/account/tenants` | `tenants.create_tenant` | |
| GET | `/api/v1/account/tenants/{id}` | `tenants.get_tenant` | |
| PUT | `/api/v1/account/tenants/{id}` | `tenants.update_tenant` | |
| DELETE | `/api/v1/account/tenants/{id}` | `tenants.delete_tenant` | |

### `/api/v1/academic` — Academic Domain
| Method | Path | Handler | Notes |
|--------|------|---------|-------|
| GET/POST | `/api/v1/academic/courses` | `courses.py` | |
| GET/PUT/DELETE | `/api/v1/academic/courses/{id}` | | |
| GET | `/api/v1/academic/courses/{id}/students` | NEW — enrolled students | Req 2.128 |
| GET/POST | `/api/v1/academic/exams` | `exams.py` | |
| GET/PUT/DELETE | `/api/v1/academic/exams/{id}` | | |
| GET | `/api/v1/academic/exams/{id}/results` | NEW — submission results | Req 2.127 |
| POST | `/api/v1/academic/exams/{id}/scan` | NEW — answer sheet scan | Req 2.130 |
| GET/POST | `/api/v1/academic/questions` | `questions.py` | Redis-first fetch |
| GET/POST | `/api/v1/academic/enrollments` | `enrollments.py` | (already plural) |
| PATCH | `/api/v1/academic/answers/{question_id}` | `answers.py` | Changed PUT→PATCH; emits Kafka |
| GET/POST | `/api/v1/academic/submissions` | `submissions.py` | |
| GET | `/api/v1/academic/students/{id}/exams` | NEW — student's exams | Req 2.129 |

### `/api/v1/billing` — Billing Domain (new prefix)
| Method | Path | Handler | File |
|--------|------|---------|------|
| GET/POST | `/api/v1/billing/invoices` | `invoices.py` | |
| GET/POST | `/api/v1/billing/plans` | `billing_plans.py` | |
| GET/POST | `/api/v1/billing/payment-methods` | `payment_methods.py` | |
| GET/POST | `/api/v1/billing/usage` | `usage.py` | |
| GET/POST | `/api/v1/billing/semesters` | `semesters.py` | |
| POST | `/api/v1/billing/webhooks/paystack` | `webhooks.py` | HMAC verified |
| POST | `/api/v1/billing/webhooks/monnify` | `webhooks.py` | HMAC verified |

### `/api/v1/analytics` — Analytics Domain (unchanged prefix)
| Method | Path | Handler | Notes |
|--------|------|---------|-------|
| GET | `/api/v1/analytics/dashboard` | `dashboard.py` | Read-only; no inline writes |
| GET | `/api/v1/analytics/dashboard/lecturer/{id}` | | |
| GET | `/api/v1/analytics/dashboard/admin/{tenant_id}` | | Keyed by tenant_id, not admin_id |
| GET | `/api/v1/analytics/dashboard/student/{id}` | | |

### `/api/v1/health`
| Method | Path | Response |
|--------|------|---------|
| GET | `/api/v1/health` | `{"status":"ok","db":"ok|error","redis":"ok|error","kafka":"ok|error"}` |


---

## Kafka Topic Design

### Topics

| Topic | Partition Key | Consumer Group | Purpose |
|-------|--------------|----------------|---------|
| `tenant-tasks` | `tenant_id` | `wazire-worker` (configurable via `KAFKA_CONSUMER_GROUP_ID`) | All background tasks |
| `wazire-answers` | `tenant_id` | `wazire-worker` | High-volume answer UPSERT events (separate topic for isolation) |
| `wazire-dead-letter` | — | ops monitoring | Unrecoverable handler failures |

### Event Catalogue

| Event | Topic | Payload Fields | Handler |
|-------|-------|---------------|---------|
| `PRELOAD_QUESTIONS` | `tenant-tasks` | `exam_id`, `duration_seconds`, `tenant_id` | `tasks/question.py` |
| `UPSERT_STUDENT_ANSWER` | `wazire-answers` | `student_id`, `exam_id`, `question_id`, `answer`, `tenant_id` | `tasks/question.py` |
| `FORCE_SUBMIT_EXAM` | `tenant-tasks` | `exam_id`, `tenant_id` | `tasks/exam.py` |
| `GRADE_SUBMISSION_ATTEMPT` | `tenant-tasks` | `submission_id`, `attempt_id`, `tenant_id` | `tasks/submission.py` |
| `REFRESH_DASHBOARD` | `tenant-tasks` | `tenant_id`, `lecturer_id?`, `student_id?` | `tasks/submission.py` |
| `INITIATE_BILLING` | `tenant-tasks` | `invoice_id`, `tenant_id`, `semester_id`, `payment_gateway` | `tasks/billing.py` (new) |
| `UPDATE_EXAM_STATUS` | `tenant-tasks` | `{}` | `tasks/exam.py` |
| `SEND_QUEUED_EMAILS` | `tenant-tasks` | `{}` | `tasks/email.py` |
| `DETECT_ANSWER` | `tenant-tasks` | varies | `tasks/question.py` |
| `PARSE_AND_CREATE` | `tenant-tasks` | varies | `tasks/question.py` |
| `SEND_EMAIL` | `tenant-tasks` | varies | `tasks/email.py` |

### Partition Key Strategy
All events include `tenant_id` as the Kafka message key. This ensures:
- All events for a given tenant are processed in order by the same worker replica.
- Per-tenant semaphores in the worker are effective (same tenant → same worker).
- `FORCE_SUBMIT_EXAM` and `GRADE_SUBMISSION_ATTEMPT` for the same exam are ordered.

### Dead-Letter Topic
When a handler exhausts retries (3 attempts with 1s/2s/4s backoff), the message is forwarded to `wazire-dead-letter` with metadata: `original_topic`, `original_offset`, `error_message`, `timestamp`. The offset is then committed so the consumer is not stuck.

---

## Redis Key Design

### Exam Question Cache

| Key Pattern | Type | TTL | Value |
|-------------|------|-----|-------|
| `exam:{exam_id}:questions` | String (JSON) | `duration_seconds + 1800` | JSON array of question dicts |
| `exam:{exam_id}:preloaded` | String | `duration_seconds + 1800` | `"1"` — sentinel to avoid double-preload |

### Groq Key Balancer (cross-process)

| Key Pattern | Type | TTL | Value |
|-------------|------|-----|-------|
| `groq:key_usage:{index}` | Integer | 65s (auto-reset per minute) | Usage counter for key at index |
| `groq:key_cooldown:{index}` | String | `retry_after_seconds` | `"1"` — key is cooling down |

### Rate Limiting

| Key Pattern | Type | TTL | Value |
|-------------|------|-----|-------|
| `ratelimit:{ip}:{endpoint}` | Integer | window_seconds | Request count |

### Per-Tenant Grading Semaphore
Semaphores are in-process `asyncio.Semaphore` objects stored in a module-level dict `_tenant_semaphores: Dict[str, asyncio.Semaphore]`. They are not Redis-backed (asyncio semaphores cannot be shared across processes; per-tenant ordering via Kafka partition key ensures the same tenant's events go to the same worker replica).

---

## Nginx Configuration Design

### File: `nginx/nginx.conf`

```nginx
worker_processes auto;

events { worker_connections 1024; }

http {
    # Rate limiting zone
    limit_req_zone $binary_remote_addr zone=api:10m rate=30r/s;

    # Gzip
    gzip on;
    gzip_types text/plain application/json application/javascript text/css;

    # Backend upstream (load-balanced across replicas)
    upstream backend {
        server backend:8000;
        # Docker Compose --scale backend=N adds more entries automatically
        # when container_name is removed from the backend service
    }

    server {
        listen 80;
        server_name _;

        # API reverse proxy
        location /api/v1/ {
            limit_req zone=api burst=50 nodelay;
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # WebSocket upgrade
        location /ws/ {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }

        # Static assets (hashed filenames — long cache)
        location /assets/ {
            root /usr/share/nginx/html;
            add_header Cache-Control "public, max-age=31536000, immutable";
        }

        # SPA fallback
        location / {
            root /usr/share/nginx/html;
            try_files $uri $uri/ /index.html;
        }
    }
}
```

### Docker Compose nginx service
```yaml
nginx:
  image: nginx:1.27-alpine
  restart: unless-stopped
  ports:
    - "80:80"
    - "443:443"
  volumes:
    - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    - frontend_dist:/usr/share/nginx/html:ro
  depends_on:
    - backend
    - frontend
  networks:
    - wazire-network
```

The `frontend` service in the multi-stage build copies `/app/dist` to a named volume `frontend_dist` that nginx mounts read-only.


---

## File / Module Structure Changes

### Backend — Renamed Files (singular → plural)

| Old Path | New Path |
|----------|----------|
| `backend/routes/account/user.py` | `backend/routes/account/users.py` |
| `backend/routes/account/tenant.py` | `backend/routes/account/tenants.py` |
| `backend/routes/academic/course.py` | `backend/routes/academic/courses.py` |
| `backend/routes/academic/exam.py` | `backend/routes/academic/exams.py` |
| `backend/routes/academic/question.py` | `backend/routes/academic/questions.py` |
| `backend/routes/academic/answer.py` | `backend/routes/academic/answers.py` |
| `backend/routes/academic/submission.py` | `backend/routes/academic/submissions.py` |
| `backend/services/academic/course.py` | `backend/services/academic/courses.py` |
| `backend/services/academic/exam.py` | `backend/services/academic/exams.py` |
| `backend/services/academic/question.py` | `backend/services/academic/questions.py` |
| `backend/services/academic/answer.py` | `backend/services/academic/answers.py` |
| `backend/services/academic/submission.py` | `backend/services/academic/submissions.py` |
| `backend/services/account/user.py` | `backend/services/account/users.py` |
| `backend/services/account/tenant.py` | `backend/services/account/tenants.py` |

### Backend — New Files

| Path | Purpose |
|------|---------|
| `backend/routes/billing/__init__.py` | Billing router package |
| `backend/routes/billing/invoices.py` | Invoice CRUD |
| `backend/routes/billing/billing_plans.py` | Billing plan CRUD |
| `backend/routes/billing/payment_methods.py` | Payment method CRUD |
| `backend/routes/billing/usage.py` | Usage CRUD |
| `backend/routes/billing/semesters.py` | Semester CRUD |
| `backend/routes/billing/webhooks.py` | Paystack/Monnify webhook handlers |
| `backend/services/billing/__init__.py` | Billing service package |
| `backend/services/billing/invoices.py` | Invoice service |
| `backend/services/billing/billing_plans.py` | Billing plan service |
| `backend/services/billing/payment_methods.py` | Payment method service |
| `backend/services/billing/usage.py` | Usage service |
| `backend/services/billing/semesters.py` | Semester service (incl. `mark_billed`) |
| `backend/services/billing/payment_gateway.py` | `PaymentGatewayService` (Paystack + Monnify) |
| `backend/core/kafka_manager.py` | `KafkaManager` facade class |
| `backend/tasks/billing.py` | `INITIATE_BILLING` handler + `HANDLERS` dict |
| `backend/tests/` | Test directory (unit, integration, e2e) |
| `backend/tests/unit/services/` | Unit tests mirroring service structure |
| `backend/tests/integration/` | Integration tests with httpx.AsyncClient |
| `backend/tests/e2e/` | End-to-end scenario tests |
| `nginx/nginx.conf` | Nginx configuration |
| `docs/API.md` | Full API documentation |
| `docs/Wazire.postman_collection.json` | Postman collection |
| `.github/workflows/ci.yml` | GitHub Actions CI pipeline |
| `.codecov.yml` | Codecov configuration |
| `backend/pyproject.toml` | pytest + coverage configuration |
| `frontend/vitest.config.ts` | Vitest + coverage configuration |
| `frontend/src/mocks/` | MSW mock handlers |
| `frontend/e2e/` | Playwright E2E tests |
| `frontend/playwright.config.ts` | Playwright configuration |

### Frontend — New API Modules

| Path | Purpose |
|------|---------|
| `frontend/src/apis/billing.ts` | Invoice, plan, payment method, usage, semester API calls |
| `frontend/src/apis/semester.ts` | Semester-specific API calls (if separated) |

---

## Key Class Designs

### `KafkaManager` (`backend/core/kafka_manager.py`)

```python
class KafkaManager:
    """Facade over KafkaProducerService for use in routes and tasks.
    
    Centralises topic routing, payload structure, and partition key assignment.
    Routes import KafkaManager; they do NOT import producer_service directly.
    """

    TOPIC_MAP = {
        "UPSERT_STUDENT_ANSWER": "wazire-answers",
        # all other events → "tenant-tasks"
    }

    def __init__(self, producer: KafkaProducerService) -> None:
        self._producer = producer

    async def emit(
        self,
        event: str,
        data: Dict[str, Any],
        partition_key: Optional[str] = None,  # typically tenant_id
    ) -> bool:
        topic = self.TOPIC_MAP.get(event, "tenant-tasks")
        key_bytes = partition_key.encode() if partition_key else None
        return await self._producer.publish_safe(topic, event, data, key=key_bytes)

# Module-level singleton, initialised in lifespan
kafka_manager: KafkaManager = None
```

### `Worker` class (`backend/worker.py`)

```python
class Worker:
    """Class-based Kafka worker with explicit lifecycle management."""

    def __init__(self) -> None:
        self._consumer = KafkaConsumerService()
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        await self._consumer.start()

    async def run(self) -> None:
        """Block until stop() is called."""
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._stop_event.set)
        await self._stop_event.wait()

    async def stop(self) -> None:
        self._stop_event.set()
        await self._consumer.stop()

    @classmethod
    def main(cls) -> None:
        worker = cls()
        async def _run():
            await worker.start()
            await worker.run()
            await worker.stop()
        asyncio.run(_run())

if __name__ == "__main__":
    Worker.main()
```

### Dispatcher Pattern (`backend/core/utils/kafka/consumer.py`)

Each `tasks/` module exports a `HANDLERS` dict:

```python
# backend/tasks/exam.py
HANDLERS: Dict[str, Handler] = {
    "UPDATE_EXAM_STATUS": handle_update_exam_status,
    "FORCE_SUBMIT_EXAM": handle_force_submit_exam,
    "PRELOAD_QUESTIONS": handle_preload_questions,
}
```

`KafkaConsumerService._load_handlers()` discovers and merges all dicts:

```python
def _load_handlers(self) -> None:
    from tasks import exam, submission, question, email, billing
    for module in (exam, submission, question, email, billing):
        self._handlers.update(getattr(module, "HANDLERS", {}))
    logger.info("Registered %d handlers: %s", len(self._handlers), list(self._handlers))
```

Adding a new event type requires only adding to the relevant `tasks/` module's `HANDLERS` dict — `consumer.py` is never modified.

### `GroqKeyRotator` (`backend/core/key_balancer.py` — upgraded)

```python
class GroqKeyRotator:
    """Redis-backed round-robin Groq API key pool with per-key cooldown.
    
    Reads keys from GROQ_API_KEY_1 … GROQ_API_KEY_4.
    Cooldown state stored in Redis so all worker replicas share it.
    Falls back to in-process round-robin if Redis is unavailable.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self.keys: List[str] = [
            k for k in [
                settings.GROQ_API_KEY_1, settings.GROQ_API_KEY_2,
                settings.GROQ_API_KEY_3, settings.GROQ_API_KEY_4,
            ] if k
        ]
        self._index = 0  # round-robin cursor (in-process fallback)

    async def get_key(self) -> Optional[str]:
        """Return the next available key, skipping cooled-down keys."""
        redis = get_redis_client()
        for _ in range(len(self.keys)):
            idx = self._index % len(self.keys)
            self._index += 1
            key = self.keys[idx]
            if redis:
                cooling = await redis.get(f"groq:key_cooldown:{idx}")
                if cooling:
                    continue
            return key
        # All keys cooling — wait for soonest reset
        await asyncio.sleep(1)
        return self.keys[0] if self.keys else None

    async def mark_rate_limited(self, key: str, retry_after: int = 60) -> None:
        """Mark a key as cooling down for retry_after seconds."""
        redis = get_redis_client()
        if redis and key in self.keys:
            idx = self.keys.index(key)
            await redis.setex(f"groq:key_cooldown:{idx}", retry_after, "1")

# Module-level singleton
_rotator: Optional[GroqKeyRotator] = None

def get_rotator() -> GroqKeyRotator:
    global _rotator
    if _rotator is None:
        _rotator = GroqKeyRotator()
    return _rotator
```


---

## Frontend Multi-Stage Dockerfile Design

```dockerfile
# Stage 1: Build
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
# /app/dist now contains the production static assets

# Stage 2: Export dist to named volume via a minimal image
FROM alpine:3.19
WORKDIR /dist
COPY --from=builder /app/dist .
# nginx mounts the frontend_dist volume; this container just populates it
CMD ["sh", "-c", "cp -r /dist/. /output/ && echo 'Frontend assets copied'"]
```

The `docker-compose.yml` frontend service uses `volumes: - frontend_dist:/output` and runs once to populate the volume. The nginx service mounts `frontend_dist:/usr/share/nginx/html:ro`.

---

## CI/CD Pipeline Design

### `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: ["**"]
  pull_request:
    branches: [main, develop]

jobs:
  backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: wazire_test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: wazire_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r backend/requirements.txt
        working-directory: backend
      - name: Lint
        run: ruff check .
        working-directory: backend
      - name: Type check
        run: mypy . --ignore-missing-imports
        working-directory: backend
      - name: Test with coverage
        run: pytest --cov=. --cov-branch --cov-fail-under=90 --cov-report=xml
        working-directory: backend
        env:
          TEST_DATABASE_URL: postgresql+asyncpg://wazire_test:test@localhost/wazire_test
          REDIS_URL: redis://localhost:6379
      - uses: codecov/codecov-action@v4
        with:
          files: backend/coverage.xml
          flags: backend

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20" }
      - run: npm ci
        working-directory: frontend
      - name: Lint
        run: npm run lint
        working-directory: frontend
      - name: Type check
        run: npx tsc --noEmit
        working-directory: frontend
      - name: Test with coverage
        run: npx vitest --run --coverage
        working-directory: frontend
      - uses: codecov/codecov-action@v4
        with:
          files: frontend/coverage/lcov.info
          flags: frontend

  playwright:
    runs-on: ubuntu-latest
    needs: [backend, frontend]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20" }
      - run: npm ci
        working-directory: frontend
      - run: npx playwright install --with-deps
        working-directory: frontend
      - name: Run E2E tests
        run: npx playwright test
        working-directory: frontend
```

### Conventional Commits Format
All commits on `fix/app-wide-refactor` branch follow:
```
<type>(<scope>): <description>

Types: fix | feat | chore | refactor | test | docs | ci
Scope: backend | frontend | docker | kafka | grading | billing | ci | nginx

Examples:
  fix(backend): add yield to lifespan context manager
  feat(backend): add tenant_code column to Tenant model
  fix(docker): correct pgbouncer and scheduler indentation in docker-compose.yml
  feat(kafka): add PRELOAD_QUESTIONS scheduler job and worker handler
  fix(frontend): change answer upsert from PUT to PATCH
  chore(backend): add gunicorn and apscheduler to requirements.txt
```

### PR Workflow
- Branch: `fix/app-wide-refactor` → target: `main` on `https://github.com/oscaroguledo/wazire.git`
- PR title: ≤ 70 characters
- PR description: summary of all changes, tasks completed, what was tested
- Merge blocked if CI fails on any job

---

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate each bug on unfixed code, then verify the fix works correctly and preserves existing behaviour.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bugs BEFORE implementing fixes. Confirm or refute root cause analysis.

**Test Plan**: Write tests that invoke the buggy code paths and assert the expected failures. Run on UNFIXED code to observe failures and understand root causes.

**Test Cases**:
1. **Lifespan test**: Start the FastAPI app and assert it serves a request — will fail on unfixed code because lifespan never yields.
2. **Invoice.to_dict test**: Instantiate `Invoice()` and call `to_dict()` — will raise `AttributeError: status` on unfixed code.
3. **Docker compose parse test**: Parse `docker-compose.yml` and assert `pgbouncer` is a top-level service — will fail on unfixed code.
4. **Answer PATCH test**: Send `PATCH /academic/answers/{id}` and assert a Kafka event is produced — will fail on unfixed code (route uses PUT and writes directly to DB).
5. **StudentAnswer UPSERT race test**: Send 100 concurrent PATCH requests for the same `(student, exam, question)` — will produce duplicate rows on unfixed code.
6. **Dashboard GET write test**: Call `GET /analytics/dashboard/` and assert no DB write occurs — will fail on unfixed code.

**Expected Counterexamples**:
- `AttributeError` on missing model columns
- `AssertionError` on wrong HTTP method routing
- Duplicate rows in `student_answers` under concurrent load
- DB write detected during GET request

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed system produces the expected behaviour.

**Pseudocode:**
```
FOR ALL input WHERE isBugCondition(input) DO
  result := fixedSystem(input)
  ASSERT expectedBehavior(result)
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed system produces the same result as the original system.

**Pseudocode:**
```
FOR ALL input WHERE NOT isBugCondition(input) DO
  ASSERT originalSystem(input) = fixedSystem(input)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many test cases automatically across the input domain.
- It catches edge cases that manual unit tests might miss.
- It provides strong guarantees that behaviour is unchanged for all non-buggy inputs.

**Test Plan**: Observe behaviour on UNFIXED code first for all currently working paths, then write property-based tests capturing that behaviour.

**Test Cases**:
1. **Auth flow preservation**: Login, refresh, me endpoints continue to work after all fixes.
2. **Course/exam CRUD preservation**: All existing CRUD operations continue to work after route renaming.
3. **Kafka handler preservation**: All existing event handlers (`GRADE_SUBMISSION_ATTEMPT`, etc.) continue to process events correctly after dispatcher refactor.
4. **Model shape preservation**: All `to_dict()` outputs continue to include existing fields after new columns are added.
5. **Docker service preservation**: `postgres` and `redis` services continue to start and pass health checks after `docker-compose.yml` is fixed.

### Unit Tests

- Every service class method: happy path + at least one error/edge case
- Every Kafka task handler: invoked directly with mock payload
- Every model `to_dict()`, `delete()`, `restore()`, `lock()` method
- Every utility function in `backend/core/utils/`
- `KafkaManager.emit()` with mocked producer
- `GroqKeyRotator.get_key()` with mocked Redis (all keys available, some cooling, all cooling)
- Worker dispatcher handler registration and dispatch by event type

### Property-Based Tests

- Generate random `(student_id, exam_id, question_id)` tuples and verify UPSERT produces exactly one row
- Generate random exam states and verify `FORCE_SUBMIT_EXAM` skips already-submitted students
- Generate random Groq API key pool states and verify `GroqKeyRotator` never returns a cooling key
- Generate random submission states and verify idempotent grading (already-graded attempts are skipped)

### Integration Tests

- Full request → middleware → route → service → DB → response stack for every endpoint
- Kafka event produced by answer PATCH endpoint (mocked Kafka producer)
- Dashboard GET returns pre-aggregated data with no inline DB writes
- Webhook handler verifies HMAC and updates Invoice + Semester atomically

### End-to-End Scenario Tests

1. **Full exam lifecycle**: tenant creation → users → course → enrollment → exam → questions → Redis preload → student answers via PATCH → Kafka → worker UPSERT → submission → grading → dashboard update
2. **Force submit**: exam time expires → scheduler emits `FORCE_SUBMIT_EXAM` → worker auto-submits unsubmitted students → grading triggered
3. **Concurrent answer UPSERT idempotency**: 100 concurrent PATCH answer requests for the same `(student, exam, question)` → assert exactly one row in `student_answers`

