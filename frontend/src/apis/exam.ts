import client, { handleEnvelope, handlePaginatedEnvelope, ApiResponse, ApiError } from '@/apis/client'
import { config } from '@/config'
import type { Exam as SharedExam, Question as SharedQuestion } from '@/lib/types'

// Use shared types from types.ts
export type Exam = SharedExam
export type Question = SharedQuestion

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

// Aligned with backend QuestionCreate schema
export interface QuestionCreate {
  number: string
  text: string
  qtype: 'multiple_choice' | 'theory' | 'fill_in_blanks'
  industry: string
  options?: any
  answer?: any
  mark?: number
  images?: string[]
  exam_ids?: string[]
  rules?: string
  parent_id?: string
  tenant_id?: string
}

// Aligned with backend QuestionUpdate schema
export interface QuestionUpdate {
  number?: string
  text?: string
  qtype?: 'multiple_choice' | 'theory' | 'fill_in_blanks'
  industry?: string
  options?: any
  answer?: any
  mark?: number
  images?: string[]
  exam_ids?: string[]
  rules?: string
  parent_id?: string
  tenant_id?: string
}

export interface QuestionListParams {
  page?: number
  per_page?: number
  search?: string
  question_type?: Question['qtype']
}

export interface QuestionListResponse {
  items: Question[]
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
  status?: 'not_started' | 'in_progress' | 'finished' | 'draft'
  start_time?: string
  max_attempts?: number
  course_id?: string
  tenant_id?: string
  semester_id?: string
}

export interface ExamUpdate {
  title?: string
  description?: string
  duration_hours?: number
  duration_minutes?: number
  total_marks?: number
  passing_marks?: number
  status?: 'not_started' | 'in_progress' | 'finished' | 'draft'
  start_time?: string
  max_attempts?: number
  course_id?: string
  tenant_id?: string
  semester_id?: string
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
 * Matches backend GET /academic/questions endpoint with exam_id filter
 */
export async function listQuestions(examId: string, params?: QuestionListParams): Promise<QuestionListResponse> {
  if (!examId) {
    throw new ApiError('Exam ID is required', 400)
  }

  try {
    // 13.11: Include exam_id as a query parameter so the backend filters by exam
    const requestParams = {
      exam_id: examId,
      page: params?.page || 1,
      per_page: params?.per_page || config.DEFAULT_PAGE_SIZE,
      search: params?.search,
      question_type: params?.question_type,
    }

    const response = await client.get<ApiResponse<Question[]>>(`/academic/questions`, { 
      params: requestParams 
    })
    
    return handlePaginatedEnvelope<Question>(response)
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
export async function getQuestion(examId: string, questionId: string): Promise<Question> {
  if (!examId || !questionId) {
    throw new ApiError('Exam ID and Question ID are required', 400)
  }

  try {
    const response = await client.get<ApiResponse<Question>>(`/academic/questions/${questionId}`)
    return handleEnvelope<Question>(response)
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
export async function createQuestion(examId: string, questionData: QuestionCreate): Promise<Question> {
  if (!examId) {
    throw new ApiError('Exam ID is required', 400)
  }
  if (!questionData.text || !questionData.qtype || !questionData.mark) {
    throw new ApiError('Question text, type, and mark are required', 400)
  }

  try {
    const response = await client.post<ApiResponse<Question>>(`/academic/questions`, questionData)
    return handleEnvelope<Question>(response)
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
export async function updateQuestion(examId: string, questionId: string, questionData: QuestionUpdate): Promise<Question> {
  if (!examId || !questionId) {
    throw new ApiError('Exam ID and Question ID are required', 400)
  }

  try {
    const response = await client.put<ApiResponse<Question>>(`/academic/questions/${questionId}`, questionData)
    return handleEnvelope<Question>(response)
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
