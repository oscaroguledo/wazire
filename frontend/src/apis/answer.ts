import client, { handleEnvelope, ApiResponse, ApiError } from '@/apis/client';

export interface StudentAnswerCreate {
  exam_id: string
  question_id: string
  answer: Record<string, any>
}

export interface StudentAnswerRead extends StudentAnswerCreate {
  id: string
  student_id: string
  last_saved_at?: string
  created_at?: string
}

export async function upsertAnswer(questionId: string, payload: StudentAnswerCreate): Promise<StudentAnswerRead> {
  if (!questionId) throw new ApiError('Question ID is required', 400)

  try {
    const response = await client.put<ApiResponse<StudentAnswerRead>>(`/academic/answers/${questionId}`, payload)
    return handleEnvelope<StudentAnswerRead>(response)
  } catch (error) {
    if (error instanceof ApiError) throw error
    throw new ApiError('Failed to save answer', 500)
  }
}

export async function listAnswers(examId: string): Promise<StudentAnswerRead[]> {
  if (!examId) throw new ApiError('Exam ID is required', 400)
  try {
    const response = await client.get<ApiResponse<StudentAnswerRead[]>>('/academic/answers/student', { params: { exam_id: examId } })
    return handleEnvelope<StudentAnswerRead[]>(response)
  } catch (error) {
    if (error instanceof ApiError) throw error
    throw new ApiError('Failed to fetch answers', 500)
  }
}

export async function submitAnswer(payload: Record<string, any>) {
  try {
    const resp = await client.post('/academic/answers/', payload)
    return handleEnvelope<any>(resp)
  } catch (error) {
    if (error instanceof ApiError) throw error
    throw new ApiError('Failed to submit answer', 500)
  }
}

export default { upsertAnswer, listAnswers, submitAnswer }
