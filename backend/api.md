# Wazire API Reference

Base URL: `/api/v1`

All responses follow the envelope:
```json
{
  "success": true,
  "message": "...",
  "data": {},
  "request_id": "..."
}
```

Authenticated endpoints require `Authorization: Bearer <access_token>`.

Roles (lowest → highest): `student` → `lecturer` → `admin` → `superadmin`

---

## Health

### GET /health
Public. Returns service status.

**Response**
```json
{ "status": "ok", "service": "wazire-api" }
```

---

## Authentication — `/api/v1/auth`

### POST /auth/register
Register a new user. Public.

**Body**
```json
{
  "first_name": "Jane",
  "middle_name": "A",
  "last_name": "Doe",
  "email": "jane@example.com",
  "password": "secret",
  "role": "student",
  "tenant_id": "uuid"
}
```

**Response** `201` — `UserRead`

---

### POST /auth/login
**Body**
```json
{ "email": "jane@example.com", "password": "secret" }
```

**Response** `200`
```json
{
  "user": { ...UserRead },
  "tokens": {
    "access_token": "...",
    "refresh_token": "...",
    "token_type": "bearer"
  }
}
```

---

### POST /auth/refresh
**Body**
```json
{ "refresh_token": "..." }
```

**Response** `200` — `AuthTokens`

---

### GET /auth/me
Auth required. Returns current user profile.

**Response** `200` — `UserRead`

---

### PUT /auth/me
Auth required. Update own profile.

**Body** (all optional)
```json
{
  "first_name": "Jane",
  "middle_name": "B",
  "last_name": "Smith",
  "password": "newpassword",
  "is_active": true
}
```

**Response** `200` — `UserRead`

---

### GET /auth/
Role: `lecturer+`. List all users (tenant-scoped for non-admins).

**Query** `page=1&per_page=50`

**Response** `200` — `UserRead[]` with pagination

---

### GET /auth/{user_id}
Role: `lecturer+`.

**Response** `200` — `UserRead`

---

### PUT /auth/{user_id}
Role: `admin`. Update any user.

**Body** — same as `PUT /auth/me`

**Response** `200` — `UserRead`

---

### DELETE /auth/{user_id}
Role: `admin`. Cannot delete own account.

**Response** `204`

---

## Tenants — `/api/v1/tenants`

All tenant endpoints require role: `admin`.

### POST /tenants/
**Body**
```json
{
  "name": "Greenfield University",
  "domain": "greenfield.edu",
  "logo_url": "https://...",
  "admin_user_ids": ["uuid"]
}
```

**Response** `201` — `TenantRead`

---

### GET /tenants/
**Query** `page=1&per_page=50`

**Response** `200` — `TenantRead[]` with pagination

---

### GET /tenants/{tenant_id}
**Response** `200` — `TenantRead`

---

### PUT /tenants/{tenant_id}
**Body** (all optional)
```json
{
  "name": "...",
  "domain": "...",
  "logo_url": "...",
  "is_active": true
}
```

**Response** `200` — `TenantRead`

---

### DELETE /tenants/{tenant_id}
**Response** `200`

---

### GET /tenants/{tenant_id}/users
**Query** `page=1&per_page=50`

**Response** `200` — user list with pagination

---

### GET /tenants/{tenant_id}/stats
**Response** `200` — tenant statistics object

---

## Courses — `/api/v1/academic/courses`

### POST /courses/
Role: `lecturer+`.

**Body**
```json
{
  "name": "Anatomy 101",
  "description": "...",
  "course_code": "ANAT101",
  "lecturer_id": "uuid",
  "tenant_id": "uuid"
}
```

**Response** `201` — course object

---

### GET /courses/
Role: `student+`. Tenant-scoped.

**Query** `page=1&per_page=50`

**Response** `200` — course list with pagination

---

### GET /courses/{course_id}
Role: `student+`.

**Response** `200` — course object

---

### PUT /courses/{course_id}
Role: `lecturer+`.

**Body** (all optional)
```json
{
  "name": "...",
  "description": "...",
  "course_code": "...",
  "lecturer_id": "uuid"
}
```

**Response** `200` — course object

---

### DELETE /courses/{course_id}
Role: `lecturer+`.

**Response** `204`

---

## Enrollments — `/api/v1/academic/enrollments`

### POST /enrollments/
Role: `lecturer+`. Enroll a student in a course.

**Body**
```json
{
  "student_id": "uuid",
  "course_id": "uuid"
}
```

**Response** `201` — enrollment object

---

### GET /enrollments/
Role: `student+`. List enrollments with filtering and pagination.

**Query** `page=1&per_page=10&search=&student_id=&course_id=&lecturer_id=&status=`

