# Wazire API Documentation

Base URL: `http://localhost:8000/api/v1`

All endpoints (except `/health` and webhooks) require:
- `Authorization: Bearer <access_token>` header
- `X-Tenant-ID: <tenant_uuid>` header (for tenant-scoped operations)

All responses follow the envelope shape:
```json
{"success": true, "message": "...", "data": ..., "page": 1, "per_page": 20, "total": 100}
```

---

## Table of Contents

1. [Health](#health)
2. [Authentication & Users](#authentication--users)
3. [Tenants](#tenants)
4. [Courses](#courses)
5. [Exams](#exams)
6. [Questions](#questions)
7. [Answers](#answers)
8. [Enrollments](#enrollments)
9. [Students](#students)
10. [Submissions](#submissions)
11. [Analytics / Dashboard](#analytics--dashboard)
12. [Billing — Invoices](#billing--invoices)
13. [Billing — Plans](#billing--plans)
14. [Billing — Payment Methods](#billing--payment-methods)
15. [Billing — Usage](#billing--usage)
16. [Billing — Semesters](#billing--semesters)
17. [Billing — Webhooks](#billing--webhooks)

---

## Health

### `GET /api/v1/health`

Probes DB, Redis, and Kafka connectivity. No authentication required.

**Response 200**
```json
{
  "status": "ok",
  "db": "ok",
  "redis": "ok",
  "kafka": "ok"
}
```
> `status` is `"degraded"` when any dependency is unhealthy; HTTP status is always 200.

---

## Authentication & Users

All auth routes are mounted under `/api/v1/auth`.

### `POST /api/v1/auth/register`

Register a new user. Superadmin registration is blocked (seed script only).

**Headers:** none required

**Request Body**
```json
{
  "email": "student@example.com",
  "password": "SecurePass123!",
  "first_name": "Ada",
  "last_name": "Lovelace",
  "role": "student",
  "tenant_code": "ABC123"
}
```
> `tenant_code` is required for `role=student` or `role=lecturer`. Ignored for `role=admin`.

**Response 201**
```json
{
  "success": true,
  "message": "Registered successfully",
  "data": {
    "id": "uuid",
    "email": "student@example.com",
    "first_name": "Ada",
    "last_name": "Lovelace",
    "role": "student",
    "tenant_id": "uuid",
    "is_active": true,
    "created_at": "2026-05-07T10:00:00Z"
  }
}
```

**Error Responses**
| Status | Condition |
|--------|-----------|
| 400 | Email already registered |
| 400 | `tenant_code` missing for lecturer/student |
| 403 | Attempted superadmin self-registration |
| 404 | `tenant_code` not found |

---

### `POST /api/v1/auth/login`

Authenticate and receive JWT tokens.

**Headers:** `X-Tenant-ID` (optional — scopes login to a specific tenant)

**Request Body**
```json
{
  "email": "admin@example.com",
  "password": "SecurePass123!"
}
```

**Response 200**
```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "user": {
      "id": "uuid",
      "email": "admin@example.com",
      "role": "admin",
      "tenant_id": "uuid"
    },
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "bearer"
  }
}
```

**Error Responses**
| Status | Condition |
|--------|-----------|
| 401 | Invalid email or password |

---

### `POST /api/v1/auth/refresh`

Exchange a refresh token for a new access token.

**Request Body**
```json
{
  "refresh_token": "eyJ..."
}
```

**Response 200**
```json
{
  "success": true,
  "message": "Token refreshed",
  "data": {
    "access_token": "eyJ...",
    "token_type": "bearer"
  }
}
```

**Error Responses**
| Status | Condition |
|--------|-----------|
| 401 | Invalid or expired refresh token |

---

### `GET /api/v1/auth/me`

Return the currently authenticated user's profile.

**Headers:** `Authorization: Bearer <token>`

**Response 200**
```json
{
  "success": true,
  "message": "Profile retrieved",
  "data": {
    "id": "uuid",
    "email": "admin@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "role": "admin",
    "tenant_id": "uuid",
    "is_active": true
  }
}
```

---

### `PUT /api/v1/auth/me`

Update the currently authenticated user's own profile.

**Headers:** `Authorization: Bearer <token>`

**Request Body** (all fields optional)
```json
{
  "first_name": "Jane",
  "last_name": "Doe",
  "password": "NewPass456!"
}
```

**Response 200**
```json
{
  "success": true,
  "message": "Profile updated",
  "data": { "id": "uuid", "first_name": "Jane", "last_name": "Doe" }
}
```

---

### `GET /api/v1/auth/`

List users. Restricted to lecturers and admins.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters**
| Param | Type | Description |
|-------|------|-------------|
| `page` | int | Page number (default 1) |
| `per_page` | int | Items per page (default 10, max 100) |
| `is_active` | bool | Filter by active status |
| `tenant_id` | uuid | Filter by tenant (admin only) |

**Response 200**
```json
{
  "success": true,
  "message": "Users retrieved",
  "data": [{ "id": "uuid", "email": "...", "role": "student" }],
  "page": 1,
  "per_page": 10,
  "total": 42
}
```

---

### `GET /api/v1/auth/{user_id}`

Get a specific user by ID. Restricted to lecturers and admins.

**Headers:** `Authorization: Bearer <token>`

**Response 200**
```json
{
  "success": true,
  "message": "User retrieved",
  "data": { "id": "uuid", "email": "...", "role": "student", "tenant_id": "uuid" }
}
```

**Error Responses**
| Status | Condition |
|--------|-----------|
| 404 | User not found |

---

### `PUT /api/v1/auth/{user_id}`

Update a user (admin only).

**Headers:** `Authorization: Bearer <token>`

**Request Body** (all fields optional)
```json
{
  "first_name": "Updated",
  "is_active": false
}
```

**Response 200**
```json
{ "success": true, "message": "User updated", "data": { "id": "uuid" } }
```

---

### `DELETE /api/v1/auth/{user_id}`

Soft-delete a user (admin only). Cannot delete your own account.

**Headers:** `Authorization: Bearer <token>`

**Response 204**
```json
{ "success": true, "message": "User deleted successfully" }
```

---

## Tenants

All tenant routes are mounted under `/api/v1/tenants`. Restricted to admins.

### `POST /api/v1/tenants/`

Create a new tenant institution. The calling admin is automatically linked as owner.

**Headers:** `Authorization: Bearer <token>`

**Request Body**
```json
{
  "name": "University of Lagos",
  "domain": "unilag.edu.ng",
  "address": "Akoka, Lagos"
}
```

**Response 201**
```json
{
  "success": true,
  "message": "Tenant created successfully",
  "data": {
    "id": "uuid",
    "name": "University of Lagos",
    "domain": "unilag.edu.ng",
    "tenant_code": "XK9P2A",
    "is_active": true,
    "created_at": "2026-05-07T10:00:00Z"
  }
}
```

**Error Responses**
| Status | Condition |
|--------|-----------|
| 400 | Admin already has a tenant |

---

### `GET /api/v1/tenants/`

Get the current admin's tenant.

**Headers:** `Authorization: Bearer <token>`

**Response 200**
```json
{
  "success": true,
  "message": "Tenant retrieved successfully",
  "data": { "id": "uuid", "name": "...", "tenant_code": "XK9P2A" }
}
```

---

### `GET /api/v1/tenants/{tenant_id}`

Get a specific tenant by ID.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters**
| Param | Type | Description |
|-------|------|-------------|
| `tenant_code` | string | Optional additional lookup by code |

**Response 200**
```json
{
  "success": true,
  "message": "Tenant retrieved successfully",
  "data": { "id": "uuid", "name": "...", "tenant_code": "XK9P2A", "start_date": null, "end_date": null }
}
```

**Error Responses**
| Status | Condition |
|--------|-----------|
| 404 | Tenant not found |

---

### `PUT /api/v1/tenants/{tenant_id}`

Update a tenant.

**Headers:** `Authorization: Bearer <token>`

**Request Body** (all fields optional)
```json
{
  "name": "Updated University Name",
  "domain": "new-domain.edu.ng",
  "start_date": "2026-01-01T00:00:00Z",
  "end_date": "2027-01-01T00:00:00Z"
}
```

**Response 200**
```json
{ "success": true, "message": "Tenant updated successfully", "data": { "id": "uuid" } }
```

---

### `DELETE /api/v1/tenants/{tenant_id}`

Soft-delete a tenant. Blocked if the tenant has associated users, courses, or exams.

**Headers:** `Authorization: Bearer <token>`

**Response 200**
```json
{ "success": true, "message": "Tenant deleted successfully" }
```

**Error Responses**
| Status | Condition |
|--------|-----------|
| 400 | Tenant has associated users / courses / exams |
| 404 | Tenant not found |

---

### `POST /api/v1/tenants/{tenant_id}/restore`

Restore a soft-deleted tenant.

**Headers:** `Authorization: Bearer <token>`

**Response 200**
```json
{ "success": true, "message": "Tenant restored successfully", "data": { "id": "uuid" } }
```

---

## Courses

All course routes are mounted under `/api/v1/academic/courses`.

### `POST /api/v1/academic/courses/`

Create a course. Lecturers are automatically set as the course lecturer.

**Headers:** `Authorization: Bearer <token>`, `X-Tenant-ID: <uuid>`

**Request Body**
```json
{
  "name": "Introduction to Algorithms",
  "course_code": "CSC301",
  "description": "Fundamental algorithms and data structures",
  "lecturer_id": "uuid"
}
```

**Response 201**
```json
{
  "success": true,
  "message": "Course created",
  "data": {
    "id": "uuid",
    "name": "Introduction to Algorithms",
    "course_code": "CSC301",
    "lecturer_id": "uuid",
    "tenant_id": "uuid",
    "created_at": "2026-05-07T10:00:00Z"
  }
}
```

---

### `GET /api/v1/academic/courses/`

List courses. Lecturers only see their own courses.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters**
| Param | Type | Description |
|-------|------|-------------|
| `page` | int | Page number (default 1) |
| `per_page` | int | Items per page (default 50) |
| `lecturer_id` | uuid | Filter by lecturer (admin only) |

**Response 200**
```json
{
  "success": true,
  "message": "Courses retrieved",
  "data": [{ "id": "uuid", "name": "...", "course_code": "CSC301" }],
  "page": 1, "per_page": 50, "total": 12
}
```

---

### `GET /api/v1/academic/courses/{course_id}`

Get a single course.

**Response 200**
```json
{ "success": true, "message": "Course retrieved", "data": { "id": "uuid", "name": "..." } }
```

---

### `PUT /api/v1/academic/courses/{course_id}`

Update a course (lecturer or admin).

**Request Body** (all fields optional)
```json
{ "name": "Advanced Algorithms", "lecturer_id": "uuid" }
```

**Response 200**
```json
{ "success": true, "message": "Course updated", "data": { "id": "uuid" } }
```

---

### `GET /api/v1/academic/courses/{course_id}/students`

List all students enrolled in a course. Restricted to lecturers and admins.

**Query Parameters**
| Param | Type | Description |
|-------|------|-------------|
| `page` | int | Page number (default 1) |
| `per_page` | int | Items per page (default 50) |

**Response 200**
```json
{
  "success": true,
  "message": "Course students retrieved",
  "data": [
    { "student_id": "uuid", "first_name": "Ada", "last_name": "Lovelace", "enrollment_status": "active" }
  ],
  "page": 1, "per_page": 50, "total": 30
}
```

---

### `DELETE /api/v1/academic/courses/{course_id}`

Delete a course (lecturer or admin).

**Response 204**
```json
{ "success": true, "message": "Course deleted" }
```

---

## Exams

All exam routes are mounted under `/api/v1/academic/exams`.

### `POST /api/v1/academic/exams/`

Create an exam. `start_time` must be a UTC-aware ISO 8601 datetime.

**Headers:** `Authorization: Bearer <token>`, `X-Tenant-ID: <uuid>`

**Request Body**
```json
{
  "title": "CSC301 Mid-Semester Exam",
  "course_id": "uuid",
  "start_time": "2026-06-01T09:00:00Z",
  "duration_hours": 2,
  "duration_minutes": 0,
  "instructions": "Answer all questions."
}
```

**Response 201**
```json
{
  "success": true,
  "message": "Exam created",
  "data": {
    "id": "uuid",
    "title": "CSC301 Mid-Semester Exam",
    "course_id": "uuid",
    "start_time": "2026-06-01T09:00:00Z",
    "end_time": "2026-06-01T11:00:00Z",
    "duration": 2.0,
    "status": "not_started",
    "tenant_id": "uuid"
  }
}
```

---

### `GET /api/v1/academic/exams/`

List exams. Students only see exams for their enrolled courses.

**Query Parameters**
| Param | Type | Description |
|-------|------|-------------|
| `page` | int | Page number (default 1) |
| `per_page` | int | Items per page (default 50) |
| `course_id` | uuid | Filter by course |
| `status` | string | Filter by status (`not_started`, `in_progress`, `finished`) |
| `year` | int | Filter by exam year |

**Response 200**
```json
{
  "success": true,
  "message": "Exams retrieved",
  "data": [{ "id": "uuid", "title": "...", "start_time": "...", "end_time": "...", "status": "not_started" }],
  "page": 1, "per_page": 50, "total": 5
}
```

---

### `GET /api/v1/academic/exams/years`

Get distinct years from exam `start_time` values.

**Response 200**
```json
{ "success": true, "message": "Exam years retrieved", "data": [2025, 2026] }
```

---

### `GET /api/v1/academic/exams/{exam_id}`

Get a single exam.

**Response 200**
```json
{ "success": true, "message": "Exam retrieved", "data": { "id": "uuid", "title": "...", "end_time": "..." } }
```

---

### `PUT /api/v1/academic/exams/{exam_id}`

Update an exam (lecturer or admin). `start_time` must be UTC-aware.

**Request Body** (all fields optional)
```json
{
  "title": "Updated Title",
  "start_time": "2026-06-02T09:00:00Z",
  "duration_hours": 3
}
```

**Response 200**
```json
{ "success": true, "message": "Exam updated", "data": { "id": "uuid", "end_time": "2026-06-02T12:00:00Z" } }
```

---

### `GET /api/v1/academic/exams/{exam_id}/results`

List all submission results for an exam. Restricted to lecturers and admins.

**Query Parameters**
| Param | Type | Description |
|-------|------|-------------|
| `page` | int | Page number (default 1) |
| `per_page` | int | Items per page (default 50) |

**Response 200**
```json
{
  "success": true,
  "message": "Exam results retrieved",
  "data": [
    {
      "student_id": "uuid",
      "latest_score": "85.50",
      "status": "graded",
      "graded_at": "2026-06-01T11:30:00Z",
      "submitted_at": "2026-06-01T10:55:00Z"
    }
  ],
  "page": 1, "per_page": 50, "total": 28
}
```

---

### `POST /api/v1/academic/exams/{exam_id}/scan`

Upload answer sheet image(s) for extraction. Restricted to lecturers and admins.

- Batches of **≤ 5 pages**: synchronous extraction, returns answers immediately (HTTP 202).
- Batches of **> 5 pages**: async via Kafka `PARSE_AND_CREATE` event (HTTP 202).

**Headers:** `Authorization: Bearer <token>`, `Content-Type: multipart/form-data`

**Form Fields**
| Field | Type | Description |
|-------|------|-------------|
| `pages` | file[] | One or more answer sheet image files |
| `student_id` | uuid | (optional) Student the sheet belongs to |

**Response 202 (sync)**
```json
{
  "success": true,
  "message": "Answer sheet extracted from 2 page(s)",
  "data": {
    "exam_id": "uuid",
    "student_id": "uuid",
    "answers": { "question-uuid": "B", "question-uuid-2": "Paris" },
    "raw_by_number": { "1": "B", "2": "Paris" }
  }
}
```

**Response 202 (async)**
```json
{
  "success": true,
  "message": "Answer sheet extraction queued for 8 pages. Results will be available shortly.",
  "data": { "exam_id": "uuid", "pages_queued": 8 }
}
```

---

### `DELETE /api/v1/academic/exams/{exam_id}`

Delete an exam (lecturer or admin).

**Response 204**
```json
{ "success": true, "message": "Exam deleted" }
```

---

## Questions

All question routes are mounted under `/api/v1/academic/questions`.

### `POST /api/v1/academic/questions/`

Create a question (lecturer or admin).

**Headers:** `Authorization: Bearer <token>`

**Request Body**
```json
{
  "text": "What is the time complexity of binary search?",
  "qtype": "multiple_choice",
  "mark": 2.0,
  "number": "1",
  "exam_ids": ["uuid"],
  "options": [
    { "text": "O(n)", "is_correct": false },
    { "text": "O(log n)", "is_correct": true },
    { "text": "O(n^2)", "is_correct": false }
  ]
}
```
> `qtype` values: `multiple_choice`, `fill_in_the_blank`, `theory`

**Response 201**
```json
{
  "success": true,
  "message": "Question created",
  "data": { "id": "uuid", "text": "...", "qtype": "multiple_choice", "mark": 2.0 }
}
```

---

### `GET /api/v1/academic/questions/`

List questions. When `exam_id` is provided, serves from Redis cache first.

**Query Parameters**
| Param | Type | Description |
|-------|------|-------------|
| `exam_id` | uuid | Filter by exam (Redis-first) |

**Response 200**
```json
{ "success": true, "message": "Questions retrieved", "data": [{ "id": "uuid", "text": "..." }] }
```

---

### `GET /api/v1/academic/questions/exam/{exam_id}`

Get all questions for a specific exam. Served from Redis cache when available.

**Response 200**
```json
{ "success": true, "message": "Exam questions retrieved", "data": [{ "id": "uuid", "text": "..." }] }
```

---

### `GET /api/v1/academic/questions/{question_id}`

Get a single question.

**Response 200**
```json
{ "success": true, "message": "Question retrieved", "data": { "id": "uuid", "text": "...", "qtype": "theory" } }
```

---

### `PUT /api/v1/academic/questions/{question_id}`

Update a question (lecturer or admin).

**Request Body** (all fields optional)
```json
{ "text": "Updated question text", "mark": 5.0 }
```

**Response 200**
```json
{ "success": true, "message": "Question updated", "data": { "id": "uuid" } }
```

---

### `DELETE /api/v1/academic/questions/{question_id}`

Delete a question (lecturer or admin).

**Response 204**
```json
{ "success": true, "message": "Question deleted" }
```

---

### `POST /api/v1/academic/questions/upload-exam-paper`

Upload a scanned/typed exam paper as base64 images. Questions are extracted and created asynchronously via Kafka `PARSE_AND_CREATE` event.

**Request Body**
```json
{
  "pages": ["<base64-image-1>", "<base64-image-2>"],
  "exam_id": "uuid",
  "industry": "computer_science",
  "mark_per_question": 2.0
}
```

**Response 202**
```json
{
  "success": true,
  "message": "Exam paper upload started — questions will be created in the background",
  "data": { "job_id": "uuid" }
}
```

---

## Answers

All answer routes are mounted under `/api/v1/academic/answers`.

### `PATCH /api/v1/academic/answers/{question_id}`

Save a student's answer during an exam. Returns immediately (optimistic acknowledgement); the actual DB write is performed asynchronously by the Kafka worker via `UPSERT_STUDENT_ANSWER`.

**Headers:** `Authorization: Bearer <token>`, `X-Tenant-ID: <uuid>`

**Request Body**
```json
{
  "exam_id": "uuid",
  "answer": "B"
}
```

**Response 200**
```json
{
  "success": true,
  "message": "Answer saved",
  "data": {
    "student_id": "uuid",
    "exam_id": "uuid",
    "question_id": "uuid",
    "answer": "B"
  }
}
```

**Error Responses**
| Status | Condition |
|--------|-----------|
| 503 | Kafka unavailable — client should retry |

---

### `GET /api/v1/academic/answers/student`

Get the current student's saved answers for an exam.

**Query Parameters**
| Param | Type | Description |
|-------|------|-------------|
| `exam_id` | uuid | **Required** — exam to retrieve answers for |

**Response 200**
```json
{
  "success": true,
  "message": "Answers retrieved",
  "data": [{ "question_id": "uuid", "answer": "B", "updated_at": "..." }]
}
```

---

### `GET /api/v1/academic/answers/`

List all answer records (lecturer/admin only).

**Query Parameters**
| Param | Type | Description |
|-------|------|-------------|
| `page` | int | Page number (default 1) |
| `per_page` | int | Items per page (default 50) |

**Response 200**
```json
{ "success": true, "data": [...], "page": 1, "per_page": 50, "total": 200 }
```

---

### `POST /api/v1/academic/answers/`

Create an answer record (lecturer/admin only — for seeding correct answers).

**Request Body**
```json
{ "exam_id": "uuid", "answer": "B" }
```

**Response 201**
```json
{ "success": true, "message": "Answer created", "data": { "id": "uuid" } }
```

---

### `GET /api/v1/academic/answers/{answer_id}`

Get a specific answer record (lecturer/admin only).

**Response 200**
```json
{ "success": true, "message": "Answer retrieved", "data": { "id": "uuid", "answer": "B" } }
```

---

### `DELETE /api/v1/academic/answers/{answer_id}`

Delete an answer record (lecturer/admin only).

**Response 204**
```json
{ "success": true, "message": "Answer deleted" }
```

---

## Enrollments

All enrollment routes are mounted under `/api/v1/academic/enrollment`.

### `GET /api/v1/academic/enrollment/`

List enrollments with optional filters.

**Query Parameters**
| Param | Type | Description |
|-------|------|-------------|
| `page` | int | Page number (default 1) |
| `per_page` | int | Items per page (default 10, max 100) |
| `student_id` | uuid | Filter by student |
| `course_id` | uuid | Filter by course |
| `lecturer_id` | uuid | Filter by lecturer |
| `enrollment_status` | string | `active`, `inactive`, `completed` |
| `semester` | string | Semester filter |

**Response 200**
```json
{ "success": true, "data": [...], "page": 1, "per_page": 10, "total": 50 }
```

---

### `GET /api/v1/academic/enrollment/check/`

Check if a student is enrolled in a course.

**Query Parameters**
| Param | Type | Description |
|-------|------|-------------|
| `student_id` | uuid | **Required** |
| `course_id` | uuid | **Required** |

**Response 200**
```json
{ "success": true, "data": { "student_id": "uuid", "course_id": "uuid", "status": "active" } }
```

---

### `GET /api/v1/academic/enrollment/student/{student_id}`

Get all enrollments for a specific student. Students can only access their own.

**Response 200**
```json
{ "success": true, "data": [...], "page": 1, "per_page": 10, "total": 5 }
```

---

### `GET /api/v1/academic/enrollment/course/{course_id}`

Get all enrollments for a specific course.

**Query Parameters:** `page`, `per_page`, `enrollment_status`, `semester`, `year`

**Response 200**
```json
{ "success": true, "data": [...], "page": 1, "per_page": 10, "total": 30 }
```

---

### `GET /api/v1/academic/enrollment/lecturer/{lecturer_id}`

Get all enrollments for courses taught by a lecturer. Lecturers can only access their own.

**Response 200**
```json
{ "success": true, "data": [...], "page": 1, "per_page": 10, "total": 80 }
```

---

### `GET /api/v1/academic/enrollment/{enrollment_id}`

Get a single enrollment record.

**Response 200**
```json
{ "success": true, "data": { "id": "uuid", "student_id": "uuid", "course_id": "uuid", "status": "active" } }
```

---

### `POST /api/v1/academic/enrollment/`

Enroll a student in a course (lecturer or admin).

**Request Body**
```json
{
  "student_id": "uuid",
  "course_id": "uuid",
  "semester": "first",
  "year": 2026
}
```

**Response 201**
```json
{ "success": true, "data": { "id": "uuid", "student_id": "uuid", "course_id": "uuid", "status": "active" } }
```

---

### `POST /api/v1/academic/enrollment/bulk/`

Bulk enroll multiple students (lecturer or admin).

**Request Body**
```json
{
  "enrollments": [
    { "student_id": "uuid", "course_id": "uuid", "semester": "first", "year": 2026 }
  ]
}
```

**Response 201**
```json
{ "success": true, "data": [{ "id": "uuid" }] }
```

---

### `PUT /api/v1/academic/enrollment/{enrollment_id}`

Update an enrollment record.

**Request Body** (all fields optional)
```json
{ "status": "completed" }
```

**Response 200**
```json
{ "success": true, "data": { "id": "uuid", "status": "completed" } }
```

---

### `DELETE /api/v1/academic/enrollment/{enrollment_id}`

Remove an enrollment (lecturer or admin).

**Response 204** — no body

---

## Students

### `GET /api/v1/academic/students/{student_id}/exams`

Get all exams for courses the student is enrolled in.

- Students can only query their own `student_id`.
- Admins and lecturers can query any student within their tenant.

**Query Parameters**
| Param | Type | Description |
|-------|------|-------------|
| `page` | int | Page number (default 1) |
| `per_page` | int | Items per page (default 50) |

**Response 200**
```json
{
  "success": true,
  "message": "Student exams retrieved",
  "data": [
    {
      "id": "uuid",
      "title": "CSC301 Mid-Semester Exam",
      "start_time": "2026-06-01T09:00:00Z",
      "end_time": "2026-06-01T11:00:00Z",
      "status": "not_started",
      "duration": 2.0,
      "course_id": "uuid"
    }
  ],
  "page": 1, "per_page": 50, "total": 3
}
```

**Error Responses**
| Status | Condition |
|--------|-----------|
| 403 | Student querying another student's exams |

---

## Submissions

All submission routes are mounted under `/api/v1/academic/submissions`.

### `POST /api/v1/academic/submissions/start`

Create a `Submission` record when a student clicks **Start Exam**. Students only.

**Headers:** `Authorization: Bearer <token>`, `X-Tenant-ID: <uuid>`

**Request Body**
```json
{ "exam_id": "uuid" }
```

**Response 201**
```json
{
  "success": true,
  "message": "Submission started",
  "data": { "id": "uuid", "exam_id": "uuid", "student_id": "uuid", "status": "pending" }
}
```

---

### `POST /api/v1/academic/submissions/`

Submit a completed exam attempt. Grading is triggered asynchronously via Kafka. Students only.

**Headers:** `Authorization: Bearer <token>`, `X-Tenant-ID: <uuid>`

**Request Body**
```json
{ "exam_id": "uuid" }
```

**Response 201**
```json
{
  "success": true,
  "message": "Attempt #1 submitted — grading in progress",
  "data": {
    "submission": { "id": "uuid", "exam_id": "uuid", "status": "submitted", "submitted_at": "2026-06-01T10:55:00Z" },
    "attempt": { "id": "uuid", "attempt_number": 1 }
  }
}
```

**Error Responses**
| Status | Condition |
|--------|-----------|
| 400 | Validation error (e.g. exam not active) |
| 403 | No tenant assigned |

---

### `POST /api/v1/academic/submissions/scan/`

Scan a student's paper answer sheet and submit. Lecturer/admin only.

**Request Body**
```json
{
  "exam_id": "uuid",
  "student_id": "uuid",
  "pages": ["<base64-image>"],
  "page_urls": ["https://storage.example.com/page1.jpg"]
}
```

**Response 201**
```json
{
  "success": true,
  "message": "Answer sheet scanned. Attempt #1 — grading in progress",
  "data": {
    "submission": { "id": "uuid", "status": "submitted" },
    "attempt": { "id": "uuid", "attempt_number": 1 }
  }
}
```

---

### `GET /api/v1/academic/submissions/`

List submissions for an exam. Lecturer/admin only.

**Query Parameters**
| Param | Type | Description |
|-------|------|-------------|
| `exam_id` | uuid | **Required** |
| `status` | string | Filter by status |
| `page` | int | Page number (default 1) |
| `per_page` | int | Items per page (default 50) |

**Response 200**
```json
{ "success": true, "data": [...], "page": 1, "per_page": 50, "total": 28 }
```

---

### `GET /api/v1/academic/submissions/exam/{exam_id}/students`

List all students and their full submission + attempt history for an exam. Lecturer/admin only.

**Query Parameters:** `page`, `per_page`

**Response 200**
```json
{ "success": true, "message": "Students and submissions retrieved", "data": [...], "total": 30 }
```

---

### `GET /api/v1/academic/submissions/lecturer`

List all submissions for the lecturer's exams (or all submissions for admins).

**Query Parameters:** `page`, `per_page`

**Response 200**
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "student_name": "Ada Lovelace",
      "exam": { "id": "uuid", "title": "CSC301 Mid-Semester Exam" },
      "status": "graded",
      "latest_score": "85.50"
    }
  ],
  "page": 1, "per_page": 50, "total": 100
}
```

---

### `GET /api/v1/academic/submissions/mine`

Get the current student's submission for an exam, or all their submissions.

**Query Parameters**
| Param | Type | Description |
|-------|------|-------------|
| `exam_id` | uuid | Optional — if omitted, returns all submissions |

**Response 200 (with exam_id)**
```json
{
  "success": true,
  "message": "Your submission retrieved",
  "data": {
    "id": "uuid",
    "exam_id": "uuid",
    "status": "graded",
    "latest_score": "85.50",
    "submitted_at": "2026-06-01T10:55:00Z",
    "attempts": [{ "id": "uuid", "attempt_number": 1, "score": "85.50", "graded_at": "..." }]
  }
}
```

---

### `GET /api/v1/academic/submissions/mine/all`

Get all submissions for the current student across all exams.

**Response 200**
```json
{ "success": true, "message": "All your submissions retrieved", "data": [...] }
```

---

## Analytics / Dashboard

All dashboard routes are mounted under `/api/v1/analytics/dashboard`. All endpoints are **read-only** — dashboard rows are written exclusively by the `REFRESH_DASHBOARD` Kafka worker.

### `GET /api/v1/analytics/dashboard/`

Get the dashboard for the currently authenticated user (role-aware).

**Response 200**
```json
{
  "success": true,
  "data": {
    "total_courses": 5,
    "total_students": 120,
    "total_exams": 10,
    "pending_submissions": 3,
    "graded_submissions": 45
  }
}
```

**Error Responses**
| Status | Condition |
|--------|-----------|
| 404 | Dashboard not yet populated (worker hasn't run yet) |

---

### `GET /api/v1/analytics/dashboard/lecturer/{lecturer_id}`

Get a specific lecturer's dashboard. Lecturers can only view their own.

**Response 200**
```json
{
  "success": true,
  "data": {
    "lecturer_id": "uuid",
    "total_courses": 3,
    "total_students": 90,
    "total_exams": 6,
    "pending_submissions": 2,
    "graded_submissions": 30
  }
}
```

---

### `GET /api/v1/analytics/dashboard/admin/{tenant_id}`

Get the admin dashboard for a tenant. Admin only.

**Response 200**
```json
{
  "success": true,
  "data": {
    "tenant_id": "uuid",
    "total_users": 200,
    "total_courses": 15,
    "total_exams": 40,
    "pending_submissions": 10,
    "graded_submissions": 150
  }
}
```

---

### `GET /api/v1/analytics/dashboard/student/{student_id}`

Get a student's dashboard. Students can only view their own.

**Response 200**
```json
{
  "success": true,
  "data": {
    "student_id": "uuid",
    "active_courses": 3,
    "completed_courses": 2,
    "pending_submissions": 1,
    "graded_submissions": 8
  }
}
```

---

### `GET /api/v1/analytics/dashboard/stats/tenant`

Get live aggregate stats for the current admin's tenant. Admin only.

**Response 200**
```json
{
  "success": true,
  "data": {
    "total_users": 200,
    "total_courses": 15,
    "total_exams": 40
  }
}
```

---

## Billing — Invoices

All invoice routes are mounted under `/api/v1/billing/invoices`.

### `GET /api/v1/billing/invoices/`

List invoices. Admins can filter by tenant; others see their own tenant only.

**Query Parameters**
| Param | Type | Description |
|-------|------|-------------|
| `page` | int | Page number (default 1) |
| `per_page` | int | Items per page (default 20, max 100) |
| `status` | string | Filter by status (`pending`, `paid`, `overdue`, `cancelled`) |
| `tenant_id` | uuid | Filter by tenant (admin only) |

**Response 200**
```json
{
  "success": true,
  "message": "Invoices retrieved",
  "data": [
    {
      "id": "uuid",
      "tenant_id": "uuid",
      "semester_id": "uuid",
      "description": "First Semester 2026 Billing",
      "student_count": 120,
      "amount_per_student": "5000.00",
      "total_amount": "600000.00",
      "status": "pending",
      "payment_reference": null,
      "payment_gateway": null,
      "paid_at": null,
      "payment_url": null,
      "created_at": "2026-05-07T10:00:00Z"
    }
  ],
  "page": 1, "per_page": 20, "total": 5
}
```

---

### `GET /api/v1/billing/invoices/{invoice_id}`

Get a specific invoice.

**Response 200**
```json
{ "success": true, "message": "Invoice retrieved", "data": { "id": "uuid", "status": "paid", "paid_at": "..." } }
```

**Error Responses**
| Status | Condition |
|--------|-----------|
| 404 | Invoice not found |

---

### `POST /api/v1/billing/invoices/`

Create an invoice manually (admin only).

**Request Body**
```json
{
  "tenant_id": "uuid",
  "semester_id": "uuid",
  "description": "First Semester 2026 Billing",
  "student_count": 120,
  "amount_per_student": 5000.00,
  "total_amount": 600000.00
}
```

**Response 201**
```json
{ "success": true, "message": "Invoice created", "data": { "id": "uuid", "status": "pending" } }
```

---

### `PUT /api/v1/billing/invoices/{invoice_id}`

Update an invoice (admin only).

**Request Body** (all fields optional)
```json
{ "description": "Updated description", "status": "overdue" }
```

**Response 200**
```json
{ "success": true, "message": "Invoice updated", "data": { "id": "uuid" } }
```

---

### `POST /api/v1/billing/invoices/{invoice_id}/mark-paid`

Manually mark an invoice as paid (admin only).

**Response 200**
```json
{ "success": true, "message": "Invoice marked as paid", "data": { "id": "uuid", "status": "paid" } }
```

---

## Billing — Plans

All billing plan routes are mounted under `/api/v1/billing/plans`.

### `GET /api/v1/billing/plans/`

List billing plans.

**Query Parameters**
| Param | Type | Description |
|-------|------|-------------|
| `page` | int | Page number (default 1) |
| `per_page` | int | Items per page (default 20, max 100) |
| `is_active` | bool | Filter by active status |
| `tenant_id` | uuid | Filter by tenant (admin only) |

**Response 200**
```json
{
  "success": true,
  "message": "Billing plans retrieved",
  "data": [{ "id": "uuid", "name": "Standard Plan", "price_per_student": "5000.00", "is_active": true }],
  "page": 1, "per_page": 20, "total": 3
}
```

---

### `GET /api/v1/billing/plans/{plan_id}`

Get a specific billing plan.

**Response 200**
```json
{ "success": true, "message": "Billing plan retrieved", "data": { "id": "uuid", "name": "Standard Plan" } }
```

---

### `POST /api/v1/billing/plans/`

Create a billing plan (admin only).

**Request Body**
```json
{ "name": "Premium Plan", "price_per_student": 8000.00, "is_active": true }
```

**Response 201**
```json
{ "success": true, "message": "Billing plan created", "data": { "id": "uuid" } }
```

---

### `PUT /api/v1/billing/plans/{plan_id}`

Update a billing plan (admin only).

**Request Body** (all fields optional)
```json
{ "price_per_student": 9000.00, "is_active": false }
```

**Response 200**
```json
{ "success": true, "message": "Billing plan updated", "data": { "id": "uuid" } }
```

---

### `DELETE /api/v1/billing/plans/{plan_id}`

Delete a billing plan (admin only).

**Response 204** — no body

---

## Billing — Payment Methods

All payment method routes are mounted under `/api/v1/billing/payment-methods`.

### `GET /api/v1/billing/payment-methods/`

List payment methods for the current tenant.

**Query Parameters:** `page`, `per_page`

**Response 200**
```json
{
  "success": true,
  "message": "Payment methods retrieved",
  "data": [{ "id": "uuid", "type": "card", "last_four": "4242", "is_default": true }],
  "page": 1, "per_page": 20, "total": 2
}
```

---

### `GET /api/v1/billing/payment-methods/{method_id}`

Get a specific payment method.

**Response 200**
```json
{ "success": true, "message": "Payment method retrieved", "data": { "id": "uuid", "type": "card" } }
```

---

### `POST /api/v1/billing/payment-methods/`

Create a payment method (admin only).

**Request Body**
```json
{ "type": "card", "last_four": "4242", "is_default": false }
```

**Response 201**
```json
{ "success": true, "message": "Payment method created", "data": { "id": "uuid" } }
```

---

### `PUT /api/v1/billing/payment-methods/{method_id}`

Update a payment method (admin only).

**Request Body** (all fields optional)
```json
{ "is_default": true }
```

**Response 200**
```json
{ "success": true, "message": "Payment method updated", "data": { "id": "uuid" } }
```

---

### `DELETE /api/v1/billing/payment-methods/{method_id}`

Delete a payment method (admin only).

**Response 204** — no body

---

### `POST /api/v1/billing/payment-methods/{method_id}/set-default`

Set a payment method as the default (admin only).

**Response 200**
```json
{ "success": true, "message": "Default payment method updated", "data": { "id": "uuid", "is_default": true } }
```

---

## Billing — Usage

All usage routes are mounted under `/api/v1/billing/usage`.

### `GET /api/v1/billing/usage/`

List usage records for the current tenant.

**Query Parameters:** `page`, `per_page`

**Response 200**
```json
{
  "success": true,
  "message": "Usage records retrieved",
  "data": [{ "id": "uuid", "period": "2026-05", "student_count": 120, "total_cost": "600000.00" }],
  "page": 1, "per_page": 20, "total": 6
}
```

---

### `GET /api/v1/billing/usage/current`

Get the current usage record for the authenticated user's tenant.

**Response 200**
```json
{ "success": true, "message": "Current usage retrieved", "data": { "id": "uuid", "period": "2026-05" } }
```

**Error Responses**
| Status | Condition |
|--------|-----------|
| 404 | No usage record found |

---

### `GET /api/v1/billing/usage/{usage_id}`

Get a specific usage record.

**Response 200**
```json
{ "success": true, "message": "Usage record retrieved", "data": { "id": "uuid", "period": "2026-05" } }
```

---

### `POST /api/v1/billing/usage/`

Create a usage record (admin only).

**Request Body**
```json
{ "period": "2026-06", "student_count": 130, "total_cost": 650000.00 }
```

**Response 201**
```json
{ "success": true, "message": "Usage record created", "data": { "id": "uuid" } }
```

---

### `PUT /api/v1/billing/usage/{usage_id}`

Update a usage record (admin only).

**Request Body** (all fields optional)
```json
{ "student_count": 135 }
```

**Response 200**
```json
{ "success": true, "message": "Usage record updated", "data": { "id": "uuid" } }
```

---

## Billing — Semesters

All semester routes are mounted under `/api/v1/billing/semesters`.

### `GET /api/v1/billing/semesters/`

List semesters.

**Query Parameters**
| Param | Type | Description |
|-------|------|-------------|
| `page` | int | Page number (default 1) |
| `per_page` | int | Items per page (default 20, max 100) |
| `status` | string | Filter by status |
| `tenant_id` | uuid | Filter by tenant (admin only) |

**Response 200**
```json
{
  "success": true,
  "message": "Semesters retrieved",
  "data": [{ "id": "uuid", "name": "First Semester 2026", "start_date": "...", "end_date": "...", "status": "active" }],
  "page": 1, "per_page": 20, "total": 4
}
```

---

### `GET /api/v1/billing/semesters/{semester_id}`

Get a specific semester.

**Response 200**
```json
{ "success": true, "message": "Semester retrieved", "data": { "id": "uuid", "name": "First Semester 2026" } }
```

---

### `POST /api/v1/billing/semesters/`

Create a semester (admin only).

**Request Body**
```json
{
  "name": "Second Semester 2026",
  "start_date": "2026-08-01T00:00:00Z",
  "end_date": "2026-12-31T23:59:59Z",
  "status": "active"
}
```

**Response 201**
```json
{ "success": true, "message": "Semester created", "data": { "id": "uuid" } }
```

---

### `PUT /api/v1/billing/semesters/{semester_id}`

Update a semester (admin only).

**Request Body** (all fields optional)
```json
{ "status": "ended" }
```

**Response 200**
```json
{ "success": true, "message": "Semester updated", "data": { "id": "uuid" } }
```

---

### `DELETE /api/v1/billing/semesters/{semester_id}`

Delete a semester (admin only).

**Response 204** — no body

---

## Billing — Webhooks

Webhook endpoints for payment gateway callbacks. **No authentication required** — verified via HMAC signature.

### `POST /api/v1/billing/webhooks/paystack`

Paystack webhook handler. Verifies `X-Paystack-Signature` header using `PAYSTACK_SECRET_KEY`.

On `charge.success` event:
- Marks the matching `Invoice` as `PAID`
- Calls `SemesterService.mark_billed()` atomically

**Headers:** `X-Paystack-Signature: <hmac-sha512-hex>`

**Request Body** (Paystack event payload)
```json
{
  "event": "charge.success",
  "data": {
    "reference": "INV-2026-001",
    "amount": 60000000,
    "paid_at": "2026-05-07T10:30:00Z"
  }
}
```

**Response 200**
```json
{ "success": true, "message": "Webhook received" }
```

**Error Responses**
| Status | Condition |
|--------|-----------|
| 400 | Missing or invalid signature |
| 400 | Invalid JSON body |

---

### `POST /api/v1/billing/webhooks/monnify`

Monnify webhook handler. Verifies `monnify-signature` header using `MONNIFY_SECRET_KEY`.

On `SUCCESSFUL_TRANSACTION` event:
- Marks the matching `Invoice` as `PAID`
- Calls `SemesterService.mark_billed()` atomically

**Headers:** `monnify-signature: <hmac-sha512-hex>`

**Request Body** (Monnify event payload)
```json
{
  "eventType": "SUCCESSFUL_TRANSACTION",
  "eventData": {
    "paymentReference": "INV-2026-001",
    "amountPaid": 600000.00,
    "completedOn": "2026-05-07T10:30:00Z"
  }
}
```

**Response 200**
```json
{ "success": true, "message": "Webhook received" }
```

**Error Responses**
| Status | Condition |
|--------|-----------|
| 400 | Missing or invalid signature |
| 400 | Invalid JSON body |

---

## Appendix: Common Response Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 202 | Accepted (async processing) |
| 204 | No Content (successful deletion) |
| 400 | Bad Request (validation error) |
| 401 | Unauthorized (missing or invalid token) |
| 403 | Forbidden (insufficient permissions) |
| 404 | Not Found |
| 422 | Unprocessable Entity (semantic validation error) |
| 500 | Internal Server Error |
| 503 | Service Unavailable (e.g. Kafka down) |

---

## Appendix: Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://user:pass@localhost/wazire` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka broker list | `localhost:9092` |
| `FRONTEND_ORIGIN` | CORS allowed origin | `https://wazire.com` |
| `PAYSTACK_SECRET_KEY` | Paystack webhook secret | `sk_test_...` |
| `MONNIFY_SECRET_KEY` | Monnify webhook secret | `...` |
| `GROQ_API_KEY_1` | Primary Groq API key | `gsk_...` |
| `GROQ_API_KEY_2` | Secondary Groq API key (optional) | `gsk_...` |
| `LOG_LEVEL` | Logging level | `INFO` (default), `DEBUG`, `WARNING`, `ERROR` |
| `DEBUG` | Debug mode | `false` (default), `true` |

---

**End of API Documentation**
