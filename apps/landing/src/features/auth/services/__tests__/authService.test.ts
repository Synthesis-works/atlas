/**
 * Tests for the canonical auth service.
 *
 * These pin the security guarantees: no demo login, no fabricated tokens,
 * generic login errors, email-only contracts, and no implicit authentication.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { AUTH_TOKEN_KEY } from '@/core/api/client';
import {
  ensureAuthenticatedSession,
  GENERIC_AUTH_ERROR,
  GENERIC_LOGIN_ERROR,
  getCurrentUser,
  isStructurallyValidJwt,
  isTokenExpired,
  logoutUser,
  setValidatedAuthToken,
  signIn,
  signUp,
} from '../authService';

function base64Url(value: string): string {
  return btoa(value).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function makeJwt(payload: Record<string, unknown> = {}): string {
  const header = base64Url(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
  const body = base64Url(JSON.stringify(payload));
  return `${header}.${body}.signature`;
}

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('authService token helpers', () => {
  it('accepts a three-part JWT and rejects fake/legacy tokens', () => {
    expect(isStructurallyValidJwt(makeJwt({ sub: '1' }))).toBe(true);
    expect(isStructurallyValidJwt('local_token_123')).toBe(false);
    expect(isStructurallyValidJwt('not-a-jwt')).toBe(false);
    expect(isStructurallyValidJwt(null)).toBe(false);
  });

  it('detects expired and unexpired tokens', () => {
    const now = Math.floor(Date.now() / 1000);
    expect(isTokenExpired(makeJwt({ exp: now + 3600 }))).toBe(false);
    expect(isTokenExpired(makeJwt({ exp: now - 60 }))).toBe(true);
    expect(isTokenExpired('local_token_1')).toBe(true);
  });

  it('refuses to store a non-JWT token', () => {
    expect(() => setValidatedAuthToken('local_token_abc')).toThrow(/INVARIANT VIOLATION/);
    expect(localStorage.getItem(AUTH_TOKEN_KEY)).toBeNull();
  });
});

describe('authService session lifecycle', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('signs in with email only and stores the real JWT', async () => {
    const token = makeJwt({ sub: 'abc', exp: Math.floor(Date.now() / 1000) + 3600 });

    let body: Record<string, unknown> = {};
    vi.stubGlobal(
      'fetch',
      vi.fn(async (_url: string, init: RequestInit) => {
        body = JSON.parse(String(init.body));
        return jsonResponse(200, { access_token: token, token_type: 'bearer' });
      })
    );

    const result = await signIn({ email: '  User@Example.COM ', password: 'secret' });

    expect(result.error).toBeNull();
    expect(result.data?.access_token).toBe(token);
    expect(body).toEqual({ email: 'user@example.com', password: 'secret' });
    expect(localStorage.getItem(AUTH_TOKEN_KEY)).toBe(token);
    expect(localStorage.getItem('atlas_logged_in')).toBeNull();
    expect(localStorage.getItem('atlas_current_user')).toBeNull();
  });

  it('returns a generic error for invalid credentials', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => jsonResponse(401, { detail: 'anything' })));

    const result = await signIn({ email: 'user@example.com', password: 'wrong' });

    expect(result.error).toBe(GENERIC_LOGIN_ERROR);
    expect(localStorage.getItem(AUTH_TOKEN_KEY)).toBeNull();
  });

  it('returns a generic error when the backend is unreachable', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new Error('network down');
      })
    );

    const result = await signIn({ email: 'user@example.com', password: 'secret' });

    expect(result.error).toBe(GENERIC_AUTH_ERROR);
    expect(localStorage.getItem(AUTH_TOKEN_KEY)).toBeNull();
  });

  it('never stores a token that is not a JWT', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => jsonResponse(200, { access_token: 'local_token_fake', token_type: 'bearer' }))
    );

    const result = await signIn({ email: 'user@example.com', password: 'secret' });

    expect(result.error).toBe(GENERIC_AUTH_ERROR);
    expect(localStorage.getItem(AUTH_TOKEN_KEY)).toBeNull();
  });

  it('registers with the exact backend contract', async () => {
    let body: Record<string, unknown> = {};
    vi.stubGlobal(
      'fetch',
      vi.fn(async (_url: string, init: RequestInit) => {
        body = JSON.parse(String(init.body));
        return jsonResponse(201, {
          id: 'user-1',
          email: 'user@example.com',
          full_name: 'Jane Doe',
          is_active: true,
          is_verified: false,
        });
      })
    );

    const result = await signUp({
      email: ' User@Example.COM ',
      full_name: '  Jane Doe  ',
      password: 'supersecret',
    });

    expect(result.error).toBeNull();
    expect(body).toEqual({
      email: 'user@example.com',
      full_name: 'Jane Doe',
      password: 'supersecret',
    });
    expect(body).not.toHaveProperty('username');
  });

  it('does not log in automatically when no session exists', async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);

    await expect(ensureAuthenticatedSession()).resolves.toBeNull();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('purges an expired stored token without contacting the backend', async () => {
    localStorage.setItem(AUTH_TOKEN_KEY, makeJwt({ exp: Math.floor(Date.now() / 1000) - 60 }));
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);

    await expect(ensureAuthenticatedSession()).resolves.toBeNull();
    expect(localStorage.getItem(AUTH_TOKEN_KEY)).toBeNull();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('returns a valid stored token', async () => {
    const token = makeJwt({ exp: Math.floor(Date.now() / 1000) + 3600 });
    localStorage.setItem(AUTH_TOKEN_KEY, token);

    await expect(ensureAuthenticatedSession()).resolves.toBe(token);
  });

  it('reads the current user from the backend with no local fallback', async () => {
    localStorage.setItem('atlas_current_user', JSON.stringify({ id: 'stale', email: 'x@y.z' }));
    vi.stubGlobal('fetch', vi.fn(async () => jsonResponse(401, { detail: 'expired' })));

    const result = await getCurrentUser();

    expect(result.data).toBeNull();
    expect(result.error).toBeTruthy();
  });

  it('logout clears the canonical token and retired markers', () => {
    localStorage.setItem(AUTH_TOKEN_KEY, makeJwt());
    localStorage.setItem('atlas_logged_in', 'true');
    localStorage.setItem('atlas_registered_users', '[]');

    logoutUser();

    expect(localStorage.getItem(AUTH_TOKEN_KEY)).toBeNull();
    expect(localStorage.getItem('atlas_logged_in')).toBeNull();
    expect(localStorage.getItem('atlas_registered_users')).toBeNull();
  });
});