**Response** `200` — paginated enrollment list
```json
{
  "items": [...],
  "pagination": {
    "page": 1,
    "per_page": 10,
    "total": 100,
    "pages": 10,
    "has_next": true,
    "has_prev": false
  }
}
```

---

### GET /enrollments/{enrollment_id}
Role: `student+`. Get specific enrollment.

**Response** `200` — enrollment object
```json
{
  "id": "uuid",
  "student_id": "uuid",
  "course_id": "uuid",
  "status": "active|completed|dropped|pending",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

---

### PUT /enrollments/{enrollment_id}
Role: `lecturer+`. Update enrollment status.

**Body**
```json
{
  "status": "active|completed|dropped|pending"
}
```

**Response** `200` — updated enrollment object

---

### DELETE /enrollments/{enrollment_id}
Role: `lecturer+`. Remove student from course.

**Response** `204`

---

### POST /enrollments/bulk/
Role: `lecturer+`. Bulk enroll multiple students.

**Body**
```json
{
  "enrollments": [
    {"student_id": "uuid", "course_id": "uuid"},
    ...
  ]
}
```

**Response** `201` — array of enrollment objects

---

### GET /enrollments/check/
Role: `student+`. Check if student is enrolled in course.

**Query** `student_id=uuid&course_id=uuid`

**Response** `200` — enrollment check result
```json
{
  "enrolled": true,
  "enrollment": {...}
}
```

---

## Exams — `/api/v1/academic/exams`

### POST /exams/
Role: `lecturer+`.

**Body**
```json
{
  "title": "Midterm Exam",
  "duration": 90,
  "course_id": "uuid",
  "tenant_id": "uuid"
}
```

**Response** `201` — exam object

---

### GET /exams/
Role: `student+`. Tenant-scoped.

**Query** `page=1&per_page=50` or `cursor=<token>`

**Response** `200` — exam list with pagination

---

### GET /exams/{exam_id}
Role: `student+`.

**Response** `200` — exam object

---

### PUT /exams/{exam_id}
Role: `lecturer+`.

**Body** (all optional)
```json
{ "title": "...", "duration": 120 }
```

**Response** `200` — exam object

---

### DELETE /exams/{exam_id}
Role: `lecturer+`.

**Response** `204`

---

## Questions — `/api/v1/academic/questions`

### POST /questions/
Role: `lecturer+`. Creates a single question.

**Body**
```json
{
  "number": "1",
  "text": "What is the powerhouse of the cell?",
  "qtype": "multiple_choice",
  "industry": "biology",
  "mark": 2.0,
  "rules": "Award full mark only for exact answer.",
  "options": [
    { "label": "a", "text": "Nucleus" },
    { "label": "b", "text": "Mitochondria" },
    { "label": "c", "text": "Ribosome" }
  ],
  "answer": "b",
  "exam_ids": ["uuid"],
  "image_url": "https://..."
}
```

- `qtype`: `"multiple_choice"` or `"theory"`
- `options`: required for MCQ, null for theory
- `answer`: correct option label for MCQ. If omitted, AI auto-detects it.
- `mark`: marks this question is worth (used in scoring)
- `rules`: optional grading instructions forwarded to the AI grader

**Response** `201` — question object

---

### POST /questions/upload
Role: `lecturer+`. Bulk-extract questions from scanned/typed exam paper pages.

**Body**
```json
{
  "pages": ["data:image/jpeg;base64,..."],
  "exam_id": "uuid",
  "industry": "medicine",
  "mark_per_question": 2.0
}
```

- `pages`: one base64 image per PDF page (frontend converts PDF → images)
- `mark_per_question`: fallback mark used when marks are not printed on the paper

**Response** `201`

> Note: this endpoint performs asynchronous extraction and may return `202 Accepted` when processing is queued.
```json
{
  "created": [ ...question objects ],
  "errors": [ { "number": "3", "error": "..." } ]
}
```

---

### GET /questions/
Role: `student+`.

**Query** `page=1&per_page=50` or `cursor=<token>`

**Response** `200` — question list with pagination

---

### GET /questions/{question_id}
Role: `student+`.

**Response** `200` — question object

---

### PUT /questions/{question_id}
Role: `lecturer+`.

**Body** (all optional — same fields as create)

**Response** `200` — question object

---

### DELETE /questions/{question_id}
Role: `lecturer+`.

**Response** `204`

---

## Answers — `/api/v1/academic/answers`

Answer records hold the correct option letter for MCQ questions. They are created automatically when a question is created with an `answer` field or via AI auto-detection. Direct management is available for admin/lecturer use.

### POST /answers/
Role: `lecturer+`. Create or import an answer record (used for manual corrections or seed data).

**Body**
```json
{
  "question_id": "uuid",
  "option": "b",
  "explanation": "Why this is correct (optional)"
}
```

**Response** `201` — `AnswerRead`

### GET /answers/
Role: `lecturer+`.

**Query** `page=1&per_page=50` or `cursor=<token>`

**Response** `200` — answer list with pagination

---

### GET /answers/{answer_id}
Role: `lecturer+`.

**Response** `200` — answer object

---

### DELETE /answers/{answer_id}
Role: `lecturer+`.

**Response** `204`

---

## Submissions — `/api/v1/academic/submissions`

### POST /submissions/
Role: `student+`. Submit a digital exam attempt.

**Body**
```json
{
  "exam_id": "uuid",
  "answers": {
    "<question_id>": "b",
    "<question_id>": { "text": "The mitochondria is..." }
  },
  "max_attempts": 3
}
```

- MCQ answer: plain option letter string `"b"` or `{ "option": "b" }`
- Theory answer: `{ "text": "..." }`
- `max_attempts`: optional cap, only applied on first submission

**Response** `201`
```json
{
  "submission": { ...SubmissionRead },
  "attempt": { ...SubmissionAttemptRead }
}
```

---

### POST /submissions/scan
Role: `lecturer+`. Grade a student's paper answer sheet from scanned images.

**Body**
```json
{
  "exam_id": "uuid",
  "student_id": "uuid",
  "pages": ["data:image/jpeg;base64,..."],
  "page_urls": ["https://storage/scan_pages/page1.jpg"],
  "max_attempts": null
}
```

- `pages`: base64 images for the AI to read and extract answers from
- `page_urls`: storage URLs already uploaded by the frontend — stored on the attempt for audit

**Response** `201` — same shape as `POST /submissions/`

### GET /submissions/exam/{exam_id}/students
Role: `lecturer+`. Returns student-level submission summaries for the specified exam (alternate endpoint used by some admin views).

**Response** `200` — `[{ "student_id": "uuid", "submission_id": "uuid", "latest_score": 47.5, ... }, ...]`

---

### GET /submissions/?exam_id=
Role: `lecturer+`. All submissions for an exam.

**Query** `exam_id=uuid&page=1&per_page=50`

**Response** `200` — `SubmissionRead[]`

---

### GET /submissions/mine?exam_id=
Role: `student+`. Own submission + all attempts for an exam.

**Query** `exam_id=uuid` (optional - if omitted, returns all submissions)

**Response** `200`
```json
{
  "id": "uuid",
  "student_id": "uuid",
  "exam_id": "uuid",
  "latest_score": 47.50,
  "attempts_count": 2,
  "attempts": [
    {
      "id": "uuid",
      "attempt_number": 1,
      "score": 47.50,
      "scan_pages": [],
      "answers": {
        "question_id": { "option": "a", "answer_score": 1.00, "reason": "..." }
      }
    }
  ]
}
```

---

### GET /submissions/mine/all
Role: `student+`. All submissions across all exams for the current student.

**Response** `200` — Array of submission objects
```json
[
  {
    "id": "uuid",
    "student_id": "uuid",
    "exam_id": "uuid",
    "latest_score": 47.50,
    "attempts_count": 2,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  },
  ...
]
```
        "<question_id>": {
          "option": "b",
          "answer_score": "1.00",
          "reason": "-"
        },
        "<question_id>": {
          "text": "The mitochondria produces ATP...",
          "answer_score": "0.85",
          "reason": "Correct concept, missing detail on electron transport chain."
        }
      },
      "graded_at": "2026-03-27T10:00:00"
    }
  ]
}
```

---

### GET /submissions/{submission_id}/attempts
Role: `lecturer+`. All attempts for a submission.

**Response** `200` — `SubmissionAttemptRead[]`

---

### PUT /submissions/attempts/{attempt_id}/grade
Role: `lecturer+`. Manually override the score on an attempt.

**Body**
```json
{ "score": 38.50 }
```

**Response** `200` — `SubmissionAttemptRead`

---

### DELETE /submissions/{submission_id}
Role: `lecturer+`.

**Response** `204`

---

## Scoring

Every `SubmissionAttempt` stores:

| Field | Description |
|---|---|
| `answers` | JSON map of `question_id → { option/text, answer_score, reason }` |
| `score` | Total: sum of `answer_score × mark` across all questions |
| `scan_pages` | Storage URLs of scanned answer sheet pages (paper submissions only) |

**answer_score** is `0.00–1.00`:
- MCQ: `1.00` if correct, `0.00` if wrong (direct comparison, no AI)
- Theory: AI-rated decimal based on accuracy and depth against the question

**question score** = `answer_score × question.mark`

**attempt score** = sum of all question scores
