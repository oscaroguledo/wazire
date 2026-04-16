import { ApiError } from './client';
import { config } from '@/config';

/**
 * Shared API utility functions to reduce code duplication across API files
 */

/**
 * Validate required fields in a payload
 */
export function validateRequiredFields(payload: Record<string, any>, requiredFields: string[]): void {
  const missingFields = requiredFields.filter(field => !payload[field]);
  if (missingFields.length > 0) {
    throw new ApiError(`Missing required fields: ${missingFields.join(', ')}`, 400);
  }
}

/**
 * Validate password against config rules
 */
export function validatePassword(password: string): void {
  if (!password) {
    throw new ApiError('Password is required', 400);
  }
  if (password.length < config.MIN_PASSWORD_LENGTH) {
    throw new ApiError(`Password must be at least ${config.MIN_PASSWORD_LENGTH} characters long`, 400);
  }
}

/**
 * Validate email format
 */
export function validateEmail(email: string): void {
  if (!email) {
    throw new ApiError('Email is required', 400);
  }
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    throw new ApiError('Please provide a valid email address', 400);
  }
}

/**
 * Validate required ID parameter
 */
export function validateRequiredId(id: string, resourceName: string = 'ID'): void {
  if (!id) {
    throw new ApiError(`${resourceName} is required`, 400);
  }
}

/**
 * Validate that at least one field is provided for update
 */
export function validateUpdatePayload(payload: Record<string, any>): void {
  if (Object.keys(payload).length === 0) {
    throw new ApiError('At least one field must be provided for update', 400);
  }
}

/**
 * Build pagination params with defaults from config
 */
export function buildPaginationParams(params?: { page?: number; per_page?: number }): Record<string, number> {
  return {
    page: params?.page || 1,
    per_page: params?.per_page || config.DEFAULT_PAGE_SIZE,
  };
}

/**
 * Common error handler for API calls
 * Maps common error messages to user-friendly ApiError instances
 */
export function handleApiError(error: unknown, context: string): never {
  if (error instanceof ApiError) {
    throw error;
  }

  if (error instanceof Error) {
    const message = error.message.toLowerCase();

    // Authentication errors
    if (message.includes('401') || message.includes('unauthorized') || message.includes('not authenticated')) {
      throw new ApiError('Authentication required', 401);
    }

    // Authorization errors
    if (message.includes('403') || message.includes('forbidden')) {
      throw new ApiError('Access denied', 403);
    }

    // Not found errors
    if (message.includes('404') || message.includes('not found')) {
      throw new ApiError('Resource not found', 404);
    }

    // Conflict errors
    if (message.includes('409') || message.includes('conflict')) {
      throw new ApiError('Resource already exists', 409);
    }

    // Rate limiting
    if (message.includes('429') || message.includes('too many requests')) {
      throw new ApiError('Too many requests. Please try again later.', 429);
    }

    // Bad request
    if (message.includes('400') || message.includes('bad request')) {
      throw new ApiError('Invalid request data', 400);
    }

    // Specific auth errors
    if (message.includes('invalid email or password') || message.includes('invalid credentials')) {
      throw new ApiError('Invalid email or password', 401);
    }

    if (message.includes('email already registered')) {
      throw new ApiError('Email already registered', 409);
    }

    if (message.includes('invalid or expired refresh token') || message.includes('session expired')) {
      throw new ApiError('Session expired. Please login again.', 401);
    }
  }

  throw new ApiError(`${context} failed. Please try again.`, 500);
}

/**
 * HTTP Status Code Constants
 */
export const HTTP_STATUS = {
  OK: 200,
  CREATED: 201,
  NO_CONTENT: 204,
  BAD_REQUEST: 400,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  CONFLICT: 409,
  UNPROCESSABLE_ENTITY: 422,
  TOO_MANY_REQUESTS: 429,
  INTERNAL_SERVER_ERROR: 500,
} as const;

/**
 * Common error messages
 */
export const ERROR_MESSAGES = {
  AUTH_REQUIRED: 'Authentication required',
  ACCESS_DENIED: 'Access denied',
  NOT_FOUND: 'Resource not found',
  ALREADY_EXISTS: 'Resource already exists',
  INVALID_CREDENTIALS: 'Invalid email or password',
  SESSION_EXPIRED: 'Session expired. Please login again.',
  TOO_MANY_REQUESTS: 'Too many requests. Please try again later.',
  INVALID_DATA: 'Invalid request data',
  OPERATION_FAILED: 'Operation failed. Please try again.',
} as const;
