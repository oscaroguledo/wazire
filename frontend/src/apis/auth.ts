import client, { handleEnvelope, handlePaginatedEnvelope, ApiResponse, ApiError } from '@/apis/client'
import { config } from '@/config'

// Auth Types (matching backend schemas)
export interface User {
  id: string
  email: string
  first_name: string
  middle_name?: string
  last_name: string
  role: 'student' | 'lecturer' | 'admin'
  tenant_id?: string
  tenant_name?: string
  logo_url?: string
  institution_id?: string  // Matric number / Reg No
  is_active: boolean
  created_at: string
  updated_at: string
  avatar?: string
}

export interface AuthTokens {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface AuthResponse {
  user: User
  tokens: AuthTokens
}

export interface LoginPayload {
  email: string
  password: string
}

export interface RegisterPayload {
  first_name: string
  middle_name?: string
  last_name: string
  email: string
  password: string
  role?: 'student' | 'lecturer' | 'admin'
  tenant_id?: string
  institution_id?: string  // Matric number / Reg No
}

export interface RefreshPayload {
  refresh_token: string
}

export interface UserListParams {
  page?: number
  per_page?: number
  role?: User['role']
  tenant_id?: string
  is_active?: boolean
}

export interface UserListResponse {
  items: User[]
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
 * Login user with email and password
 * Matches backend POST /auth/login endpoint
 */
export async function login(payload: LoginPayload): Promise<AuthResponse> {
  if (!payload.email || !payload.password) {
    throw new ApiError('Email and password are required', 400)
  }

  try {
    const response = await client.post<ApiResponse<AuthResponse>>('/auth/login', payload)
    const data = handleEnvelope<AuthResponse>(response)
    
    // Validate response structure
    if (!data.user || !data.tokens) {
      throw new ApiError('Invalid authentication response', 500)
    }

    // Store tokens securely
    try {
      localStorage.setItem(config.TOKEN_KEY, data.tokens.access_token)
      if (data.tokens.refresh_token) {
        localStorage.setItem('refresh_token', data.tokens.refresh_token)
      }
      localStorage.setItem('wazire_user', JSON.stringify(data.user))
    } catch (storageError) {
      console.warn('Failed to store auth data:', storageError)
      // Continue without throwing - auth still works
    }

    return data
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    
    // Handle specific backend error responses
    if (error instanceof Error) {
      if (error.message.includes('Invalid email or password')) {
        throw new ApiError('Invalid email or password', 401)
      }
      if (error.message.includes('Email already registered')) {
        throw new ApiError('Email already registered', 409)
      }
      if (error.message.includes('401') || error.message.includes('Unauthorized')) {
        throw new ApiError('Invalid credentials', 401)
      }
      if (error.message.includes('429') || error.message.includes('Too many requests')) {
        throw new ApiError('Too many login attempts. Please try again later.', 429)
      }
    }
    
    throw new ApiError('Login failed. Please try again.', 500)
  }
}

/**
 * Register a new user
 * Matches backend POST /auth/register endpoint
 */
export async function register(payload: RegisterPayload): Promise<User> {
  if (!payload.email || !payload.password || !payload.first_name || !payload.last_name) {
    throw new ApiError('All required fields must be provided', 400)
  }

  if (payload.password.length < 8) {
    throw new ApiError('Password must be at least 8 characters long', 400)
  }

  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(payload.email)) {
    throw new ApiError('Please provide a valid email address', 400)
  }

