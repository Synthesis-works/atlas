/**
 * Features — Authentication Service
 *
 * CANONICAL AUTHENTICATION AUTHORITY — single source of truth for the browser session.
 *
 * INVARIANTS (must never be violated):
 *   1. Only real backend-issued JWTs may be stored in localStorage (`atlas_token`).
 *   2. `local_token_*` and demo markers MUST NEVER be written. If detected, the
 *      session is cleared instead of being used.
 *   3. signIn()/signUp() return a real backend result or a real error — no silent
 *      fallback, no demo account, no offline user store.
 *   4. Nothing in this module logs a user in implicitly.
 */

import {
  apiClient,
  ApiError,
  clearAuthSession,
  getAuthToken,
  setAuthToken,
} from '@/core/api/client';
import type { ServiceResult } from '@/core/types/service';

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_verified: boolean;
  org_id?: string | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface SignInPayload {
  email: string;
  password: string;
}

export interface SignUpPayload {
  email: string;
  full_name: string;
  password: string;
}

/** Deliberately generic: never reveal whether an account exists. */
export const GENERIC_LOGIN_ERROR = 'Invalid email or password.';
export const GENERIC_AUTH_ERROR = 'Unable to sign in right now. Please try again.';

function decodeJwtPayload(token: string): Record<string, unknown> | null {
  if (!token || token.startsWith('local_token_')) return null;
  const parts = token.split('.');
  if (parts.length !== 3) return null;
  try {
    const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    const padded = base64.padEnd(Math.ceil(base64.length / 4) * 4, '=');
    const parsed = JSON.parse(atob(padded));
    return parsed && typeof parsed === 'object' ? (parsed as Record<string, unknown>) : null;
  } catch {
    return null;
  }
}

/**
 * Validates that a token is a structurally valid JWT (3-part dot-separated).
 * Does NOT verify the signature — that is the backend's job.
 * Returns false for any local_token_* strings or malformed tokens.
 */
export function isStructurallyValidJwt(token: string | null): boolean {
  return decodeJwtPayload(token ?? '') !== null;
}

/**
 * Sets the auth token with mandatory validation.
 * THROWS if a non-JWT token (e.g. local_token_*) is provided.
 * This is the enforcement point that keeps fake tokens out of localStorage.
 */
export function setValidatedAuthToken(token: string | null): void {
  if (token !== null && !isStructurallyValidJwt(token)) {
    throw new Error(
      `[AuthService] INVARIANT VIOLATION: Attempted to store non-JWT token: "${token.substring(0, 30)}...". ` +
        `Only real backend-issued JWTs may be stored.`
    );
  }
  setAuthToken(token);
}

export function isTokenExpired(token: string): boolean {
  const payload = decodeJwtPayload(token);
  if (!payload) return true;
  const exp = payload.exp;
  if (typeof exp !== 'number') return false;
  // 10s skew allowance so we do not send a token that expires in flight.
  return Date.now() >= exp * 1000 - 10_000;
}

/**
 * Authenticates against the canonical backend.
 * Returns a real JWT or a real error. NEVER generates fake tokens and NEVER
 * registers users implicitly. Login failures are intentionally generic.
 */
export async function signIn(payload: SignInPayload): Promise<ServiceResult<TokenResponse>> {
  const email = payload.email.trim().toLowerCase();
  const password = payload.password;

  try {
    // apiClient never attaches an Authorization header to /auth/login.
    const data = await apiClient.post<Partial<TokenResponse>>('/api/v1/auth/login', {
      email,
      password,
    });
    const token = data?.access_token;

    if (!token) {
      return { data: null as unknown as TokenResponse, error: GENERIC_AUTH_ERROR };
    }

    // Validate before storing — the invariant enforcement point.
    setValidatedAuthToken(token);
    return {
      data: { access_token: token, token_type: data?.token_type ?? 'bearer' },
      error: null,
    };
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) {
      return { data: null as unknown as TokenResponse, error: GENERIC_LOGIN_ERROR };
    }
    return { data: null as unknown as TokenResponse, error: GENERIC_AUTH_ERROR };
  }
}

/**
 * Creates an account. Does not sign the user in; callers must call signIn()
 * afterwards so the browser session is always backed by a real JWT.
 */
export async function signUp(payload: SignUpPayload): Promise<ServiceResult<UserProfile>> {
  const email = payload.email.trim().toLowerCase();
  const fullName = payload.full_name.trim();

  try {
    const data = await apiClient.post<UserProfile>('/api/v1/auth/register', {
      email,
      full_name: fullName,
      password: payload.password,
    });
    if (data?.id) {
      return { data, error: null };
    }
    return {
      data: null as unknown as UserProfile,
      error: 'Unable to create your account right now. Please try again.',
    };
  } catch (err) {
    if (err instanceof ApiError && err.status === 409) {
      return {
        data: null as unknown as UserProfile,
        error: 'An account with this email already exists.',
      };
    }
    if (err instanceof ApiError && err.status === 422) {
      return {
        data: null as unknown as UserProfile,
        error: 'Please check your name, email, and password and try again.',
      };
    }
    return {
      data: null as unknown as UserProfile,
      error: 'Unable to create your account right now. Please try again.',
    };
  }
}

/**
 * Reads the current user from the backend. No cached/local fallback: an
 * unverifiable session is not a session.
 */
export async function getCurrentUser(): Promise<ServiceResult<UserProfile | null>> {
  try {
    const data = await apiClient.get<UserProfile>('/api/v1/auth/me');
    if (!data?.id) {
      return { data: null, error: 'Session could not be verified.' };
    }
    return { data, error: null };
  } catch (err) {
    return {
      data: null,
      error: err instanceof Error ? err.message : 'Session could not be verified.',
    };
  }
}

/** Clears the canonical browser session and any retired auth markers. */
export function logoutUser(): void {
  clearAuthSession();
}

/**
 * Returns a usable stored token, or null.
 *
 * This intentionally performs NO login attempt. Callers that need credentials
 * must go through the Login page. Malformed or expired tokens are purged so a
 * dead session can never masquerade as an authenticated one.
 */
export async function ensureAuthenticatedSession(): Promise<string | null> {
  const token = getAuthToken();
  if (!token) return null;

  if (!isStructurallyValidJwt(token) || isTokenExpired(token)) {
    clearAuthSession();
    return null;
  }

  return token;
}
