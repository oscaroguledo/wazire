# Implementation Plan

<!-- ============================================================
     PROPERTY-BASED TESTS (run BEFORE any fix is implemented)
     ============================================================ -->

- [x] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - Critical Backend & Infrastructure Defects
  - **CRITICAL**: This test MUST FAIL on unfixed code — failure confirms the bugs exist
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior — it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate each bug exists
  - **Scoped PBT Approach**: For deterministic bugs, scope the property to the concrete failing case(s) to ensure reproducibility
  - Test 1 — Lifespan yield: start the FastAPI app and assert it serves a request; on unfixed code the lifespan never yields so the server immediately shuts down (isBugCondition: `lifespan` has no `yield`)
  - Test 2 — Invoice.to_dict crash: instantiate `Invoice()` and call `to_dict()`; on unfixed code raises `AttributeError: 'Invoice' object has no attribute 'status'`
  - Test 3 — BillingPlan.to_dict crash: instantiate `BillingPlan()` and call `to_dict()`; on unfixed code raises `AttributeError: 'BillingPlan' object has no attribute 'is_active'`
  - Test 4 — models/__init__ import crash: `import backend.models`; on unfixed code raises `ModuleNotFoundError` for `models.account.oauth` and `ImportError` for `PaymentMethodDetails`
  - Test 5 — SubmissionService field mismatch: create a `SubmissionModel(attempts_count=0)`; on unfixed code raises `TypeError: unexpected keyword argument 'attempts_count'`
  - Test 6 — get_db() misuse: call `grade_attempt_background()` with a mock; on unfixed code raises `AttributeError: __aenter__` because `get_db()` is not an async context manager
  - Test 7 — Docker compose structure: parse `docker-compose.yml` and assert `pgbouncer` and `scheduler` are top-level services; on unfixed code both are nested under sibling services
  - Test 8 — Answer PATCH method: send `PATCH /api/v1/academic/answers/{id}` and assert a Kafka event is produced; on unfixed code the route uses PUT and writes directly to DB
  - Test 9 — StudentAnswer UPSERT race: send 100 concurrent PATCH requests for the same `(student_id, exam_id, question_id)`; on unfixed code produces duplicate rows (no UNIQUE constraint)
  - Test 10 — Dashboard GET write: call `GET /api/v1/analytics/dashboard/` and assert no `db.add()` / `db.commit()` is called; on unfixed code the GET handler writes to the analytics table
  - Run all tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests FAIL (this is correct — it proves the bugs exist)
  - Document counterexamples found to understand root cause
  - Mark task complete when tests are written, run, and failures are documented
  - _Requirements: 1.1, 1.4, 1.6, 1.7, 1.9, 1.10, 1.12, 1.13, 1.22, 1.30, 1.52_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - All Currently Working Paths Unchanged
  - **IMPORTANT**: Follow observation-first methodology
  - Observe: `POST /api/v1/auth/login` with valid credentials returns `AuthResponse` with `user` and `tokens` on unfixed code
  - Observe: `GET /api/v1/auth/me` with valid JWT returns current user profile on unfixed code
  - Observe: Course/exam CRUD endpoints return correct shapes on unfixed code
  - Observe: `KafkaConsumerService` dispatches `GRADE_SUBMISSION_ATTEMPT` correctly on unfixed code
  - Observe: `postgres` and `redis` Docker services start and pass health checks on unfixed code
  - Observe: All model `to_dict()` outputs for non-buggy models include their existing fields on unfixed code
  - Write property-based test: for all auth requests with valid credentials, login/me/refresh continue to return the same response shape after any fix
  - Write property-based test: for all existing Kafka event types (`GRADE_SUBMISSION_ATTEMPT`, `REFRESH_DASHBOARD`, `DETECT_ANSWER`, `PARSE_AND_CREATE`, `SEND_EMAIL`, `UPDATE_EXAM_STATUS`, `SEND_QUEUED_EMAILS`), handlers continue to process events correctly after dispatcher refactor
  - Write property-based test: for all model `to_dict()` calls on non-buggy models, existing fields are present and unchanged after new columns are added
  - Write property-based test: for all non-buggy Docker services (`postgres`, `redis`), they continue to start and pass health checks after `docker-compose.yml` is fixed
  - Verify all preservation tests PASS on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.14, 3.15, 3.22, 3.23, 3.24, 3.36, 3.40_


<!-- ============================================================
     PHASE 1 — CRITICAL BACKEND CRASHES (unblock the app)
     ============================================================ -->

- [-] 3. Fix critical backend crashes that prevent the app from starting or running

  - [x] 3.1 Fix lifespan yield in `backend/main.py`
    - Add `yield` statement inside the `@asynccontextmanager async def lifespan(app)` function after all startup tasks complete
    - Ensure shutdown code (producer stop, etc.) is placed after the `yield`
    - _Bug_Condition: isBugCondition(input) where input.target = 'lifespan' AND defectPresent('no yield')_
    - _Expected_Behavior: server enters runtime and serves requests after startup; shutdown code runs only on stop_
    - _Preservation: all existing router registrations and startup tasks continue to run unchanged (3.1, 3.10)_
    - _Requirements: 2.1, 3.1_

  - [x] 3.2 Remove unused `consumer_service` import from `backend/main.py`
    - Change `from core.utils.kafka import producer_service, consumer_service` to `from core.utils.kafka import producer_service`
    - Remove any reference to `consumer_service` in `main.py`
    - _Bug_Condition: isBugCondition(input) where input.target = 'main.py consumer_service import'_
    - _Expected_Behavior: main.py only imports producer_service; no worker dependencies in API process_
    - _Preservation: producer_service lifespan start/stop continues unchanged (3.10, 3.40)_
    - _Requirements: 2.3, 2.40_

  - [x] 3.3 Fix `backend/models/__init__.py` broken imports
    - Remove `from models.account.oauth import OAuth` (file does not exist)
    - Remove `PaymentMethodDetails` from `from models.billings.paymentmethod import ...` (class does not exist)
    - Retain all other model imports and `__all__` entries unchanged
    - _Bug_Condition: isBugCondition(input) where input.target = 'models.__init__' AND (missingModule('oauth') OR missingClass('PaymentMethodDetails'))_
    - _Expected_Behavior: `import backend.models` succeeds; all other models remain importable_
    - _Preservation: all other model imports in __all__ continue unchanged (3.36)_
    - _Requirements: 2.4, 2.47, 3.36_

  - [x] 3.4 Add missing `Invoice.status` column to `backend/models/billings/invoice.py`
    - Define `InvoiceStatus` enum: `pending`, `paid`, `overdue`, `cancelled`
    - Add `status: Mapped[InvoiceStatus]` column with `default=InvoiceStatus.PENDING`, `nullable=False`
    - Ensure `to_dict()` and `__repr__()` reference `self.status.value` correctly
    - _Bug_Condition: isBugCondition(input) where input.target = 'Invoice.to_dict' AND defectPresent('missing status column')_
    - _Expected_Behavior: Invoice.to_dict() returns dict including 'status'; no AttributeError_
    - _Preservation: all existing invoice fields (id, tenant_id, semester_id, description, student_count, amount_per_student, total_amount, created_at, updated_at) unchanged (3.33)_
    - _Requirements: 2.9, 2.44, 3.33_

  - [x] 3.5 Add missing `BillingPlan.is_active` column to `backend/models/billings/plan.py`
    - Add `is_active: Mapped[bool]` column with `default=True`, `nullable=False`
    - Ensure `to_dict()` references `self.is_active` correctly
    - _Bug_Condition: isBugCondition(input) where input.target = 'BillingPlan.to_dict' AND defectPresent('missing is_active column')_
    - _Expected_Behavior: BillingPlan.to_dict() returns dict including 'is_active'; no AttributeError_
    - _Preservation: all existing billing plan fields unchanged (3.34)_
    - _Requirements: 2.10, 2.45, 3.34_

  - [x] 3.6 Add missing `Tenant.start_date` and `Tenant.end_date` columns to `backend/models/account/tenant.py`
    - Add `start_date: Mapped[Optional[datetime]]` with `DateTime(timezone=True)`, nullable
    - Add `end_date: Mapped[Optional[datetime]]` with `DateTime(timezone=True)`, nullable
    - _Bug_Condition: isBugCondition(input) where input.target = 'Tenant.start_date' AND defectPresent('missing mapped columns')_
    - _Expected_Behavior: Tenant model has start_date and end_date columns consistent with existing indexes_
    - _Preservation: all existing tenant fields unchanged (3.35)_
    - _Requirements: 2.11, 2.46, 3.35_

  - [x] 3.7 Fix `SubmissionService` field name mismatches in `backend/services/academic/submission.py`
    - Replace `attempts_count=0` with `attempts=0` in `SubmissionModel` constructor calls
    - Remove `attempt_number` and `scan_pages` from `SubmissionAttemptModel` constructor calls
    - _Bug_Condition: isBugCondition(input) where input.target = 'SubmissionService' AND (wrongField('attempts_count') OR nonExistentField('attempt_number') OR nonExistentField('scan_pages'))_
    - _Expected_Behavior: SubmissionModel and SubmissionAttemptModel created without TypeError_
    - _Preservation: submission creation flow continues to create Submission and SubmissionAttempt records (3.17)_
    - _Requirements: 2.7, 2.8_

  - [x] 3.8 Fix `get_db()` usage in `grade_attempt_background`
    - Replace `async with get_db() as db:` with the async generator pattern: `async for db in get_db(): ...`
    - _Bug_Condition: isBugCondition(input) where input.target = 'SubmissionService.grade_attempt_background' AND defectPresent('get_db() used as async context manager')_
    - _Expected_Behavior: grade_attempt_background obtains a DB session without AttributeError: __aenter___
    - _Preservation: grading logic and GRADE_SUBMISSION_ATTEMPT handler continue to function (3.32)_
    - _Requirements: 2.6_

  - [x] 3.9 Add `apscheduler` to `backend/requirements.txt`
    - Add `apscheduler` at a pinned version compatible with the existing scheduler code
    - _Bug_Condition: isBugCondition(input) where input.target = 'scheduler.py' AND defectPresent('missing apscheduler dependency')_
    - _Expected_Behavior: scheduler.py imports and runs without ModuleNotFoundError_
    - _Preservation: all other pinned dependencies unchanged (3.56)_
    - _Requirements: 2.5_

  - [x] 3.10 Fix `register` endpoint missing `request` parameter in `backend/routes/account/user.py`
    - Add `request: Request` as a function parameter to the `register` handler
    - Import `Request` from `fastapi` if not already imported
    - _Bug_Condition: isBugCondition(input) where input.target = 'register' AND defectPresent('missing request parameter')_
    - _Expected_Behavior: POST /api/v1/auth/register no longer raises NameError: name 'request' is not defined_
    - _Preservation: all other register logic (user creation, token return) unchanged_
    - _Requirements: 2.2_

  - [x] 3.11 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Critical Backend & Infrastructure Defects
    - **IMPORTANT**: Re-run the SAME test from task 1 — do NOT write a new test
    - The test from task 1 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run bug condition exploration test from step 1
    - **EXPECTED OUTCOME**: Test PASSES (confirms bugs are fixed)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10, 2.11_

  - [x] 3.12 Verify preservation tests still pass
    - **Property 2: Preservation** - All Currently Working Paths Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 — do NOT write new tests
    - Run preservation property tests from step 2
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all tests still pass after Phase 1 fixes (no regressions)


