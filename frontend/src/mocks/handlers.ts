/**
 * MSW (Mock Service Worker) handlers for all backend API endpoints.
 * Used in Vitest tests to intercept HTTP requests and return mock responses.
 */
import { http, HttpResponse } from 'msw'

const BASE_URL = 'http://localhost:8000/api/v1'

// ---------------------------------------------------------------------------
// Shared mock data
// ---------------------------------------------------------------------------

export const mockUser = {
  id: 'user-1',
  email: 'student@test.com',
  first_name: 'Test',
  middle_name: null,
  last_name: 'Student',
  role: 'student' as const,
  is_active: true,
  tenant_id: 'tenant-1',
  institution_id: null,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

export const mockAdminUser = {
  ...mockUser,
  id: 'admin-1',
  email: 'admin@test.com',
  first_name: 'Test',
  last_name: 'Admin',
  role: 'admin' as const,
}

export const mockLecturerUser = {
  ...mockUser,
  id: 'lecturer-1',
  email: 'lecturer@test.com',
  first_name: 'Test',
  last_name: 'Lecturer',
  role: 'lecturer' as const,
}

export const mockTokens = {
  access_token: 'mock-access-token',
  refresh_token: 'mock-refresh-token',
  token_type: 'bearer',
}

export const mockTenant = {
  id: 'tenant-1',
  name: 'Test University',
  description: 'A test university',
  logo_url: null,
  domain: 'test.edu',
  is_active: true,
  is_deleted: false,
  deleted_at: null,
  tenant_code: 'ABC123',
  start_date: null,
  end_date: null,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

export const mockCourse = {
  id: 'course-1',
  name: 'Introduction to Computer Science',
  description: 'A foundational CS course',
  course_code: 'CS101',
  lecturer: mockLecturerUser,
  tenant_id: 'tenant-1',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

export const mockExam = {
  id: 'exam-1',
  title: 'Midterm Exam',
  description: 'Midterm examination',
  duration_hours: 2,
  duration_minutes: 0,
  total_marks: 100,
  passing_marks: 50,
  status: 'not_started' as const,
  max_attempts: 1,
  start_time: '2024-06-01T09:00:00Z',
  end_time: '2024-06-01T11:00:00Z',
  course_id: 'course-1',
  lecturer: mockLecturerUser,
  tenant_id: 'tenant-1',
  created_by: 'lecturer-1',
  updated_by: null,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  question_count: 10,
  submission_count: 0,
}

export const mockQuestion = {
  id: 'question-1',
  number: '1',
  text: 'What is 2 + 2?',
  rules: null,
  images: [],
  parent_id: null,
  tenant_id: 'tenant-1',
  industry: null,
  qtype: 'multiple_choice',
  options: { A: '3', B: '4', C: '5', D: '6' },
  parsed_options: [
    { label: 'A', text: '3' },
    { label: 'B', text: '4' },
    { label: 'C', text: '5' },
    { label: 'D', text: '6' },
  ],
  exams: [{ id: 'exam-1' }],
  mark: 10,
  answer: null,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

export const mockEnrollment = {
  id: 'enrollment-1',
  student_id: 'user-1',
  course_id: 'course-1',
  semester: 'fall' as const,
  year: 2024,
  status: 'active' as const,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

export const mockSubmission = {
  id: 'submission-1',
  student_id: 'user-1',
  exam_id: 'exam-1',
  latest_score: null,
  attempts: 1,
  submitted_at: null,
  graded_at: null,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  status: 'pending',
}

export const mockAdminDashboard = {
  id: 'dashboard-1',
  tenant_id: 'tenant-1',
  total_users: 100,
  total_lecturers: 10,
  total_students: 90,
  total_courses: 20,
  total_exams: 50,
  total_submissions: 200,
  graded_submissions: 150,
  pending_submissions: 50,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

export const mockStudentDashboard = {
  id: 'student-dashboard-1',
  student_id: 'user-1',
  total_courses: 5,
  total_exams: 10,
  total_submissions: 8,
  graded_submissions: 6,
  pending_submissions: 2,
  active_courses: 3,
  completed_courses: 2,
  missed_exams: 1,
  upcoming_exams: 2,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

export const mockInvoice = {
  id: 'invoice-1',
  tenant_id: 'tenant-1',
  semester_id: 'semester-1',
  description: 'Semester billing',
  student_count: 90,
  amount_per_student: 5000,
  total_amount: 450000,
  status: 'pending' as const,
  payment_reference: null,
  payment_gateway: null,
  paid_at: null,
  payment_url: null,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

// ---------------------------------------------------------------------------
// Helper: build standard API envelope
// ---------------------------------------------------------------------------

function envelope<T>(data: T, message = 'Success') {
  return {
    success: true,
    message,
    data,
    request_id: 'test-request-id',
    timestamp: new Date().toISOString() + 'Z',
  }
}

function paginatedEnvelope<T>(items: T[], total = 1) {
  return {
    success: true,
    message: 'Success',
    data: items,
    meta: {
      page: 1,
      per_page: 20,
      total,
      pages: 1,
      has_next: false,
      has_prev: false,
      next_page: null,
      prev_page: null,
    },
    request_id: 'test-request-id',
    timestamp: new Date().toISOString() + 'Z',
  }
}

// ---------------------------------------------------------------------------
// Auth handlers
// ---------------------------------------------------------------------------

export const authHandlers = [
  http.post(`${BASE_URL}/auth/login`, async ({ request }) => {
    const body = await request.json() as { email: string; password: string }
    if (body.email === 'invalid@test.com') {
      return HttpResponse.json(
        { success: false, error: 'Invalid credentials', message: 'Invalid credentials' },
        { status: 401 }
      )
    }
    return HttpResponse.json(
      envelope({ user: mockUser, tokens: mockTokens })
    )
  }),

  http.post(`${BASE_URL}/auth/register`, async ({ request }) => {
    const body = await request.json() as Record<string, unknown>
    if (!body.email || !body.password) {
      return HttpResponse.json(
        { success: false, error: 'Missing required fields', message: 'Missing required fields' },
        { status: 422 }
      )
    }
    return HttpResponse.json(envelope(mockUser), { status: 201 })
  }),

  http.get(`${BASE_URL}/auth/me`, () => {
    return HttpResponse.json(envelope(mockUser))
  }),

  http.post(`${BASE_URL}/auth/refresh`, () => {
    return HttpResponse.json(envelope(mockTokens))
  }),

  http.put(`${BASE_URL}/auth/me`, async ({ request }) => {
    const body = await request.json() as Record<string, unknown>
    return HttpResponse.json(envelope({ ...mockUser, ...body }))
  }),
]

// ---------------------------------------------------------------------------
// Account (users + tenants) handlers
// ---------------------------------------------------------------------------

export const accountHandlers = [
  http.get(`${BASE_URL}/account/users`, () => {
    return HttpResponse.json(paginatedEnvelope([mockUser, mockAdminUser, mockLecturerUser], 3))
  }),

  http.get(`${BASE_URL}/account/users/:userId`, ({ params }) => {
    if (params.userId === 'not-found') {
      return HttpResponse.json(
        { success: false, error: 'User not found', message: 'User not found' },
        { status: 404 }
      )
    }
    return HttpResponse.json(envelope(mockUser))
  }),

  http.put(`${BASE_URL}/account/users/:userId`, async ({ request }) => {
    const body = await request.json() as Record<string, unknown>
    return HttpResponse.json(envelope({ ...mockUser, ...body }))
  }),

  http.delete(`${BASE_URL}/account/users/:userId`, () => {
    return new HttpResponse(null, { status: 204 })
  }),

  http.get(`${BASE_URL}/account/tenants`, () => {
    return HttpResponse.json(paginatedEnvelope([mockTenant], 1))
  }),

  http.post(`${BASE_URL}/account/tenants`, async ({ request }) => {
    const body = await request.json() as Record<string, unknown>
    return HttpResponse.json(envelope({ ...mockTenant, ...body }), { status: 201 })
  }),

  http.get(`${BASE_URL}/account/tenants/:tenantId`, () => {
    return HttpResponse.json(envelope(mockTenant))
  }),

  http.put(`${BASE_URL}/account/tenants/:tenantId`, async ({ request }) => {
    const body = await request.json() as Record<string, unknown>
    return HttpResponse.json(envelope({ ...mockTenant, ...body }))
  }),

  http.delete(`${BASE_URL}/account/tenants/:tenantId`, () => {
    return new HttpResponse(null, { status: 204 })
  }),
]

// ---------------------------------------------------------------------------
// Academic handlers
// ---------------------------------------------------------------------------

export const academicHandlers = [
  // Courses
  http.get(`${BASE_URL}/academic/courses`, () => {
    return HttpResponse.json(paginatedEnvelope([mockCourse], 1))
  }),

  http.post(`${BASE_URL}/academic/courses`, async ({ request }) => {
    const body = await request.json() as Record<string, unknown>
    return HttpResponse.json(envelope({ ...mockCourse, ...body }), { status: 201 })
  }),

  http.get(`${BASE_URL}/academic/courses/:courseId`, () => {
    return HttpResponse.json(envelope(mockCourse))
  }),

  http.put(`${BASE_URL}/academic/courses/:courseId`, async ({ request }) => {
    const body = await request.json() as Record<string, unknown>
    return HttpResponse.json(envelope({ ...mockCourse, ...body }))
  }),

  http.delete(`${BASE_URL}/academic/courses/:courseId`, () => {
    return new HttpResponse(null, { status: 204 })
  }),

  http.get(`${BASE_URL}/academic/courses/:courseId/students`, () => {
    return HttpResponse.json(paginatedEnvelope([mockUser], 1))
  }),

  // Exams
  http.get(`${BASE_URL}/academic/exams`, () => {
    return HttpResponse.json(paginatedEnvelope([mockExam], 1))
  }),

  http.post(`${BASE_URL}/academic/exams`, async ({ request }) => {
    const body = await request.json() as Record<string, unknown>
    return HttpResponse.json(envelope({ ...mockExam, ...body }), { status: 201 })
  }),

  http.get(`${BASE_URL}/academic/exams/:examId`, () => {
    return HttpResponse.json(envelope(mockExam))
  }),

  http.put(`${BASE_URL}/academic/exams/:examId`, async ({ request }) => {
    const body = await request.json() as Record<string, unknown>
    return HttpResponse.json(envelope({ ...mockExam, ...body }))
  }),

  http.delete(`${BASE_URL}/academic/exams/:examId`, () => {
    return new HttpResponse(null, { status: 204 })
  }),

  http.get(`${BASE_URL}/academic/exams/:examId/results`, () => {
    return HttpResponse.json(paginatedEnvelope([mockSubmission], 1))
  }),

  // Questions
  http.get(`${BASE_URL}/academic/questions`, () => {
    return HttpResponse.json(paginatedEnvelope([mockQuestion], 1))
  }),

  http.post(`${BASE_URL}/academic/questions`, async ({ request }) => {
    const body = await request.json() as Record<string, unknown>
    return HttpResponse.json(envelope({ ...mockQuestion, ...body }), { status: 201 })
  }),

  http.get(`${BASE_URL}/academic/questions/:questionId`, () => {
    return HttpResponse.json(envelope(mockQuestion))
  }),

  // Enrollments
  http.get(`${BASE_URL}/academic/enrollments`, () => {
    return HttpResponse.json(paginatedEnvelope([mockEnrollment], 1))
  }),

  http.post(`${BASE_URL}/academic/enrollments`, async ({ request }) => {
    const body = await request.json() as Record<string, unknown>
    return HttpResponse.json(envelope({ ...mockEnrollment, ...body }), { status: 201 })
  }),

  // Answers
  http.patch(`${BASE_URL}/academic/answers/:questionId`, async ({ request }) => {
    const body = await request.json() as Record<string, unknown>
    return HttpResponse.json(
      envelope({
        id: 'answer-1',
        student_id: 'user-1',
        exam_id: body.exam_id,
        question_id: body.question_id,
        answer: body.answer,
        created_at: '2024-01-01T00:00:00Z',
      })
    )
  }),

  http.get(`${BASE_URL}/academic/answers/student`, () => {
    return HttpResponse.json(paginatedEnvelope([], 0))
  }),

  // Submissions
  http.get(`${BASE_URL}/academic/submissions`, () => {
    return HttpResponse.json(paginatedEnvelope([mockSubmission], 1))
  }),

  http.post(`${BASE_URL}/academic/submissions`, async ({ request }) => {
    const body = await request.json() as Record<string, unknown>
    return HttpResponse.json(envelope({ ...mockSubmission, ...body }), { status: 201 })
  }),

  http.get(`${BASE_URL}/academic/submissions/:submissionId`, () => {
    return HttpResponse.json(envelope(mockSubmission))
  }),

  // Students
  http.get(`${BASE_URL}/academic/students/:studentId/exams`, () => {
    return HttpResponse.json(paginatedEnvelope([mockExam], 1))
  }),
]

// ---------------------------------------------------------------------------
// Analytics handlers
// ---------------------------------------------------------------------------

export const analyticsHandlers = [
  http.get(`${BASE_URL}/analytics/dashboard`, () => {
    return HttpResponse.json(envelope(mockAdminDashboard))
  }),

  http.get(`${BASE_URL}/analytics/dashboard/admin/:tenantId`, () => {
    return HttpResponse.json(envelope(mockAdminDashboard))
  }),

  http.get(`${BASE_URL}/analytics/dashboard/student/:studentId`, () => {
    return HttpResponse.json(envelope(mockStudentDashboard))
  }),

  http.get(`${BASE_URL}/analytics/dashboard/lecturer/:lecturerId`, () => {
    return HttpResponse.json(
      envelope({
        id: 'lecturer-dashboard-1',
        lecturer_id: 'lecturer-1',
        total_courses: 5,
        total_exams: 15,
        total_students: 120,
        pending_submissions: 30,
        graded_submissions: 90,
        active_courses: 3,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      })
    )
  }),
]

// ---------------------------------------------------------------------------
// Billing handlers
// ---------------------------------------------------------------------------

export const billingHandlers = [
  http.get(`${BASE_URL}/billing/invoices`, () => {
    return HttpResponse.json(paginatedEnvelope([mockInvoice], 1))
  }),

  http.get(`${BASE_URL}/billing/invoices/:invoiceId`, () => {
    return HttpResponse.json(envelope(mockInvoice))
  }),

  http.get(`${BASE_URL}/billing/plans`, () => {
    return HttpResponse.json(
      paginatedEnvelope(
        [
          {
            id: 'plan-1',
            name: 'Starter',
            plan_type: 'starter',
            price_per_student: 5000,
            max_students: 100,
            is_active: true,
            created_at: '2024-01-01T00:00:00Z',
            updated_at: '2024-01-01T00:00:00Z',
          },
        ],
        1
      )
    )
  }),

  http.get(`${BASE_URL}/billing/usage`, () => {
    return HttpResponse.json(
      envelope({
        id: 'usage-1',
        tenant_id: 'tenant-1',
        student_count: 90,
        exams_graded: 200,
        plan: 'starter',
        plan_updated_at: '2024-01-01T00:00:00Z',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      })
    )
  }),

  http.get(`${BASE_URL}/billing/semesters`, () => {
    return HttpResponse.json(
      paginatedEnvelope(
        [
          {
            id: 'semester-1',
            name: 'Fall 2024',
            start_date: '2024-09-01T00:00:00Z',
            end_date: '2024-12-31T00:00:00Z',
            is_billed: false,
            status: 'active',
            tenant_id: 'tenant-1',
            created_at: '2024-01-01T00:00:00Z',
            updated_at: '2024-01-01T00:00:00Z',
          },
        ],
        1
      )
    )
  }),
]

// ---------------------------------------------------------------------------
// Health handler
// ---------------------------------------------------------------------------

export const healthHandlers = [
  http.get(`${BASE_URL}/health`, () => {
    return HttpResponse.json({ status: 'ok', db: 'ok', redis: 'ok', kafka: 'ok' })
  }),
]

// ---------------------------------------------------------------------------
// Combined handlers export
// ---------------------------------------------------------------------------

export const handlers = [
  ...authHandlers,
  ...accountHandlers,
  ...academicHandlers,
  ...analyticsHandlers,
  ...billingHandlers,
  ...healthHandlers,
]
