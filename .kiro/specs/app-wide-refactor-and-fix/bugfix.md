# Bugfix Requirements Document

## Introduction

The Wazire full-stack application (FastAPI backend + React/TypeScript frontend + Docker) has accumulated a set of critical bugs that prevent it from starting, running, and functioning correctly. These range from a fatal missing `yield` in the backend lifespan that prevents the server from ever entering its runtime, to Python syntax errors, missing model columns, broken imports, a malformed Docker Compose file, a missing dependency, and several frontend type and logic errors. This document captures every defect found, the correct behavior expected, and the existing behavior that must be preserved.

---

## Bug Analysis

### Current Behavior (Defect)

**Backend — Fatal startup / runtime bugs**

1.1 WHEN the FastAPI application starts THEN the lifespan context manager in `backend/main.py` never yields, causing the server to run startup code and immediately execute shutdown code without ever entering the application runtime

1.2 WHEN the `POST /api/v1/auth/register` endpoint is called THEN the handler crashes with `NameError: name 'request' is not defined` because the `request: Request` parameter is missing from the function signature in `backend/routes/account/user.py`

1.3 WHEN `backend/main.py` imports `consumer_service` from `core.utils.kafka` THEN the import succeeds but `consumer_service` is never used in `main.py`, creating dead code that misleads readers into thinking the consumer runs in the web process

1.4 WHEN `backend/models/__init__.py` is imported THEN it crashes with `ModuleNotFoundError` because it imports `OAuth` from `models.account.oauth`, a file that does not exist

1.5 WHEN `backend/scheduler.py` is executed THEN it crashes with `ModuleNotFoundError: No module named 'apscheduler'` because `apscheduler` is not listed in `backend/requirements.txt`

1.6 WHEN `SubmissionService.grade_attempt_background()` is called by the background worker THEN it crashes with `AttributeError: __aenter__` because `get_db()` is an async generator and cannot be used as an async context manager (`async with get_db() as db:`)

1.7 WHEN `SubmissionService.submit_exam()` or `create_submission()` creates a `SubmissionModel` THEN it passes `attempts_count=0` as a constructor argument, but the `Submission` model column is named `attempts` (not `attempts_count`), causing an `unexpected keyword argument` error

1.8 WHEN `SubmissionService.submit_exam()` creates a `SubmissionAttemptModel` THEN it passes `attempt_number` and `scan_pages` as constructor arguments, but neither column exists on the `SubmissionAttempt` model (the model uses `id` as the auto-incrementing attempt number and has no `scan_pages` column)

1.9 WHEN `Invoice.to_dict()` or `Invoice.__repr__()` is called THEN it crashes with `AttributeError: 'Invoice' object has no attribute 'status'` because the `status` column is never defined on the `Invoice` model despite being indexed and referenced

1.10 WHEN `BillingPlan.to_dict()` is called THEN it crashes with `AttributeError: 'BillingPlan' object has no attribute 'is_active'` because the `is_active` column is never defined on the `BillingPlan` model despite being indexed and referenced

1.11 WHEN `backend/models/account/tenant.py` is used THEN `start_date` and `end_date` columns are indexed and referenced in `TenantCreate`/`TenantRead` schemas but are never defined as mapped columns on the `Tenant` model

**Docker — Compose YAML structure bugs**

1.12 WHEN `docker-compose.yml` is parsed THEN the `pgbouncer` service is treated as a nested key under `postgres` instead of a top-level service because it is indented one level too deep, causing `pgbouncer` to be silently ignored and the `backend` service (which depends on `pgbouncer`) to fail to start

1.13 WHEN `docker-compose.yml` is parsed THEN the `scheduler` service is treated as a nested key under `worker` instead of a top-level service because it is indented one level too deep, causing the scheduler process to never run

1.14 WHEN the `frontend` Docker container runs THEN it executes `npm run dev` (a development server with hot-reload) instead of building a production bundle and serving it, making the container unsuitable for any non-development deployment

**Frontend — Type, import, and logic bugs**

1.15 WHEN `frontend/src/pages/UserManagement.tsx` is compiled THEN TypeScript reports errors because the `User` type is used throughout the file but is never imported (no `import type { User } from '@/lib/types'` or equivalent)

1.16 WHEN a user with role `superadmin` is returned from the backend THEN the frontend `UserRole` type in `frontend/src/lib/types.ts` does not include `'superadmin'`, causing TypeScript type errors and potential runtime mismatches for superadmin users

1.17 WHEN `AuthContext.register()` completes the auto-login after registration THEN the access token is never stored in `localStorage` (the `login()` API call result is used but `localStorage.setItem` for the token is not called), leaving the user in an unauthenticated state despite a successful registration

---

### Expected Behavior (Correct)

**Backend — Fatal startup / runtime bugs**

2.1 WHEN the FastAPI application starts THEN the lifespan context manager SHALL yield after completing startup tasks, allowing the application to enter its runtime and serve requests, and only execute shutdown code after the yield when the application is stopping

2.2 WHEN the `POST /api/v1/auth/register` endpoint is called THEN the handler SHALL include `request: Request` as a function parameter so the `request` variable is available for building the response

2.3 WHEN `backend/main.py` imports from `core.utils.kafka` THEN it SHALL only import `producer_service` (which is actually used in the lifespan), removing the unused `consumer_service` import

2.4 WHEN `backend/models/__init__.py` is imported THEN it SHALL NOT import `OAuth` from a non-existent module; the import SHALL be removed or replaced with the correct module path if an OAuth model is needed

2.5 WHEN `backend/scheduler.py` is executed THEN `apscheduler` SHALL be listed in `backend/requirements.txt` so the dependency is available in all environments

2.6 WHEN `SubmissionService.grade_attempt_background()` needs a database session THEN it SHALL use the async generator pattern (`async for db in get_db(): ...`) or a helper like `with_db()` instead of `async with get_db() as db:`

2.7 WHEN `SubmissionService` creates a `SubmissionModel` THEN it SHALL use the correct column name `attempts=0` matching the model definition

2.8 WHEN `SubmissionService` creates a `SubmissionAttemptModel` THEN it SHALL only pass columns that exist on the model; `attempt_number` and `scan_pages` SHALL be removed from the constructor call (or the model SHALL be updated to include these columns if they are intentionally required)

2.9 WHEN `Invoice.to_dict()` or `Invoice.__repr__()` is called THEN the `Invoice` model SHALL define a `status` column (e.g. an `InvoiceStatus` enum column) so the attribute exists and the methods work correctly

2.10 WHEN `BillingPlan.to_dict()` is called THEN the `BillingPlan` model SHALL define an `is_active` boolean column so the attribute exists and the method works correctly

2.11 WHEN the `Tenant` model is used THEN `start_date` and `end_date` SHALL be defined as mapped `DateTime` columns on the model, consistent with the indexes and schemas that reference them

**Docker — Compose YAML structure bugs**

2.12 WHEN `docker-compose.yml` is parsed THEN `pgbouncer` SHALL be a top-level service at the same indentation level as `postgres`, `redis`, `backend`, `frontend`, `worker`, and `scheduler`

2.13 WHEN `docker-compose.yml` is parsed THEN `scheduler` SHALL be a top-level service at the same indentation level as all other services

2.14 WHEN the `frontend` Docker container is built for production THEN the Dockerfile SHALL build the static assets with `npm run build` and serve them with a production-grade static server (e.g. nginx), not run the Vite dev server

**Frontend — Type, import, and logic bugs**

2.15 WHEN `frontend/src/pages/UserManagement.tsx` is compiled THEN it SHALL import the `User` type from `@/lib/types` (or `@/apis/auth`) so all `User` references resolve correctly

2.16 WHEN the backend returns a user with role `superadmin` THEN the `UserRole` type in `frontend/src/lib/types.ts` SHALL include `'superadmin'` as a valid value

2.17 WHEN `AuthContext.register()` completes the auto-login after registration THEN the access token SHALL be stored in `localStorage` under the configured token key so the user is authenticated immediately after registering

---

### Unchanged Behavior (Regression Prevention)

3.1 WHEN the backend starts successfully THEN it SHALL CONTINUE TO register all API routers under `/api/v1` and serve requests on the configured host and port

3.2 WHEN a valid JWT token is provided THEN the authentication middleware SHALL CONTINUE TO validate it, look up the user, and attach the user to the request context

3.3 WHEN the `POST /api/v1/auth/login` endpoint is called with valid credentials THEN it SHALL CONTINUE TO return an `AuthResponse` with `user` and `tokens` fields

3.4 WHEN the `GET /api/v1/auth/me` endpoint is called with a valid token THEN it SHALL CONTINUE TO return the current user's profile

3.5 WHEN courses, exams, questions, enrollments, and answers endpoints are called THEN they SHALL CONTINUE TO function as currently implemented (these routes have no identified bugs)

3.6 WHEN the tenant middleware processes a request THEN it SHALL CONTINUE TO read the `X-Tenant-ID` header and attach it to `request.state.tenant_id`

3.7 WHEN the rate limiter is configured THEN it SHALL CONTINUE TO enforce rate limits and return 429 responses when limits are exceeded

3.8 WHEN the database connection pool is initialized THEN it SHALL CONTINUE TO use the configured `DATABASE_URL` with async engine settings

3.9 WHEN Redis is configured THEN the Redis client SHALL CONTINUE TO connect using the configured `REDIS_URL`

3.10 WHEN the Kafka producer is started in the lifespan THEN it SHALL CONTINUE TO publish events to the configured broker (or fail gracefully if Kafka is not configured)

3.11 WHEN the frontend login page is rendered THEN it SHALL CONTINUE TO display the login form and handle authentication correctly

3.12 WHEN the frontend routing resolves a protected route THEN it SHALL CONTINUE TO redirect unauthenticated users to `/login`

3.13 WHEN the frontend `UserManagement` page loads THEN it SHALL CONTINUE TO fetch and display the paginated user list with search and filter functionality

3.14 WHEN the Docker `postgres` and `redis` services start THEN they SHALL CONTINUE TO use the same image versions, environment variables, volumes, and health checks as currently configured

3.15 WHEN the `worker` service runs THEN it SHALL CONTINUE TO execute `python worker.py` and consume Kafka events for background grading and dashboard refresh

---

## Exam Data Flow Architecture Deviations

The following bug conditions document deviations from the intended exam data flow architecture:

- **Course/Exam Creation**: Lecturers/admins create courses and exams → written directly to PostgreSQL (no Kafka involved)
- **Pre-Exam (Scheduler-triggered)**: ~15 minutes before exam start, the scheduler detects approaching exams, produces a Kafka event, and the consumer pushes questions from PostgreSQL → Redis (TTL = exam duration + buffer)
- **During Exam — Question Fetching**: Students fetch exam questions FROM Redis (not PostgreSQL directly)
- **During Exam — Answer Submission**: Frontend sends a PATCH per answer → API produces a Kafka event → worker consumes and UPSERTs to PostgreSQL

### Current Behavior (Defect) — Architecture Deviations

1.18 WHEN the scheduler runs THEN it does NOT detect exams approaching within ~15 minutes of their start time and does NOT emit a `PRELOAD_QUESTIONS` Kafka event; the scheduler only has jobs for `UPDATE_EXAM_STATUS` and `SEND_QUEUED_EMAILS`, so questions are never pre-loaded into Redis before students arrive

1.19 WHEN the Kafka consumer worker starts THEN it does NOT register a handler for any `PRELOAD_QUESTIONS` event, so even if such an event were produced it would be silently discarded with a "No handler" warning

1.20 WHEN the worker would handle a `PRELOAD_QUESTIONS` event THEN no code exists to read exam questions from PostgreSQL and write them to Redis with a TTL matching the exam duration plus a buffer

1.21 WHEN a student fetches exam questions during an active exam THEN the `GET /academic/questions/exam/{exam_id}` and `GET /academic/questions/?exam_id=` endpoints query PostgreSQL directly via `QuestionService.list()` instead of reading from Redis, defeating the purpose of pre-loading and increasing DB load during peak exam time

1.22 WHEN a student clicks an answer during an exam THEN the frontend calls `PUT /academic/answers/{question_id}` (using HTTP PUT, not PATCH), and the API handler (`upsert_answer` in `backend/routes/academic/answer.py`) writes the answer directly to PostgreSQL via `StudentAnswerService.upsert()` — no Kafka event is produced, bypassing the intended Kafka buffer and decoupling

1.23 WHEN the Kafka consumer worker starts THEN it does NOT register a handler for any `UPSERT_STUDENT_ANSWER` (or equivalent) event, so the worker cannot perform the intended PostgreSQL UPSERT on behalf of the API

### Expected Behavior (Correct) — Architecture Deviations