<!-- ============================================================
     PHASE 2 — DOCKER & INFRASTRUCTURE
     ============================================================ -->

- [x] 4. Fix Docker Compose YAML structure and add missing infrastructure services

  - [x] 4.1 Fix `docker-compose.yml` YAML indentation for `pgbouncer` and `scheduler`
    - Move `pgbouncer` service definition to top-level (same indentation as `postgres`, `redis`, `backend`)
    - Move `scheduler` service definition to top-level (same indentation as `worker`)
    - Verify `backend` `depends_on: pgbouncer` resolves correctly after fix
    - _Bug_Condition: isBugCondition(input) where input.target = 'docker-compose.yml' AND structuralDefectPresent('pgbouncer nested under postgres') AND structuralDefectPresent('scheduler nested under worker')_
    - _Expected_Behavior: docker compose up starts pgbouncer and scheduler as independent top-level services_
    - _Preservation: postgres, redis, backend, frontend, worker service definitions unchanged (3.14, 3.30)_
    - _Requirements: 2.12, 2.13_

  - [x] 4.2 Add Kafka service to `docker-compose.yml`
    - Uncomment or add the `kafka` service with KRaft-mode configuration
    - Add `kafka: condition: service_healthy` to `worker` and `scheduler` `depends_on` blocks
    - Add health check for Kafka service
    - _Bug_Condition: isBugCondition(input) where input.target = 'docker-compose.yml' AND structuralDefectPresent('kafka service missing')_
    - _Expected_Behavior: worker and scheduler can connect to Kafka broker on startup_
    - _Preservation: postgres, redis, backend, frontend, worker, scheduler service definitions unchanged (3.30)_
    - _Requirements: 2.38_

  - [x] 4.3 Add nginx service and `nginx/nginx.conf` configuration file
    - Create `nginx/nginx.conf` with: reverse proxy to `backend:8000` for `/api/v1/`, WebSocket upgrade for `/ws/`, gzip compression, cache headers for `/assets/`, rate-limiting zone (30r/s), SPA fallback for `/`
    - Add `nginx` service to `docker-compose.yml` with ports `80:80` and `443:443`, mounting `nginx.conf` and `frontend_dist` volume
    - Add `frontend_dist` named volume to `docker-compose.yml`
    - _Bug_Condition: isBugCondition(input) where input.target = 'docker-compose.yml' AND structuralDefectPresent('no nginx service')_
    - _Expected_Behavior: nginx is the sole entry point; all traffic routed through nginx_
    - _Preservation: all other services unchanged (3.83)_
    - _Requirements: 2.131, 2.132, 2.133_

  - [x] 4.4 Fix frontend `Dockerfile` to multi-stage production build
    - Stage 1 (`builder`): `FROM node:20-alpine AS builder`, `npm ci`, `npm run build` → produces `/app/dist`
    - Stage 2: `FROM alpine:3.19`, copy `/app/dist` to `/dist`, `CMD ["sh", "-c", "cp -r /dist/. /output/ && echo 'Frontend assets copied'"]`
    - Update `docker-compose.yml` frontend service to use `volumes: - frontend_dist:/output`
    - Remove `CMD ["npm", "run", "dev", ...]` from frontend Dockerfile
    - _Bug_Condition: isBugCondition(input) where input.target = 'frontend/Dockerfile' AND structuralDefectPresent('runs npm run dev instead of npm run build')_
    - _Expected_Behavior: frontend image builds static assets; nginx serves them from frontend_dist volume_
    - _Preservation: frontend application runtime behaviour unchanged (3.84)_
    - _Requirements: 2.14, 2.134_

  - [x] 4.5 Remove backend direct port exposure from `docker-compose.yml`
    - Remove `ports: - "${BACKEND_PORT:-8000}:8000"` from the `backend` service
    - Backend is only reachable via nginx on the internal `wazire-network`
    - _Bug_Condition: isBugCondition(input) where input.target = 'docker-compose.yml' AND structuralDefectPresent('backend port exposed directly')_
    - _Expected_Behavior: backend has no host-port binding; all external traffic goes through nginx_
    - _Preservation: backend service environment, volumes, depends_on unchanged (3.83)_
    - _Requirements: 2.135_

  - [x] 4.6 Add `gunicorn` to `backend/requirements.txt` and update backend `Dockerfile` CMD
    - Add `gunicorn` at a pinned version to `backend/requirements.txt`
    - Update `CMD` in `backend/Dockerfile` to: `gunicorn main:app -k uvicorn.workers.UvicornWorker --workers ${GUNICORN_WORKERS:-4} --bind 0.0.0.0:8000`
    - _Bug_Condition: isBugCondition(input) where input.target = 'backend/Dockerfile' AND structuralDefectPresent('single-process uvicorn, no gunicorn')_
    - _Expected_Behavior: backend runs under gunicorn with configurable worker count_
    - _Preservation: FastAPI app entrypoint (main:app) and all route registrations unchanged (3.85)_
    - _Requirements: 2.136_

  - [x] 4.7 Add `GET /health` endpoint to the backend
    - Create a `/api/v1/health` route that probes DB, Redis, and Kafka connectivity
    - Return `{"status": "ok", "db": "ok"|"error", "redis": "ok"|"error", "kafka": "ok"|"error"}` with HTTP 200 always
    - Register the health router in `main.py`
    - _Bug_Condition: isBugCondition(input) where input.target = 'GET /health' AND defectPresent('endpoint missing')_
    - _Expected_Behavior: GET /api/v1/health returns structured JSON health status_
    - _Preservation: all existing routes unchanged_
    - _Requirements: 2.137_

  - [x] 4.8 Fix all `docker-compose.yml` restart policies and add `deploy.replicas`
    - Ensure every service has `restart: unless-stopped`
    - Add `deploy: replicas: 1` to services that must remain single-instance (scheduler, kafka, postgres, redis, frontend, nginx)
    - Remove `container_name: wazire-backend` from the backend service to allow horizontal scaling
    - _Bug_Condition: isBugCondition(input) where input.target = 'docker-compose.yml' AND structuralDefectPresent('hardcoded container_name prevents scaling')_
    - _Expected_Behavior: docker compose up --scale backend=2 works; single-instance services enforced via deploy.replicas_
    - _Preservation: all other service definitions unchanged (3.30)_
    - _Requirements: 2.39, 2.139_


<!-- ============================================================
     PHASE 3 — MODEL SCHEMA ADDITIONS
     ============================================================ -->

