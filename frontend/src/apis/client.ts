import axios, { AxiosInstance, AxiosResponse, AxiosError, InternalAxiosRequestConfig } from 'axios'
import { config, getAuthToken, removeAuthToken } from '@/config'
import { errorTracker } from '@/utils/errorTracking'

// Create axios instance with configuration
const client: AxiosInstance = axios.create({
  baseURL: config.API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: config.API_TIMEOUT,
})

// Request interceptor to attach auth token
client.interceptors.request.use((cfg: InternalAxiosRequestConfig) => {
  const token = getAuthToken()

  // Ensure headers object exists
  cfg.headers = cfg.headers || {}

  if (token) {
    cfg.headers.Authorization = `Bearer ${token}`
  }

  // Add request ID for debugging
  cfg.headers['X-Request-ID'] = generateRequestId()

  return cfg
})

// Response interceptor to handle common errors
client.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError) => {
    // Handle 401 Unauthorized - token expired or invalid
    if (error.response?.status === 401) {
      removeAuthToken()
      // Redirect to login page
      window.location.href = config.ROUTES.LOGIN
      return Promise.reject(error)
    }

    // Handle 403 Forbidden - insufficient permissions
    if (error.response?.status === 403) {
      errorTracker.track(error, { action: 'api_request', status: 403, url: error.config?.url });
      return Promise.reject(error)
    }

    // Handle 404 Not Found
    if (error.response?.status === 404) {
      errorTracker.track(error, { action: 'api_request', status: 404, url: error.config?.url });
      return Promise.reject(error)
    }

    // Handle 500 Server Error
    if (error.response?.status && error.response?.status >= 500) {
      errorTracker.track(error, { action: 'api_request', status: error.response.status, url: error.config?.url });
      return Promise.reject(error)
    }

    return Promise.reject(error)
  }
)

// Generate unique request ID
function generateRequestId(): string {
  return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

// API Response Types
export interface ApiResponse<T = any> {
  success: boolean
  message: string
  data?: T
  error?: string
  meta?: PaginationMeta
  pagination?: {
    page: number
    per_page: number
    total: number
    pages: number
    has_next: boolean
    has_prev: boolean
  }
}

export interface PaginationMeta {
  page: number
  per_page: number
  total: number
  pages: number
  has_next: boolean
  has_prev: boolean
  next_page?: number | null
  prev_page?: number | null
}

export interface PaginatedResponse<T> {
  items: T[]
  pagination: PaginationMeta
}

/**
 * Handle API response envelope
 * Extracts data from backend response format
 */
export function handleEnvelope<T>(resp: AxiosResponse<ApiResponse<T>>): T {
  if (!resp) {
    throw new Error('Invalid API response: No response received')
  }
  
  // Handle 204 No Content - return undefined for void operations
  if (resp.status === 204) {
    return undefined as T
  }
  
  if (!resp.data) {
    throw new Error('Invalid API response: No data received')
  }
  
  const body = resp.data
  
  // Handle empty object case for 204-like responses
  if (Object.keys(body).length === 0) {
    return undefined as T
  }
  
  if (body.success === false) {
    const message = body.error || body.message || 'API Error'
    throw new Error(message)
  }
  
  // Allow null/undefined data for successful responses (e.g., no submission found)
  if (body.data === undefined) {
    throw new Error('API response missing data field')
  }
  
  return body.data
}

/**
 * Handle paginated API response envelope
 * Extracts both data and meta pagination from backend response
 */
export function handlePaginatedEnvelope<T>(resp: AxiosResponse<ApiResponse<T[]>>): PaginatedResponse<T> {
  if (!resp || !resp.data) {
    throw new Error('Invalid API response: No data received')
  }

  const body = resp.data

  if (body.success === false) {
    const message = body.error || body.message || 'API Error'
    throw new Error(message)
  }

  const items = body.data ?? []
  const pagination = body.meta ?? {} as PaginationMeta

  // Use backend pagination if available (offset/limit), otherwise fallback to defaults
  const meta: PaginationMeta = {
    page: pagination.page || 1,
    per_page: pagination.per_page || items.length,
    total: pagination.total ?? items.length,
    pages: pagination.pages || 1,
    has_next: pagination.has_next || false,
    has_prev: pagination.has_prev || false,
    next_page: pagination.next_page || null,
    prev_page: pagination.prev_page || null,
  }

  return { items: items as T[], pagination: meta }
}


/**
 * Error handling helper
 */
export class ApiError extends Error {
  public status?: number
  public code?: string
  public details?: unknown

  constructor(message: string, status?: number, code?: string, details?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }
}

/**
 * Safe API request wrapper
 */
export async function safeRequest<T>(
  requestFn: () => Promise<AxiosResponse<T>>
): Promise<T> {
  try {
    const response = await requestFn()
    return response.data
  } catch (error: unknown) {
    if (error instanceof AxiosError && error.response) {
      const status = error.response.status
      const data = error.response.data as { message?: string; error?: string; code?: string }

      throw new ApiError(
        data?.message || data?.error || `HTTP ${status} Error`,
        status,
        data?.code,
        data
      )
    } else if (error instanceof AxiosError && error.request) {
      throw new ApiError('Network error: Unable to reach server', 0, 'NETWORK_ERROR')
    } else if (error instanceof Error) {
      throw new ApiError(error.message || 'Unknown error occurred', 0, 'UNKNOWN_ERROR')
    } else {
      throw new ApiError('Unknown error occurred', 0, 'UNKNOWN_ERROR')
    }
  }
}

/**
 * File upload helper
 */
export function uploadFile(file: File, additionalData?: Record<string, string | number | boolean | File>): Promise<AxiosResponse> {
  const formData = new FormData()
  formData.append('file', file)

  if (additionalData) {
    Object.entries(additionalData).forEach(([key, value]) => {
      formData.append(key, value as string | Blob)
    })
  }

  return client.post('/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    timeout: config.UPLOAD_TIMEOUT,
  })
}

/**
 * Export default client
 */
export default client