2.18 WHEN the scheduler runs THEN it SHALL include a periodic job (e.g. every 1–5 minutes) that queries PostgreSQL for exams whose `start_time` is within the next ~15 minutes and whose questions have not yet been pre-loaded, and SHALL emit a `PRELOAD_QUESTIONS` Kafka event for each such exam containing the `exam_id` and exam duration

2.19 WHEN the Kafka consumer worker starts THEN it SHALL register a `PRELOAD_QUESTIONS` handler so that pre-load events are dispatched to the correct task function

2.20 WHEN the `PRELOAD_QUESTIONS` Kafka event is consumed THEN the handler SHALL fetch all questions for the given exam from PostgreSQL and write them to Redis under a key scoped to the exam (e.g. `exam:{exam_id}:questions`) with a TTL equal to the exam duration in seconds plus a configurable buffer (e.g. 30 minutes), ensuring questions are hot in Redis before students arrive

2.21 WHEN a student fetches exam questions during an active exam THEN the API SHALL first attempt to read questions from Redis (using the pre-loaded key); only if the Redis key is absent (cache miss) SHALL it fall back to querying PostgreSQL directly, so that DB load is reduced during peak exam time

2.22 WHEN a student clicks an answer during an exam THEN the frontend SHALL send a `PATCH` request (not `PUT`) to the API; the API handler SHALL immediately produce a Kafka event (e.g. `UPSERT_STUDENT_ANSWER`) containing `student_id`, `exam_id`, `question_id`, and the answer payload, and SHALL return a fast acknowledgement without waiting for the DB write

2.23 WHEN the `UPSERT_STUDENT_ANSWER` Kafka event is consumed by the worker THEN the handler SHALL perform an UPSERT into the `student_answers` PostgreSQL table via `StudentAnswerService.upsert()`, decoupling the API response latency from the DB write

### Unchanged Behavior (Regression Prevention) — Architecture Deviations

3.16 WHEN a lecturer or admin creates a course or exam THEN the system SHALL CONTINUE TO write directly to PostgreSQL without involving Kafka, preserving the existing synchronous creation flow

3.17 WHEN a student submits the final exam (POST `/academic/submissions/`) THEN the system SHALL CONTINUE TO create the `Submission` and `SubmissionAttempt` records synchronously and enqueue grading via the existing `GRADE_SUBMISSION_ATTEMPT` Kafka event

3.18 WHEN Redis is unavailable during question fetch THEN the system SHALL CONTINUE TO fall back to PostgreSQL so that students are never blocked from accessing exam questions due to a Redis outage

3.19 WHEN the scheduler's existing `UPDATE_EXAM_STATUS` and `SEND_QUEUED_EMAILS` jobs run THEN they SHALL CONTINUE TO function as currently implemented, unaffected by the addition of the new `PRELOAD_QUESTIONS` job

3.20 WHEN the worker's existing Kafka event handlers (`GRADE_SUBMISSION_ATTEMPT`, `REFRESH_DASHBOARD`, `DETECT_ANSWER`, `PARSE_AND_CREATE`, `SEND_EMAIL`, `UPDATE_EXAM_STATUS`, `SEND_QUEUED_EMAILS`) are invoked THEN they SHALL CONTINUE TO function as currently implemented, unaffected by the addition of the new `UPSERT_STUDENT_ANSWER` handler

---

## Force-Submit & Structural Architecture Deviations

The following bug conditions document (a) the missing exam force-submission flow and (b) structural deviations from the senior backend architect's required high-scale pattern for the worker, dispatcher, and Kafka manager.

**Confirmed non-issues (do not flag):**
- All models in `backend/models/` are correct — no model bugs in this section.
- `backend/scheduler.py` already emits Kafka events via `producer_service.publish_safe()` for its existing jobs; it does NOT perform direct DB writes. No defect for existing scheduler jobs.
- `backend/core/utils/kafka/consumer.py` already implements a class-based `KafkaConsumerService`. No defect there.
- `backend/core/utils/kafka/producer.py` already implements a class-based `KafkaProducerService`. No defect there.

### Current Behavior (Defect) — Force-Submit & Structural Deviations

1.24 WHEN an exam's time expires (i.e. `start_time + duration` has elapsed and the exam status transitions to `finished`) THEN the scheduler does NOT emit a `FORCE_SUBMIT_EXAM` Kafka event; no job exists in `backend/scheduler.py` to detect expired exams and trigger auto-submission for unsubmitted students

1.25 WHEN a `FORCE_SUBMIT_EXAM` Kafka event is produced THEN the worker does NOT handle it; no handler for `FORCE_SUBMIT_EXAM` is registered in `KafkaConsumerService._load_handlers()` in `backend/core/utils/kafka/consumer.py`, so the event is silently discarded with a "No handler" warning and enrolled students who have not submitted are never auto-submitted

1.26 WHEN `backend/worker.py` is executed THEN it runs as a procedural module-level script (`main()` function) rather than as a class-based worker; the entry point is not encapsulated in a class (e.g. `class Worker`) with lifecycle methods (`start`, `stop`, `run`), making it harder to test, extend, and manage in a high-scale environment

1.27 WHEN the Kafka consumer needs to register event handlers THEN `KafkaConsumerService._load_handlers()` in `backend/core/utils/kafka/consumer.py` hard-codes all handler imports and assignments in a single monolithic method; there is no dispatcher pattern where individual task modules in `backend/tasks/` self-register their handlers by event type (e.g. via a `register(dispatcher)` function or a `HANDLERS` dict exported per module), making it necessary to edit `consumer.py` every time a new event type is added

1.28 WHEN a FastAPI route needs to publish a Kafka event THEN it calls `producer_service.publish_safe()` directly (importing `producer_service` from `core.utils.kafka`); there is no `KafkaManager` class that encapsulates the producer and provides a higher-level interface for routes, meaning routes are tightly coupled to the producer implementation and there is no single place to add cross-cutting concerns (e.g. topic routing, payload validation, retry policy) for outbound events

### Expected Behavior (Correct) — Force-Submit & Structural Deviations

2.24 WHEN the scheduler runs THEN it SHALL include a periodic job (e.g. every 1–5 minutes) that queries PostgreSQL for exams whose `start_time + duration` has elapsed and whose status is `in_progress` (or equivalent active state), and SHALL emit a `FORCE_SUBMIT_EXAM` Kafka event for each such exam containing at minimum the `exam_id`, so that auto-submission can be handled asynchronously by the worker

2.25 WHEN a `FORCE_SUBMIT_EXAM` Kafka event is consumed by the worker THEN the handler SHALL (a) query all `Enrollment` records for the given `exam_id` to find enrolled students, (b) filter out students who already have a `Submission` record for that exam, (c) auto-create a `Submission` (with `status=submitted`) and a `SubmissionAttempt` record for each unsubmitted student, and (d) emit a `GRADE_SUBMISSION_ATTEMPT` Kafka event for each newly created attempt so that grading proceeds via the existing flow; the handler SHALL be registered in `KafkaConsumerService._load_handlers()` under the key `"FORCE_SUBMIT_EXAM"`

2.26 WHEN `backend/worker.py` is executed THEN the entry point SHALL be encapsulated in a class-based worker (e.g. `class Worker`) with explicit `start()`, `run()`, and `stop()` lifecycle methods that manage the `KafkaConsumerService` instance, signal handling, and the event loop, so the worker is testable, extensible, and consistent with the high-scale architectural pattern

2.27 WHEN a new Kafka event type is added to the system THEN it SHALL be possible to register its handler by adding a `HANDLERS` dict (or equivalent `register(dispatcher)` function) to the relevant module in `backend/tasks/` without modifying `backend/core/utils/kafka/consumer.py`; `KafkaConsumerService` SHALL discover and merge handler registrations from all task modules at startup using the dispatcher pattern, so that `consumer.py` is decoupled from the specific set of event types

2.28 WHEN a FastAPI route needs to publish a Kafka event THEN it SHALL use a `KafkaManager` class (or equivalent facade) rather than calling `producer_service` directly; `KafkaManager` SHALL wrap `KafkaProducerService` and expose a clean, route-friendly API (e.g. `kafka_manager.emit(event, data)`) so that topic routing, payload structure, and cross-cutting concerns are centralised in one place and routes are decoupled from the producer implementation

### Unchanged Behavior (Regression Prevention) — Force-Submit & Structural Deviations

3.21 WHEN the scheduler's existing `UPDATE_EXAM_STATUS` and `SEND_QUEUED_EMAILS` jobs run THEN they SHALL CONTINUE TO emit their respective Kafka events via `producer_service.publish_safe()` exactly as currently implemented, unaffected by the addition of the new `FORCE_SUBMIT_EXAM` job

3.22 WHEN the worker's existing Kafka event handlers (`GRADE_SUBMISSION_ATTEMPT`, `REFRESH_DASHBOARD`, `DETECT_ANSWER`, `PARSE_AND_CREATE`, `SEND_EMAIL`, `UPDATE_EXAM_STATUS`, `SEND_QUEUED_EMAILS`) are invoked THEN they SHALL CONTINUE TO function as currently implemented, unaffected by the refactor to a dispatcher pattern or the addition of the `FORCE_SUBMIT_EXAM` handler

3.23 WHEN `backend/core/utils/kafka/consumer.py` is refactored to support the dispatcher pattern THEN `KafkaConsumerService` SHALL CONTINUE TO use manual offset commit, dead-letter logging, and reconnect-on-error behaviour as currently implemented

3.24 WHEN `backend/core/utils/kafka/producer.py` is unchanged THEN `KafkaProducerService` SHALL CONTINUE TO function as the underlying producer; `KafkaManager` SHALL delegate to it rather than replace it

3.25 WHEN a student manually submits an exam before the expiry time THEN the system SHALL CONTINUE TO create the `Submission` and `SubmissionAttempt` records via the existing synchronous submission flow, and the `FORCE_SUBMIT_EXAM` handler SHALL skip that student (because a `Submission` record already exists) without creating a duplicate


---

## Production-Grade Resilience Requirements

The following bug conditions document gaps in three production-grade architectural pillars: zero-data-loss answer persistence, high-fidelity UTC timing, and horizontally-scalable infrastructure.

### Current Behavior (Defect) — Production-Grade Resilience

**Pillar 1 — Zero-Data-Loss ("O-Ring Tightness")**

1.29 WHEN a student submits an answer via `PUT /academic/answers/{question_id}` THEN the API handler in `backend/routes/academic/answer.py` writes the answer directly to PostgreSQL via `StudentAnswerService.upsert()` without producing a Kafka event first; if the DB is slow, busy, or temporarily unavailable the write fails and the answer is lost with no buffer or retry mechanism

1.30 WHEN two concurrent `PUT /academic/answers/{question_id}` requests arrive for the same `(student_id, exam_id, question_id)` tuple THEN `StudentAnswerService.upsert()` performs a SELECT followed by a separate INSERT or UPDATE; because there is no database-level `UNIQUE` constraint on `(student_id, exam_id, question_id)` in the `student_answers` table and no `ON CONFLICT DO UPDATE` clause, a race condition between the two requests can produce a duplicate row or a lost write instead of a clean idempotent UPSERT

1.31 WHEN the Kafka consumer worker processes a `GRADE_SUBMISSION_ATTEMPT` event and the handler raises an exception THEN `KafkaConsumerService._handle_message()` in `backend/core/utils/kafka/consumer.py` logs the error and still commits the offset; the event is permanently discarded with no dead-letter topic and no retry, meaning a transient DB failure during grading silently loses the grading job

1.32 WHEN `emit_grade_attempt()` or `emit_refresh_dashboard()` in `backend/tasks/submission.py` is called THEN it uses `asyncio.ensure_future()` to schedule the Kafka publish; if the event loop is not running or the coroutine raises an exception the fire-and-forget call silently drops the event with no error surfaced to the caller

1.33 WHEN the Kafka consumer processes a message and the worker process is killed after the handler completes but before `_commit()` succeeds THEN the message is redelivered on restart; for `GRADE_SUBMISSION_ATTEMPT` there is no idempotency check (e.g. checking whether `attempt.graded_at` is already set) before re-running the grading logic, so the attempt can be graded twice and the score overwritten

**Pillar 2 — High-Fidelity Timing ("Cheating vs. Lag")**

1.34 WHEN an `Exam` record is stored with a naive (timezone-unaware) `start_time` datetime THEN `_update_exam_statuses()` in `backend/tasks/exam.py` silently patches it with `start_time.replace(tzinfo=timezone.utc)` instead of rejecting or flagging the record; this means a naive timestamp that was stored in local time is silently misinterpreted as UTC, causing the exam to open or close at the wrong wall-clock time