- [x] 5. Add all missing model columns and constraints, then write a single Alembic migration

  - [x] 5.1 Add `Exam.end_time` column to `backend/models/academic/exam.py`
    - Add `end_time: Mapped[Optional[datetime]]` with `DateTime(timezone=True)`, nullable
    - Compute and persist `end_time = start_time + timedelta(hours=float(duration))` in exam create/update service methods
    - Include `end_time` in all exam API responses
    - _Requirements: 2.35, 2.51, 3.28_

  - [x] 5.2 Remove `Exam.student_id` column from `backend/models/academic/exam.py`
    - Remove `student_id` column and its index `ix_exams_student_id`
    - Student participation continues via `Enrollment` and `Submission` records
    - Update any service or schema that references `exam.student_id`
    - _Requirements: 2.48, 3.37_

  - [x] 5.3 Add `Submission.submitted_at` column to `backend/models/academic/submission.py`
    - Add `submitted_at: Mapped[Optional[datetime]]` with `DateTime(timezone=True)`, nullable, default `None`
    - Populate with `datetime.now(timezone.utc)` when a submission is received
    - Include in all submission API responses
    - _Requirements: 2.36, 2.50, 3.29_

  - [x] 5.4 Add `SubmissionAttempt.grading_started_at` column to `backend/models/academic/submission.py`
    - Add `grading_started_at: Mapped[Optional[datetime]]` with `DateTime(timezone=True)`, nullable, default `None`
    - Set to `datetime.now(timezone.utc)` at the start of grading
    - _Requirements: 2.148, 3.92_

  - [x] 5.5 Add `StudentAnswer` UNIQUE constraint to `backend/models/academic/student_answer.py`
    - Add `UniqueConstraint('student_id', 'exam_id', 'question_id', name='uq_student_answer_student_exam_question')` to `__table_args__`
    - Update `StudentAnswerService.upsert()` to use `INSERT ... ON CONFLICT (student_id, exam_id, question_id) DO UPDATE SET answer=EXCLUDED.answer, updated_at=now()`
    - _Requirements: 2.30, 2.49, 3.38_

  - [x] 5.6 Add `Tenant.tenant_code` column to `backend/models/account/tenant.py`
    - Add `tenant_code: Mapped[str]` with `String(6)`, `unique=True`, `nullable=False`
    - Add `Index("ix_tenants_tenant_code", "tenant_code", unique=True)`
    - _Requirements: 2.102, 3.66_

  - [x] 5.7 Add `Tenant.paystack_customer_code` and `Tenant.monnify_account_reference` columns
    - Add `paystack_customer_code: Mapped[Optional[str]]` with `String(100)`, nullable
    - Add `monnify_account_reference: Mapped[Optional[str]]` with `String(100)`, nullable
    - _Requirements: 2.106, 3.69_

  - [x] 5.8 Add `Invoice` payment columns to `backend/models/billings/invoice.py`
    - Add `payment_reference: Mapped[Optional[str]]` (`String(100)`, nullable)
    - Add `payment_gateway: Mapped[Optional[str]]` (`SAEnum('paystack','monnify')`, nullable)
    - Add `paid_at: Mapped[Optional[datetime]]` (`DateTime(timezone=True)`, nullable)
    - Add `payment_url: Mapped[Optional[str]]` (`String(500)`, nullable)
    - Include all four fields in `Invoice.to_dict()` and all invoice API responses
    - _Requirements: 2.105, 3.68_

  - [x] 5.9 Add `SubmissionStatus.grading_in_progress` enum value
    - Add `GRADING_IN_PROGRESS = "grading_in_progress"` to the `SubmissionStatus` enum
    - Ensure all existing status values (`pending`, `submitted`, `graded`) remain valid
    - _Requirements: 2.147, 3.91_

  - [x] 5.10 Write single Alembic migration covering all schema changes
    - Create `backend/alembic/versions/YYYYMMDD_app_wide_refactor.py`
    - Migration covers in one transaction: `Exam.end_time` add, `Exam.student_id` drop, `Submission.submitted_at` add, `SubmissionAttempt.grading_started_at` add, `StudentAnswer` UNIQUE constraint add, `Tenant.tenant_code` add, `Tenant.paystack_customer_code` add, `Tenant.monnify_account_reference` add, `Invoice.status` add, `Invoice` payment columns add, `BillingPlan.is_active` add, `Tenant.start_date` add, `Tenant.end_date` add, `SubmissionStatus` enum update
    - Include `downgrade()` that reverses all changes
    - _Requirements: 2.9, 2.10, 2.11, 2.35, 2.36, 2.44, 2.45, 2.46, 2.48, 2.49, 2.50, 2.51, 2.102, 2.105, 2.106, 2.147, 2.148_


<!-- ============================================================
     PHASE 4 — BACKEND ARCHITECTURE REFACTOR
     ============================================================ -->

- [x] 6. Refactor backend architecture: rename files, implement KafkaManager, class-based Worker, dispatcher pattern, OLAP/OLTP separation, and production settings

  - [x] 6.1 Rename all route and service files from singular to plural nouns
    - Rename route files: `user.py`→`users.py`, `tenant.py`→`tenants.py`, `course.py`→`courses.py`, `exam.py`→`exams.py`, `question.py`→`questions.py`, `answer.py`→`answers.py`, `submission.py`→`submissions.py`
    - Rename service files: same pattern for all files in `backend/services/academic/` and `backend/services/account/`
    - _Requirements: 2.54, 3.40_

  - [x] 6.2 Update all imports in `main.py` and elsewhere to use renamed files
    - Update all `from routes.account.user import ...` → `from routes.account.users import ...` etc.
    - Update all `from services.academic.course import ...` → `from services.academic.courses import ...` etc.
    - Verify no broken imports remain after renaming
    - _Requirements: 2.54, 2.55_

  - [x] 6.3 Implement `KafkaManager` facade class in `backend/core/kafka_manager.py`
    - Create `class KafkaManager` with `TOPIC_MAP` dict routing `UPSERT_STUDENT_ANSWER` to `wazire-answers` and all others to `tenant-tasks`
    - Implement `async def emit(self, event, data, partition_key=None) -> bool`
    - Create module-level singleton `kafka_manager: KafkaManager = None`; initialise in lifespan
    - _Bug_Condition: isBugCondition(input) where input.target = 'routes calling producer_service directly' AND defectPresent('no KafkaManager facade')_
    - _Expected_Behavior: routes use kafka_manager.emit(); topic routing and partition key centralised_
    - _Preservation: KafkaProducerService unchanged; KafkaManager delegates to it (3.24)_
    - _Requirements: 2.28, 3.24_

  - [x] 6.4 Refactor `backend/worker.py` to class-based `Worker`
    - Create `class Worker` with `__init__`, `start()`, `run()`, `stop()`, and `classmethod main()` lifecycle methods
    - `start()` calls `self._consumer.start()`; `run()` waits on `_stop_event`; `stop()` sets event and calls `self._consumer.stop()`
    - Add signal handlers for `SIGINT` and `SIGTERM` in `run()`
    - `if __name__ == "__main__": Worker.main()`
    - _Bug_Condition: isBugCondition(input) where input.target = 'worker.py' AND defectPresent('procedural module-level script, no class')_
    - _Expected_Behavior: worker is class-based with explicit lifecycle; testable and extensible_
    - _Preservation: existing Kafka event handlers continue to function (3.22)_
    - _Requirements: 2.26_

  - [x] 6.5 Implement dispatcher pattern — `HANDLERS` dict per tasks module
    - Add `HANDLERS: Dict[str, Handler]` dict to each `backend/tasks/` module (`exam.py`, `submission.py`, `question.py`, `email.py`)
    - Update `KafkaConsumerService._load_handlers()` to iterate over task modules and merge their `HANDLERS` dicts
    - Make `KAFKA_CONSUMER_GROUP_ID` configurable via environment variable (default `"wazire-worker"`)
    - _Bug_Condition: isBugCondition(input) where input.target = 'KafkaConsumerService._load_handlers' AND defectPresent('monolithic hard-coded handler registration')_
    - _Expected_Behavior: new event types added by adding to tasks module HANDLERS dict; consumer.py never modified_
    - _Preservation: all existing handlers (GRADE_SUBMISSION_ATTEMPT, REFRESH_DASHBOARD, etc.) continue to function (3.22, 3.23)_
    - _Requirements: 2.27, 2.42, 3.22, 3.23_

  - [x] 6.6 Fix OLAP/OLTP separation — make dashboard GET endpoints read-only
    - Remove `get_or_create_*` inline DB writes from all dashboard GET route handlers
    - If no dashboard row exists, return HTTP 404 or empty-metrics response — do NOT create a row inline
    - Move `compute_admin_stats()` aggregation logic to the `REFRESH_DASHBOARD` worker handler
    - _Bug_Condition: isBugCondition(input) where input.target = 'GET /analytics/dashboard/' AND defectPresent('db.add()/db.commit() inside GET handler')_
    - _Expected_Behavior: GET dashboard endpoints are read-only; no analytics writes in API request path_
    - _Preservation: dashboard response shape unchanged (3.39)_
    - _Requirements: 2.52, 2.53, 3.39_

  - [x] 6.7 Fix `DashboardService` wrong column queries
    - Fix `get_or_create_admin_dashboard()`: use `graded_submissions` and `pending_submissions` (not `total_graded_submissions`/`total_pending_submissions`); query by `tenant_id` not `admin_id`
    - Fix `get_or_create_student_dashboard()`: use `graded_submissions` and `pending_submissions`; add `active_courses=0` and `completed_courses=0` to constructor
    - Fix `get_or_create_lecturer_dashboard()`: ensure `tenant_id` is included in constructor
    - _Bug_Condition: isBugCondition(input) where input.target = 'DashboardService' AND defectPresent('wrong column names in constructor')_
    - _Expected_Behavior: AdminDashboard and StudentDashboard created without TypeError; correct fields populated_
    - _Preservation: to_dict() output shape unchanged (3.42)_
    - _Requirements: 2.57, 2.58, 3.42, 3.76_

  - [x] 6.8 Fix `require_admin_or_superadmin` import in analytics routes
    - Replace broken import with the correct auth helper from `core.middleware.auth`
    - Define `require_admin_or_superadmin` in `core.middleware.auth` if it does not exist
    - _Bug_Condition: isBugCondition(input) where input.target = 'analytics routes' AND defectPresent('broken require_admin_or_superadmin import')_
    - _Expected_Behavior: analytics routes load without ImportError at startup_
    - _Requirements: 2.121_

  - [x] 6.9 Fix CORS, DEBUG, and LOG_LEVEL production settings in `backend/core/config.py`
    - Set CORS allowed origins to `FRONTEND_ORIGIN` env var (not `*`)
    - Set `DEBUG` default to `False`; only `True` when `DEBUG=true` in environment
    - Read `LOG_LEVEL` from environment variable (default `"INFO"`)
    - Apply `LOG_LEVEL` to application logger and all middleware loggers
    - _Bug_Condition: isBugCondition(input) where input.target = 'CORS/DEBUG/LOG_LEVEL' AND defectPresent('wildcard CORS, DEBUG=True default')_
    - _Expected_Behavior: production-safe defaults; CORS restricted to FRONTEND_ORIGIN_
    - _Preservation: all API endpoints continue to function for requests from configured origin (3.87)_
    - _Requirements: 2.139, 3.87_


