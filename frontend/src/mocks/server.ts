/**
 * MSW Node.js server for Vitest test environment.
 * Intercepts HTTP requests during tests and returns mock responses.
 */
import { setupServer } from 'msw/node'
import { handlers } from './handlers'

// Create the MSW server with all handlers
export const server = setupServer(...handlers)
