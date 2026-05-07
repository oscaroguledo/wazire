/**
 * Unit tests for auth API functions.
 *
 * Tests: login, register, refresh, me, listUsers, getUser, updateUser, deleteUser
 * Uses MSW to intercept HTTP requests.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@/mocks/server'
import * as authApi from '@/apis/auth'
import { ApiError } from '@/apis/client'

const BASE_URL = '/api/v1'

const mockUser = {
  id: 'user-1',
  email: 'test@test.com',
  first_name: 'Test',
  middle_name: null,
  last_name: 'User',
  role: 'student' as const,
  is_active: true,
  tenant_id: 'tenant-1',
  institution_id: null,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

const mockTokens = {
  access_token: 'mock-access-token',
  refresh_token: 'mock-refresh-token',
  token_type: 'bearer',
}

function envelope<T>(data: T) {
  return { success: true, message: 'Success', data, request_id: 'test', timestamp: new Date().toISOString() }
}

describe('auth API', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  describe('login()', () => {
    it('returns user and tokens on success', async () => {
      server.use(
        http.post(`${BASE_URL}/auth/login`, () =>
          HttpResponse.json(envelope({ user: mockUser, tokens: mockTokens }))
        )
      )

      const result = await authApi.login({ email: 'test@test.com', password: 'password' })

      expect(result.user.email).toBe('test@test.com')
      expect(result.tokens.access_token).toBe('mock-access-token')
    })

    it('stores access token in localStorage on success', async () => {
      server.use(
        http.post(`${BASE_URL}/auth/login`, () =>
          HttpResponse.json(envelope({ user: mockUser, tokens: mockTokens }))
        )
      )

      await authApi.login({ email: 'test@test.com', password: 'password' })

      expect(localStorage.getItem('access_token')).toBe('mock-access-token')
    })

    it('throws ApiError on invalid credentials', async () => {
      server.use(
        http.post(`${BASE_URL}/auth/login`, () =>
          HttpResponse.json(
            { success: false, error: 'Invalid credentials', message: 'Invalid credentials' },
            { status: 401 }
          )
        )
      )

      await expect(authApi.login({ email: 'bad@test.com', password: 'wrong' }))
        .rejects.toThrow()
    })

    it('throws ApiError when required fields are missing', async () => {
      await expect(authApi.login({ email: '', password: 'password' }))
        .rejects.toThrow(ApiError)
    })
  })

  describe('register()', () => {
    it('returns user on successful registration', async () => {
      server.use(
        http.post(`${BASE_URL}/auth/register`, () =>
          HttpResponse.json(envelope(mockUser), { status: 201 })
        )
      )

      const result = await authApi.register({
        first_name: 'Test',
        last_name: 'User',
        email: 'test@test.com',
        password: 'SecurePass123!',
      })

      expect(result.email).toBe('test@test.com')
    })

    it('throws ApiError for invalid email', async () => {
      await expect(authApi.register({
        first_name: 'Test',
        last_name: 'User',
        email: 'not-an-email',
        password: 'SecurePass123!',
      })).rejects.toThrow(ApiError)
    })

    it('throws ApiError for short password', async () => {
      await expect(authApi.register({
        first_name: 'Test',
        last_name: 'User',
        email: 'test@test.com',
        password: 'short',
      })).rejects.toThrow(ApiError)
    })
  })

  describe('me()', () => {
    it('returns current user profile', async () => {
      server.use(
        http.get(`${BASE_URL}/auth/me`, () =>
          HttpResponse.json(envelope(mockUser))
        )
      )

      const result = await authApi.me()

      expect(result.id).toBe('user-1')
      expect(result.email).toBe('test@test.com')
    })

    it('throws on 401 response', async () => {
      server.use(
        http.get(`${BASE_URL}/auth/me`, () =>
          HttpResponse.json(
            { success: false, error: 'Unauthorized', message: 'Unauthorized' },
            { status: 401 }
          )
        )
      )

      await expect(authApi.me()).rejects.toThrow()
    })
  })

  describe('refresh()', () => {
    it('returns new tokens on success', async () => {
      server.use(
        http.post(`${BASE_URL}/auth/refresh`, () =>
          HttpResponse.json(envelope(mockTokens))
        )
      )

      const result = await authApi.refresh('mock-refresh-token')

      expect(result.access_token).toBe('mock-access-token')
    })

    it('throws ApiError when refresh token is empty', async () => {
      await expect(authApi.refresh('')).rejects.toThrow(ApiError)
    })
  })

  describe('listUsers()', () => {
    it('returns paginated user list', async () => {
      server.use(
        http.get(`${BASE_URL}/account/users`, () =>
          HttpResponse.json({
            success: true,
            message: 'Success',
            data: [mockUser],
            meta: { page: 1, per_page: 10, total: 1, pages: 1, has_next: false, has_prev: false },
            request_id: 'test',
            timestamp: new Date().toISOString(),
          })
        )
      )

      const result = await authApi.listUsers()

      expect(result.items).toHaveLength(1)
      expect(result.items[0].email).toBe('test@test.com')
      expect(result.pagination.total).toBe(1)
    })
  })

  describe('getUser()', () => {
    it('returns user by ID', async () => {
      server.use(
        http.get(`${BASE_URL}/account/users/user-1`, () =>
          HttpResponse.json(envelope(mockUser))
        )
      )

      const result = await authApi.getUser('user-1')

      expect(result.id).toBe('user-1')
    })

    it('throws ApiError when user ID is empty', async () => {
      await expect(authApi.getUser('')).rejects.toThrow(ApiError)
    })
  })

  describe('updateUser()', () => {
    it('returns updated user', async () => {
      server.use(
        http.put(`${BASE_URL}/account/users/user-1`, () =>
          HttpResponse.json(envelope({ ...mockUser, first_name: 'Updated' }))
        )
      )

      const result = await authApi.updateUser('user-1', { first_name: 'Updated' })

      expect(result.first_name).toBe('Updated')
    })

    it('throws ApiError when payload is empty', async () => {
      await expect(authApi.updateUser('user-1', {})).rejects.toThrow(ApiError)
    })
  })

  describe('deleteUser()', () => {
    it('completes without error on success', async () => {
      server.use(
        http.delete(`${BASE_URL}/account/users/user-1`, () =>
          new HttpResponse(null, { status: 204 })
        )
      )

      await expect(authApi.deleteUser('user-1')).resolves.not.toThrow()
    })

    it('throws ApiError when user ID is empty', async () => {
      await expect(authApi.deleteUser('')).rejects.toThrow(ApiError)
    })
  })
})