<!-- ============================================================
     PHASE 5 — ONBOARDING & REGISTRATION FLOW
     ============================================================ -->

- [x] 7. Implement tenant join-code onboarding and fix the registration flow

  - [x] 7.1 Auto-generate `tenant_code` in `TenantService.create()`
    - Implement `generate_tenant_code()` helper: 6-character uppercase alphanumeric string using `secrets.token_hex(3).upper()`
    - Retry on collision until a unique value is found
    - Store generated code on the `Tenant` record
    - _Bug_Condition: isBugCondition(input) where input.target = 'TenantService.create' AND defectPresent('no tenant_code generated')_
    - _Expected_Behavior: every new tenant gets a unique 6-char uppercase alphanumeric tenant_code_
    - _Preservation: all existing tenant service methods (update, delete, restore, list, get) unchanged (3.69)_
    - _Requirements: 2.104, 3.69_

  - [x] 7.2 Update registration endpoint: role validation and `tenant_code` lookup
    - Add optional `tenant_code: str` field to `UserCreate` schema
    - In register handler: if `role=lecturer` or `role=student`, look up `Tenant` by `tenant_code`; set `user.tenant_id = tenant.id`; return HTTP 404 if no tenant found
    - Block `role=superadmin` registration via this endpoint (superadmin created via seed script only)
    - `tenant_code` is optional and ignored for `role=superadmin`
    - _Bug_Condition: isBugCondition(input) where input.target = 'POST /api/v1/auth/register' AND defectPresent('no tenant_code lookup, no role validation')_
    - _Expected_Behavior: lecturers/students linked to tenant via tenant_code; superadmin registration blocked_
    - _Preservation: superadmin registration via seed script continues; existing registration flow for valid roles unchanged (3.67)_
    - _Requirements: 2.103, 3.67_

  - [x] 7.3 Implement superadmin seed script
    - Update or create `backend/seed_db.py` to create a superadmin user with `role=superadmin`
    - Script should be idempotent (skip if superadmin already exists)
    - Document usage in comments
    - _Requirements: 2.103_

  - [x] 7.4 Update `TenantRead` schema to include `tenant_code`
    - Add `tenant_code: str` to `TenantRead` Pydantic schema
    - Ensure `tenant_code` is returned in all tenant API responses
    - _Requirements: 2.102, 3.66_


<!-- ============================================================
     PHASE 6 — EXAM DATA FLOW ARCHITECTURE
     ============================================================ -->

- [x] 8. Implement the correct exam data flow: Redis preload, Kafka-buffered answer UPSERT, force-submit, and UTC timing

  - [x] 8.1 Add `PRELOAD_QUESTIONS` scheduler job to `backend/scheduler.py`
    - Add a periodic job (every 1–5 minutes) that queries PostgreSQL for exams whose `start_time` is within the next ~15 minutes and whose `exam:{exam_id}:preloaded` Redis key is absent
    - Emit a `PRELOAD_QUESTIONS` Kafka event for each such exam: `{exam_id, duration_seconds, tenant_id}`
    - Use `KafkaManager.emit()` (not `producer_service` directly)
    - _Bug_Condition: isBugCondition(input) where input.target = 'scheduler.PRELOAD_QUESTIONS' AND architectureDeviationPresent_
    - _Expected_Behavior: scheduler detects approaching exams and emits PRELOAD_QUESTIONS events_
    - _Preservation: existing UPDATE_EXAM_STATUS and SEND_QUEUED_EMAILS jobs unchanged (3.19, 3.21)_
    - _Requirements: 2.18, 3.19_

  - [x] 8.2 Add `PRELOAD_QUESTIONS` worker handler in `backend/tasks/question.py`
    - Implement `handle_preload_questions(payload)` handler
    - Fetch all questions for `exam_id` from PostgreSQL
    - Write to Redis: `SET exam:{exam_id}:questions = JSON(questions)` with TTL = `duration_seconds + 1800`
    - Set sentinel: `SET exam:{exam_id}:preloaded = "1"` with same TTL
    - Add `"PRELOAD_QUESTIONS": handle_preload_questions` to `HANDLERS` dict in `question.py`
    - _Bug_Condition: isBugCondition(input) where input.target = 'worker.PRELOAD_QUESTIONS' AND architectureDeviationPresent_
    - _Expected_Behavior: PRELOAD_QUESTIONS event writes questions to Redis with correct TTL_
    - _Preservation: existing DETECT_ANSWER and PARSE_AND_CREATE handlers unchanged (3.20)_
    - _Requirements: 2.19, 2.20, 3.20_

  - [x] 8.3 Update question fetch endpoints to read from Redis first (with PostgreSQL fallback)
    - In `GET /api/v1/academic/questions/?exam_id=` and `GET /api/v1/academic/questions/exam/{exam_id}`: try `GET exam:{exam_id}:questions` from Redis first
    - On cache miss: fall back to PostgreSQL `QuestionService.list()`
    - _Bug_Condition: isBugCondition(input) where input.target = 'question.GET' AND architectureDeviationPresent('queries PostgreSQL directly')_
    - _Expected_Behavior: questions served from Redis during active exam; PostgreSQL fallback on cache miss_
    - _Preservation: Redis unavailability falls back to PostgreSQL; students never blocked (3.18)_
    - _Requirements: 2.21, 3.18_

  - [x] 8.4 Change answer endpoint from PUT to PATCH and emit `UPSERT_STUDENT_ANSWER` Kafka event
    - Change route decorator from `@router.put` to `@router.patch` in `backend/routes/academic/answers.py`
    - Replace direct `StudentAnswerService.upsert()` DB call with `KafkaManager.emit("UPSERT_STUDENT_ANSWER", {...}, partition_key=tenant_id)`
    - Return HTTP 200 with optimistic acknowledgement immediately (no DB wait)
    - _Bug_Condition: isBugCondition(input) where input.target = 'answer.PUT' AND architectureDeviationPresent('writes directly to DB, no Kafka')_
    - _Expected_Behavior: PATCH /academic/answers/{id} emits Kafka event and returns fast acknowledgement_
    - _Preservation: API response contract (HTTP 200, success/message/data shape) unchanged (3.27)_
    - _Requirements: 2.22, 2.29, 3.27_

  - [x] 8.5 Add `UPSERT_STUDENT_ANSWER` worker handler in `backend/tasks/question.py`
    - Implement `handle_upsert_student_answer(payload)` handler
    - Perform `INSERT INTO student_answers ... ON CONFLICT (student_id, exam_id, question_id) DO UPDATE SET answer=EXCLUDED.answer, updated_at=now()`
    - Commit Kafka offset only after successful DB write
    - Add `"UPSERT_STUDENT_ANSWER": handle_upsert_student_answer` to `HANDLERS` dict
    - _Bug_Condition: isBugCondition(input) where input.target = 'worker.UPSERT_STUDENT_ANSWER' AND architectureDeviationPresent_
    - _Expected_Behavior: worker performs atomic UPSERT; no duplicate rows; offset committed after DB write_
    - _Preservation: existing question handlers unchanged (3.20)_
    - _Requirements: 2.23, 2.30, 3.20_

  - [x] 8.6 Add `FORCE_SUBMIT_EXAM` scheduler job to `backend/scheduler.py`
    - Add a periodic job (every 1–5 minutes) that queries PostgreSQL for exams where `start_time + duration <= now()` and `status = 'in_progress'`
    - Emit a `FORCE_SUBMIT_EXAM` Kafka event for each such exam: `{exam_id, tenant_id}`
    - _Bug_Condition: isBugCondition(input) where input.target = 'scheduler.FORCE_SUBMIT_EXAM' AND defectPresent('no force-submit job')_
    - _Expected_Behavior: scheduler detects expired exams and emits FORCE_SUBMIT_EXAM events_
    - _Preservation: existing scheduler jobs unchanged (3.21)_
    - _Requirements: 2.24, 3.21_

  - [x] 8.7 Add `FORCE_SUBMIT_EXAM` worker handler in `backend/tasks/exam.py`
    - Implement `handle_force_submit_exam(payload)` handler
    - Query all `Enrollment` records for `exam_id`; filter out students with existing `Submission`
    - Auto-create `Submission(status='submitted', submitted_at=exam.end_time)` and `SubmissionAttempt` for each unsubmitted student
    - Emit `GRADE_SUBMISSION_ATTEMPT` Kafka event for each new attempt
    - Add `"FORCE_SUBMIT_EXAM": handle_force_submit_exam` to `HANDLERS` dict in `exam.py`
    - _Bug_Condition: isBugCondition(input) where input.target = 'worker.FORCE_SUBMIT_EXAM' AND defectPresent('no handler registered')_
    - _Expected_Behavior: unsubmitted students auto-submitted; grading triggered; already-submitted students skipped_
    - _Preservation: manual submission flow unchanged; FORCE_SUBMIT skips students with existing Submission (3.25)_
    - _Requirements: 2.25, 3.25_

  - [x] 8.8 Add UTC timestamp validation for `Exam.start_time`
    - In exam create/update schema or service: validate that `start_time` is a UTC-aware datetime (`tzinfo` is not `None`)
    - Reject naive `start_time` values with a clear validation error
    - In `_update_exam_statuses()`: log an error and skip exams with naive `start_time` instead of silently patching
    - _Bug_Condition: isBugCondition(input) where input.target = 'Exam.start_time' AND defectPresent('naive datetime silently patched')_
    - _Expected_Behavior: naive start_time rejected at schema layer; _update_exam_statuses skips and logs offending exams_
    - _Requirements: 2.34_

  - [x] 8.9 Compute and persist `Exam.end_time` on create/update
    - In `ExamService.create()` and `ExamService.update()`: compute `end_time = start_time + timedelta(hours=float(duration))` and persist it
    - Include `end_time` in all exam API responses
    - _Requirements: 2.35, 2.51_


