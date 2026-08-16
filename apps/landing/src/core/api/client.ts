/**
 * Core — Generic HTTP API Client
 * Transport layer handling base URL configuration, JWT Bearer header injection,
 * automatic APIResponse<T> unwrapping, and structured HTTP error handling.
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

  const token = getAuthToken();
  const reqHeaders = options.headers as Record<string, string> | undefined;
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: 'application/vnd.atlas.v1+json, application/json',
    'X-Request-ID': reqHeaders?.['X-Request-ID'] || generateRequestId(),
    ...reqHeaders,
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
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
      const errorMessage =
        rawData?.detail ||
        rawData?.message ||
        `HTTP Error ${response.status}: ${response.statusText}`;

      if (response.status === 401) {
        setAuthToken(null);
      }

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