1.35 WHEN the `Exam` model is read by the frontend THEN there is no `end_time` field stored on the model; the canonical exam end time (`start_time + duration`) is only computed transiently inside `_update_exam_statuses()` and is never persisted or returned in the API response, so the frontend must compute `end_time` client-side from `start_time` and `duration`, making the displayed countdown manipulable by a student who alters their local clock or intercepts the computation

1.36 WHEN a student submits an exam THEN the `Submission` model in `backend/models/academic/submission.py` has no `submitted_at` timestamp column; the backend cannot authoritatively record the exact UTC moment the student submitted, making it impossible to enforce or audit whether the submission arrived before the exam's `end_time`

1.37 WHEN a student closes their browser during an active exam and the exam time expires THEN the scheduler emits `UPDATE_EXAM_STATUS` (which marks the exam `finished`) but does NOT emit `FORCE_SUBMIT_EXAM`; because the `FORCE_SUBMIT_EXAM` handler does not yet exist (defect 1.24), the student who walked away is never auto-submitted and their answers are silently abandoned with no `Submission` record created

**Pillar 3 — Scalable Infrastructure ("Eight Scale")**

1.38 WHEN `docker-compose.yml` is used to bring up the full stack THEN the `kafka` service definition is entirely commented out; the `worker` and `scheduler` services depend on Kafka to function but there is no Kafka container in the compose file, meaning the worker and scheduler start but immediately fail to connect to any broker, making the entire async task pipeline non-functional in the composed environment

1.39 WHEN `docker-compose.yml` is used to scale the `backend` service THEN the `backend` service has `container_name: wazire-backend` hardcoded; Docker does not allow multiple containers to share the same name, so `docker compose up --scale backend=2` fails, preventing horizontal scaling of the API tier even if it were desired

1.40 WHEN `backend/main.py` is imported by the API process THEN it imports `consumer_service` from `core.utils.kafka` at module level (line: `from core.utils.kafka import producer_service, consumer_service`); `consumer_service` is a `KafkaConsumerService` instance whose `_load_handlers()` method imports from `tasks.*`, which in turn import from `services.*` and `models.*`; although the import is currently lazy (inside `_load_handlers`), the presence of `consumer_service` in `main.py`'s module-level namespace creates a latent circular-import risk and violates the architectural rule that the API process must not import the worker's entry-point dependencies

1.41 WHEN `backend/worker.py` is executed THEN it imports `consumer_service` from `core.utils.kafka` at module level; `KafkaConsumerService._load_handlers()` performs all task imports lazily (inside the method), but if any task module is ever refactored to import from `routes/` or `main.py` at module level the circular import will silently break the worker process; there is currently no enforced import boundary preventing `tasks/` modules from importing `routes/` or `main.py` symbols

1.42 WHEN two or more `worker` container replicas are running and both consume from the same Kafka topic THEN both replicas use the hardcoded `GROUP_ID = "wazire-worker"` in `KafkaConsumerService`; while this is the correct Kafka consumer-group pattern for load-balanced consumption, the `GROUP_ID` is a string literal embedded in `consumer.py` with no configuration override via environment variable, making it impossible to run a second independent consumer group (e.g. for a separate analytics worker) without modifying source code

1.43 WHEN the `worker` service processes a heavy grading task (e.g. `GRADE_SUBMISSION_ATTEMPT` with AI similarity grading via `SimilarityGrader`) THEN the grading runs in the same asyncio event loop as all other Kafka message consumption; there is no task isolation or concurrency limit, so a slow grading job blocks the consumer loop and delays processing of all other event types (e.g. `REFRESH_DASHBOARD`, `UPSERT_STUDENT_ANSWER`) for the duration of the grading call

---

### Expected Behavior (Correct) — Production-Grade Resilience

**Pillar 1 — Zero-Data-Loss ("O-Ring Tightness")**

2.29 WHEN a student submits an answer via the answer endpoint THEN the API handler SHALL produce a Kafka event (e.g. `UPSERT_STUDENT_ANSWER`) immediately and return a fast acknowledgement; the actual PostgreSQL write SHALL be performed by the worker consuming that event, so that a DB slowdown or spike does not cause the answer to be lost — the answer is safely buffered in Kafka until the worker can write it

2.30 WHEN `StudentAnswerService.upsert()` writes to the `student_answers` table THEN the table SHALL have a database-level `UNIQUE` constraint on `(student_id, exam_id, question_id)` and the upsert SHALL use `INSERT ... ON CONFLICT (student_id, exam_id, question_id) DO UPDATE SET answer = EXCLUDED.answer` so that concurrent duplicate requests are handled atomically by the database engine with no race condition and no duplicate rows

2.31 WHEN the Kafka consumer worker fails to process a critical event (e.g. `GRADE_SUBMISSION_ATTEMPT`) THEN the system SHALL NOT silently discard the event after a single failure; the handler SHALL implement at minimum an in-process retry with exponential backoff, and unrecoverable failures SHALL be forwarded to a dead-letter Kafka topic (or equivalent persistent log) so that no grading job is permanently lost

2.32 WHEN `emit_grade_attempt()` or `emit_refresh_dashboard()` publishes a Kafka event THEN it SHALL use `await producer_service.publish_safe(...)` directly (or via `KafkaManager`) rather than `asyncio.ensure_future()`; the caller SHALL be able to observe whether the publish succeeded, and failures SHALL be logged with enough context to allow manual replay

2.33 WHEN the Kafka consumer redelivers a `GRADE_SUBMISSION_ATTEMPT` message after a crash-before-commit scenario THEN the handler SHALL check whether `attempt.graded_at` is already set before re-running grading; if the attempt is already graded the handler SHALL skip re-grading and commit the offset, ensuring idempotent processing with no score overwrite

**Pillar 2 — High-Fidelity Timing ("Cheating vs. Lag")**

2.34 WHEN an `Exam` record is created or updated THEN the API SHALL validate that `start_time` is a UTC-aware datetime (i.e. `tzinfo` is not `None`); records with naive `start_time` values SHALL be rejected at the schema/validation layer with a clear error, and `_update_exam_statuses()` SHALL NOT silently patch naive timestamps — it SHALL log an error and skip the offending exam instead

2.35 WHEN an `Exam` record is created or its `start_time` or `duration` is updated THEN the backend SHALL compute and persist `end_time = start_time + duration` as a UTC-aware `DateTime(timezone=True)` column on the `Exam` model; the API response for exam detail SHALL include `end_time` so the frontend can display a countdown derived from the authoritative backend value rather than computing it client-side

2.36 WHEN a student submits an exam THEN the `Submission` record SHALL include a `submitted_at` column populated with `datetime.now(timezone.utc)` at the moment the submission is received by the backend; this timestamp SHALL be used to determine whether the submission arrived before `exam.end_time` and SHALL be returned in the submission API response for audit purposes

2.37 WHEN a student closes their browser during an active exam and the exam time expires THEN the scheduler's `FORCE_SUBMIT_EXAM` job (defined in requirement 2.24) SHALL auto-create a `Submission` record with `submitted_at = exam.end_time` for that student, ensuring the backend authoritatively records the submission time even for abandoned sessions

**Pillar 3 — Scalable Infrastructure ("Eight Scale")**

2.38 WHEN `docker-compose.yml` is used to bring up the full stack THEN the `kafka` service definition SHALL be uncommented and present as a top-level service with the KRaft-mode configuration already present in the commented block; the `worker` and `scheduler` services SHALL declare `kafka: condition: service_healthy` in their `depends_on` blocks so they do not start before Kafka is ready

2.39 WHEN `docker-compose.yml` defines the `backend` service THEN the `container_name: wazire-backend` field SHALL be removed so that Docker Compose can assign unique names when scaling; services that must remain as single instances (API x1, Redis x1, PostgreSQL x1, Frontend x1, Scheduler x1, Kafka x1) SHALL enforce this via `deploy: replicas: 1` rather than a hardcoded container name

2.40 WHEN `backend/main.py` is imported by the API process THEN it SHALL NOT import `consumer_service` at module level; only `producer_service` (which is actually used in the lifespan) SHALL be imported, enforcing the architectural boundary that the API process does not load worker dependencies

2.41 WHEN `backend/tasks/` modules are authored or refactored THEN they SHALL only import from `models/`, `schemas/`, `services/`, and `core/`; they SHALL NOT import from `routes/`, `main.py`, or `worker.py`; this import boundary SHALL be documented in a module-level comment in each `tasks/` file and enforced by code review so that the worker process can always import task modules without pulling in API-process entry-point code

2.42 WHEN the Kafka consumer group ID needs to be configured for a different deployment (e.g. a separate analytics worker) THEN `KafkaConsumerService.GROUP_ID` SHALL be overridable via an environment variable (e.g. `KAFKA_CONSUMER_GROUP_ID`, defaulting to `"wazire-worker"`), so that multiple independent consumer groups can be deployed without source-code changes

2.43 WHEN the worker processes a heavy grading task THEN the handler SHALL run the CPU/IO-intensive grading work in a way that does not block the consumer event loop for other message types; at minimum, the `GRADE_SUBMISSION_ATTEMPT` handler SHALL be dispatched as a separate `asyncio.Task` (or run in a thread/process pool executor) so that lighter-weight events (e.g. `REFRESH_DASHBOARD`) continue to be processed with low latency during a grading spike

---

### Unchanged Behavior (Regression Prevention) — Production-Grade Resilience

3.26 WHEN `StudentAnswerService.upsert()` is refactored to use `INSERT ... ON CONFLICT DO UPDATE` THEN it SHALL CONTINUE TO return the final `StudentAnswer` row (whether newly inserted or updated) with the same interface expected by callers in `SubmissionService.submit_exam()` and the answer route handler

3.27 WHEN the answer endpoint is changed to produce a Kafka event instead of writing directly to the DB THEN the API response contract (HTTP 200, `{"success": true, "message": "Answer saved", "data": {...}}`) SHALL CONTINUE TO be returned to the frontend; the response data MAY be the optimistic payload rather than the DB-confirmed row, but the status code and shape SHALL remain unchanged

3.28 WHEN the `Exam` model gains an `end_time` column THEN all existing exam API responses that currently return `start_time` and `duration` SHALL CONTINUE TO include those fields unchanged; `end_time` is additive and SHALL NOT replace or remove any existing field

3.29 WHEN the `Submission` model gains a `submitted_at` column THEN all existing submission API responses SHALL CONTINUE TO include the existing fields (`id`, `student_id`, `exam_id`, `latest_score`, `attempts`, `status`, `graded_at`, `created_at`, `updated_at`); `submitted_at` is additive

3.30 WHEN the Kafka service is uncommented in `docker-compose.yml` THEN the existing `postgres`, `redis`, `backend`, `frontend`, `worker`, and `scheduler` service definitions SHALL CONTINUE TO use the same image versions, environment variables, volumes, health checks, and network configuration as currently specified; only the `depends_on` blocks of `worker` and `scheduler` SHALL be extended to include `kafka`

3.31 WHEN `KafkaConsumerService.GROUP_ID` is made configurable via environment variable THEN the default value SHALL remain `"wazire-worker"` so that existing deployments that do not set `KAFKA_CONSUMER_GROUP_ID` continue to consume from the same consumer group without any change in behaviour

3.32 WHEN the `GRADE_SUBMISSION_ATTEMPT` handler is made non-blocking via `asyncio.Task` dispatch THEN the grading logic itself (`SubmissionService.grade_attempt_background()`) SHALL CONTINUE TO function identically; only the dispatch mechanism changes, not the grading algorithm, DB writes, or dashboard refresh events emitted after grading


---

## Full-System Scope & Naming Requirements

This section captures defects identified from a full domain model study of the multi-tenant online exam platform. The system serves Nigerian tertiary institutions and handles: tenant/school management, user roles (student/lecturer/admin/superadmin), semester-based billing (₦2,000/student), course/enrollment/exam/question/answer/submission flows, and OLAP analytics dashboards updated asynchronously via Kafka.

### Current Behavior (Defect) — Model Integrity

1.44 WHEN `Invoice.to_dict()` or `Invoice.__repr__()` is called THEN the system crashes with `AttributeError: 'Invoice' object has no attribute 'status'` because the `Invoice` model in `backend/models/billings/invoice.py` defines an index `ix_invoice_status` on a `status` column and references `self.status.value` in both methods, but no `status` mapped column is declared on the model

1.45 WHEN `BillingPlan.to_dict()` is called THEN the system crashes with `AttributeError: 'BillingPlan' object has no attribute 'is_active'` because the `BillingPlan` model in `backend/models/billings/plan.py` defines an index `ix_billing_plans_is_active` on an `is_active` column and references `self.is_active` in `to_dict()`, but no `is_active` mapped column is declared on the model