<!-- ============================================================
     PHASE 7 — PRODUCTION RESILIENCE
     ============================================================ -->

- [x] 9. Harden production resilience: safe Kafka publishes, dead-letter forwarding, idempotency, and offset commit discipline

  - [x] 9.1 Replace `asyncio.ensure_future` with `await publish_safe` in task handlers
    - In `backend/tasks/submission.py`: replace all `asyncio.ensure_future(producer_service.publish_safe(...))` calls with `await kafka_manager.emit(...)` (or `await producer_service.publish_safe(...)`)
    - Ensure failures are logged with enough context for manual replay
    - _Bug_Condition: isBugCondition(input) where input.target = 'emit_grade_attempt/emit_refresh_dashboard' AND defectPresent('asyncio.ensure_future silently drops events')_
    - _Expected_Behavior: Kafka publish is awaited; failures are observable and logged_
    - _Preservation: grading and dashboard refresh events continue to be emitted (3.32)_
    - _Requirements: 2.32, 3.32_

  - [x] 9.2 Add dead-letter topic forwarding on exhausted retries
    - In `KafkaConsumerService._handle_message()`: after 3 retry attempts (1s, 2s, 4s backoff), forward the message to `wazire-dead-letter` topic with metadata (`original_topic`, `original_offset`, `error_message`, `timestamp`)
    - Commit the offset after forwarding to dead-letter so the consumer is not stuck
    - _Bug_Condition: isBugCondition(input) where input.target = 'KafkaConsumerService._handle_message' AND defectPresent('offset committed on first failure, no dead-letter')_
    - _Expected_Behavior: failed events forwarded to dead-letter after 3 retries; no grading job permanently lost_
    - _Preservation: manual-commit, dead-letter-logging, reconnect-on-error behaviour preserved (3.23)_
    - _Requirements: 2.31, 3.23_

  - [x] 9.3 Add idempotency check (`attempt.graded_at`) before re-grading
    - At the start of the `GRADE_SUBMISSION_ATTEMPT` handler: check if `attempt.graded_at IS NOT NULL`
    - If already graded: skip re-grading, commit offset, and return
    - _Bug_Condition: isBugCondition(input) where input.target = 'GRADE_SUBMISSION_ATTEMPT handler' AND defectPresent('no idempotency check, score overwritten on redelivery')_
    - _Expected_Behavior: redelivered grading events are skipped if attempt already graded; no score overwrite_
    - _Preservation: grading logic unchanged for non-idempotent (first-time) events (3.32)_
    - _Requirements: 2.33_

  - [x] 9.4 Commit Kafka offset only after successful DB write
    - In `UPSERT_STUDENT_ANSWER` and `GRADE_SUBMISSION_ATTEMPT` handlers: do not commit offset until all DB writes have been committed successfully
    - If DB write raises an exception: do not commit offset; allow message redelivery on worker restart
    - _Bug_Condition: isBugCondition(input) where input.target = 'GRADE_SUBMISSION_ATTEMPT offset commit' AND defectPresent('offset committed before DB write completes')_
    - _Expected_Behavior: offset committed only after successful DB write; no grading job silently lost on crash_
    - _Requirements: 2.149_


<!-- ============================================================
     PHASE 8 — ADVANCED AI GRADING ENGINE
     ============================================================ -->

