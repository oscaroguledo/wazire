import client, { handleEnvelope, handlePaginatedEnvelope, ApiResponse, ApiError } from '@/apis/client'
import { config } from '@/config'
import { validateRequiredFields, validateRequiredId, validateUpdatePayload, handleApiError } from './api-utils'
import type { Course as SharedCourse } from '@/lib/types'

// Use shared Course type from types.ts
export type Course = SharedCourse

export interface CourseCreate {
  name: string
  description?: string
  course_code: string
  lecturer_id?: string
  tenant_id?: string
}

export interface CourseUpdate {
  name?: string
  description?: string
  course_code?: string
  lecturer_id?: string
  tenant_id?: string
}

export interface CourseListParams {
  page?: number
  per_page?: number
  search?: string
  lecturer_id?: string
  tenant_id?: string
}

export interface CourseListResponse {
  items: Course[]
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
 * List courses with pagination and filtering
 * Matches backend GET /academic/courses endpoint
 */
export async function listCourses(params?: CourseListParams): Promise<CourseListResponse> {
  try {
    const requestParams = {
      page: params?.page || 1,
      per_page: params?.per_page || config.DEFAULT_PAGE_SIZE,
      search: params?.search,
      lecturer_id: params?.lecturer_id,
      tenant_id: params?.tenant_id,
    }

    const response = await client.get<ApiResponse<Course[]>>('/academic/courses/', { 
      params: requestParams 
    })
    
    return handlePaginatedEnvelope<Course>(response)
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    
    if (error instanceof Error) {
      if (error.message.includes('401') || error.message.includes('Not authenticated')) {
        throw new ApiError('Authentication required to view courses', 401)
      }
      if (error.message.includes('403') || error.message.includes('Forbidden')) {
        throw new ApiError('Access denied to view courses', 403)
      }
      if (error.message.includes('404') || error.message.includes('Not Found')) {
        throw new ApiError('Courses endpoint not found', 404)
      }
    }
    
    throw new ApiError('Failed to fetch courses', 500)
  }
}

/**
 * Get a single course by ID
 * Matches backend GET /academic/courses/{course_id} endpoint
 */
export async function getCourse(courseId: string): Promise<Course> {
  validateRequiredId(courseId, 'Course ID')

  try {
    const response = await client.get<ApiResponse<Course>>(`/academic/courses/${courseId}`)
    return handleEnvelope<Course>(response)
  } catch (error) {
    handleApiError(error, 'Get course')
  }
}

/**
 * Create a new course
 * Matches backend POST /academic/courses endpoint
 */
export async function createCourse(courseData: CourseCreate): Promise<Course> {
  validateRequiredFields(courseData, ['name', 'course_code'])

  try {
    const response = await client.post<ApiResponse<Course>>('/academic/courses/', courseData)
    return handleEnvelope<Course>(response)
  } catch (error) {
    handleApiError(error, 'Create course')
  }
}

/**
 * Update an existing course
 * Matches backend PUT /academic/courses/{course_id} endpoint
 */
export async function updateCourse(courseId: string, courseData: CourseUpdate): Promise<Course> {
  validateRequiredId(courseId, 'Course ID')
  validateUpdatePayload(courseData)

  try {
    const response = await client.put<ApiResponse<Course>>(`/academic/courses/${courseId}`, courseData)
    return handleEnvelope<Course>(response)
  } catch (error) {
    handleApiError(error, 'Update course')
  }
}

/**
 * Delete a course
 * Matches backend DELETE /academic/courses/{course_id} endpoint
 */
export async function deleteCourse(courseId: string): Promise<void> {
  validateRequiredId(courseId, 'Course ID')

  try {
    const response = await client.delete<ApiResponse<void>>(`/academic/courses/${courseId}`)
    // For 204 responses, there's no body, so don't use handleEnvelope
    if (response.status === 204) {
      return
    }
    // For other success responses, use handleEnvelope
    handleEnvelope<void>(response)
  } catch (error) {
    handleApiError(error, 'Delete course')
  }
}

export default { listCourses, getCourse, createCourse, updateCourse, deleteCourse }