1.46 WHEN the `Tenant` model is used in queries or migrations THEN SQLAlchemy raises an error because `backend/models/account/tenant.py` declares indexes `ix_tenants_start_date` and `ix_tenants_end_date` referencing `start_date` and `end_date` columns, but neither column is defined as a mapped column on the `Tenant` model

1.47 WHEN `backend/models/__init__.py` is imported THEN it crashes with `ImportError` on two lines: (a) `from models.account.oauth import OAuth` — the file `backend/models/account/oauth.py` does not exist; (b) `from models.billings.paymentmethod import PaymentMethod, PaymentMethodDetails` — `PaymentMethodDetails` is not defined in `backend/models/billings/paymentmethod.py` (only `PaymentMethod` and `PaymentMethodType` exist there)

1.48 WHEN the `Exam` model is used THEN it contains a `student_id` column (`ForeignKey("account.users.id")`) with a corresponding index `ix_exams_student_id`; exams belong to courses (via `course_id`), not to individual students — student participation is tracked via `Enrollment` and `Submission` records; the `student_id` column on `Exam` is semantically incorrect and pollutes the model with a field that has no valid use case at the exam level

1.49 WHEN two concurrent `UPSERT_STUDENT_ANSWER` worker events arrive for the same `(student_id, exam_id, question_id)` tuple THEN `StudentAnswerService.upsert()` can produce a duplicate row or a lost write because the `student_answers` table in `backend/models/academic/student_answer.py` has no `UNIQUE` constraint on `(student_id, exam_id, question_id)` — only non-unique composite indexes exist — making a true atomic `INSERT ... ON CONFLICT DO UPDATE` impossible at the database level

1.50 WHEN a student submits an exam THEN the `Submission` record has no `submitted_at` column; the backend cannot authoritatively record the exact UTC moment of submission, making it impossible to enforce or audit whether the submission arrived before `exam.end_time` (this defect is also captured as 1.36 in the timing pillar; it is restated here for model-completeness tracking)

1.51 WHEN the frontend or scheduler needs to display or enforce the exam end time THEN the `Exam` model has no `end_time` stored column; `end_time` is only computed transiently inside `_update_exam_statuses()` and is never persisted or returned in the API response (this defect is also captured as 1.35; restated here for model-completeness tracking)

### Current Behavior (Defect) — OLAP/OLTP Separation Violation

1.52 WHEN a user calls `GET /api/v1/analytics/dashboard/` (or any dashboard GET endpoint) THEN the route handler calls `DashboardService.get_or_create_lecturer_dashboard()`, `get_or_create_admin_dashboard()`, or `get_or_create_student_dashboard()`, each of which performs `self.db.add(dashboard)` + `await self.db.commit()` to create a new analytics row if one does not exist; this means a read-only GET request on an OLTP API route directly writes to the `analytics.*` tables, violating the OLAP/OLTP separation rule that all analytics writes must happen exclusively via Kafka-triggered worker tasks

1.53 WHEN `GET /api/v1/analytics/dashboard/stats/tenant` is called THEN `DashboardService.compute_admin_stats()` executes multiple live aggregate queries (`COUNT(*)` joins across `users`, `courses`, `exams`, `submissions`) directly on the OLTP PostgreSQL database in the API request path; these OLAP-style aggregation queries run synchronously during the HTTP request, competing with OLTP writes and increasing latency for all concurrent users

### Current Behavior (Defect) — Route & File Naming Violations

1.54 WHEN the backend route files are inspected THEN the following files use singular nouns instead of the required plural-noun convention: `backend/routes/account/user.py` (should be `users.py`), `backend/routes/account/tenant.py` (should be `tenants.py`), `backend/routes/academic/course.py` (should be `courses.py`), `backend/routes/academic/exam.py` (should be `exams.py`), `backend/routes/academic/question.py` (should be `questions.py`), `backend/routes/academic/answer.py` (should be `answers.py`), `backend/routes/academic/submission.py` (should be `submissions.py`); the corresponding service files in `backend/services/` follow the same singular pattern and must be renamed to match

1.55 WHEN the account and academic API routes are registered in `backend/main.py` THEN the `user` and `tenant` routers are mounted without a domain prefix (`/api/v1/auth` and `/api/v1/tenants`) while academic routes use `/api/v1/academic/{resource}`; there is no `/api/v1/account/` prefix for account-domain routes and no `/api/v1/billing/` prefix for billing routes, making the URL structure inconsistent with the required pattern `/api/v1/{domain}/{resource}` (e.g. `/api/v1/account/users`, `/api/v1/billing/invoices`)

### Current Behavior (Defect) — API Documentation

1.56 WHEN a developer or integration partner needs to test or integrate with the backend API THEN no Postman collection file exists in the repository and no `API.md` documentation file exists; the only partial API documentation is `docs/USER_ROLES_API.md`, which covers only user role endpoints and does not document billing, academic, or analytics routes

### Current Behavior (Defect) — Frontend/Backend Field Mismatches

1.57 WHEN the frontend calls the admin dashboard endpoint and receives a response THEN `DashboardService.get_or_create_admin_dashboard()` constructs `AdminDashboard` with fields `total_graded_submissions` and `total_pending_submissions`, but the `AdminDashboard` model defines those columns as `graded_submissions` and `pending_submissions`; the service passes non-existent keyword arguments to the model constructor, causing a runtime `TypeError` when a new admin dashboard row is created

1.58 WHEN the frontend calls the student dashboard endpoint and receives a response THEN `DashboardService.get_or_create_student_dashboard()` constructs `StudentDashboard` with fields `total_graded_submissions` and `total_pending_submissions`, but the `StudentDashboard` model defines those columns as `graded_submissions` and `pending_submissions`; the service also omits `active_courses` and `completed_courses` from the constructor, leaving those fields at their default values rather than computing them

---

### Expected Behavior (Correct) — Model Integrity

2.44 WHEN `Invoice.to_dict()` or `Invoice.__repr__()` is called THEN the `Invoice` model SHALL define an `InvoiceStatus` enum column named `status` (values: `pending`, `paid`, `overdue`, `cancelled`) with a non-nullable default of `pending`, consistent with the existing index and all references to `self.status.value` in the model

2.45 WHEN `BillingPlan.to_dict()` is called THEN the `BillingPlan` model SHALL define an `is_active` boolean column (default `True`, non-nullable) consistent with the existing index `ix_billing_plans_is_active` and the reference in `to_dict()`

2.46 WHEN the `Tenant` model is used in queries or migrations THEN `start_date` and `end_date` SHALL be defined as `Mapped[Optional[datetime]]` columns with `DateTime(timezone=True)` on the `Tenant` model, consistent with the existing indexes `ix_tenants_start_date` and `ix_tenants_end_date`

2.47 WHEN `backend/models/__init__.py` is imported THEN it SHALL NOT import `OAuth` (no such model exists; the import SHALL be removed) and SHALL NOT import `PaymentMethodDetails` (no such class exists in `paymentmethod.py`; the import SHALL be removed); if an OAuth model is needed in future it SHALL be created first before being imported

2.48 WHEN the `Exam` model is defined THEN the `student_id` column and its index `ix_exams_student_id` SHALL be removed; student participation in an exam SHALL continue to be tracked exclusively via `Enrollment` (student ↔ course ↔ semester) and `Submission` (student ↔ exam) records; the `Exam` model SHALL only carry `course_id`, `tenant_id`, and `semester_id` as foreign-key relationships

2.49 WHEN `StudentAnswerService.upsert()` writes to the `student_answers` table THEN the `StudentAnswer` model SHALL declare a `UniqueConstraint('student_id', 'exam_id', 'question_id', name='uq_student_answer_student_exam_question')` in `__table_args__` so that the database enforces uniqueness at the storage level and an `INSERT ... ON CONFLICT (student_id, exam_id, question_id) DO UPDATE SET answer = EXCLUDED.answer, updated_at = now()` statement can be used for a safe, atomic UPSERT

2.50 WHEN a student submits an exam THEN the `Submission` model SHALL include a `submitted_at` column (`DateTime(timezone=True)`, nullable, default `None`) that is populated with `datetime.now(timezone.utc)` at the moment the submission is received; this field SHALL be returned in all submission API responses (see also requirement 2.36)

2.51 WHEN an `Exam` record is created or its `start_time` or `duration` is updated THEN the `Exam` model SHALL include an `end_time` column (`DateTime(timezone=True)`, nullable) that is computed and persisted as `start_time + timedelta(hours=float(duration))`; the field SHALL be returned in all exam API responses (see also requirement 2.35)

### Expected Behavior (Correct) — OLAP/OLTP Separation

2.52 WHEN a user calls any dashboard GET endpoint THEN the route handler SHALL only read from the `analytics.*` tables (SELECT only); if no dashboard row exists for the user, the handler SHALL return a 404 or an empty-metrics response — it SHALL NOT create a new analytics row inline; dashboard rows SHALL only be created or updated by the Kafka worker when it processes a `REFRESH_DASHBOARD` event

2.53 WHEN `GET /api/v1/analytics/dashboard/stats/tenant` is called THEN the endpoint SHALL read pre-aggregated metrics from the `analytics.admin_dashboard` table (a single SELECT by `tenant_id`) rather than executing live `COUNT(*)` aggregate queries across OLTP tables; the `compute_admin_stats()` method SHALL be moved to the worker and invoked only as part of `REFRESH_DASHBOARD` event handling, so that OLAP aggregation never runs in the API request path

### Expected Behavior (Correct) — Route & File Naming

2.54 WHEN the backend route and service files are named THEN all files SHALL use plural nouns: `users.py`, `tenants.py`, `courses.py`, `exams.py`, `questions.py`, `answers.py`, `submissions.py`, `enrollments.py` (already correct), `invoices.py`, `billing_plans.py`, `payment_methods.py`, `usage.py`, `dashboard.py` (already correct); all corresponding service files SHALL be renamed to match; all imports in `main.py` and elsewhere SHALL be updated to use the new names

2.55 WHEN API routes are registered in `backend/main.py` THEN all routes SHALL follow the pattern `/api/v1/{domain}/{resource}`: account-domain routes SHALL use prefix `/api/v1/account` (e.g. `/api/v1/account/users`, `/api/v1/account/tenants`), academic routes SHALL use `/api/v1/academic` (already partially correct), billing routes SHALL use `/api/v1/billing` (e.g. `/api/v1/billing/invoices`, `/api/v1/billing/semesters`), and analytics routes SHALL use `/api/v1/analytics` (already correct); the current `/api/v1/auth` prefix for user/auth routes SHALL be retained only for authentication endpoints (`/login`, `/register`, `/me`) and the user management endpoints SHALL move to `/api/v1/account/users`

### Expected Behavior (Correct) — API Documentation

2.56 WHEN a developer or integration partner needs to test or integrate with the backend API THEN a Postman collection file (`docs/Wazire.postman_collection.json`) SHALL exist in the repository covering all endpoints across all domains (account, academic, billing, analytics), and an `API.md` file SHALL exist in `docs/` documenting every endpoint with its method, path, required headers, request body schema, and example response; both documents SHALL be kept in sync with the actual route definitions

### Expected Behavior (Correct) — Frontend/Backend Field Alignment

2.57 WHEN `DashboardService.get_or_create_admin_dashboard()` creates a new `AdminDashboard` row THEN it SHALL use the correct model column names `graded_submissions` and `pending_submissions` (not `total_graded_submissions` / `total_pending_submissions`); the constructor call SHALL only pass columns that are defined on the `AdminDashboard` model

2.58 WHEN `DashboardService.get_or_create_student_dashboard()` creates a new `StudentDashboard` row THEN it SHALL use the correct model column names `graded_submissions` and `pending_submissions`, and SHALL also initialise `active_courses=0` and `completed_courses=0` to match all columns defined on the `StudentDashboard` model

---

### Unchanged Behavior (Regression Prevention) — Full-System Scope

3.33 WHEN the `Invoice` model gains a `status` column THEN all existing invoice API responses that currently return `id`, `tenant_id`, `semester_id`, `description`, `student_count`, `amount_per_student`, `total_amount`, `created_at`, and `updated_at` SHALL CONTINUE TO include those fields unchanged; `status` is additive

3.34 WHEN the `BillingPlan` model gains an `is_active` column THEN all existing billing plan API responses SHALL CONTINUE TO include the existing fields (`id`, `tenant_id`, `plan_id`, `name`, `description`, `price_per_student`, `min_students`, `features`); `is_active` is additive