- [x] 10. Refactor and harden the AI grading engine: correct imports, batch grading, key rotation, throttling, and bulk DB writes

  - [x] 10.1 Fix Groq import: `from groq.client import Groq as GroqClient`
    - In `backend/services/engine/base.py`, `similarity_grader.py`, and `answer_grader.py`: change primary import to `from groq.client import Groq as GroqClient` with fallback `from groq import Groq`
    - Use `GroqClient` consistently across all engine files
    - _Bug_Condition: isBugCondition(input) where input.target = 'grading engine' AND defectPresent('from groq import Groq fails in some environments')_
    - _Expected_Behavior: Groq client imports successfully in all deployment environments_
    - _Requirements: 2.143_

  - [x] 10.2 Refactor `QuestionAnswerer` and `SimilarityGrader` to inherit from `GroqEngineBase`
    - Both classes inherit from `GroqEngineBase` in `backend/services/engine/base.py`
    - Delegate client initialisation to `GroqEngineBase._init_client()`
    - Remove duplicated initialisation code from each subclass
    - _Bug_Condition: isBugCondition(input) where input.target = 'QuestionAnswerer/SimilarityGrader' AND defectPresent('duplicated client init code')_
    - _Expected_Behavior: single client init in GroqEngineBase; subclasses inherit without duplication_
    - _Preservation: public method signatures (grade(), answer_question(), process()) unchanged (3.78)_
    - _Requirements: 2.124, 3.78_

  - [x] 10.3 Fix `SimilarityGrader.grade()` async/sync mismatch using `asyncio.to_thread`
    - Wrap `self.client.chat.completions.create(...)` in `await asyncio.to_thread(...)` inside `SimilarityGrader.grade()`
    - Ensure the method remains `async def` and is non-blocking
    - _Bug_Condition: isBugCondition(input) where input.target = 'SimilarityGrader.grade' AND defectPresent('await on synchronous return value')_
    - _Expected_Behavior: SimilarityGrader.grade() is non-blocking; event loop not blocked during Groq call_
    - _Preservation: MCQ and FITB grading branches continue to execute synchronously inline (3.77)_
    - _Requirements: 2.122, 3.77_

  - [x] 10.4 Fix `QuestionAnswerer` blocking event loop using `asyncio.to_thread`
    - Wrap blocking Groq HTTP call in `asyncio.to_thread()` inside `QuestionAnswerer.answer_question()`
    - _Bug_Condition: isBugCondition(input) where input.target = 'QuestionAnswerer.answer_question' AND defectPresent('blocking Groq call on event loop')_
    - _Expected_Behavior: QuestionAnswerer.answer_question() is non-blocking_
    - _Preservation: return type and error contract unchanged (3.79)_
    - _Requirements: 2.123_

  - [x] 10.5 Implement `GroqKeyRotator` with Redis-backed cross-process cooldown
    - Upgrade `backend/core/key_balancer.py` to `GroqKeyRotator` class
    - Read up to 4 keys from `GROQ_API_KEY_1`…`GROQ_API_KEY_4`
    - Store cooldown state in Redis: `groq:key_cooldown:{index}` with TTL = `retry_after_seconds`
    - `get_key()`: round-robin, skip cooling keys; if all cooling, wait 1s and return first key
    - `mark_rate_limited(key, retry_after)`: set Redis cooldown flag
    - Module-level singleton via `get_rotator()`
    - _Bug_Condition: isBugCondition(input) where input.target = 'GroqKeyRotator' AND defectPresent('per-process only, no cross-process coordination')_
    - _Expected_Behavior: all worker replicas share cooldown state via Redis; no replica sends to rate-limited key_
    - _Preservation: round-robin key selection order and 429-backoff behaviour preserved (3.95)_
    - _Requirements: 2.144, 2.152, 2.153, 3.89, 3.95_

  - [x] 10.6 Implement batch grading — all theory questions in one Groq call per submission
    - In `SubmissionService.grade_attempt_background()`: collect all theory questions for the submission
    - Build a single batch prompt requesting structured JSON response keyed by `question_id`
    - Make one Groq API call for all theory questions; parse JSON response per question
    - MCQ and FITB continue to be graded inline without API call
    - _Bug_Condition: isBugCondition(input) where input.target = 'grade_attempt_background' AND defectPresent('one Groq call per question, O(N) API calls')_
    - _Expected_Behavior: at most one Groq API call per submission regardless of theory question count_
    - _Preservation: MCQ/FITB grading unchanged; error-result contract unchanged (3.88)_
    - _Requirements: 2.142, 3.88_

  - [x] 10.7 Add retry logic with exponential backoff (3 attempts: 1s, 2s, 4s)
    - In `SimilarityGrader.grade()` and `QuestionAnswerer.answer_question()`: retry on 429 or transient error up to 3 times with 1s, 2s, 4s delays
    - Do not retry on permanent errors (invalid API key)
    - On exhausted retries: return `(Decimal("0.00"), "Error: ...")` / `{"answer": "Error: ...", "confidence": 0.0}`
    - _Requirements: 2.125, 3.79_

  - [x] 10.8 Add jitter between consecutive Groq API calls (0.1–0.5s)
    - In the grading worker: after processing each submission's Groq call, apply `await asyncio.sleep(random.uniform(0.1, 0.5))` before the next submission's call
    - Jitter applied between submissions, not between questions within a single batch
    - _Requirements: 2.145, 3.93_

  - [x] 10.9 Implement per-tenant `asyncio.Semaphore` (`GRADING_CONCURRENCY_PER_TENANT`)
    - In `backend/tasks/submission.py`: maintain a module-level dict `_tenant_semaphores: Dict[str, asyncio.Semaphore]`
    - Create semaphore on first use per tenant; default max = 2; configurable via `GRADING_CONCURRENCY_PER_TENANT` env var
    - Acquire semaphore before starting grading; release after completion
    - _Bug_Condition: isBugCondition(input) where input.target = 'GRADE_SUBMISSION_ATTEMPT' AND defectPresent('no per-tenant concurrency limit')_
    - _Expected_Behavior: max GRADING_CONCURRENCY_PER_TENANT concurrent grading tasks per tenant; others wait_
    - _Preservation: grading logic unchanged; semaphore wraps handler invocation (3.90)_
    - _Requirements: 2.146, 3.90_

  - [x] 10.10 Implement bulk DB writes: `insert().values([...])` for grade results
    - Replace per-row `session.add()` loop with `session.execute(insert(StudentAnswer).values([...]))` bulk insert
    - Use `ON CONFLICT DO UPDATE` in the bulk insert to remain idempotent
    - Replace row-by-row `SubmissionAttempt` score updates with a single `UPDATE ... WHERE id IN (...)`
    - _Bug_Condition: isBugCondition(input) where input.target = 'grade_attempt_background DB writes' AND defectPresent('O(N) session.add() calls')_
    - _Expected_Behavior: 500 question grades saved in a single DB round trip; attempt scores updated in one bulk UPDATE_
    - _Preservation: final set of rows written identical to per-row approach; UniqueConstraint enforced (3.94)_
    - _Requirements: 2.150, 2.151, 3.94_

  - [x] 10.11 Add `GRADING_BATCH_SIZE` and `DB_WRITE_BATCH_SIZE` env vars to config
    - Add `GRADING_BATCH_SIZE: int = 20` and `DB_WRITE_BATCH_SIZE: int = 500` to `backend/core/config.py`
    - Use these values in the grading batch logic and bulk DB write logic
    - _Requirements: 2.156_

  - [x] 10.12 Set `Submission.status = grading_in_progress` at grading start
    - At the start of `grade_attempt_background()` (after idempotency check): set `submission.status = SubmissionStatus.GRADING_IN_PROGRESS`
    - _Requirements: 2.147_

  - [x] 10.13 Set `SubmissionAttempt.grading_started_at` at grading start
    - At the start of `grade_attempt_background()`: set `attempt.grading_started_at = datetime.now(timezone.utc)`
    - _Requirements: 2.148_

  - [x] 10.14 Kafka partition by `tenant_id` for `GRADE_SUBMISSION_ATTEMPT` events
    - When emitting `GRADE_SUBMISSION_ATTEMPT`: pass `partition_key=tenant_id` to `KafkaManager.emit()`
    - Also use `student_id` as partition key for `UPSERT_STUDENT_ANSWER` and `tenant_id` for `REFRESH_DASHBOARD`
    - _Bug_Condition: isBugCondition(input) where input.target = 'GRADE_SUBMISSION_ATTEMPT Kafka message' AND defectPresent('no partition key, random distribution')_
    - _Expected_Behavior: all grading events for a tenant routed to same partition and worker replica_
    - _Preservation: message payload schema unchanged; consumers deserialise identically (3.96)_
    - _Requirements: 2.154, 2.155, 3.96_


<!-- ============================================================
     PHASE 9 — BILLING & PAYMENT INTEGRATION
     ============================================================ -->

- [x] 11. Implement billing routes, services, payment gateway integration, and webhook handlers

  - [x] 11.1 Create billing routes and services (invoices, plans, payment_methods, usage, semesters)
    - Create `backend/routes/billing/__init__.py`, `invoices.py`, `billing_plans.py`, `payment_methods.py`, `usage.py`, `semesters.py`, `webhooks.py`
    - Create `backend/services/billing/__init__.py`, `invoices.py`, `billing_plans.py`, `payment_methods.py`, `usage.py`, `semesters.py`
    - Register all billing routers in `main.py` under prefix `/api/v1/billing`
    - _Requirements: 2.55_

  - [x] 11.2 Implement `PaymentGatewayService` (Paystack + Monnify)
    - Create `backend/services/billing/payment_gateway.py` with `PaymentGatewayService` class
    - Paystack: `POST https://api.paystack.co/transaction/initialize` using `PAYSTACK_SECRET_KEY`; store `authorization_url` → `Invoice.payment_url`, `reference` → `Invoice.payment_reference`
    - Monnify: equivalent direct-debit endpoint using `MONNIFY_API_KEY` and `MONNIFY_SECRET_KEY`
    - Add `PAYSTACK_SECRET_KEY`, `MONNIFY_API_KEY`, `MONNIFY_SECRET_KEY` to `backend/core/config.py` as optional settings with `None` defaults
    - _Requirements: 2.109_

  - [x] 11.3 Add `INITIATE_BILLING` Kafka event and worker handler
    - Create `backend/tasks/billing.py` with `handle_initiate_billing(payload)` handler
    - Handler calls `PaymentGatewayService.initiate(invoice)` and updates `Invoice.payment_url` and `Invoice.payment_reference`
    - Add `HANDLERS = {"INITIATE_BILLING": handle_initiate_billing}` to `billing.py`
    - Update `KafkaConsumerService._load_handlers()` to include `billing` module
    - _Requirements: 2.109_

  - [x] 11.4 Add end-of-semester billing scheduler job
    - Add a periodic job (hourly or daily) to `backend/scheduler.py`
    - Query `Semester` records where `end_date <= now()` AND `is_billed = False` AND `status = 'ended'`
    - For each: count active students, create `Invoice(status='pending', ...)`, emit `INITIATE_BILLING` Kafka event
    - _Bug_Condition: isBugCondition(input) where input.target = 'scheduler billing job' AND defectPresent('no end-of-semester billing job')_
    - _Expected_Behavior: scheduler detects ended unbilled semesters and initiates billing via Kafka_
    - _Preservation: existing scheduler jobs unchanged (3.70)_
    - _Requirements: 2.107, 3.70_

  - [x] 11.5 Implement Paystack webhook handler (HMAC verification)
    - In `backend/routes/billing/webhooks.py`: `POST /api/v1/billing/webhooks/paystack`
    - Verify HMAC signature using `PAYSTACK_SECRET_KEY`; return HTTP 400 on invalid signature
    - On `charge.success`: look up `Invoice` by `payment_reference`; set `Invoice.status='paid'`, `Invoice.paid_at=now()`; call `SemesterService.mark_billed()`; return HTTP 200
    - _Requirements: 2.108_

  - [x] 11.6 Implement Monnify webhook handler (HMAC verification)
    - In `backend/routes/billing/webhooks.py`: `POST /api/v1/billing/webhooks/monnify`
    - Verify HMAC signature using `MONNIFY_API_SECRET`; return HTTP 400 on invalid signature
    - On successful payment event: same Invoice + Semester update as Paystack handler
    - _Requirements: 2.108_

  - [x] 11.7 Implement `SemesterService.mark_billed()`
    - Add `mark_billed(semester_id, billed_at)` method to `SemesterService`
    - Sets `semester.is_billed = True` and `semester.billed_at = billed_at`; commits atomically with invoice status update
    - _Bug_Condition: isBugCondition(input) where input.target = 'SemesterService.mark_billed' AND defectPresent('method does not exist')_
    - _Expected_Behavior: Semester.is_billed and Semester.billed_at written atomically after payment confirmation_
    - _Requirements: 2.110_

  - [x] 11.8 Add `PAYSTACK_SECRET_KEY`, `MONNIFY_API_KEY`, `MONNIFY_SECRET_KEY` to config and `.env.example`
    - Add all three keys to `backend/core/config.py` as optional settings
    - Add to `backend/.env.example` with placeholder values and explanatory comments
    - _Requirements: 2.109, 2.138_


<!-- ============================================================
     PHASE 10 — NEW API ENDPOINTS
     ============================================================ -->

