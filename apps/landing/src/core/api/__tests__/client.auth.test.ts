/**
 * Regression tests for session handling in the HTTP client.
 *
 * The client must never re-authenticate on its own: a 401 from a protected
 * endpoint clears the single authoritative token exactly once and notifies
 * listeners, while /auth/login never receives a stale Authorization header.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  apiClient,
  ApiError,
  AUTH_SESSION_CLEARED_EVENT,
  AUTH_TOKEN_KEY,
} from '../client';

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('apiClient authentication', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('clears the session once on a protected 401 without retrying', async () => {
    localStorage.setItem(AUTH_TOKEN_KEY, 'header.payload.signature');
    localStorage.setItem('atlas_logged_in', 'true');
    localStorage.setItem('atlas_current_user', '{"id":"1"}');

    const fetchMock = vi.fn(async () => jsonResponse(401, { detail: 'Could not validate' }));
    vi.stubGlobal('fetch', fetchMock);

    const cleared = vi.fn();
    window.addEventListener(AUTH_SESSION_CLEARED_EVENT, cleared);

    await expect(apiClient.get('/api/v1/executions')).rejects.toBeInstanceOf(ApiError);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(localStorage.getItem(AUTH_TOKEN_KEY)).toBeNull();
    expect(localStorage.getItem('atlas_logged_in')).toBeNull();
    expect(localStorage.getItem('atlas_current_user')).toBeNull();
    expect(cleared).toHaveBeenCalledTimes(1);

    window.removeEventListener(AUTH_SESSION_CLEARED_EVENT, cleared);
  });

  it('never attaches an Authorization header to /auth/login', async () => {
    localStorage.setItem(AUTH_TOKEN_KEY, 'stale.payload.signature');

    let capturedHeaders: Record<string, string> = {};
    vi.stubGlobal(
      'fetch',
      vi.fn(async (_url: string, init: RequestInit) => {
        capturedHeaders = init.headers as Record<string, string>;
        return jsonResponse(200, { access_token: 'new.payload.signature', token_type: 'bearer' });
      })
    );

    await apiClient.post('/api/v1/auth/login', { email: 'a@b.co', password: 'secret' });

    expect(capturedHeaders.Authorization).toBeUndefined();
  });

  it('attaches the token to protected endpoints', async () => {
    localStorage.setItem(AUTH_TOKEN_KEY, 'header.payload.signature');

    let capturedHeaders: Record<string, string> = {};
    vi.stubGlobal(
      'fetch',
      vi.fn(async (_url: string, init: RequestInit) => {
        capturedHeaders = init.headers as Record<string, string>;
        return jsonResponse(200, { ok: true });
      })
    );

    await apiClient.get('/api/v1/executions');

    expect(capturedHeaders.Authorization).toBe('Bearer header.payload.signature');
  });

  it('does not clear a valid session when a login attempt fails', async () => {
    localStorage.setItem(AUTH_TOKEN_KEY, 'valid.payload.signature');
    vi.stubGlobal('fetch', vi.fn(async () => jsonResponse(401, { detail: 'bad credentials' })));

    await expect(
      apiClient.post('/api/v1/auth/login', { email: 'a@b.co', password: 'wrong' })
    ).rejects.toBeInstanceOf(ApiError);

    expect(localStorage.getItem(AUTH_TOKEN_KEY)).toBe('valid.payload.signature');
  });
});