3.35 WHEN the `Tenant` model gains `start_date` and `end_date` columns THEN all existing tenant API responses SHALL CONTINUE TO include the existing fields (`id`, `name`, `domain`, `logo_url`, `is_active`, `is_deleted`, `deleted_at`, `created_at`, `updated_at`); the new date columns are additive

3.36 WHEN `backend/models/__init__.py` is corrected to remove the `OAuth` and `PaymentMethodDetails` imports THEN all other model imports in that file (`User`, `Tenant`, `Invoice`, `CurrentUsage`, `PaymentMethod`, `Course`, `Enrollment`, `Exam`, `Question`, `Answer`, `QuestionExams`, `Submission`, `SubmissionAttempt`, `StudentAnswer`, `LecturerDashboard`, `AdminDashboard`, `StudentDashboard`) SHALL CONTINUE TO be imported and exported in `__all__` without change

3.37 WHEN the `Exam.student_id` column is removed THEN all existing exam API responses that return `course_id`, `tenant_id`, `semester_id`, `title`, `description`, `start_time`, `duration`, `status`, `max_attempts`, `total_marks`, `passing_marks`, `created_at`, and `updated_at` SHALL CONTINUE TO include those fields; only `student_id` is removed from the response shape

3.38 WHEN the `UniqueConstraint` is added to `StudentAnswer(student_id, exam_id, question_id)` THEN the existing composite indexes on `student_answers` (`ix_student_answers_student_exam`, `ix_student_answers_exam_question`, etc.) SHALL CONTINUE TO exist and function; the unique constraint is additive at the database level

3.39 WHEN dashboard GET endpoints are changed to read-only (no inline `get_or_create` writes) THEN the response shape for all dashboard endpoints (`/dashboard/`, `/dashboard/lecturer/{id}`, `/dashboard/admin/{id}`, `/dashboard/student/{id}`) SHALL CONTINUE TO return the same JSON structure as currently defined in `LecturerDashboardRead`, `AdminDashboardRead`, and `StudentDashboardRead` schemas

3.40 WHEN route and service files are renamed to plural nouns THEN all existing endpoint paths that are already correct (e.g. `/api/v1/academic/enrollments`, `/api/v1/analytics/dashboard`) SHALL CONTINUE TO be served at the same URL paths; only the file names and import statements change, not the router `prefix` values for already-correct paths

3.41 WHEN `API.md` and the Postman collection are created THEN no existing source code, model, schema, service, or route file SHALL be modified as a result; the documentation files are purely additive

3.42 WHEN `DashboardService` constructor calls are corrected to use the right column names THEN the `to_dict()` output shape for `AdminDashboard` and `StudentDashboard` SHALL CONTINUE TO use the keys `graded_submissions` and `pending_submissions` as currently defined in the model's `to_dict()` method; no frontend field names change as a result of this fix


---

## Frontend API Alignment Requirements

The following bug conditions document mismatches between the frontend API client code and the backend models, routes, and field names. All frontend API files must call the correct URLs, use the correct HTTP methods, and use TypeScript types that exactly mirror the backend model fields.

### Current Behavior (Defect) — URL Mismatches

1.59 WHEN `frontend/src/apis/auth.ts` calls `listUsers()` THEN it sends a `GET` request to `/auth/` (i.e. `/api/v1/auth/`), but per requirement 2.55 the user management endpoints will be served at `/api/v1/account/users`; the request reaches the wrong route prefix and returns a 404 or incorrect data

1.60 WHEN `frontend/src/apis/auth.ts` calls `getUser(userId)` THEN it sends a `GET` request to `/auth/{userId}` (i.e. `/api/v1/auth/{userId}`), but the correct backend path per requirement 2.55 is `/api/v1/account/users/{userId}`; the request reaches the wrong route and returns a 404

1.61 WHEN `frontend/src/apis/auth.ts` calls `updateUser(userId, payload)` THEN it sends a `PUT` request to `/auth/{userId}`, but the correct backend path is `/api/v1/account/users/{userId}`; the request reaches the wrong route and returns a 404

1.62 WHEN `frontend/src/apis/auth.ts` calls `deleteUser(userId)` THEN it sends a `DELETE` request to `/auth/{userId}`, but the correct backend path is `/api/v1/account/users/{userId}`; the request reaches the wrong route and returns a 404

1.63 WHEN `frontend/src/apis/tenant.ts` calls any tenant function (`createTenant`, `listTenants`, `getTenant`, `updateTenant`, `deleteTenant`, `getTenantUsers`, `getTenantStats`) THEN it sends requests to `/tenants/` and `/tenants/{id}`, but the correct backend path per requirement 2.55 is `/api/v1/account/tenants/` and `/api/v1/account/tenants/{id}`; all tenant requests reach the wrong route prefix and return 404s

1.64 WHEN `frontend/src/apis/enrollment.ts` calls any enrollment function (`listEnrollment`, `getEnrollment`, `enrollStudent`, `updateEnrollment`, `removeEnrollment`, `bulkEnroll`, `checkEnrollment`) THEN it sends requests to `/academic/enrollment/` (singular), but the correct backend path is `/academic/enrollments/` (plural, per requirement 2.54); all enrollment requests return 404s

1.65 WHEN `frontend/src/apis/answer.ts` calls `upsertAnswer(questionId, payload)` THEN it uses `client.put(...)` (HTTP PUT), but per requirement 2.22 the answer upsert endpoint must be called with HTTP PATCH; the backend route handler for PATCH and PUT may differ, causing the answer to be rejected or routed incorrectly

1.66 WHEN `frontend/src/apis/auth.ts` calls `getAdminStats()` THEN it sends a `GET` request to `/auth/admin/stats`; this endpoint does not exist on the backend — admin statistics are served from the analytics dashboard at `/analytics/dashboard/admin/{tenantId}` (per the `AdminDashboard` model); the call returns a 404 and the function silently returns zeroed-out stats

1.67 WHEN `frontend/src/apis/dashboard.ts` calls `getAdminDashboard(adminId)` THEN it sends a `GET` request to `/analytics/dashboard/admin/{adminId}` where `adminId` is a user ID; but the `AdminDashboard` model is keyed by `tenant_id` (one dashboard per tenant, not per admin user), so passing an admin user ID returns a 404 or the wrong record

### Current Behavior (Defect) — TypeScript Type Mismatches

1.68 WHEN the backend returns a `Submission` object THEN the frontend `Submission` type in `frontend/src/lib/types.ts` uses the field name `attempts_count`, but the backend `Submission` model column is named `attempts`; the frontend reads `undefined` for the attempt count on every submission response

1.69 WHEN the backend returns a `Submission` object THEN the frontend `Submission` type has no `submitted_at` field, but per requirement 2.50 the backend `Submission` model will include a `submitted_at` column; the frontend cannot display or use the authoritative submission timestamp

1.70 WHEN the backend returns a `SubmissionAttempt` object THEN the frontend `SubmissionAttempt` type declares `attempt_number: number` and `scan_pages: string[]`, but the backend `SubmissionAttempt` model has neither column (the model only has `id`, `submission_id`, `score`, `created_at`); the frontend type references fields that do not exist on the backend model, causing silent `undefined` values

1.71 WHEN the backend returns an `AdminDashboard` object THEN the frontend `AdminDashboard` type uses `total_graded_submissions` and `total_pending_submissions`, but the backend `AdminDashboard` model columns are named `graded_submissions` and `pending_submissions`; the frontend reads `undefined` for both submission metric fields

1.72 WHEN the backend returns a `StudentDashboard` object THEN the frontend `StudentDashboard` type uses `total_graded_submissions` and `total_pending_submissions`, but the backend `StudentDashboard` model columns are named `graded_submissions` and `pending_submissions`; additionally the frontend type is missing `active_courses`, `completed_courses`, and `average_score` fields that exist on the backend model, so those metrics are never surfaced in the UI

1.73 WHEN the backend returns an `Exam` object THEN the frontend `Exam` type declares `course: Course | null` and `lecturer: User | null` as nested objects, but the backend `Exam` model only stores `course_id` as a UUID foreign key and has no `lecturer_id` column at all; the frontend type assumes eager-loaded nested objects that the backend does not return, causing the frontend to read `undefined` for `exam.course` and `exam.lecturer`

1.74 WHEN the backend returns an `Enrollment` object THEN the frontend `Enrollment` type declares `student: User` and `course: Course` as nested objects, but the backend `Enrollment` model only stores `student_id` and `course_id` as UUID foreign keys; the frontend type assumes eager-loaded nested objects that the backend does not return

1.75 WHEN the backend returns an `Enrollment` object THEN the frontend `Enrollment` type declares `semester: 'fall' | 'spring' | 'summer'` as a string enum field, but the backend `Enrollment` model stores `semester_id` as a UUID foreign key to the `billings.semesters` table; there is no `semester` string field on the backend model, and the `SemesterType` enum values are `'first' | 'second' | 'third'` — not `'fall' | 'spring' | 'summer'`

1.76 WHEN the backend returns a `Tenant` object THEN the frontend `Tenant` type is missing the fields `domain`, `is_active`, `is_deleted`, and `deleted_at` that are defined on the backend `Tenant` model; the frontend cannot read or display these fields even though the backend always returns them

1.77 WHEN the backend returns an `Invoice` object THEN the frontend `Invoice` type declares `tenant: Tenant | null` as a nested object, but the backend `Invoice` model only stores `tenant_id` as a UUID foreign key; additionally the frontend `InvoiceStatus` type includes `'failed'` and `'refunded'` but per requirement 2.44 the backend `InvoiceStatus` enum values are `'pending'`, `'paid'`, `'overdue'`, and `'cancelled'`; the frontend type uses two status values that do not exist on the backend

1.78 WHEN the backend returns a `CurrentUsage` object THEN the frontend `CurrentUsage` type declares `exams_graded` and `plan: PlanType` as fields, but the backend `CurrentUsage` model has no `exams_graded` column and `current_plan` is a UUID foreign key (not a `PlanType` string); additionally the frontend `PlanType` type is `'starter' | 'intermediate' | 'enterprise'` but the backend `BillingPlan` model uses `plan_id = 'standard'` as the only plan identifier; the frontend type references a field that does not exist and uses plan type values that do not match the backend

1.79 WHEN the backend returns an `Exam` object THEN the frontend `Exam` type has no `end_time` field, but per requirement 2.51 the backend `Exam` model will include a persisted `end_time` column; the frontend cannot use the authoritative backend-computed end time and must compute it client-side instead

1.80 WHEN the frontend `Question` type is used THEN it declares `exams: {id: string}[]` as a field, implying the backend question endpoint returns a list of associated exam IDs; the backend `Question` model has no such field — exam-question associations are stored in a `QuestionExams` join table and are not returned by default on question list/detail endpoints; the frontend type assumes data that is not present in standard API responses

### Current Behavior (Defect) — Missing API Modules

1.81 WHEN the frontend needs to display or manage invoices, billing plans, payment methods, semesters, or current usage THEN no `frontend/src/apis/billing.ts` module exists; all billing-related API calls are absent, making the billing UI non-functional and forcing any billing page to either crash or use hardcoded mock data

1.82 WHEN the frontend needs to display or manage semester records THEN no `frontend/src/apis/semester.ts` module exists; semester management (listing, creating, activating semesters) has no corresponding API client, making semester-related features non-functional

### Current Behavior (Defect) — Field Name Mismatches in Request Payloads

1.83 WHEN `frontend/src/apis/exam.ts` sends a `QuestionCreate` payload to the backend THEN it uses the field name `question_text`, but the backend `Question` model column is named `text`; the backend receives `question_text` as an unknown field and `text` as missing, causing a validation error or silent data loss

1.84 WHEN `frontend/src/apis/exam.ts` sends a `QuestionCreate` payload to the backend THEN it uses the field name `question_type`, but the backend `Question` model column is named `qtype`; the backend receives `question_type` as an unknown field and `qtype` as missing, causing a validation error

1.85 WHEN `frontend/src/apis/exam.ts` sends a `QuestionCreate` payload to the backend THEN it uses the field name `marks`, but the backend `Question` model column is named `mark` (singular); the backend receives `marks` as an unknown field and `mark` as missing, causing a validation error

1.86 WHEN `frontend/src/apis/exam.ts` calls `listQuestions(examId, params)` THEN it ignores the `examId` parameter and sends a `GET` request to `/academic/questions` without an `exam_id` filter; the backend returns all questions across all exams instead of only the questions for the specified exam, causing the wrong question set to be displayed

---

### Expected Behavior (Correct) — URL Mismatches

2.59 WHEN `frontend/src/apis/auth.ts` calls `listUsers()` THEN it SHALL send a `GET` request to `/account/users/` (resolving to `/api/v1/account/users/`) matching the backend route prefix defined in requirement 2.55

