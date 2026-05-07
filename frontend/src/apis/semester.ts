/**
 * Semester API functions
 * Routes under /api/v1/billing/semesters/
 */
import client, { handleEnvelope, handlePaginatedEnvelope, ApiError } from '@/apis/client'

export interface SemesterRecord {
  id: string
  tenant_id: string
  name: string
  semester: 'fall' | 'spring' | 'summer'
  year: number
  start_date: string | null
  end_date: string | null
  is_active: boolean
  is_billed: boolean
  billed_at: string | null
  created_at: string
  updated_at: string
}

export interface SemesterListParams {
  page?: number
  per_page?: number
  tenant_id?: string
  is_active?: boolean
}

export interface SemesterListResponse {
  items: SemesterRecord[]
  pagination: {
    page: number
    per_page: number
    total: number
    pages: number
    has_next: boolean
    has_prev: boolean
  }
}

/** Extract error message from API error */
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

export async function listSemesters(params?: SemesterListParams): Promise<SemesterListResponse> {
  try {
    const response = await client.get('/billing/semesters', { params })
    return handlePaginatedEnvelope<SemesterRecord>(response)
  } catch (error) {
    throw new ApiError(extractMessage(error, 'Failed to fetch semesters'))
  }
}

export async function getSemester(semesterId: string): Promise<SemesterRecord> {
  if (!semesterId) throw new ApiError('Semester ID is required', 400)
  try {
    const response = await client.get(`/billing/semesters/${semesterId}`)
    return handleEnvelope<SemesterRecord>(response)
  } catch (error) {
    throw new ApiError(extractMessage(error, 'Failed to fetch semester'))
  }
}

export default { listSemesters, getSemester }