- [x] 12. Add new read-only and functional API endpoints

  - [x] 12.1 Add `GET /api/v1/academic/exams/{exam_id}/results`
    - Return list of all `Submission` records for the exam: `student_id`, `latest_score`, `status`, `graded_at`, `submitted_at`
    - Scope to requesting user's tenant; restrict to lecturers and admins
    - _Requirements: 2.127, 3.81_

  - [x] 12.2 Add `GET /api/v1/academic/courses/{course_id}/students`
    - Return list of all users enrolled in the course via `Enrollment` table: `student_id`, `user.first_name`, `user.last_name`, `enrollment.status`
    - Scope to requesting user's tenant; restrict to admins and lecturers
    - _Requirements: 2.128, 3.81_

  - [x] 12.3 Add `GET /api/v1/academic/students/{student_id}/exams`
    - Return list of all exams for courses the student is enrolled in: `exam.id`, `exam.title`, `exam.start_time`, `exam.end_time`, `exam.status`, `exam.duration`
    - Scope to student's tenant; students can only query their own `student_id`
    - _Requirements: 2.129, 3.81_

  - [x] 12.4 Add `POST /api/v1/academic/exams/{exam_id}/scan` (answer sheet extraction)
    - Accept multipart image upload; pass to `AnswerSheetExtractor` in `backend/services/engine/answer_sheet_extractor.py`
    - Return extracted answers as structured JSON
    - Wire to a Kafka task handler for async extraction of large batches
    - _Requirements: 2.130, 3.82_

  - [x] 12.5 Fix `REFRESH_DASHBOARD` worker handler
    - Implement `upsert_metrics` method on `DashboardService` that computes fresh aggregate metrics and writes via `INSERT ... ON CONFLICT DO UPDATE`
    - Include lecturer dashboard refresh: compute `total_courses`, `total_students`, `total_exams`, `pending_submissions`, `graded_submissions` for affected lecturer
    - _Bug_Condition: isBugCondition(input) where input.target = 'REFRESH_DASHBOARD handler' AND defectPresent('missing upsert_metrics, missing lecturer dashboard refresh')_
    - _Expected_Behavior: REFRESH_DASHBOARD upserts all three dashboard types (admin, lecturer, student)_
    - _Preservation: existing admin and student dashboard refresh logic unchanged (3.80)_
    - _Requirements: 2.119, 2.120, 3.80_


<!-- ============================================================
     PHASE 11 — FRONTEND FIXES
     ============================================================ -->

- [x] 13. Fix all frontend type errors, API URL mismatches, and missing modules

  - [x] 13.1 Fix `UserManagement.tsx` missing `User` import
    - Add `import type { User } from '@/lib/types'` (or equivalent) to `frontend/src/pages/UserManagement.tsx`
    - _Bug_Condition: isBugCondition(input) where input.target = 'UserManagement.tsx' AND missingImport('User')_
    - _Expected_Behavior: UserManagement.tsx compiles without TypeScript errors_
    - _Preservation: UserManagement page continues to fetch and display paginated user list (3.13)_
    - _Requirements: 2.15, 3.13_

  - [x] 13.2 Add `superadmin` to `UserRole` type in `frontend/src/lib/types.ts`
    - Add `'superadmin'` to the `UserRole` union type
    - _Bug_Condition: isBugCondition(input) where input.target = 'UserRole type' AND typeMismatch('missing superadmin')_
    - _Expected_Behavior: UserRole includes 'superadmin'; no TypeScript errors for superadmin users_
    - _Requirements: 2.16_

  - [x] 13.3 Fix `AuthContext.register()` token storage
    - After auto-login following registration: call `localStorage.setItem(TOKEN_KEY, accessToken)` to store the access token
    - _Bug_Condition: isBugCondition(input) where input.target = 'AuthContext.register' AND defectPresent('token not stored in localStorage')_
    - _Expected_Behavior: user is authenticated immediately after registration; token stored in localStorage_
    - _Preservation: login, logout, and token refresh flows unchanged (3.11)_
    - _Requirements: 2.17_

  - [x] 13.4 Fix all API URL mismatches in `auth.ts`, `tenant.ts`, `enrollment.ts`, `dashboard.ts`
    - `auth.ts`: change `listUsers()` → `/api/v1/account/users`, `getUser()` → `/api/v1/account/users/{id}`, `updateUser()` → `/api/v1/account/users/{id}`, `deleteUser()` → `/api/v1/account/users/{id}`
    - `tenant.ts`: change all tenant URLs from `/tenants/` to `/api/v1/account/tenants/`
    - `enrollment.ts`: change `/academic/enrollment/` (singular) to `/academic/enrollments/` (plural)
    - `dashboard.ts`: change `getAdminDashboard(adminId)` to pass `tenantId` (not `adminId`) to `/analytics/dashboard/admin/{tenantId}`
    - _Bug_Condition: isBugCondition(input) where input.target IN ['auth.ts','tenant.ts','enrollment.ts','dashboard.ts'] AND wrongURL_
    - _Expected_Behavior: all API calls reach correct backend routes; no 404s_
    - _Requirements: 2.59–2.67_

  - [x] 13.5 Fix `answer.ts` `upsertAnswer`: change PUT to PATCH
    - In `frontend/src/apis/answer.ts`: change `client.put(...)` to `client.patch(...)` in `upsertAnswer()`
    - _Bug_Condition: isBugCondition(input) where input.target = 'answer.ts' AND wrongMethod('PUT instead of PATCH')_
    - _Expected_Behavior: answer upsert uses PATCH; matches backend route handler_
    - _Requirements: 2.65_

  - [x] 13.6 Remove `getAdminStats()` from `auth.ts`
    - Remove the `getAdminStats()` function from `frontend/src/apis/auth.ts` (endpoint does not exist on backend)
    - Update any component that calls `getAdminStats()` to use the analytics dashboard endpoint instead
    - _Bug_Condition: isBugCondition(input) where input.target = 'auth.ts getAdminStats' AND wrongURL('/auth/admin/stats does not exist')_
    - _Expected_Behavior: no calls to non-existent /auth/admin/stats endpoint_
    - _Requirements: 2.66_

  - [x] 13.7 Fix all TypeScript type mismatches in `frontend/src/lib/types.ts`
    - `Submission`: rename `attempts_count` → `attempts`; add `submitted_at: string | null`
    - `SubmissionAttempt`: remove `attempt_number` and `scan_pages` fields; use `id` as attempt number
    - `AdminDashboard` and `StudentDashboard`: rename `total_graded_submissions`/`total_pending_submissions` → `graded_submissions`/`pending_submissions`; add `active_courses` and `completed_courses` to `StudentDashboard`
    - `Exam`: replace `course: Course | null` with `course_id: string | null`; add `end_time: string | null`; remove `student_id`
    - `Enrollment`: replace `student: User` and `course: Course` with `student_id: string` and `course_id: string`
    - `Tenant`: add `domain`, `is_active`, `is_deleted`, `deleted_at`, `tenant_code` fields
    - `Invoice`: update `InvoiceStatus` to `'pending' | 'paid' | 'overdue' | 'cancelled'`; add `payment_reference`, `payment_gateway`, `paid_at`, `payment_url`
    - `CurrentUsage`: align with backend model fields
    - _Bug_Condition: isBugCondition(input) where input.target = 'types.ts' AND typeMismatch_
    - _Expected_Behavior: all TypeScript types exactly mirror backend model fields; no type errors_
    - _Preservation: components using existing correct fields continue to work (3.47–3.55)_
    - _Requirements: 2.68–2.86, 3.47–3.55_

  - [x] 13.8 Create `frontend/src/apis/billing.ts`
    - Implement API functions for: `listInvoices`, `getInvoice`, `listBillingPlans`, `getBillingPlan`, `listPaymentMethods`, `getUsage`, `listSemesters`, `getSemester`
    - Use correct URLs under `/api/v1/billing/`
    - _Requirements: 2.56_

  - [x] 13.9 Create `frontend/src/apis/semester.ts`
    - Implement semester-specific API functions if separated from billing.ts
    - _Requirements: 2.56_

  - [x] 13.10 Fix `QuestionCreate` field names in `frontend/src/apis/exam.ts`
    - Rename `question_text` → `text`, `question_type` → `qtype`, `marks` → `mark` in `QuestionCreate` interface
    - Apply same corrections to `QuestionUpdate` interface
    - _Bug_Condition: isBugCondition(input) where input.target = 'exam.ts QuestionCreate' AND typeMismatch('wrong field names')_
    - _Expected_Behavior: question create/update payloads use correct field names matching backend schema_
    - _Preservation: QuestionUpdate interface updated consistently (3.54)_
    - _Requirements: 2.84, 3.54_

  - [x] 13.11 Fix `listQuestions` to pass `exam_id` filter
    - In `frontend/src/apis/exam.ts`: update `listQuestions(examId, params?)` to include `exam_id: examId` in the query params object
    - _Bug_Condition: isBugCondition(input) where input.target = 'exam.ts listQuestions' AND defectPresent('exam_id not passed as query param')_
    - _Expected_Behavior: listQuestions sends exam_id as query parameter; returns questions for the correct exam_
    - _Preservation: function signature unchanged (3.55)_
    - _Requirements: 2.85, 3.55_


<!-- ============================================================
     PHASE 12 — API DOCUMENTATION
     ============================================================ -->