2.60 WHEN `frontend/src/apis/auth.ts` calls `getUser(userId)` THEN it SHALL send a `GET` request to `/account/users/{userId}` matching the backend route

2.61 WHEN `frontend/src/apis/auth.ts` calls `updateUser(userId, payload)` THEN it SHALL send a `PUT` request to `/account/users/{userId}` matching the backend route

2.62 WHEN `frontend/src/apis/auth.ts` calls `deleteUser(userId)` THEN it SHALL send a `DELETE` request to `/account/users/{userId}` matching the backend route

2.63 WHEN `frontend/src/apis/tenant.ts` calls any tenant function THEN it SHALL send requests to `/account/tenants/` and `/account/tenants/{id}` (resolving to `/api/v1/account/tenants/` and `/api/v1/account/tenants/{id}`) matching the backend route prefix defined in requirement 2.55

2.64 WHEN `frontend/src/apis/enrollment.ts` calls any enrollment function THEN it SHALL send requests to `/academic/enrollments/` (plural) matching the backend route name defined in requirement 2.54

2.65 WHEN `frontend/src/apis/answer.ts` calls `upsertAnswer(questionId, payload)` THEN it SHALL use `client.patch(...)` (HTTP PATCH) instead of `client.put(...)`, matching the architecture requirement defined in requirement 2.22

2.66 WHEN the frontend needs admin statistics THEN `getAdminStats()` in `frontend/src/apis/auth.ts` SHALL be removed or replaced with a call to `getAdminDashboard(tenantId)` in `frontend/src/apis/dashboard.ts`, which reads from the correct `/analytics/dashboard/admin/{tenantId}` endpoint

2.67 WHEN `frontend/src/apis/dashboard.ts` calls `getAdminDashboard(tenantId)` THEN the parameter SHALL be a `tenantId` (UUID of the tenant), not an `adminId` (UUID of a user), matching the `AdminDashboard` model which is keyed by `tenant_id`

---

### Expected Behavior (Correct) — TypeScript Type Mismatches

2.68 WHEN the frontend `Submission` type is defined THEN it SHALL use `attempts: number` (not `attempts_count`) to match the backend `Submission` model column name

2.69 WHEN the frontend `Submission` type is defined THEN it SHALL include `submitted_at: string | null` to match the `submitted_at` column being added to the backend `Submission` model per requirement 2.50

2.70 WHEN the frontend `SubmissionAttempt` type is defined THEN it SHALL only declare fields that exist on the backend `SubmissionAttempt` model: `id: number`, `submission_id: string`, `score: string | null`, `created_at: string`; the fields `attempt_number` and `scan_pages` SHALL be removed from the type

2.71 WHEN the frontend `AdminDashboard` type is defined THEN it SHALL use `graded_submissions: number` and `pending_submissions: number` (not `total_graded_submissions` / `total_pending_submissions`) to match the backend `AdminDashboard` model column names; it SHALL also replace `admin_id` with `tenant_id` to match the model's actual primary key relationship

2.72 WHEN the frontend `StudentDashboard` type is defined THEN it SHALL use `graded_submissions: number` and `pending_submissions: number` (not `total_graded_submissions` / `total_pending_submissions`), and SHALL add the missing fields `active_courses: number`, `completed_courses: number`, and `average_score: number | null` to match all columns on the backend `StudentDashboard` model

2.73 WHEN the frontend `Exam` type is defined THEN `course: Course | null` SHALL be replaced with `course_id: string | null` and `lecturer: User | null` SHALL be removed entirely, since the backend `Exam` model stores only `course_id` as a FK and has no `lecturer_id` column; if the frontend needs enriched course data it SHALL fetch it separately

2.74 WHEN the frontend `Enrollment` type is defined THEN `student: User` SHALL be replaced with `student_id: string` and `course: Course` SHALL be replaced with `course_id: string`, since the backend `Enrollment` model stores only FK IDs; if the frontend needs enriched user or course data it SHALL fetch it separately

2.75 WHEN the frontend `Enrollment` type is defined THEN the `semester` field typed as `'fall' | 'spring' | 'summer'` SHALL be replaced with `semester_id: string | null` (a UUID FK to the `billings.semesters` table), and the `EnrollmentCreate` payload in `enrollment.ts` SHALL send `semester_id: string` instead of `semester: Semester`; the `Semester` type alias SHALL be updated to `'first' | 'second' | 'third'` to match the backend `SemesterType` enum if a semester label is needed for display purposes

2.76 WHEN the frontend `Tenant` type is defined THEN it SHALL include the missing fields `domain: string | null`, `is_active: boolean`, `is_deleted: boolean`, and `deleted_at: string | null` to match all columns on the backend `Tenant` model

2.77 WHEN the frontend `Invoice` type is defined THEN `tenant: Tenant | null` SHALL be replaced with `tenant_id: string` (a UUID FK), and the `InvoiceStatus` type SHALL be updated to `'pending' | 'paid' | 'overdue' | 'cancelled'` to match the backend `InvoiceStatus` enum values defined in requirement 2.44

2.78 WHEN the frontend `CurrentUsage` type is defined THEN `exams_graded` SHALL be removed (no such column on the backend model), `plan: PlanType` SHALL be replaced with `current_plan: string | null` (a UUID FK to `billing_plans`), and `tenant: Tenant | null` SHALL be replaced with `tenant_id: string`; the `PlanType` type alias SHALL be updated to `'standard'` (the only plan identifier used by the backend `BillingPlan` model)

2.79 WHEN the frontend `Exam` type is defined THEN it SHALL include `end_time: string | null` to match the `end_time` column being added to the backend `Exam` model per requirement 2.51

2.80 WHEN the frontend `Question` type is defined THEN the `exams: {id: string}[]` field SHALL be marked as optional (`exams?: {id: string}[]`) and documented as a non-default enrichment field that is only present when the backend explicitly joins the `QuestionExams` table; standard question list and detail responses SHALL NOT be expected to include this field

---

### Expected Behavior (Correct) — Missing API Modules

2.81 WHEN the frontend needs to interact with billing resources THEN a `frontend/src/apis/billing.ts` module SHALL exist and SHALL export typed functions for: listing and getting invoices (`GET /billing/invoices/`, `GET /billing/invoices/{id}`), listing and getting billing plans (`GET /billing/billing_plans/`, `GET /billing/billing_plans/{id}`), listing and getting payment methods (`GET /billing/payment_methods/`), and getting current usage (`GET /billing/usage/`); all functions SHALL use the correct `/api/v1/billing/` prefix per requirement 2.55

2.82 WHEN the frontend needs to interact with semester resources THEN a `frontend/src/apis/semester.ts` module SHALL exist and SHALL export typed functions for: listing semesters (`GET /billing/semesters/`), getting a semester by ID (`GET /billing/semesters/{id}`), creating a semester (`POST /billing/semesters/`), and updating a semester (`PUT /billing/semesters/{id}`); all functions SHALL use the correct `/api/v1/billing/semesters` prefix per requirement 2.55

---

### Expected Behavior (Correct) — Field Name Mismatches in Request Payloads

2.83 WHEN `frontend/src/apis/exam.ts` sends a `QuestionCreate` payload THEN the field `question_text` SHALL be renamed to `text` to match the backend `Question` model column name

2.84 WHEN `frontend/src/apis/exam.ts` sends a `QuestionCreate` payload THEN the field `question_type` SHALL be renamed to `qtype` to match the backend `Question` model column name

2.85 WHEN `frontend/src/apis/exam.ts` sends a `QuestionCreate` payload THEN the field `marks` SHALL be renamed to `mark` (singular) to match the backend `Question` model column name

2.86 WHEN `frontend/src/apis/exam.ts` calls `listQuestions(examId, params)` THEN it SHALL include `exam_id: examId` in the query parameters sent to `/academic/questions/`, so the backend filters and returns only the questions associated with the specified exam

---

### Unchanged Behavior (Regression Prevention) — Frontend API Alignment

3.43 WHEN `frontend/src/apis/auth.ts` URL paths for `listUsers`, `getUser`, `updateUser`, and `deleteUser` are corrected to `/account/users/` THEN the `login`, `register`, `refresh`, `me`, and `updateMe` functions SHALL CONTINUE TO call `/auth/login`, `/auth/register`, `/auth/refresh`, `/auth/me`, and `/auth/me` respectively — only the user management paths change, not the authentication paths

3.44 WHEN `frontend/src/apis/enrollment.ts` URL paths are corrected from `/academic/enrollment/` to `/academic/enrollments/` THEN all existing function signatures (`listEnrollment`, `getEnrollment`, `enrollStudent`, `updateEnrollment`, `removeEnrollment`, `bulkEnroll`, `checkEnrollment`) SHALL CONTINUE TO accept the same parameters and return the same response types; only the URL string changes

3.45 WHEN `frontend/src/apis/answer.ts` `upsertAnswer` is changed from `client.put` to `client.patch` THEN the function signature, parameters, and return type SHALL CONTINUE TO be identical; only the HTTP method changes

3.46 WHEN the frontend `Submission` type field is renamed from `attempts_count` to `attempts` THEN all components and hooks that currently read `submission.attempts_count` SHALL be updated to read `submission.attempts` so that no component is left referencing the old field name

3.47 WHEN the frontend `SubmissionAttempt` type is corrected to remove `attempt_number` and `scan_pages` THEN any component that currently reads `attempt.attempt_number` or `attempt.scan_pages` SHALL be updated to use `attempt.id` (the auto-incrementing integer that serves as the attempt number) and to remove references to `scan_pages` respectively

3.48 WHEN the frontend `AdminDashboard` type fields are renamed from `total_graded_submissions`/`total_pending_submissions` to `graded_submissions`/`pending_submissions` THEN all components that render admin dashboard metrics SHALL be updated to use the new field names so that no component reads `undefined`

3.49 WHEN the frontend `StudentDashboard` type fields are renamed from `total_graded_submissions`/`total_pending_submissions` to `graded_submissions`/`pending_submissions` THEN all components that render student dashboard metrics SHALL be updated to use the new field names

3.50 WHEN the frontend `Exam` type is changed to replace `course: Course | null` with `course_id: string | null` THEN all components that currently access `exam.course.name` or `exam.course.course_code` SHALL be updated to fetch course data separately or use a pre-enriched response shape; no component SHALL be left dereferencing `exam.course` as a nested object

3.51 WHEN the frontend `Enrollment` type is changed to replace `student: User` and `course: Course` with `student_id: string` and `course_id: string` THEN all components that currently access `enrollment.student.first_name` or `enrollment.course.name` SHALL be updated to fetch user and course data separately; no component SHALL be left dereferencing nested objects that no longer exist on the type

3.52 WHEN the frontend `Tenant` type gains `domain`, `is_active`, `is_deleted`, and `deleted_at` fields THEN all existing components that render tenant data using `tenant.name`, `tenant.logo_url`, `tenant.created_at`, and `tenant.updated_at` SHALL CONTINUE TO work without modification; the new fields are additive

3.53 WHEN the frontend `Invoice` type `InvoiceStatus` is updated to `'pending' | 'paid' | 'overdue' | 'cancelled'` THEN any component that currently renders a badge or label for `'failed'` or `'refunded'` invoice statuses SHALL be updated to handle the correct status values; no component SHALL be left with unreachable branches for the removed status values

3.54 WHEN `frontend/src/apis/exam.ts` `QuestionCreate` field names are corrected (`question_text` → `text`, `question_type` → `qtype`, `marks` → `mark`) THEN the `QuestionUpdate` interface SHALL also be updated with the same field name corrections so that update payloads are consistent with create payloads

3.55 WHEN `frontend/src/apis/exam.ts` `listQuestions` is corrected to pass `exam_id` as a query parameter THEN the function signature SHALL CONTINUE TO accept `examId: string` as its first parameter and `params?: QuestionListParams` as its second; only the internal request construction changes to include `exam_id: examId` in the params object


---

## Test Coverage & CI/CD Requirements

The following bug conditions document the complete absence of automated test infrastructure, coverage measurement, and CI/CD pipeline integration across the backend and frontend.

### Current Behavior (Defect) — Test Coverage & CI/CD

1.87 WHEN the backend codebase is inspected THEN no test files exist anywhere in the backend — there is no `tests/` directory, no `test_*.py` files, and no `*_test.py` files; the backend has zero automated test coverage

1.88 WHEN the frontend codebase is inspected THEN no test files exist in the frontend — there are no `*.test.ts`, `*.test.tsx`, `*.spec.ts`, or `*.spec.tsx` files beyond any stubs; the frontend has zero automated test coverage

1.89 WHEN `backend/requirements.txt` is inspected THEN `pytest-cov` is not listed as a dependency; line and branch coverage cannot be measured for the backend even if tests were added

