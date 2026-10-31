/**
 * Core — Generic HTTP API Client
 *
 * Transport layer handling base URL configuration, JWT Bearer header injection,
 * automatic APIResponse<T> unwrapping, and structured HTTP error handling.
 *
 * AUTHENTICATION ARCHITECTURE:
 *   - This module NEVER calls /auth/login and never holds credentials.
 *   - `atlas_token` is the only authentication authority in the browser.
 *   - On a 401 from a protected endpoint, the invalid session is cleared and a
 *     single event is emitted. AuthProvider reacts by moving the app to the
 *     unauthenticated state. There is no retry and no silent re-authentication.
 *   - /auth/login itself NEVER receives an Authorization header.
 */

export interface ApiErrorPayload {
  status: number;
  message: string;
  details?: any;
}

export class ApiError extends Error {
  status: number;
  details?: any;

  constructor(status: number, message: string, details?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.details = details;
  }
}

const getBaseUrl = (): string => {
  if (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL.replace(/\/$/, '');
  }
  return 'http://localhost:8000';
};

export const getApiBaseUrl = getBaseUrl;

export const AUTH_TOKEN_KEY = 'atlas_token';
export const AUTH_SESSION_CLEARED_EVENT = 'atlas:auth-session-cleared';

/** Keys written by retired local/demo authentication code. Never authoritative. */
const LEGACY_AUTH_KEYS = [
  'atlas_logged_in',
  'atlas_current_user',
  'atlas_registered_users',
] as const;

export const clearLegacyAuthKeys = (): void => {
  try {
    for (const key of LEGACY_AUTH_KEYS) {
      localStorage.removeItem(key);
    }
  } catch (_) {
    // Storage can be unavailable in private/restricted contexts. Auth state
    // simply stays unauthenticated in that case.
  }
};

export const getAuthToken = (): string | null => {
  try {
    return localStorage.getItem(AUTH_TOKEN_KEY);
  } catch (_) {
    return null;
  }
};

export const setAuthToken = (token: string | null): void => {
  try {
    if (token) {
      localStorage.setItem(AUTH_TOKEN_KEY, token);
      // A successful login supersedes and cleans up retired auth markers.
      clearLegacyAuthKeys();
    } else {
      localStorage.removeItem(AUTH_TOKEN_KEY);
    }
  } catch (_) {
    // Storage failures must not fabricate an authenticated session.
  }
};

/**
 * Clears the authenticated browser session and notifies listeners.
 * Idempotent: safe to call from concurrent 401 handlers.
 */
export const clearAuthSession = (): void => {
  setAuthToken(null);
  clearLegacyAuthKeys();
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent(AUTH_SESSION_CLEARED_EVENT));
  }
};

export interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: any;
  params?: Record<string, string | number | boolean | undefined>;
}

async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const baseUrl = getBaseUrl();
  let url = `${baseUrl}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;

  if (options.params) {
    const searchParams = new URLSearchParams();
    Object.entries(options.params).forEach(([key, val]) => {
      if (val !== undefined && val !== null) {
        searchParams.append(key, String(val));
      }
    });
    const queryString = searchParams.toString();
    if (queryString) {
      url += `${url.includes('?') ? '&' : '?'}${queryString}`;
    }
  }

  const generateRequestId = (): string => {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) {
      return crypto.randomUUID();
    }
    return `req-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
  };

  const reqHeaders = options.headers as Record<string, string> | undefined;
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: 'application/vnd.atlas.v1+json, application/json',
    'X-Request-ID': reqHeaders?.['X-Request-ID'] || generateRequestId(),
    ...reqHeaders,
  };

  // /auth/login MUST NEVER receive an Authorization header.
  const isAuthLoginEndpoint = endpoint.includes('/api/v1/auth/login');
  if (!isAuthLoginEndpoint) {
    const activeToken = getAuthToken();
    if (activeToken) {
      headers['Authorization'] = `Bearer ${activeToken}`;
    }
  }

  const config: RequestInit = {
    ...options,
    headers,
  };

  if (options.body !== undefined) {
    config.body = typeof options.body === 'string' ? options.body : JSON.stringify(options.body);
  }

  try {
    const response = await fetch(url, config);

    // Handle 204 No Content
    if (response.status === 204) {
      return null as unknown as T;
    }

    const rawData = await response.json().catch(() => null);

    if (!response.ok) {
      if (response.status === 401 && !isAuthLoginEndpoint) {
        // The session is no longer authoritative. Clear it once and let the
        // AuthProvider transition the application to the login state. We never
        // retry and never substitute different credentials.
        clearAuthSession();
      }

      // statusText is frequently empty (HTTP/2, proxied responses), so the
      // fallback deliberately carries only the numeric status.
      const errorMessage =
        rawData?.detail || rawData?.message || rawData?.error?.message || `HTTP Error ${response.status}`;

      throw new ApiError(response.status, errorMessage, rawData);
    }

    // Unwrap APIResponse[T] envelope if present: { success: boolean, data: T, message: string }
    if (rawData && typeof rawData === 'object' && 'success' in rawData && 'data' in rawData) {
      return rawData.data as T;
    }

    return rawData as T;
  } catch (err: any) {
    if (err instanceof ApiError) {
      throw err;
    }
    throw new ApiError(0, err?.message || 'Network request failed');
  }
}

export const apiClient = {
  get: <T>(endpoint: string, options?: RequestOptions) =>
    request<T>(endpoint, { ...options, method: 'GET' }),

  post: <T>(endpoint: string, body?: any, options?: RequestOptions) =>
    request<T>(endpoint, { ...options, method: 'POST', body }),

  put: <T>(endpoint: string, body?: any, options?: RequestOptions) =>
    request<T>(endpoint, { ...options, method: 'PUT', body }),

  patch: <T>(endpoint: string, body?: any, options?: RequestOptions) =>
    request<T>(endpoint, { ...options, method: 'PATCH', body }),

  delete: <T>(endpoint: string, options?: RequestOptions) =>
    request<T>(endpoint, { ...options, method: 'DELETE' }),
};
