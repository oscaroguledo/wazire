import client, { handleEnvelope, handlePaginatedEnvelope, ApiResponse, ApiError } from '@/apis/client'
import { config } from '@/config'

// Submission Types (matching backend schemas)
export interface Submission {
  id: string
  exam_id: string
  exam_title?: string
  student_id: string
  student_name?: string
  lecturer_id: string
  lecturer_name?: string
  tenant_id?: string
  status: 'pending' | 'submitted' | 'graded' | 'returned'
  score?: number
  max_score: number
  percentage?: number
  started_at?: string
  submitted_at?: string
  graded_at?: string
  feedback?: string
  attempts: SubmissionAttempt[]
  created_at: string
  updated_at: string
}

export interface SubmissionAttempt {
  id: string
  submission_id: string
  attempt_number: number
  score?: number
  max_score: number
  started_at: string
  submitted_at?: string
  graded_at?: string
  feedback?: string
  created_at: string
}

export interface SubmissionAnswer {
  id: string
  attempt_id: string
  question_id: string
  question_text?: string
  answer: string | string[] | number
  is_correct?: boolean
  marks_obtained?: number
  max_marks: number
  feedback?: string
  created_at: string
}

export interface SubmissionCreate {
  exam_id: string
  student_id?: string
  tenant_id?: string
}

export interface SubmissionUpdate {
  status?: 'pending' | 'submitted' | 'graded' | 'returned'
  score?: number
  feedback?: string
}

export interface SubmissionListParams {
  page?: number
  per_page?: number
  search?: string
  status?: Submission['status']
  exam_id?: string
  student_id?: string
  lecturer_id?: string
  tenant_id?: string
  course_id?: string
  start_date?: string
  end_date?: string
}

export interface SubmissionListResponse {
  items: Submission[]
  pagination: {
    page: number
    per_page: number
    total: number
    pages: number
    has_next: boolean
    has_prev: boolean
  }
}

/**
 * List submissions with pagination and filtering
 * Matches backend GET /academic/submissions endpoint
 */
export async function listSubmissions(params?: SubmissionListParams): Promise<SubmissionListResponse> {
  try {
    // For lecturers, use the dedicated endpoint
    if (params?.lecturer_id) {
      const requestParams = {
        page: params?.page || 1,
        per_page: params?.per_page || config.DEFAULT_PAGE_SIZE,
      }

      const response = await client.get<ApiResponse<Submission[]>>('/academic/submissions/lecturer', { 
        params: requestParams 
      })
      
      return handlePaginatedEnvelope<Submission>(response)
    }

    // For students and general use, use the existing endpoint (requires exam_id)
    const requestParams = {
      page: params?.page || 1,
      per_page: params?.per_page || config.DEFAULT_PAGE_SIZE,
      search: params?.search,
      status: params?.status,
      exam_id: params?.exam_id,
      student_id: params?.student_id,
      tenant_id: params?.tenant_id,
      course_id: params?.course_id,
      start_date: params?.start_date,
      end_date: params?.end_date,
    }

    const response = await client.get<ApiResponse<Submission[]>>('/academic/submissions/', { 
      params: requestParams 
    })
    
    return handlePaginatedEnvelope<Submission>(response)
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    
    if (error instanceof Error) {
      if (error.message.includes('401') || error.message.includes('Not authenticated')) {
        throw new ApiError('Authentication required to view submissions', 401)
      }
      if (error.message.includes('403') || error.message.includes('Forbidden')) {
        throw new ApiError('Access denied to view submissions', 403)
      }
      if (error.message.includes('404') || error.message.includes('Not Found')) {
        throw new ApiError('Submissions endpoint not found', 404)
      }
    }
    
    throw new ApiError('Failed to fetch submissions', 500)
  }
}

/**
 * Get a single submission by ID
 * Matches backend GET /academic/submissions/{submission_id} endpoint
 */
export async function getSubmission(submissionId: string): Promise<Submission> {
  if (!submissionId) {
    throw new ApiError('Submission ID is required', 400)
  }

  try {
    const response = await client.get<ApiResponse<Submission>>(`/academic/submissions/${submissionId}/`)
    return handleEnvelope<Submission>(response)
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    
    if (error instanceof Error) {
      if (error.message.includes('401') || error.message.includes('Not authenticated')) {
        throw new ApiError('Authentication required to view submission', 401)
      }
      if (error.message.includes('403') || error.message.includes('Forbidden')) {
        throw new ApiError('Access denied to view this submission', 403)
      }
      if (error.message.includes('404') || error.message.includes('Not Found')) {
        throw new ApiError('Submission not found', 404)
      }
    }
    
    throw new ApiError('Failed to fetch submission', 500)
  }
}

/**
 * Create a new submission (start exam)
 * Matches backend POST /academic/submissions endpoint
 */
export async function createSubmission(submissionData: SubmissionCreate): Promise<Submission> {
  if (!submissionData.exam_id) {
    throw new ApiError('Exam ID is required', 400)
  }

  try {
    const response = await client.post<ApiResponse<Submission>>('/academic/submissions/', submissionData)
    return handleEnvelope<Submission>(response)
  } catch (error: any) {
    if (error instanceof ApiError) {
      throw error
    }
    
    // Axios error with response - extract backend message
    if (error.response?.data) {
      const backendError = error.response.data.error || error.response.data.message || 'Failed to start exam'
      throw new ApiError(backendError, error.response.status)
    }
    
    if (error instanceof Error) {
      if (error.message.includes('401') || error.message.includes('Not authenticated')) {
        throw new ApiError('Authentication required to start exam', 401)
      }
      if (error.message.includes('403') || error.message.includes('Forbidden')) {
        throw new ApiError('Access denied to start this exam', 403)
      }
      if (error.message.includes('404') || error.message.includes('Not Found')) {
        throw new ApiError('Exam not found', 404)
      }
    }
    
    throw new ApiError('Failed to start exam', 500)
  }
}

