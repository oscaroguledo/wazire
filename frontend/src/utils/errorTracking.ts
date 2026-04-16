/**
 * Error tracking utility
 * In production, this would integrate with services like Sentry, LogRocket, or custom error tracking
 */

interface ErrorContext {
  component?: string;
  action?: string;
  userId?: string;
  [key: string]: unknown;
}

class ErrorTracker {
  private isEnabled: boolean;
  private errors: Array<{ error: Error; context: ErrorContext; timestamp: Date }> = [];

  constructor() {
    this.isEnabled = process.env.NODE_ENV === 'production' || process.env.NODE_ENV === 'staging';
  }

  /**
   * Track an error with context
   */
  track(error: Error, context: ErrorContext = {}): void {
    const errorData = {
      error,
      context,
      timestamp: new Date(),
    };

    // Store in memory for debugging
    this.errors.push(errorData);

    // Keep only last 100 errors in memory
    if (this.errors.length > 100) {
      this.errors.shift();
    }

    // Log to console in development
    if (!this.isEnabled) {
      console.error('[ErrorTracker]', error, context);
      return;
    }

    // In production, send to error tracking service
    // Example: Sentry.captureException(error, { extra: context });
    this.sendToService(errorData);
  }

  /**
   * Send error to tracking service
   * Implement this based on your error tracking service
   */
  private sendToService(errorData: { error: Error; context: ErrorContext; timestamp: Date }): void {
    // Placeholder for error tracking service integration
    // Examples:
    // - Sentry: Sentry.captureException(errorData.error, { extra: errorData.context })
    // - LogRocket: LogRocket.captureException(errorData.error)
    // - Custom API: fetch('/api/errors', { method: 'POST', body: JSON.stringify(errorData) })
    
    // For now, just log to console with structured data
    console.error('[Error Tracking Service]', {
      message: errorData.error.message,
      stack: errorData.error.stack,
      context: errorData.context,
      timestamp: errorData.timestamp.toISOString(),
    });
  }

  /**
   * Get recent errors for debugging
   */
  getRecentErrors(count = 10): Array<{ error: Error; context: ErrorContext; timestamp: Date }> {
    return this.errors.slice(-count);
  }

  /**
   * Clear all stored errors
   */
  clearErrors(): void {
    this.errors = [];
  }
}

// Singleton instance
export const errorTracker = new ErrorTracker();

// Make available globally for ErrorBoundary
if (typeof window !== 'undefined') {
  (window as any).trackError = (error: Error, errorInfo: { componentStack?: string }) => {
    errorTracker.track(error, {
      component: errorInfo.componentStack,
      source: 'ErrorBoundary',
    });
  };
}

/**
 * Helper function to track errors in async operations
 */
export function trackAsyncError<T>(
  promise: Promise<T>,
  context: ErrorContext
): Promise<T> {
  return promise.catch((error: Error) => {
    errorTracker.track(error, context);
    throw error;
  });
}

/**
 * Higher-order function to wrap async handlers with error tracking
 */
export function withErrorTracking<T extends (...args: unknown[]) => Promise<unknown>>(
  fn: T,
  context: ErrorContext
): T {
  return (async (...args: Parameters<T>) => {
    try {
      return await fn(...args);
    } catch (error) {
      errorTracker.track(error as Error, context);
      throw error;
    }
  }) as T;
}
