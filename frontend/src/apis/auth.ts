import client, { handleEnvelope, handlePaginatedEnvelope, ApiResponse, ApiError } from '@/apis/client'
import { config } from '@/config'
import { validateRequiredFields, validatePassword, validateEmail, validateRequiredId, validateUpdatePayload, handleApiError } from './api-utils'
import type { User as SharedUser } from '@/lib/types'

// Use shared User type from types.ts
export type User = SharedUser

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
  validateRequiredFields(payload, ['email', 'password'])

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
    handleApiError(error, 'Login')
  }
}

/**
 * Register a new user
 * Matches backend POST /auth/register endpoint
 */
export async function register(payload: RegisterPayload): Promise<User> {
  validateRequiredFields(payload, ['email', 'password', 'first_name', 'last_name'])
  validatePassword(payload.password)
  validateEmail(payload.email)

  try {
    const response = await client.post<ApiResponse<User>>('/auth/register', payload)
    return handleEnvelope<User>(response)
  } catch (error) {
    handleApiError(error, 'Registration')
  }
}

/**
 * Refresh access token
 * Matches backend POST /auth/refresh endpoint
 */
export async function refresh(refreshToken: string): Promise<AuthTokens> {
  validateRequiredId(refreshToken, 'Refresh token')

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
    handleApiError(error, 'Token refresh')
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
    handleApiError(error, 'Get user profile')
  }
}

/**
 * Update current user profile
 * Matches backend PUT /auth/me endpoint
 */
export async function updateMe(payload: Partial<Omit<User, 'id' | 'created_at' | 'updated_at'>>): Promise<User> {
  validateUpdatePayload(payload)

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
    handleApiError(error, 'Profile update')
  }
}

/**
 * List users (admin only)
 * Matches backend GET /account/users endpoint
 */
export async function listUsers(params?: UserListParams): Promise<UserListResponse> {
  try {
    const requestParams: Record<string, any> = {
      page: params?.page || 1,
      per_page: params?.per_page || config.DEFAULT_PAGE_SIZE,
    }
    if (params?.tenant_id) requestParams.tenant_id = params.tenant_id

    const response = await client.get<ApiResponse<User[]>>('/account/users', { params: requestParams })
    return handlePaginatedEnvelope<User>(response)
  } catch (error) {
    handleApiError(error, 'List users')
  }
}

/**
 * Get user by ID (admin only)
 * Matches backend GET /account/users/{user_id} endpoint
 */
export async function getUser(userId: string): Promise<User> {
  validateRequiredId(userId, 'User ID')

  try {
    const response = await client.get<ApiResponse<User>>(`/account/users/${userId}`)
    return handleEnvelope<User>(response)
  } catch (error) {
    handleApiError(error, 'Get user')
  }
}

/**
 * Update user (admin only)
 * Matches backend PUT /account/users/{user_id} endpoint
 */
export async function updateUser(userId: string, payload: Partial<Omit<User, 'id' | 'created_at' | 'updated_at'>>): Promise<User> {
  validateRequiredId(userId, 'User ID')
  validateUpdatePayload(payload)

  try {
    const response = await client.put<ApiResponse<User>>(`/account/users/${userId}`, payload)
    return handleEnvelope<User>(response)
  } catch (error) {
    handleApiError(error, 'Update user')
  }
}

/**
 * Delete user (admin only)
 * Matches backend DELETE /account/users/{user_id} endpoint
 */
export async function deleteUser(userId: string): Promise<void> {
  validateRequiredId(userId, 'User ID')

  try {
    const response = await client.delete<ApiResponse<void>>(`/account/users/${userId}`)
    handleEnvelope<void>(response)
  } catch (error) {
    handleApiError(error, 'Delete user')
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
