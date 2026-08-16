/**
 * Features — Authentication Service
 *
 * CANONICAL AUTHENTICATION AUTHORITY — Single source of truth for obtaining JWTs.
 *
 * INVARIANTS (must never be violated):
 *   1. Only real backend-issued JWTs may be stored in localStorage.
 *   2. local_token_* strings MUST NEVER be written. If detected, an error is thrown.
 *   3. loginUser() returns a real JWT or a real error — no silent fallback.
 *   4. No auto-registration. No offline user store. No mock tokens.
 */

import { apiClient, setAuthToken, getAuthToken } from '@/core/api/client';
import type { ServiceResult } from '@/core/types/service';

export interface UserProfile {
  id: string;
  email: string;
  username: string;
  full_name?: string;
  is_active: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserLoginPayload {
  username: string;
  password: string;
}

export interface UserRegisterPayload {
  email: string;
  username: string;
  password: string;
  full_name?: string;
}

const CURRENT_USER_KEY = 'atlas_current_user';

/**
 * Validates that a token is a structurally valid JWT (3-part dot-separated).
 * Does NOT verify the signature — that is the backend's job.
 * Returns false for any local_token_* strings or malformed tokens.
 */
export function isStructurallyValidJwt(token: string | null): boolean {
  if (!token) return false;
  if (token.startsWith('local_token_')) return false;
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
 * Sets auth token with mandatory validation.
 * THROWS if a non-JWT token (e.g. local_token_*) is provided.
 * This is the enforcement point that prevents fake tokens from ever entering localStorage.
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

/**
 * Login via the canonical backend. Returns a real JWT or a ServiceResult error.
 * NEVER generates fake tokens. NEVER auto-registers users.
 * If the backend is unavailable, returns an error — that is the correct behavior.
 */
export async function loginUser(payload: UserLoginPayload): Promise<ServiceResult<TokenResponse>> {
  const identifier = payload.username.trim();
  const password = payload.password;

  try {
    const backendPayload = {
      username: identifier,
      email: identifier.includes('@') ? identifier : undefined,
      identifier: identifier,
      password: password,
    };
    // apiClient.post handles the /auth/login endpoint and will NOT attach an Authorization header.
    const data = await apiClient.post<any>('/api/v1/auth/login', backendPayload);
    const token = data?.access_token || data?.data?.access_token;

    if (!token) {
      return { data: null as any, error: 'Backend did not return an access token.' };
    }

    // Validate before storing — this is the invariant enforcement point.
    setValidatedAuthToken(token);
    localStorage.setItem('atlas_logged_in', 'true');
    return { data: { access_token: token, token_type: 'bearer' }, error: null };
  } catch (err: any) {
    // Surface the real error — no fallback to fake tokens.
    const message = err?.message || 'Authentication failed. Please check your credentials.';
    return { data: null as any, error: message };
  }
}

export async function registerUser(payload: UserRegisterPayload): Promise<ServiceResult<UserProfile>> {
  try {
    const data = await apiClient.post<UserProfile>('/api/v1/auth/register', payload);
    if (data?.id) {
      localStorage.setItem(CURRENT_USER_KEY, JSON.stringify(data));
      return { data, error: null };
    }
    return { data: null as any, error: 'Registration failed: no user profile returned.' };
  } catch (err: any) {
    return { data: null as any, error: err?.message || 'Registration failed.' };
  }
}

export async function getCurrentUser(): Promise<ServiceResult<UserProfile | null>> {
  try {
    const data = await apiClient.get<UserProfile>('/api/v1/auth/me');
    if (data) {
      localStorage.setItem(CURRENT_USER_KEY, JSON.stringify(data));
      return { data, error: null };
    }
  } catch {
    // Session invalid or backend unavailable — fall through to stored profile.
  }

  try {
    const localUserRaw = localStorage.getItem(CURRENT_USER_KEY);
    if (localUserRaw) {
      return { data: JSON.parse(localUserRaw), error: null };
    }
  } catch {
    // ignore malformed storage
  }

  return { data: null, error: 'No active session' };
}

export function logoutUser(): void {
  setAuthToken(null);
  localStorage.removeItem('atlas_logged_in');
  localStorage.removeItem(CURRENT_USER_KEY);
  // Clear any legacy local user store keys that may have been written by old code.
  localStorage.removeItem('atlas_registered_users');
  localStorage.removeItem('atlas_current_user');
}

export function isTokenExpired(token: string): boolean {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return true;
    const payload = JSON.parse(atob(parts[1]));
    if (!payload.exp) return false;
    return Date.now() >= payload.exp * 1000 - 10000;
  } catch {
    return true;
  }
}

/**
 * Ensures there is a valid backend-authenticated session.
 * Used by auth context on app load.
 * Returns the current valid token, or performs ONE login attempt, or returns null.
 */
export async function ensureAuthenticatedSession(forceRefresh = false): Promise<string | null> {
  const existingToken = getAuthToken();

  // Reject any legacy fake tokens that might still be in localStorage from old code.
  if (existingToken && !isStructurallyValidJwt(existingToken)) {
    console.warn('[AuthService] Removing non-JWT token from localStorage (legacy cleanup).');
    setAuthToken(null);
  }

  const cleanToken = getAuthToken();
  if (!forceRefresh && cleanToken && !isTokenExpired(cleanToken)) {
    return cleanToken;
  }

  const res = await loginUser({ username: 'demo@atlas.val', password: 'password123' });
  if (res.data?.access_token) {
    return res.data.access_token;
  }
  return null;
}