export async function startSubmission(submissionData: { exam_id: string }): Promise<Submission> {
  if (!submissionData.exam_id) {
    throw new ApiError('Exam ID is required to start exam', 400)
  }

  try {
    const response = await client.post<ApiResponse<Submission>>('/academic/submissions/start', submissionData)
    return handleEnvelope<Submission>(response)
  } catch (error) {
    if (error instanceof ApiError) throw error
    throw new ApiError('Failed to start submission', 500)
  }
}

/**
 * Update a submission
 * Matches backend PUT /academic/submissions/{submission_id} endpoint
 */
export async function updateSubmission(submissionId: string, submissionData: SubmissionUpdate): Promise<Submission> {
  if (!submissionId) {
    throw new ApiError('Submission ID is required', 400)
  }

  if (Object.keys(submissionData).length === 0) {
    throw new ApiError('At least one field must be provided for update', 400)
  }

  try {
    const response = await client.put<ApiResponse<Submission>>(`/academic/submissions/${submissionId}/`, submissionData)
    return handleEnvelope<Submission>(response)
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    
    if (error instanceof Error) {
      if (error.message.includes('401') || error.message.includes('Not authenticated')) {
        throw new ApiError('Authentication required to update submission', 401)
      }
      if (error.message.includes('403') || error.message.includes('Forbidden')) {
        throw new ApiError('Access denied to update this submission', 403)
      }
      if (error.message.includes('404') || error.message.includes('Not Found')) {
        throw new ApiError('Submission not found', 404)
      }
      if (error.message.includes('400') || error.message.includes('Bad Request')) {
        throw new ApiError('Invalid submission data', 400)
      }
    }
    
    throw new ApiError('Failed to update submission', 500)
  }
}

/**
 * Get current user's submission for a specific exam
 * Matches backend GET /academic/submissions/mine?exam_id= endpoint
 */
export async function getMySubmission(examId?: string): Promise<Submission> {
  try {
    const params = examId ? { exam_id: examId } : {}
    const response = await client.get<ApiResponse<Submission>>('/academic/submissions/mine', { params })
    return handleEnvelope<Submission>(response)
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    
    if (error instanceof Error) {
      if (error.message.includes('401') || error.message.includes('Not authenticated')) {
        throw new ApiError('Authentication required to view submission', 401)
      }
      if (error.message.includes('403') || error.message.includes('Forbidden')) {
        throw new ApiError('Access denied to view this submission', 403)
      }
      if (error.message.includes('404') || error.message.includes('Not Found')) {
        throw new ApiError('Submission not found for this exam', 404)
      }
    }
    
    throw new ApiError('Failed to fetch your submission', 500)
  }
}

/**
 * Get all submissions for the current user across all exams
 * Matches backend GET /academic/submissions/mine/all endpoint
 */
export async function getAllMySubmissions(): Promise<Submission[]> {
  try {
    const response = await client.get<ApiResponse<Submission[]>>('/academic/submissions/mine/all')
    return handleEnvelope<Submission[]>(response)
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    
    if (error instanceof Error) {
      if (error.message.includes('401') || error.message.includes('Not authenticated')) {
        throw new ApiError('Authentication required to view submissions', 401)
      }
      if (error.message.includes('403') || error.message.includes('Forbidden')) {
        throw new ApiError('Access denied to view submissions', 403)
      }
    }
    
    throw new ApiError('Failed to fetch your submissions', 500)
  }
}

export interface ExamSubmitData {
  exam_id: string
  max_attempts?: number
}

export interface ExamSubmitResult {
  submission: Submission
  attempt: SubmissionAttempt
}

/**
 * Submit exam answers (complete an attempt)
 * Matches backend POST /academic/submissions/submit endpoint
 */
export async function submitExam(submitData: ExamSubmitData): Promise<ExamSubmitResult> {
  if (!submitData.exam_id) {
    throw new ApiError('Exam ID is required', 400)
  }

  try {
    // backend expects POST /academic/submissions/ with minimal payload (exam_id)
    const response = await client.post<ApiResponse<ExamSubmitResult>>('/academic/submissions/', submitData)
    return handleEnvelope<ExamSubmitResult>(response)
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    
    if (error instanceof Error) {
      if (error.message.includes('401') || error.message.includes('Not authenticated')) {
        throw new ApiError('Authentication required to submit exam', 401)
      }
      if (error.message.includes('403') || error.message.includes('Forbidden')) {
        throw new ApiError('Access denied to submit this exam', 403)
      }
      if (error.message.includes('404') || error.message.includes('Not Found')) {
        throw new ApiError('Exam or submission not found', 404)
      }
      if (error.message.includes('400') || error.message.includes('Bad Request')) {
        throw new ApiError('Invalid submission data - check your answers', 400)
      }
    }
    
    throw new ApiError('Failed to submit exam', 500)
  }
}

export default { 
  listSubmissions, 
  getSubmission, 
  createSubmission, 
  updateSubmission,
  getMySubmission,
  getAllMySubmissions,
  submitExam
}
