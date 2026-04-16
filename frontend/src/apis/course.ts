import client, { handleEnvelope, handlePaginatedEnvelope, ApiResponse, ApiError } from '@/apis/client'
import { config } from '@/config'

// Course Types (matching backend schemas)
export interface Course {
  id: string
  name: string
  description?: string
  course_code: string
  lecturer: any
  tenant_id?: string
  tenant?: string
  created_at: string
  updated_at: string
}

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
  if (!courseId) {
    throw new ApiError('Course ID is required', 400)
  }

  try {
    const response = await client.get<ApiResponse<Course>>(`/academic/courses/${courseId}`)
    return handleEnvelope<Course>(response)
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    
    if (error instanceof Error) {
      if (error.message.includes('401') || error.message.includes('Not authenticated')) {
        throw new ApiError('Authentication required to view course', 401)
      }
      if (error.message.includes('403') || error.message.includes('Forbidden')) {
        throw new ApiError('Access denied to view this course', 403)
      }
      if (error.message.includes('404') || error.message.includes('Not Found')) {
        throw new ApiError('Course not found', 404)
      }
    }
    
    throw new ApiError('Failed to fetch course', 500)
  }
}

/**
 * Create a new course
 * Matches backend POST /academic/courses endpoint
 */
export async function createCourse(courseData: CourseCreate): Promise<Course> {
  if (!courseData.name || !courseData.course_code) {
    throw new ApiError('Course name and code are required', 400)
  }

  try {
    const response = await client.post<ApiResponse<Course>>('/academic/courses/', courseData)
    return handleEnvelope<Course>(response)
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    
    if (error instanceof Error) {
      if (error.message.includes('401') || error.message.includes('Not authenticated')) {
        throw new ApiError('Authentication required to create courses', 401)
      }
      if (error.message.includes('403') || error.message.includes('Forbidden')) {
        throw new ApiError('Access denied to create courses', 403)
      }
      if (error.message.includes('400') || error.message.includes('Bad Request')) {
        throw new ApiError('Invalid course data', 400)
      }
      if (error.message.includes('409') || error.message.includes('Conflict')) {
        throw new ApiError('Course code already exists', 409)
      }
    }
    
    throw new ApiError('Failed to create course', 500)
  }
}

/**
 * Update an existing course
 * Matches backend PUT /academic/courses/{course_id} endpoint
 */
export async function updateCourse(courseId: string, courseData: CourseUpdate): Promise<Course> {
  if (!courseId) {
    throw new ApiError('Course ID is required', 400)
  }

  if (Object.keys(courseData).length === 0) {
    throw new ApiError('At least one field must be provided for update', 400)
  }

  try {
    const response = await client.put<ApiResponse<Course>>(`/academic/courses/${courseId}`, courseData)
    return handleEnvelope<Course>(response)
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    
    if (error instanceof Error) {
      if (error.message.includes('401') || error.message.includes('Not authenticated')) {
        throw new ApiError('Authentication required to update courses', 401)
      }
      if (error.message.includes('403') || error.message.includes('Forbidden')) {
        throw new ApiError('Access denied to update this course', 403)
      }
      if (error.message.includes('404') || error.message.includes('Not Found')) {
        throw new ApiError('Course not found', 404)
      }
      if (error.message.includes('400') || error.message.includes('Bad Request')) {
        throw new ApiError('Invalid course data', 400)
      }
      if (error.message.includes('409') || error.message.includes('Conflict')) {
        throw new ApiError('Course code already exists', 409)
      }
    }
    
    throw new ApiError('Failed to update course', 500)
  }
}

/**
 * Delete a course
 * Matches backend DELETE /academic/courses/{course_id} endpoint
 */
export async function deleteCourse(courseId: string): Promise<void> {
  if (!courseId) {
    throw new ApiError('Course ID is required', 400)
  }

  try {
    const response = await client.delete<ApiResponse<void>>(`/academic/courses/${courseId}`)
    // For 204 responses, there's no body, so don't use handleEnvelope
    if (response.status === 204) {
      return
    }
    // For other success responses, use handleEnvelope
    handleEnvelope<void>(response)
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    
    if (error instanceof Error) {
      if (error.message.includes('401') || error.message.includes('Not authenticated')) {
        throw new ApiError('Authentication required to delete courses', 401)
      }
      if (error.message.includes('403') || error.message.includes('Forbidden')) {
        throw new ApiError('Access denied to delete this course', 403)
      }
      if (error.message.includes('404') || error.message.includes('Not Found')) {
        throw new ApiError('Course not found', 404)
      }
      if (error.message.includes('400') || error.message.includes('Bad Request')) {
        throw new ApiError('Cannot delete course with existing enrollments or exams', 400)
      }
    }
    
    throw new ApiError('Failed to delete course', 500)
  }
}

export default { listCourses, getCourse, createCourse, updateCourse, deleteCourse }
