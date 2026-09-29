/**
 * Error handling utilities for the BHUMISETU frontend.
 * Provides standardized error formatting, logging, and user-facing messages.
 */

/** Application-specific error codes */
export type AppErrorCode =
  | 'NETWORK_ERROR'
  | 'AUTH_EXPIRED'
  | 'AUTH_REQUIRED'
  | 'FORBIDDEN'
  | 'NOT_FOUND'
  | 'VALIDATION_ERROR'
  | 'RATE_LIMITED'
  | 'SERVER_ERROR'
  | 'TIMEOUT'
  | 'UNKNOWN';

/** Structured application error */
export interface AppError {
  code: AppErrorCode;
  message: string;
  userMessage: string;
  statusCode?: number;
  details?: Record<string, unknown>;
  timestamp: string;
}

/** Map HTTP status codes to application error codes */
function statusToErrorCode(status: number): AppErrorCode {
  switch (status) {
    case 401: return 'AUTH_EXPIRED';
    case 403: return 'FORBIDDEN';
    case 404: return 'NOT_FOUND';
    case 422: return 'VALIDATION_ERROR';
    case 429: return 'RATE_LIMITED';
    default:
      if (status >= 500) return 'SERVER_ERROR';
      return 'UNKNOWN';
  }
}

/** User-friendly error messages in English */
const USER_MESSAGES: Record<AppErrorCode, string> = {
  NETWORK_ERROR: 'Unable to connect to the server. Please check your internet connection.',
  AUTH_EXPIRED: 'Your session has expired. Please log in again.',
  AUTH_REQUIRED: 'You need to log in to access this feature.',
  FORBIDDEN: 'You do not have permission to perform this action.',
  NOT_FOUND: 'The requested information could not be found.',
  VALIDATION_ERROR: 'Please check your input and try again.',
  RATE_LIMITED: 'Too many requests. Please wait a moment and try again.',
  SERVER_ERROR: 'An unexpected error occurred. Our team has been notified.',
  TIMEOUT: 'The request took too long. Please try again.',
  UNKNOWN: 'Something went wrong. Please try again later.',
};

/**
 * Parse an error (from fetch, axios, or generic throw) into a structured AppError.
 */
export function parseError(error: unknown): AppError {
  const timestamp = new Date().toISOString();

  // Handle fetch Response errors
  if (error instanceof Response) {
    const code = statusToErrorCode(error.status);
    return {
      code,
      message: `HTTP ${error.status}: ${error.statusText}`,
      userMessage: USER_MESSAGES[code],
      statusCode: error.status,
      timestamp,
    };
  }

  // Handle errors with response property (axios-style)
  if (typeof error === 'object' && error !== null && 'response' in error) {
    const resp = (error as { response: { status: number; data?: unknown } }).response;
    const code = statusToErrorCode(resp.status);
    return {
      code,
      message: `HTTP ${resp.status}`,
      userMessage: USER_MESSAGES[code],
      statusCode: resp.status,
      details: typeof resp.data === 'object' ? resp.data as Record<string, unknown> : undefined,
      timestamp,
    };
  }

  // Handle network errors
  if (error instanceof TypeError && error.message.includes('fetch')) {
    return {
      code: 'NETWORK_ERROR',
      message: error.message,
      userMessage: USER_MESSAGES.NETWORK_ERROR,
      timestamp,
    };
  }

  // Handle timeout errors
  if (error instanceof DOMException && error.name === 'AbortError') {
    return {
      code: 'TIMEOUT',
      message: 'Request aborted due to timeout',
      userMessage: USER_MESSAGES.TIMEOUT,
      timestamp,
    };
  }

  // Handle generic Error
  if (error instanceof Error) {
    return {
      code: 'UNKNOWN',
      message: error.message,
      userMessage: USER_MESSAGES.UNKNOWN,
      timestamp,
    };
  }

  // Fallback for unknown error shapes
  return {
    code: 'UNKNOWN',
    message: String(error),
    userMessage: USER_MESSAGES.UNKNOWN,
    timestamp,
  };
}

/**
 * Log an error to the console with structured formatting.
 * In production, this would also send to error tracking service.
 */
export function logError(error: AppError, context?: string): void {
  const prefix = context ? `[${context}]` : '[Error]';
  console.error(
    `${prefix} ${error.code}: ${error.message}`,
    error.details ? { details: error.details } : '',
  );
}

/**
 * Check if an error indicates the user's session has expired.
 */
export function isAuthError(error: AppError): boolean {
  return error.code === 'AUTH_EXPIRED' || error.code === 'AUTH_REQUIRED';
}

/**
 * Check if an error is retryable (transient network or server errors).
 */
export function isRetryable(error: AppError): boolean {
  return ['NETWORK_ERROR', 'TIMEOUT', 'SERVER_ERROR', 'RATE_LIMITED'].includes(error.code);
}