- [x] 14. Create API documentation and Postman collection

  - [x] 14.1 Create `docs/API.md` covering all endpoints
    - Document every endpoint across all domains (account, academic, billing, analytics, health)
    - For each endpoint: method, path, required headers (`Authorization`, `X-Tenant-ID`), request body schema, example response
    - _Bug_Condition: isBugCondition(input) where input.target = 'docs/API.md' AND defectPresent('file does not exist')_
    - _Expected_Behavior: developers can find all endpoint documentation in docs/API.md_
    - _Preservation: no source code modified (3.41)_
    - _Requirements: 2.56_

  - [x] 14.2 Create `docs/Wazire.postman_collection.json`
    - Create Postman collection covering all endpoints across all domains
    - Include example request bodies, headers, and environment variables
    - _Requirements: 2.56_


<!-- ============================================================
     PHASE 13 — TEST INFRASTRUCTURE & COVERAGE
     ============================================================ -->

- [x] 15. Set up test infrastructure and write comprehensive test coverage

  - [x] 15.1 Set up pytest + pytest-cov configuration (`backend/pyproject.toml`)
    - Add `pytest`, `pytest-asyncio`, `pytest-cov`, `httpx` to `backend/requirements.txt`
    - Create `backend/pyproject.toml` with `[tool.pytest.ini_options]` and `[tool.coverage.run]` sections
    - Configure `--cov=.`, `--cov-branch`, `--cov-fail-under=90`
    - Exclude `alembic/env.py`, `seed_db.py` from coverage measurement
    - _Requirements: 2.87, 2.89, 2.93_

  - [x] 15.2 Set up Vitest + `@vitest/coverage-v8` (`frontend/vitest.config.ts`)
    - Add `vitest`, `@vitest/coverage-v8`, `@testing-library/react`, `msw` to `frontend/package.json` devDependencies
    - Create `frontend/vitest.config.ts` with `coverage.provider = 'v8'` and `coverage.thresholds = { lines: 90, branches: 90 }`
    - _Requirements: 2.88, 2.92_

  - [x] 15.3 Set up MSW mock handlers (`frontend/src/mocks/`)
    - Create `frontend/src/mocks/handlers.ts` with MSW handlers for all backend API endpoints
    - Create `frontend/src/mocks/server.ts` for Node.js test environment setup
    - _Requirements: 2.100_

  - [x] 15.4 Write backend unit tests (services, task handlers, model methods, utilities, KafkaManager, GroqKeyRotator)
    - Create `backend/tests/unit/services/` mirroring service module structure
    - Every public service method: happy path + at least one error/edge case (mocked DB, Redis, Kafka)
    - Every Kafka task handler: invoked directly with mock payload; assert service calls and Kafka emissions
    - Every model `to_dict()`, `delete()`, `restore()`, `lock()` method
    - Every utility function in `backend/core/utils/` (encryption, token, response, sanitization, validation)
    - `KafkaManager.emit()` with mocked producer: assert correct topic and payload
    - `GroqKeyRotator.get_key()` with mocked Redis: all keys available, some cooling, all cooling
    - Worker dispatcher: handler registration and correct dispatch by event type
    - Test files MUST NOT import from `main.py` or `worker.py`
    - _Requirements: 2.95, 2.96, 2.97, 2.94_

  - [x] 15.5 Write backend integration tests (all API routes)
    - Use `pytest-asyncio` with `httpx.AsyncClient` against a real test PostgreSQL database (`TEST_DATABASE_URL`)
    - Cover: auth (register, login, refresh, me), course CRUD, exam CRUD and status transitions, question CRUD, enrollment (enroll, list, bulk enroll), answer PATCH (verify Kafka event produced with mocked Kafka), submission (create, submit, get), dashboard GET (read-only, no inline writes), billing (invoices, plans, payment methods, usage, semesters)
    - _Requirements: 2.98, 3.62_

  - [x] 15.6 Write backend E2E scenario tests (full exam lifecycle, force submit, concurrent UPSERT)
    - Scenario 1 — Full exam lifecycle: tenant creation → users → course → enrollment → exam → questions → Redis preload → student answers via PATCH → Kafka → worker UPSERT → submission → grading → dashboard update
    - Scenario 2 — Force submit: exam time expires → scheduler emits `FORCE_SUBMIT_EXAM` → worker auto-submits unsubmitted students → grading triggered
    - Scenario 3 — Concurrent answer UPSERT idempotency: 100 concurrent PATCH answer requests for same `(student, exam, question)` → assert exactly one row in `student_answers`
    - _Requirements: 2.99_

  - [x] 15.7 Write frontend unit tests (API functions, components, AuthContext)
    - Every API function in `apis/*.ts`: assert correct URL, HTTP method, request payload shape, response parsing
    - Every utility function in `utils/*.ts`
    - Every shared component: `@testing-library/react` render test with representative props
    - `AuthContext` login, logout, register, token storage: each with unit tests
    - _Requirements: 2.100, 3.63_

  - [x] 15.8 Write frontend integration tests (page components with MSW)
    - Every page component (Login, Dashboard, Courses, Exams, TakeExam, UserManagement): Vitest + MSW integration test
    - Cover: form submission → correct API call, correct rendering of mocked responses, navigation/redirect behaviour
    - _Requirements: 2.101_

  - [x] 15.9 Set up Playwright (`frontend/playwright.config.ts`)
    - Create `frontend/playwright.config.ts` targeting the application
    - Install Playwright browsers
    - _Requirements: 2.101_

  - [x] 15.10 Write Playwright E2E tests (3 critical paths)
    - Path (a): student login → navigate to exam → take exam → submit → see result
    - Path (b): lecturer login → create course → create exam → add questions → publish
    - Path (c): admin login → manage users → view dashboard
    - _Requirements: 2.101_


<!-- ============================================================
     PHASE 14 — CI/CD PIPELINE
     ============================================================ -->

- [x] 16. Set up CI/CD pipeline, coverage reporting, and environment documentation

  - [x] 16.1 Create `.github/workflows/ci.yml` (backend + frontend + playwright jobs)
    - `backend` job: lint (`ruff`), type-check (`mypy`), test with coverage (`pytest --cov --cov-fail-under=90`), upload to Codecov
    - `frontend` job: lint (`eslint`), type-check (`tsc --noEmit`), test with coverage (`vitest --run --coverage`), upload to Codecov
    - `playwright` job: runs after backend + frontend jobs; installs browsers; runs `npx playwright test`
    - Trigger on `push` (all branches) and `pull_request` (targeting `main` and `develop`)
    - _Bug_Condition: isBugCondition(input) where input.target = '.github/workflows/ci.yml' AND defectPresent('no CI pipeline')_
    - _Expected_Behavior: CI runs automatically on push/PR; blocks merge if any job fails_
    - _Preservation: no existing source code modified (3.58)_
    - _Requirements: 2.89, 2.93_

  - [x] 16.2 Create `.codecov.yml`
    - Configure Codecov to aggregate backend and frontend coverage reports
    - Set overall coverage threshold to 90%
    - _Requirements: 2.90, 2.92_

  - [x] 16.3 Add Codecov badge to `README.md`
    - Prepend Codecov badge near the top of `README.md` linking to `https://codecov.io/gh/oscaroguledo/wazire`
    - _Bug_Condition: isBugCondition(input) where input.target = 'README.md' AND defectPresent('no coverage badge')_
    - _Expected_Behavior: README displays current coverage percentage; badge updates after each CI run_
    - _Preservation: all existing README content unchanged below the badge (3.59)_
    - _Requirements: 2.91, 3.59_

  - [x] 16.4 Update `backend/.env.example` and `frontend/.env.example` with all variables
    - `backend/.env.example`: add all missing variables — `GROQ_API_KEY_1`–`GROQ_API_KEY_4`, `PAYSTACK_SECRET_KEY`, `MONNIFY_API_KEY`, `MONNIFY_SECRET_KEY`, `KAFKA_CONSUMER_GROUP_ID`, `LOG_LEVEL`, `DEBUG`, `GUNICORN_WORKERS`, `GRADING_CONCURRENCY_PER_TENANT`, `GRADING_BATCH_SIZE`, `DB_WRITE_BATCH_SIZE`, `FRONTEND_ORIGIN`, `KAFKA_GRADING_PARTITIONS`
    - `frontend/.env.example`: add all missing variables
    - Each variable has a comment explaining its purpose and an example/placeholder value
    - No secret values committed — only placeholder strings
    - _Requirements: 2.138_

  - [x] 16.5 Document conventional commits and branch strategy
    - Add a `CONTRIBUTING.md` or section in `README.md` documenting: Conventional Commits format (`fix`, `feat`, `chore`, `refactor`, `test`, `docs`, `ci` with scopes), branch strategy (`fix/app-wide-refactor` → `main`), PR requirements (CI must pass, title ≤ 70 chars)
    - _Requirements: 2.140, 2.141_

<!-- ============================================================
     FINAL CHECKPOINT
     ============================================================ -->

- [ ] 17. Checkpoint — Ensure all tests pass
  - Run `pytest --cov --cov-fail-under=90` in `backend/` — all tests must pass
  - Run `npx vitest --run --coverage` in `frontend/` — all tests must pass
  - Run `npx playwright test` in `frontend/` — all E2E tests must pass
  - Verify CI pipeline passes on all jobs (backend, frontend, playwright)
  - Verify Codecov reports ≥ 90% combined coverage
  - Ensure all tasks in phases 1–14 are marked complete
  - Ask the user if any questions arise before opening the PR
  - _Requirements: 2.87, 2.88, 2.89, 2.90, 2.91, 2.92_
