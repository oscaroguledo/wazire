import client, { handleEnvelope, handlePaginatedEnvelope, ApiResponse, ApiError } from '@/apis/client'
import { config } from '@/config'

// Exam Types (matching backend schemas)
export interface Exam {
  id: string
  title: string
  description?: string
  course: any
  lecturer: any
  tenant_id?: string
  duration_hours: number
  duration_minutes: number
  total_marks: number
  passing_marks?: number
  status: 'not_started' | 'in_progress' | 'finished'
  max_attempts: number
  start_time?: string
  created_by?: string
  updated_by?: string
  created_at: string
  updated_at: string
  question_count: number
  submission_count: number
  questions?: ExamQuestion[]
}

export interface ExamQuestion {
  id: string
  number: string
  text: string
  images?: string[]  // array of base64 encoded images
  parent_id?: string
  tenant_id?: string
  rules?: string
  mark: number
  industry: string
  qtype: 'multiple_choice' | 'theory' | 'fill_in_blanks'
  options?: Array<{label: string; text: string}>
  parsed_options?: Array<{ label: string; text: string }>
  exams?: { id: string }[]
  answer?: Answer
  created_at: string
  updated_at: string
}

export interface Answer {
  id: string
  value?: string
  text_value?: string
  acceptable_variations?: string[]
  answer_type?: 'mcq' | 'fitb'
  question?: { id: string }[]
  created_at: string
  updated_at: string
}

export interface QuestionCreate {
  question_text: string
  question_type: 'multiple_choice' | 'theory' | 'fill_in_blanks'
  options?: string[]
  correct_answer?: string | string[]
  marks: number
  order?: number
  images?: string[]  // array of base64 encoded images
  industry?: string
}

export interface QuestionUpdate {
  question_text?: string
  question_type?: 'multiple_choice' | 'theory' | 'fill_in_blanks'
  options?: string[]
  correct_answer?: string | string[]
  marks?: number
  order?: number
  images?: string[]  // array of base64 encoded images
  industry?: string
}

export interface QuestionListParams {
  page?: number
  per_page?: number
  search?: string
  question_type?: ExamQuestion['qtype']
}

export interface QuestionListResponse {
  items: ExamQuestion[]
  pagination: {
    page: number
    per_page: number
    total: number
    pages: number
    has_next: boolean
    has_prev: boolean
  }
}

export interface ExamCreate {
  title: string
  description?: string
  duration_hours: number
  duration_minutes?: number
  total_marks?: number
  passing_marks?: number
  status?: string
  start_time?: string
  max_attempts?: number
  course_id?: string
  tenant_id?: string
}

export interface ExamUpdate {
  title?: string
  description?: string
  duration_hours?: number
  duration_minutes?: number
  total_marks?: number
  passing_marks?: number
  status?: string
  start_time?: string
  max_attempts?: number
  course_id?: string
  tenant_id?: string
}

export interface ExamListParams {
  page?: number
  per_page?: number
  search?: string
  status?: Exam['status']
  course_id?: string
  lecturer_id?: string
  tenant_id?: string
  start_date?: string
  end_date?: string
  year?: number  // Filter by exam year
}

