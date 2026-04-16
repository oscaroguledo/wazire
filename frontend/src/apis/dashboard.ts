import client, { handleEnvelope, ApiError } from '@/apis/client'

export interface LecturerDashboard {
  id: string
  lecturer_id: string
  total_courses: number
  total_exams: number
  total_students: number
  pending_submissions: number
  graded_submissions: number
  active_courses: number
  created_at: string
  updated_at: string
}

export interface AdminDashboard {
  id: string
  admin_id: string
  total_users: number
  total_lecturers: number
  total_students: number
  total_courses: number
  total_exams: number
  total_submissions: number
  total_graded_submissions: number
  total_pending_submissions: number
  created_at: string
  updated_at: string
}

export interface StudentDashboard {
  id: string
  student_id: string
  total_courses: number
  total_exams: number
  total_submissions: number
  total_graded_submissions: number
  total_pending_submissions: number
  missed_exams: number
  upcoming_exams: number
  created_at: string
  updated_at: string
}

export type DashboardData = LecturerDashboard | AdminDashboard | StudentDashboard

/** Extract the most useful message from an axios/API error */
function extractMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) return error.message
  const e = error as any
  const detail = e?.response?.data?.detail
  if (typeof detail === 'string') return detail
  const apiError = e?.response?.data?.error
  if (typeof apiError === 'string') return apiError
  if (e?.message) return e.message
  return fallback
}

export async function getMyDashboard(): Promise<DashboardData> {
  try {
    const response = await client.get('/analytics/dashboard/')
    return handleEnvelope<DashboardData>(response)
  } catch (error) {
    throw new ApiError(extractMessage(error, 'Failed to fetch dashboard'))
  }
}

export async function getLecturerDashboard(lecturerId: string): Promise<LecturerDashboard> {
  try {
    const response = await client.get(`/analytics/dashboard/lecturer/${lecturerId}`)
    return handleEnvelope<LecturerDashboard>(response)
  } catch (error) {
    throw new ApiError(extractMessage(error, 'Failed to fetch lecturer dashboard'))
  }
}

export async function getAdminDashboard(adminId: string): Promise<AdminDashboard> {
  try {
    const response = await client.get(`/analytics/dashboard/admin/${adminId}`)
    return handleEnvelope<AdminDashboard>(response)
  } catch (error) {
    throw new ApiError(extractMessage(error, 'Failed to fetch admin dashboard'))
  }
}

export async function getStudentDashboard(studentId: string): Promise<StudentDashboard> {
  try {
    const response = await client.get(`/analytics/dashboard/student/${studentId}`)
    return handleEnvelope<StudentDashboard>(response)
  } catch (error) {
    throw new ApiError(extractMessage(error, 'Failed to fetch student dashboard'))
  }
}