  try {
    const response = await client.post<ApiResponse<User>>('/auth/register', payload)
    return handleEnvelope<User>(response)
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    
    if (error instanceof Error) {
      if (error.message.includes('Email already registered')) {
        throw new ApiError('Email already registered', 409)
      }
      if (error.message.includes('400') || error.message.includes('Bad Request')) {
        throw new ApiError('Invalid registration data', 400)
      }
    }
    
    throw new ApiError('Registration failed. Please try again.', 500)
  }
}

/**
 * Refresh access token
 * Matches backend POST /auth/refresh endpoint
 */
export async function refresh(refreshToken: string): Promise<AuthTokens> {
  if (!refreshToken) {
    throw new ApiError('Refresh token is required', 400)
  }

  try {
    const response = await client.post<ApiResponse<AuthTokens>>('/auth/refresh', { 
      refresh_token: refreshToken 
    })
    const tokens = handleEnvelope<AuthTokens>(response)
    
    // Update stored access token
    try {
      localStorage.setItem(config.TOKEN_KEY, tokens.access_token)
      if (tokens.refresh_token) {
        localStorage.setItem('refresh_token', tokens.refresh_token)
      }
    } catch (storageError) {
      console.warn('Failed to store refreshed token:', storageError)
    }

    return tokens
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    
    if (error instanceof Error) {
      if (error.message.includes('Invalid or expired refresh token')) {
        throw new ApiError('Session expired. Please login again.', 401)
      }
      if (error.message.includes('401') || error.message.includes('Unauthorized')) {
        throw new ApiError('Session expired. Please login again.', 401)
      }
    }
    
    throw new ApiError('Token refresh failed', 500)
  }
}

/**
 * Get current user profile
 * Matches backend GET /auth/me endpoint
 */
export async function me(): Promise<User> {
  try {
    const response = await client.get<ApiResponse<User>>('/auth/me')
    return handleEnvelope<User>(response)
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    
    if (error instanceof Error) {
      if (error.message.includes('401') || error.message.includes('Unauthorized')) {
        throw new ApiError('Authentication required', 401)
      }
    }
    
    throw new ApiError('Failed to get user profile', 500)
  }
}

/**
 * Get admin statistics (admin only)
 * Uses existing user management system
 */
export async function getAdminStats(): Promise<{
  total_users: number;
  student_users: number;
  lecturer_users: number;
  admin_users: number;
  total_courses: number;
  total_exams: number;
  total_submissions: number;
  total_tenants: number;
  active_users: number;
  pending_approvals: number;
}> {
  try {
    const response = await client.get<ApiResponse<{
      total_users: number;
      student_users: number;
      lecturer_users: number;
      admin_users: number;
      total_courses: number;
      total_exams: number;
      total_submissions: number;
      total_tenants: number;
      active_users: number;
      pending_approvals: number;
    }>>('/auth/admin/stats')
    return response.data.data ?? {
      total_users: 0,
      student_users: 0,
      lecturer_users: 0,
      admin_users: 0,
      total_courses: 0,
      total_exams: 0,
      total_submissions: 0,
      total_tenants: 0,
      active_users: 0,
      pending_approvals: 0
    }
  } catch (error) {
    console.error('Failed to fetch admin stats:', error)
    // Return default stats if API fails
    return {
      total_users: 0,
      student_users: 0,
      lecturer_users: 0,
      admin_users: 0,
      total_courses: 0,
      total_exams: 0,
      total_submissions: 0,
      total_tenants: 0,
      active_users: 0,
      pending_approvals: 0
    }
  }
}

/**
 * Update current user profile
 * Matches backend PUT /auth/me endpoint
 */
export async function updateMe(payload: Partial<Omit<User, 'id' | 'created_at' | 'updated_at'>>): Promise<User> {
  if (Object.keys(payload).length === 0) {
    throw new ApiError('At least one field must be provided for update', 400)
  }

  try {
    const response = await client.put<ApiResponse<User>>('/auth/me', payload)
    const updatedUser = handleEnvelope<User>(response)
    
    // Update stored user data
    try {
      localStorage.setItem('wazire_user', JSON.stringify(updatedUser))
    } catch (storageError) {
      console.warn('Failed to store updated user data:', storageError)
    }

    return updatedUser
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    
    if (error instanceof Error) {
      if (error.message.includes('401') || error.message.includes('Unauthorized')) {
        throw new ApiError('Authentication required', 401)
      }
      if (error.message.includes('400') || error.message.includes('Bad Request')) {
        throw new ApiError('Invalid update data', 400)
      }
    }
    
    throw new ApiError('Profile update failed', 500)
  }
}

/**
 * List users (admin only)
 * Matches backend GET /auth/ endpoint (keyset pagination)
 */
export async function listUsers(params?: UserListParams): Promise<UserListResponse> {
  try {
    const requestParams: Record<string, any> = {
      page: params?.page || 1,
      per_page: params?.per_page || config.DEFAULT_PAGE_SIZE,
    }
    if (params?.tenant_id) requestParams.tenant_id = params.tenant_id

    const response = await client.get<ApiResponse<User[]>>('/auth/', { params: requestParams })
    return handlePaginatedEnvelope<User>(response)
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (error instanceof Error) {
      if (error.message.includes('401') || error.message.includes('403')) {
        throw new ApiError('Admin access required', 403)
      }
    }
    throw new ApiError('Failed to list users', 500)
  }
}

/**
 * Get user by ID (admin only)
 * Matches backend GET /auth/{user_id} endpoint
 */
export async function getUser(userId: string): Promise<User> {
  if (!userId) {
    throw new ApiError('User ID is required', 400)
  }

  try {
    const response = await client.get<ApiResponse<User>>(`/auth/${userId}`)
    return handleEnvelope<User>(response)
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    
    if (error instanceof Error) {
      if (error.message.includes('401') || error.message.includes('Unauthorized')) {
        throw new ApiError('Authentication required', 401)
      }
      if (error.message.includes('403') || error.message.includes('Forbidden')) {
        throw new ApiError('Admin access required', 403)
      }
      if (error.message.includes('404') || error.message.includes('Not Found')) {
        throw new ApiError('User not found', 404)
      }
    }
    
    throw new ApiError('Failed to get user', 500)
  }
}

/**
 * Update user (admin only)
 * Matches backend PUT /auth/{user_id} endpoint
 */
export async function updateUser(userId: string, payload: Partial<Omit<User, 'id' | 'created_at' | 'updated_at'>>): Promise<User> {
  if (!userId) {
    throw new ApiError('User ID is required', 400)
  }

  if (Object.keys(payload).length === 0) {
    throw new ApiError('At least one field must be provided for update', 400)
  }

  try {
    const response = await client.put<ApiResponse<User>>(`/auth/${userId}`, payload)
    return handleEnvelope<User>(response)
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    
    if (error instanceof Error) {
      if (error.message.includes('401') || error.message.includes('Unauthorized')) {
        throw new ApiError('Authentication required', 401)
      }
      if (error.message.includes('403') || error.message.includes('Forbidden')) {
        throw new ApiError('Admin access required', 403)
      }
      if (error.message.includes('404') || error.message.includes('Not Found')) {
        throw new ApiError('User not found', 404)
      }
      if (error.message.includes('400') || error.message.includes('Bad Request')) {
        throw new ApiError('Invalid update data', 400)
      }
    }
    
    throw new ApiError('Failed to update user', 500)
  }
}

/**
 * Delete user (admin only)
 * Matches backend DELETE /auth/{user_id} endpoint
 */
export async function deleteUser(userId: string): Promise<void> {
  if (!userId) {
    throw new ApiError('User ID is required', 400)
  }

  try {
    const response = await client.delete<ApiResponse<void>>(`/auth/${userId}`)
    handleEnvelope<void>(response)
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    
    if (error instanceof Error) {
      if (error.message.includes('401') || error.message.includes('Unauthorized')) {
        throw new ApiError('Authentication required', 401)
      }
      if (error.message.includes('403') || error.message.includes('Forbidden')) {
        throw new ApiError('Admin access required', 403)
      }
      if (error.message.includes('404') || error.message.includes('Not Found')) {
        throw new ApiError('User not found', 404)
      }
    }
    
    throw new ApiError('Failed to delete user', 500)
  }
}

export default { 
  login, 
  register, 
  refresh, 
  me, 
  updateMe, 
  listUsers, 
  getUser, 
  updateUser, 
  deleteUser 
}