export interface ExamListResponse {
  items: Exam[]
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
 * List exams with pagination and filtering
 * Matches backend GET /academic/exams endpoint
 */
export async function listExams(params?: ExamListParams): Promise<ExamListResponse> {
  try {
    const requestParams = {
      page: params?.page || 1,
      per_page: params?.per_page || config.DEFAULT_PAGE_SIZE,
      search: params?.search,
      status: params?.status,
      course_id: params?.course_id,
      lecturer_id: params?.lecturer_id,
      tenant_id: params?.tenant_id,
      start_date: params?.start_date,
      end_date: params?.end_date,
      year: params?.year,
    }

    const response = await client.get<ApiResponse<Exam[]>>('/academic/exams/', { 
      params: requestParams 
    })
    
    return handlePaginatedEnvelope<Exam>(response)
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    
    if (error instanceof Error) {
      if (error.message.includes('401') || error.message.includes('Not authenticated')) {
        throw new ApiError('Authentication required to view exams', 401)
      }
      if (error.message.includes('403') || error.message.includes('Forbidden')) {
        throw new ApiError('Access denied to view exams', 403)
      }
      if (error.message.includes('404') || error.message.includes('Not Found')) {
        throw new ApiError('Exams endpoint not found', 404)
      }
    }
    
    throw new ApiError('Failed to fetch exams', 500)
  }
}

/**
 * Get a single exam by ID
 * Matches backend GET /academic/exams/{exam_id} endpoint
 */
export async function getExam(examId: string): Promise<Exam> {
  if (!examId) {
    throw new ApiError('Exam ID is required', 400)
  }

  try {
    const response = await client.get<ApiResponse<Exam>>(`/academic/exams/${examId}`)
    return handleEnvelope<Exam>(response)
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    
    if (error instanceof Error) {
      if (error.message.includes('401') || error.message.includes('Not authenticated')) {
        throw new ApiError('Authentication required to view exam', 401)
      }
      if (error.message.includes('403') || error.message.includes('Forbidden')) {
        throw new ApiError('Access denied to view this exam', 403)
      }
      if (error.message.includes('404') || error.message.includes('Not Found')) {
        throw new ApiError('Exam not found', 404)
      }
    }
    
    throw new ApiError('Failed to fetch exam', 500)
  }
}

/**
 * Create a new exam
 * Matches backend POST /academic/exams endpoint
 */
export async function createExam(examData: ExamCreate): Promise<Exam> {
  if (!examData.title || !examData.course_id || !examData.duration_hours) {
    throw new ApiError('Exam title, course ID, and duration hours are required', 400)
  }

  try {
    const response = await client.post<ApiResponse<Exam>>('/academic/exams/', examData)
    return handleEnvelope<Exam>(response)
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    
    if (error instanceof Error) {
      if (error.message.includes('401') || error.message.includes('Not authenticated')) {
        throw new ApiError('Authentication required to create exams', 401)
      }
      if (error.message.includes('403') || error.message.includes('Forbidden')) {
        throw new ApiError('Access denied to create exams', 403)
      }
      if (error.message.includes('400') || error.message.includes('Bad Request')) {
        throw new ApiError('Invalid exam data', 400)
      }
      if (error.message.includes('404') || error.message.includes('Not Found')) {
        throw new ApiError('Course not found', 404)
      }
    }
    
    throw new ApiError('Failed to create exam', 500)
  }
}

/**
 * Update an existing exam
 * Matches backend PUT /academic/exams/{exam_id} endpoint
 */
export async function updateExam(examId: string, examData: ExamUpdate): Promise<Exam> {
  if (!examId) {
    throw new ApiError('Exam ID is required', 400)
  }

  if (Object.keys(examData).length === 0) {
    throw new ApiError('At least one field must be provided for update', 400)
  }

  try {
    const response = await client.put<ApiResponse<Exam>>(`/academic/exams/${examId}`, examData)
    return handleEnvelope<Exam>(response)
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    
    if (error instanceof Error) {
      if (error.message.includes('401') || error.message.includes('Not authenticated')) {
        throw new ApiError('Authentication required to update exams', 401)
      }
      if (error.message.includes('403') || error.message.includes('Forbidden')) {
        throw new ApiError('Access denied to update this exam', 403)
      }
      if (error.message.includes('404') || error.message.includes('Not Found')) {
        throw new ApiError('Exam not found', 404)
      }
      if (error.message.includes('400') || error.message.includes('Bad Request')) {
        throw new ApiError('Invalid exam data', 400)
      }
    }
    
    throw new ApiError('Failed to update exam', 500)
  }
}

/**
 * Delete an exam
 * Matches backend DELETE /academic/exams/{exam_id} endpoint
 */
export async function deleteExam(examId: string): Promise<void> {
  if (!examId) {
    throw new ApiError('Exam ID is required', 400)
  }

  try {
    const response = await client.delete<ApiResponse<void>>(`/academic/exams/${examId}`)
    handleEnvelope<void>(response)
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    
    if (error instanceof Error) {
      if (error.message.includes('401') || error.message.includes('Not authenticated')) {
        throw new ApiError('Authentication required to delete exams', 401)
      }
      if (error.message.includes('403') || error.message.includes('Forbidden')) {
        throw new ApiError('Access denied to delete this exam', 403)
      }
      if (error.message.includes('404') || error.message.includes('Not Found')) {
        throw new ApiError('Exam not found', 404)
      }
      if (error.message.includes('400') || error.message.includes('Bad Request')) {
        throw new ApiError('Cannot delete exam with existing submissions', 400)
      }
    }
    
    throw new ApiError('Failed to delete exam', 500)
  }
}

/**
 * Get list of unique years from exam start_times
 * Matches backend GET /academic/exams/years endpoint
 */
export async function getExamYears(): Promise<number[]> {
  try {
    const response = await client.get<ApiResponse<number[]>>('/academic/exams/years')
    return handleEnvelope<number[]>(response)
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    
    if (error instanceof Error) {
      if (error.message.includes('401') || error.message.includes('Not authenticated')) {
        throw new ApiError('Authentication required', 401)
      }
    }
    
    throw new ApiError('Failed to fetch exam years', 500)
  }
}

/**
 * List questions for an exam
 * Matches backend GET /academic/exams/{exam_id}/questions endpoint
 */
export async function listQuestions(examId: string, params?: QuestionListParams): Promise<QuestionListResponse> {
  if (!examId) {
    throw new ApiError('Exam ID is required', 400)
  }

  try {
    const requestParams = {
      page: params?.page || 1,
      per_page: params?.per_page || config.DEFAULT_PAGE_SIZE,
      search: params?.search,
      question_type: params?.question_type,
    }

    const response = await client.get<ApiResponse<ExamQuestion[]>>(`/academic/questions`, { 
      params: requestParams 
    })
    
    return handlePaginatedEnvelope<ExamQuestion>(response)
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    
    if (error instanceof Error) {
      if (error.message.includes('401') || error.message.includes('Not authenticated')) {
        throw new ApiError('Authentication required to view questions', 401)
      }
      if (error.message.includes('403') || error.message.includes('Forbidden')) {
        throw new ApiError('Access denied to view questions', 403)
      }
      if (error.message.includes('404') || error.message.includes('Not Found')) {
        throw new ApiError('Exam not found', 404)
      }
    }
    
    throw new ApiError('Failed to fetch questions', 500)
  }
}

/**
 * Get a single question by ID
 * Matches backend GET /academic/exams/{exam_id}/questions/{question_id} endpoint
 */
export async function getQuestion(examId: string, questionId: string): Promise<ExamQuestion> {
  if (!examId || !questionId) {
    throw new ApiError('Exam ID and Question ID are required', 400)
  }

  try {
    const response = await client.get<ApiResponse<ExamQuestion>>(`/academic/questions/${questionId}`)
    return handleEnvelope<ExamQuestion>(response)
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    
    if (error instanceof Error) {
      if (error.message.includes('401') || error.message.includes('Not authenticated')) {
        throw new ApiError('Authentication required to view question', 401)
      }
      if (error.message.includes('403') || error.message.includes('Forbidden')) {
        throw new ApiError('Access denied to view this question', 403)
      }
      if (error.message.includes('404') || error.message.includes('Not Found')) {
        throw new ApiError('Question not found', 404)
      }
    }
    
    throw new ApiError('Failed to fetch question', 500)
  }
}

/**
 * Create a new question for an exam
 * Matches backend POST /academic/exams/{exam_id}/questions endpoint
 */
export async function createQuestion(examId: string, questionData: QuestionCreate): Promise<ExamQuestion> {
  if (!examId) {
    throw new ApiError('Exam ID is required', 400)
  }
  if (!questionData.question_text || !questionData.question_type || !questionData.marks) {
    throw new ApiError('Question text, type, and marks are required', 400)
  }

  try {
    const response = await client.post<ApiResponse<ExamQuestion>>(`/academic/questions`, questionData)
    return handleEnvelope<ExamQuestion>(response)
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    
    if (error instanceof Error) {
      if (error.message.includes('401') || error.message.includes('Not authenticated')) {
        throw new ApiError('Authentication required to create questions', 401)
      }
      if (error.message.includes('403') || error.message.includes('Forbidden')) {
        throw new ApiError('Access denied to create questions', 403)
      }
      if (error.message.includes('404') || error.message.includes('Not Found')) {
        throw new ApiError('Exam not found', 404)
      }
    }
    
    throw new ApiError('Failed to create question', 500)
  }
}

/**
 * Update an existing question
 * Matches backend PUT /academic/exams/{exam_id}/questions/{question_id} endpoint
 */
export async function updateQuestion(examId: string, questionId: string, questionData: QuestionUpdate): Promise<ExamQuestion> {
  if (!examId || !questionId) {
    throw new ApiError('Exam ID and Question ID are required', 400)
  }

  try {
    const response = await client.put<ApiResponse<ExamQuestion>>(`/academic/questions/${questionId}`, questionData)
    return handleEnvelope<ExamQuestion>(response)
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    
    if (error instanceof Error) {
      if (error.message.includes('401') || error.message.includes('Not authenticated')) {
        throw new ApiError('Authentication required to update questions', 401)
      }
      if (error.message.includes('403') || error.message.includes('Forbidden')) {
        throw new ApiError('Access denied to update this question', 403)
      }
      if (error.message.includes('404') || error.message.includes('Not Found')) {
        throw new ApiError('Question not found', 404)
      }
    }
    
    throw new ApiError('Failed to update question', 500)
  }
}

/**
 * Delete a question
 * Matches backend DELETE /academic/exams/{exam_id}/questions/{question_id} endpoint
 */
export async function deleteQuestion(examId: string, questionId: string): Promise<void> {
  if (!examId || !questionId) {
    throw new ApiError('Exam ID and Question ID are required', 400)
  }

  try {
    const response = await client.delete<ApiResponse<void>>(`/academic/questions/${questionId}`)
    handleEnvelope<void>(response)
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    
    if (error instanceof Error) {
      if (error.message.includes('401') || error.message.includes('Not authenticated')) {
        throw new ApiError('Authentication required to delete questions', 401)
      }
      if (error.message.includes('403') || error.message.includes('Forbidden')) {
        throw new ApiError('Access denied to delete this question', 403)
      }
      if (error.message.includes('404') || error.message.includes('Not Found')) {
        throw new ApiError('Question not found', 404)
      }
    }
    
    throw new ApiError('Failed to delete question', 500)
  }
}

export default { 
  listExams, 
  getExam, 
  createExam, 
  updateExam, 
  deleteExam,
  listQuestions,
  getQuestion,
  createQuestion,
  updateQuestion,
  deleteQuestion
}