1.90 WHEN `frontend/package.json` devDependencies are inspected THEN `@vitest/coverage-v8` is not listed; line and branch coverage cannot be measured for the frontend even if tests were added

1.91 WHEN the repository root is inspected THEN no GitHub Actions workflow files exist under `.github/workflows/`; there is no CI pipeline that runs on push or pull request events, meaning no automated checks gate merges to `main` or `develop`

1.92 WHEN a pull request is opened against `main` or `develop` THEN no Codecov (or equivalent) configuration file (e.g. `.codecov.yml`) exists and no coverage upload step is configured; coverage results are never posted as a PR comment and are invisible to reviewers

1.93 WHEN the repository `README.md` is inspected THEN no coverage badge is present; there is no visual indicator of the current overall coverage percentage for the project

1.94 WHEN a test file is authored for a backend task THEN there is no documented or enforced rule preventing it from importing directly from `main.py` or `worker.py`; test files could inadvertently pull in API-process or worker-process entry-point dependencies, violating the import boundary established in requirement 2.41

---

### Expected Behavior (Correct) — Test Coverage & CI/CD

2.87 WHEN backend Python files are tested THEN every backend Python file SHALL achieve ≥ 90% line coverage and ≥ 90% branch coverage as measured by `pytest` with `pytest-cov`; `pytest-cov` SHALL be added to `backend/requirements.txt` and coverage SHALL be configured via `pyproject.toml` or `setup.cfg` with `--cov=.` and `--cov-branch` flags

2.88 WHEN frontend TypeScript/TSX files are tested THEN every frontend TypeScript and TSX file SHALL achieve ≥ 90% line coverage and ≥ 90% branch coverage as measured by Vitest with `@vitest/coverage-v8`; `@vitest/coverage-v8` SHALL be added to `frontend/package.json` devDependencies and a `vitest.config.ts` SHALL configure `coverage.provider = 'v8'` with `coverage.thresholds` set to `lines: 90, branches: 90`

2.89 WHEN code is pushed to any branch or a pull request is opened against `main` or `develop` THEN a GitHub Actions CI pipeline SHALL run automatically; the pipeline SHALL be defined in `.github/workflows/ci.yml` and SHALL trigger on `push` (all branches) and `pull_request` (targeting `main` and `develop`)

2.90 WHEN the CI pipeline completes a test run THEN coverage reports SHALL be uploaded to Codecov (or an equivalent service) using the official Codecov GitHub Action; the upload SHALL include both backend and frontend coverage reports so that per-file coverage is visible on GitHub pull requests as an automated comment

2.91 WHEN the repository README is viewed THEN a Codecov (or equivalent) coverage badge SHALL appear near the top of the file, displaying the current overall coverage percentage and linking to the full coverage report; the badge SHALL update automatically after each CI run

2.92 WHEN the CI pipeline evaluates overall coverage THEN it SHALL fail (exit non-zero, blocking merge) if the overall combined coverage drops below 90%; the backend CI step SHALL use `pytest --cov --cov-fail-under=90` and the frontend CI step SHALL use `vitest --run --coverage` with `coverage.thresholds` enforced in `vitest.config.ts`

2.93 WHEN the CI pipeline runs THEN it SHALL execute steps in the following strict order: (a) lint, (b) type-check, (c) tests with coverage, (d) coverage upload; a failure in any earlier step SHALL prevent subsequent steps from running; specifically: backend SHALL run `ruff` (or `flake8`) lint → `mypy` type check → `pytest` with coverage; frontend SHALL run `eslint` → `tsc --noEmit` type check → `vitest --run` with coverage

2.94 WHEN test files are authored for backend tasks or services THEN they SHALL NOT import from `main.py` or `worker.py` directly; test files SHALL only import from `models/`, `schemas/`, `services/`, `core/`, and `tasks/` modules, enforcing the import boundary established in requirement 2.41; test files SHALL be placed either co-located with the module under test or in a dedicated `backend/tests/` directory — not scattered across unrelated directories

---

### Unchanged Behavior (Regression Prevention) — Test Coverage & CI/CD

3.56 WHEN `pytest-cov` is added to `backend/requirements.txt` THEN all existing backend dependencies (`fastapi`, `sqlalchemy`, `asyncpg`, `pydantic`, `redis`, `aiokafka`, etc.) SHALL CONTINUE TO be listed at their current pinned versions without modification; `pytest-cov` is additive

3.57 WHEN `@vitest/coverage-v8` is added to `frontend/package.json` devDependencies THEN all existing devDependencies (`vite`, `typescript`, `eslint`, `@vitejs/plugin-react`, etc.) SHALL CONTINUE TO be listed at their current versions without modification; the new package is additive

3.58 WHEN the GitHub Actions CI pipeline is introduced THEN no existing source code, model, schema, service, route, or configuration file SHALL be modified as a result of adding the workflow YAML; the CI pipeline is purely additive infrastructure

3.59 WHEN the Codecov badge is added to the README THEN all existing README content (project description, setup instructions, Docker usage, environment variable documentation) SHALL CONTINUE TO appear unchanged below the badge; the badge is prepended, not a replacement

3.60 WHEN the CI pipeline enforces the ≥ 90% coverage threshold THEN the threshold SHALL apply to the overall project coverage aggregate; individual utility or configuration files that are genuinely untestable (e.g. `alembic/env.py`, `seed_db.py`) MAY be excluded from coverage measurement via `.coveragerc` or `vitest.config.ts` `coverage.exclude` patterns without lowering the threshold for the remaining testable code


---

### Test Types — Full Coverage Strategy

#### Current Behavior (Defect) — Missing Test Types

1.95 WHEN the backend codebase is inspected THEN no unit tests exist for any service class method — `CourseService`, `ExamService`, `QuestionService`, `EnrollmentService`, `SubmissionService`, `StudentAnswerService`, `UserService`, `TenantService`, `DashboardService`, and all engine services (`AnswerGrader`, `SimilarityGrader`, etc.) have zero unit test coverage; all service logic is untested in isolation

1.96 WHEN the backend codebase is inspected THEN no unit tests exist for any Kafka task handler — the event handlers for `GRADE_SUBMISSION_ATTEMPT`, `REFRESH_DASHBOARD`, `PRELOAD_QUESTIONS`, `UPSERT_STUDENT_ANSWER`, `FORCE_SUBMIT_EXAM`, `DETECT_ANSWER`, `PARSE_AND_CREATE`, `SEND_EMAIL`, and `UPDATE_EXAM_STATUS` in `backend/tasks/` have zero unit test coverage; task dispatch and handler logic is entirely untested

1.97 WHEN the backend codebase is inspected THEN no unit tests exist for any model method — `to_dict()`, `delete()`, `restore()`, and `lock()` on `User`, `Tenant`, and other models are untested; no unit tests exist for any utility function in `backend/core/utils/` (encryption, token generation, response helpers, sanitization, validation); `KafkaManager.emit()` and the worker dispatcher's handler registration and dispatch logic are also untested

1.98 WHEN the backend codebase is inspected THEN no integration tests exist for any API route — no test exercises the full request → middleware → route handler → service → DB → response stack for any endpoint across auth, account, academic, billing, or analytics domains; the complete absence of integration tests means no route contract is verified end-to-end

1.99 WHEN the backend codebase is inspected THEN no end-to-end scenario tests exist for any multi-step user journey — the full exam lifecycle (tenant creation → user creation → course → enrollment → exam → questions → Redis preload → student answers via Kafka → submission → grading → dashboard update), the force-submit flow (exam expiry → scheduler → worker auto-submission → grading), and concurrent UPSERT idempotency (100 concurrent PATCH answer requests → single DB row) are all untested

1.100 WHEN the frontend codebase is inspected THEN no unit tests exist for any API function in `apis/*.ts`, any utility function in `utils/*.ts`, or any shared component (Button, Input, Modal, Table, Pagination, etc.); `AuthContext` login, logout, register, and token storage logic are also untested; no MSW (Mock Service Worker) setup exists to intercept API calls in tests

1.101 WHEN the frontend codebase is inspected THEN no integration tests exist for any page component with mocked API responses — Login, Dashboard, Courses, Exams, TakeExam, and UserManagement pages are untested with MSW; no Playwright E2E tests exist for any critical user path (student taking an exam, lecturer creating a course/exam, admin managing users)

---

#### Expected Behavior (Correct) — Missing Test Types

2.95 WHEN backend unit tests are authored THEN every public method on every service class SHALL have at least one unit test using `pytest` and `pytest-asyncio` with mocked DB session, Redis client, and Kafka producer; tests SHALL cover the happy path and at least one error/edge-case path per method; test files SHALL be placed in `backend/tests/unit/services/` mirroring the service module structure

2.96 WHEN backend unit tests are authored THEN every Kafka task handler in `backend/tasks/` SHALL have at least one unit test that invokes the handler directly with a mock event payload and asserts the expected service calls and Kafka emissions; the `KafkaManager.emit()` method SHALL be tested with a mocked producer asserting correct topic and payload; the worker dispatcher SHALL be tested to verify handler registration and correct dispatch by event type

2.97 WHEN backend unit tests are authored THEN every model method (`to_dict()`, `delete()`, `restore()`, `lock()`) on `User`, `Tenant`, and other models SHALL have unit tests asserting correct output shape and side effects; every utility function in `backend/core/utils/` (encryption, token generation, response helpers, sanitization, validation) SHALL have unit tests covering normal inputs, boundary values, and invalid inputs

2.98 WHEN backend integration tests are authored THEN every API route SHALL be tested end-to-end using `pytest-asyncio` with `httpx.AsyncClient` against a real test PostgreSQL database (separate from production); the following flows SHALL each have at least one integration test: auth (register, login, refresh, me, update profile), course CRUD, exam CRUD and status transitions, question CRUD and exam assignment, enrollment (enroll, list, update status, bulk enroll), answer PATCH (verifying Kafka event produced with mocked Kafka), submission (create, submit, get my submission), dashboard GET (returns pre-aggregated data with no inline writes), and billing (invoices, plans, payment methods, usage, semesters)

2.99 WHEN backend end-to-end scenario tests are authored THEN the following three scenarios SHALL each be implemented as a single `pytest-asyncio` test using the full application stack: Scenario 1 — full exam lifecycle (create tenant → create users → create course → enroll student → create exam → add questions → scheduler preloads questions to Redis → student starts exam → student answers questions via PATCH → Kafka → worker UPSERT → student submits → worker grades → dashboard updated); Scenario 2 — force submit (exam time expires → scheduler emits `FORCE_SUBMIT_EXAM` → worker auto-submits unsubmitted students → grading triggered); Scenario 3 — concurrent answer UPSERT idempotency (100 concurrent PATCH answer requests for the same `(student, exam, question)` → assert exactly one row in `student_answers` table)

2.100 WHEN frontend unit tests are authored THEN every API function in `apis/*.ts` SHALL have a Vitest unit test asserting the correct URL, HTTP method, request payload shape, and response parsing; every utility function in `utils/*.ts` SHALL have unit tests; every shared component SHALL have a `@testing-library/react` render test asserting correct output with representative props; `AuthContext` login, logout, register, and token storage SHALL each have unit tests; an MSW (`msw`) setup file SHALL be created at `frontend/src/mocks/` with handlers for all backend API endpoints so that tests can intercept and mock API calls without real network requests

2.101 WHEN frontend integration and E2E tests are authored THEN every page component (Login, Dashboard, Courses, Exams, TakeExam, UserManagement) SHALL have a Vitest + MSW integration test covering: form submission triggering the correct API call, correct rendering of mocked API responses, and navigation/redirect behaviour; Playwright E2E tests SHALL cover three critical paths: (a) student login → navigate to exam → take exam → submit → see result, (b) lecturer login → create course → create exam → add questions → publish, (c) admin login → manage users → view dashboard; Playwright config SHALL target the repository at `https://github.com/oscaroguledo/wazire` and the CI workflow SHALL run Playwright tests in the `playwright` job after the frontend unit/integration job completes

---

#### Unchanged Behavior (Regression Prevention) — Missing Test Types

3.61 WHEN backend unit tests are added under `backend/tests/unit/` THEN all existing backend source files in `models/`, `schemas/`, `services/`, `routes/`, `core/`, and `tasks/` SHALL CONTINUE TO be importable without modification; test files are purely additive and SHALL NOT alter any production module's public interface or behaviour

3.62 WHEN backend integration tests use a dedicated test PostgreSQL database THEN the production `DATABASE_URL` environment variable SHALL CONTINUE TO point to the production/staging database; integration tests SHALL use a separate `TEST_DATABASE_URL` (or equivalent) configured only in the CI environment and in local `.env.test` files, ensuring production data is never touched by test runs

