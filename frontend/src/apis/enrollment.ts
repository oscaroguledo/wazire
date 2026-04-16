import client, { handleEnvelope, handlePaginatedEnvelope, ApiError } from '@/apis/client'

export type Semester = 'fall' | 'spring' | 'summer' | 'winter' | 'interim' | 'first' | 'second' | 'third' | 'fourth' | 'fifth' | 'sixth' | 'seventh' | 'eighth'

export interface Enrollment {
  id: string
  student_id: string
  student_name?: string
  student_email?: string
  institution_id?: string
  course_id: string
  course_name?: string
  lecturer_id?: string
  semester: Semester
  year?: number
  status: 'active' | 'completed' | 'dropped' | 'pending'
  created_at: string
  updated_at: string
}

export interface EnrollmentCreate {
  student_id: string
  course_id: string
  semester: Semester
  year?: number
}

export interface EnrollmentUpdate {
  status?: Enrollment['status']
}

export interface EnrollmentCheckResponse {
  enrolled: boolean
  enrollment?: Enrollment
}

export interface EnrollmentListParams {
  page?: number
  per_page?: number
  search?: string
  student_id?: string
  course_id?: string
  lecturer_id?: string
  status?: Enrollment['status']
  semester?: Semester
  year?: number
}

export interface EnrollmentListResponse {
  items: Enrollment[]
  pagination: {
    page: number
    per_page: number
    total: number
    pages: number
    has_next: boolean
    has_prev: boolean
  }
}

/** Extract the most useful message from an axios/API error */
function extractMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) return error.message
  const e = error as any
  // FastAPI HTTPException detail
  const detail = e?.response?.data?.detail
  if (typeof detail === 'string') return detail
  // Our custom Response error field
  const apiError = e?.response?.data?.error
  if (typeof apiError === 'string') return apiError
  if (e?.message) return e.message
  return fallback
}

export async function listEnrollment(params: EnrollmentListParams = {}): Promise<EnrollmentListResponse> {
  try {
    const response = await client.get(`/academic/enrollment/`, { params })
    return handlePaginatedEnvelope<Enrollment>(response)
  } catch (error) {
    throw new ApiError(extractMessage(error, 'Failed to fetch enrollments'))
  }
}

export async function getEnrollment(id: string): Promise<Enrollment> {
  try {
    const response = await client.get(`/academic/enrollment/${id}`)
    return handleEnvelope<Enrollment>(response)
  } catch (error) {
    throw new ApiError(extractMessage(error, 'Failed to fetch enrollment'))
  }
}

export async function enrollStudent(data: EnrollmentCreate): Promise<Enrollment> {
  try {
    const response = await client.post(`/academic/enrollment/`, data)
    return handleEnvelope<Enrollment>(response)
  } catch (error) {
    throw new ApiError(extractMessage(error, 'Failed to enroll student'))
  }
}

export async function updateEnrollment(id: string, data: EnrollmentUpdate): Promise<Enrollment> {
  try {
    const response = await client.put(`/academic/enrollment/${id}`, data)
    return handleEnvelope<Enrollment>(response)
  } catch (error) {
    throw new ApiError(extractMessage(error, 'Failed to update enrollment'))
  }
}

export async function removeEnrollment(id: string): Promise<void> {
  try {
    await client.delete(`/academic/enrollment/${id}`)
  } catch (error) {
    throw new ApiError(extractMessage(error, 'Failed to remove enrollment'))
  }
}

export async function getCourseEnrollment(courseId: string, params: Omit<EnrollmentListParams, 'course_id'> = {}): Promise<EnrollmentListResponse> {
  return listEnrollment({ ...params, course_id: courseId })
}

export async function getStudentEnrollment(studentId: string, params: Omit<EnrollmentListParams, 'student_id'> = {}): Promise<EnrollmentListResponse> {
  return listEnrollment({ ...params, student_id: studentId })
}

export async function getLecturerEnrollment(lecturerId: string, params: Omit<EnrollmentListParams, 'lecturer_id'> = {}): Promise<EnrollmentListResponse> {
  return listEnrollment({ ...params, lecturer_id: lecturerId })
}

export async function bulkEnroll(enrollments: EnrollmentCreate[]): Promise<Enrollment[]> {
  try {
    const response = await client.post(`/academic/enrollment/bulk`, { enrollments })
    return handleEnvelope<Enrollment[]>(response)
  } catch (error) {
    throw new ApiError(extractMessage(error, 'Failed to bulk enroll students'))
  }
}

export async function checkEnrollment(studentId: string, courseId: string): Promise<EnrollmentCheckResponse> {
  try {
    const response = await client.get(`/academic/enrollment/check`, {
      params: { student_id: studentId, course_id: courseId }
    })
    return handleEnvelope<EnrollmentCheckResponse>(response)
  } catch (error) {
    throw new ApiError(extractMessage(error, 'Failed to check enrollment'))
  }
}
