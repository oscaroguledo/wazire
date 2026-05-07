import client, { handleEnvelope, ApiError } from '@/apis/client'
import type { LecturerDashboard as SharedLecturerDashboard, AdminDashboard as SharedAdminDashboard, StudentDashboard as SharedStudentDashboard } from '@/lib/types'

// Use shared dashboard types from types.ts
export type LecturerDashboard = SharedLecturerDashboard
export type AdminDashboard = SharedAdminDashboard
export type StudentDashboard = SharedStudentDashboard

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

// 13.4: Changed getAdminDashboard to accept tenantId (not adminId) per backend route /analytics/dashboard/admin/{tenantId}
export async function getAdminDashboard(tenantId: string): Promise<AdminDashboard> {
  try {
    const response = await client.get(`/analytics/dashboard/admin/${tenantId}`)
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