3.63 WHEN MSW is added to the frontend test setup THEN the production `frontend/src/apis/client.ts` Axios instance and all `apis/*.ts` modules SHALL CONTINUE TO function identically in the browser runtime; MSW intercepts requests only in the Node.js test environment (via `msw/node` server) and does not affect the production build or browser behaviour

3.64 WHEN Playwright E2E tests are added under `frontend/e2e/` (or `tests/e2e/`) THEN the existing Vitest unit and integration test configuration in `vitest.config.ts` SHALL CONTINUE TO be used exclusively for unit and integration tests; Playwright SHALL use its own `playwright.config.ts` and SHALL NOT interfere with the Vitest test run or coverage collection

3.65 WHEN the CI workflow is extended to include backend unit, integration, and E2E test jobs and frontend unit, integration, and Playwright E2E jobs THEN the Codecov upload step SHALL aggregate coverage from all jobs (backend `pytest-cov` XML report + frontend Vitest `coverage-v8` JSON/lcov report) into a single combined report uploaded to `https://codecov.io/gh/oscaroguledo/wazire` using the `CODECOV_TOKEN` secret stored in the `oscaroguledo/wazire` repository settings; the overall ≥ 90% threshold defined in requirement 2.92 SHALL apply to the combined aggregate


---

## Onboarding Flow, Tenant Code & Payment Integration

The following bug conditions document the missing tenant join-code mechanism that enables lecturer and student self-registration, and the incomplete Paystack/Monnify payment integration required for end-of-semester billing.

**Confirmed flow:**
1. Superadmin registers → creates the tenant (school) → tenant receives a unique 6-letter uppercase alphanumeric code (e.g. `UNILAG`, `FUTA01`) auto-generated on creation
2. Lecturers register using the tenant's 6-letter code → account linked to that tenant with `role=lecturer`
3. Students register using the tenant's 6-letter code → account linked to that tenant with `role=student`
4. Lecturers/admins create courses, exams, questions, enroll students, and create MCQ answers
5. Students take exams — autosave via Kafka+PostgreSQL, grading in background
6. At end of semester the scheduler initiates billing via Paystack or Monnify

### Current Behavior (Defect) — Onboarding Flow, Tenant Code & Payment Integration

1.102 WHEN a lecturer or student attempts to self-register to a specific school THEN the system has no mechanism to link them to a tenant because the `Tenant` model in `backend/models/account/tenant.py` has no `tenant_code` column; there is no unique join code that can be shared with users to identify their institution during registration

1.103 WHEN `POST /api/v1/auth/register` is called with a `tenant_code` field in the request body THEN the registration endpoint ignores it because the `UserCreate` schema in `backend/schemas/account/auth.py` does not accept a `tenant_code` field; the backend cannot look up the tenant by code and cannot set `user.tenant_id` during self-registration

1.104 WHEN a superadmin creates a new tenant THEN no `tenant_code` is generated or stored because the `TenantCreate` schema and `TenantService.create()` have no logic to auto-generate a 6-character uppercase alphanumeric code; the tenant is created without a join code, making lecturer and student self-registration impossible

1.105 WHEN `Invoice.to_dict()` is called or an invoice is returned via the API THEN the response contains no `payment_reference`, `payment_gateway`, `paid_at`, or `payment_url` fields because the `Invoice` model in `backend/models/billings/invoice.py` defines none of these columns; payment tracking and gateway redirect URLs cannot be stored or surfaced

1.106 WHEN the scheduler attempts to initiate a recurring charge for a tenant at end of semester THEN it cannot do so because the `Tenant` model has no `paystack_customer_code` or `monnify_account_reference` column; there is no stored gateway customer reference to use when initiating a charge authorization or direct debit

1.107 WHEN the end-of-semester billing job runs THEN no such job exists in `backend/scheduler.py`; the scheduler has no periodic task that detects semesters whose `end_date` has passed and `is_billed = False`, counts active students, creates an `Invoice` record, and initiates a charge via Paystack or Monnify

1.108 WHEN Paystack or Monnify sends a webhook event to confirm payment THEN no webhook handler route exists anywhere in the backend; there is no endpoint to receive, verify (HMAC signature check), and process payment confirmation events from either gateway, so `Invoice.status` is never updated to `paid` and `Semester.is_billed` is never set to `True`

1.109 WHEN any billing service needs to call the Paystack or Monnify API THEN no integration code exists anywhere in the codebase — there are no HTTP client wrappers, no API key configuration entries in `backend/core/config.py`, and no service classes for either gateway; the entire payment initiation and verification layer is absent

1.110 WHEN the billing scheduler job or webhook handler needs to update `Semester.is_billed` and `Semester.billed_at` after a successful payment THEN no service method exists on `SemesterService` (or equivalent) to perform this update; the `Semester` model fields `is_billed` and `billed_at` are defined but never written to by any application code path

---

### Expected Behavior (Correct) — Onboarding Flow, Tenant Code & Payment Integration

2.102 WHEN a new tenant is created THEN the `Tenant` model SHALL include a `tenant_code` column defined as `Mapped[str]` with `String(6)`, `unique=True`, `nullable=False`, indexed via `Index("ix_tenants_tenant_code", "tenant_code", unique=True)`; the code SHALL be auto-generated at creation time as a 6-character uppercase alphanumeric string (e.g. using `secrets.token_hex(3).upper()`) and SHALL be returned in all `TenantRead` responses so it can be shared with lecturers and students

2.103 WHEN `POST /api/v1/auth/register` is called with `role=lecturer` or `role=student` THEN the `UserCreate` schema SHALL accept an optional `tenant_code: str` field; the registration handler SHALL look up the `Tenant` by `tenant_code`, set `user.tenant_id = tenant.id`, and reject the request with HTTP 404 if no tenant with that code exists; superadmin registration SHALL NOT require `tenant_code` (it is optional and ignored for `role=superadmin`)

2.104 WHEN `TenantService.create()` creates a new tenant THEN it SHALL auto-generate a unique `tenant_code` by calling a helper (e.g. `generate_tenant_code()`) that produces a 6-character uppercase alphanumeric string, retrying on collision until a unique value is found; the generated code SHALL be stored on the `Tenant` record and returned in the creation response

2.105 WHEN an `Invoice` record is created or updated THEN the `Invoice` model SHALL define the following additional columns: `payment_reference: Mapped[Optional[str]]` (`String(100)`, nullable, the Paystack/Monnify transaction reference), `payment_gateway: Mapped[Optional[str]]` (`SAEnum` with values `'paystack'` and `'monnify'`, nullable), `paid_at: Mapped[Optional[datetime]]` (`DateTime(timezone=True)`, nullable, timestamp when payment was confirmed), and `payment_url: Mapped[Optional[str]]` (`String(500)`, nullable, the checkout/redirect URL returned by the gateway); all four fields SHALL be included in `Invoice.to_dict()` and all invoice API responses

2.106 WHEN a tenant is onboarded or their payment method is set up THEN the `Tenant` model SHALL define `paystack_customer_code: Mapped[Optional[str]]` (`String(100)`, nullable) and `monnify_account_reference: Mapped[Optional[str]]` (`String(100)`, nullable) columns so that the gateway's customer or account reference can be stored and reused for recurring charges without re-creating the customer on each billing cycle

2.107 WHEN the scheduler runs its periodic jobs THEN it SHALL include an end-of-semester billing job (e.g. every hour or daily) that: (a) queries all `Semester` records where `end_date <= now()` and `is_billed = False` and `status = 'ended'`; (b) for each such semester, counts active students for the tenant; (c) creates an `Invoice` record with `status='pending'`, `student_count`, `amount_per_student`, and `total_amount`; (d) emits a `INITIATE_BILLING` Kafka event containing `invoice_id`, `tenant_id`, `semester_id`, and `payment_gateway` preference; the actual gateway API call SHALL be handled by the worker consuming that event, keeping the scheduler free of blocking HTTP calls

2.108 WHEN Paystack or Monnify sends a webhook POST to the backend THEN a dedicated webhook handler route SHALL exist (e.g. `POST /api/v1/billing/webhooks/paystack` and `POST /api/v1/billing/webhooks/monnify`); each handler SHALL: (a) verify the request signature using the gateway's HMAC secret (stored in environment variables `PAYSTACK_SECRET_KEY` / `MONNIFY_API_SECRET`); (b) on a successful `charge.success` or equivalent event, look up the `Invoice` by `payment_reference`; (c) set `Invoice.status = 'paid'`, `Invoice.paid_at = now()`; (d) set `Semester.is_billed = True`, `Semester.billed_at = now()`; (e) return HTTP 200 to acknowledge receipt; invalid signatures SHALL return HTTP 400

2.109 WHEN the worker consumes an `INITIATE_BILLING` Kafka event THEN a `PaymentGatewayService` (or equivalent) SHALL exist in `backend/services/` that wraps the Paystack and Monnify HTTP APIs; for Paystack it SHALL call the `POST https://api.paystack.co/transaction/initialize` endpoint using the `PAYSTACK_SECRET_KEY` environment variable and store the returned `authorization_url` in `Invoice.payment_url` and `reference` in `Invoice.payment_reference`; for Monnify it SHALL call the equivalent direct-debit or payment initiation endpoint using `MONNIFY_API_KEY` and `MONNIFY_SECRET_KEY`; both gateway keys SHALL be declared in `backend/core/config.py` as optional settings with `None` defaults

2.110 WHEN a `Semester` record transitions to `status='ended'` and billing is confirmed via webhook THEN `SemesterService` (or equivalent) SHALL expose an `mark_billed(semester_id, billed_at)` method that sets `semester.is_billed = True` and `semester.billed_at = billed_at` and commits the change; this method SHALL be called by the webhook handler after successfully updating the associated `Invoice`, ensuring `Semester.is_billed` and `Semester.billed_at` are always written atomically with the invoice status update

---

### Unchanged Behavior (Regression Prevention) — Onboarding Flow, Tenant Code & Payment Integration

3.66 WHEN the `Tenant` model gains a `tenant_code` column THEN all existing tenant API responses that currently return `id`, `name`, `domain`, `logo_url`, `is_active`, `is_deleted`, `deleted_at`, `created_at`, and `updated_at` SHALL CONTINUE TO include those fields unchanged; `tenant_code` is additive and SHALL NOT replace or remove any existing field

3.67 WHEN the `UserCreate` schema gains an optional `tenant_code` field THEN the existing registration flow for `role=superadmin` SHALL CONTINUE TO work without providing `tenant_code`; the field SHALL be optional with a `None` default so that no existing registration call is broken by its addition

3.68 WHEN the `Invoice` model gains `payment_reference`, `payment_gateway`, `paid_at`, and `payment_url` columns THEN all existing invoice API responses that currently return `id`, `tenant_id`, `semester_id`, `description`, `student_count`, `amount_per_student`, `total_amount`, `status`, `created_at`, and `updated_at` SHALL CONTINUE TO include those fields unchanged; the four new payment columns are additive

3.69 WHEN the `Tenant` model gains `paystack_customer_code` and `monnify_account_reference` columns THEN all existing tenant service methods (`create`, `update`, `delete`, `restore`, `list`, `get`) SHALL CONTINUE TO function without modification; the new columns are nullable with `None` defaults and require no changes to existing service logic

3.70 WHEN the end-of-semester billing scheduler job is added THEN the existing scheduler jobs (`UPDATE_EXAM_STATUS`, `SEND_QUEUED_EMAILS`, `PRELOAD_QUESTIONS`, `FORCE_SUBMIT_EXAM`) SHALL CONTINUE TO run on their existing schedules without modification; the new billing job is additive

3.71 WHEN the Paystack and Monnify webhook handler routes are added under `/api/v1/billing/webhooks/` THEN all existing billing routes (`/api/v1/billing/invoices`, `/api/v1/billing/semesters`, `/api/v1/billing/billing_plans`, `/api/v1/billing/payment_methods`, `/api/v1/billing/usage`) SHALL CONTINUE TO be served at their existing paths without modification; the webhook routes are additive

3.72 WHEN `PaymentGatewayService` and the `INITIATE_BILLING` Kafka handler are added THEN the existing worker event handlers (`GRADE_SUBMISSION_ATTEMPT`, `REFRESH_DASHBOARD`, `PRELOAD_QUESTIONS`, `UPSERT_STUDENT_ANSWER`, `FORCE_SUBMIT_EXAM`, `DETECT_ANSWER`, `PARSE_AND_CREATE`, `SEND_EMAIL`, `UPDATE_EXAM_STATUS`) SHALL CONTINUE TO function as currently implemented; the new handler is additive and does not modify any existing handler's logic or registration
