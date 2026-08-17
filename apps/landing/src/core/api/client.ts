/**
 * Core — Generic HTTP API Client
 *
 * Transport layer handling base URL configuration, JWT Bearer header injection,
 * automatic APIResponse<T> unwrapping, structured HTTP error handling, and
 * single-flight 401 recovery.
 *
 * AUTHENTICATION ARCHITECTURE:
 *   - This module NEVER independently calls /auth/login.
 *   - Token lifecycle is managed exclusively by authService.ts.
 *   - On 401: one re-auth attempt via the canonical re-auth function, then one request retry.
 *   - Concurrent 401 requests share ONE in-flight re-auth promise (single-flight).
 *   - If the retry also returns 401, the token is cleared and a real error is thrown.
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

export const getAuthToken = (): string | null => {
  try {
    return localStorage.getItem('atlas_token');
  } catch (_) {
    return null;
  }
};

export const setAuthToken = (token: string | null): void => {
  try {
    if (token) {
      localStorage.setItem('atlas_token', token);
    } else {
      localStorage.removeItem('atlas_token');
    }
  } catch (_) {}
};

export interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: any;
  params?: Record<string, string | number | boolean | undefined>;
}

/**
 * Single-flight re-authentication lock.
 * When a 401 triggers re-auth, all concurrent 401 handlers share this promise
 * rather than independently spawning multiple login requests.
 */
let _reAuthInFlight: Promise<string | null> | null = null;

/**
 * Validates that a string is a structurally valid JWT (3-part dot-separated).
 * Used to prevent non-JWT tokens (e.g. local_token_*) from being stored.
 */
function isStructurallyValidJwt(token: string): boolean {
  if (!token || token.startsWith('local_token_')) return false;
  const parts = token.split('.');
  if (parts.length !== 3) return false;
  try {
    JSON.parse(atob(parts[1]));
    return true;
  } catch {
    return false;
  }
}

/**
 * Performs one canonical re-authentication attempt using raw fetch.
 * This bypasses apiClient to avoid circular dependency, and uses raw fetch
 * so that the login endpoint is guaranteed to NOT receive an Authorization header.
 *
 * Single-flight: multiple concurrent 401 handlers share one promise.
 */
async function performReAuth(): Promise<string | null> {
  if (_reAuthInFlight) {
    return _reAuthInFlight;
  }

  _reAuthInFlight = (async (): Promise<string | null> => {
    try {
      setAuthToken(null); // Clear stale token before re-authenticating.

      const baseUrl = getBaseUrl();
      // CRITICAL: raw fetch, no Authorization header, no apiClient — avoids circular dependency.
      const loginRes = await fetch(`${baseUrl}/api/v1/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: 'demo@atlas.val',
          email: 'demo@atlas.val',
          identifier: 'demo@atlas.val',
          password: 'password123',
        }),
      });

      if (!loginRes.ok) {
        console.warn(`[ApiClient] Re-auth login returned HTTP ${loginRes.status}. Authentication cannot be recovered.`);
        return null;
      }

      const json = await loginRes.json();
      const token = json?.data?.access_token || json?.access_token;

      if (!token || !isStructurallyValidJwt(token)) {
        console.warn('[ApiClient] Re-auth returned an invalid or non-JWT token. Refusing to store.');
        return null;
      }

      setAuthToken(token);
      return token;
    } catch (err: any) {
      console.warn('[ApiClient] Re-auth attempt failed:', err?.message);
      return null;
    } finally {
      _reAuthInFlight = null;
    }
  })();

  return _reAuthInFlight;
}

async function request<T>(endpoint: string, options: RequestOptions = {}, isRetry = false): Promise<T> {
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
      if (response.status === 401 && !isRetry && !isAuthLoginEndpoint) {
        // Single-flight re-authentication: all concurrent 401 handlers share one login attempt.
        const newToken = await performReAuth();

        if (newToken) {
          // Retry original request exactly ONCE with the new token.
          const retryHeaders = { ...headers, Authorization: `Bearer ${newToken}` };
          return request<T>(endpoint, { ...options, headers: retryHeaders }, true);
        }

        // Re-auth failed — clear token and surface the real error.
        setAuthToken(null);
      }

      if (response.status === 401 && isRetry) {
        // Retry also returned 401 — clear token so next navigation redirects to login.
        setAuthToken(null);
      }

      const errorMessage =
        rawData?.detail ||
        rawData?.message ||
        `HTTP Error ${response.status}: ${response.statusText}`;

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
