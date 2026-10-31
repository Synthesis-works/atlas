/**
 * Tests for AuthProvider — the single authority for client authentication state.
 */

import { act, renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AUTH_SESSION_CLEARED_EVENT, AUTH_TOKEN_KEY } from '@/core/api/client';

const mocks = vi.hoisted(() => ({
  ensureAuthenticatedSession: vi.fn(),
  getCurrentUser: vi.fn(),
  signIn: vi.fn(),
  signUp: vi.fn(),
}));

vi.mock('../services/authService', () => mocks);

import { AuthProvider, useAuth } from '../AuthProvider';

const profile = {
  id: 'user-1',
  email: 'user@example.com',
  full_name: 'Jane Doe',
  is_active: true,
  is_verified: true,
};

function wrapper({ children }: { children: ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>;
}

describe('AuthProvider', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
    mocks.ensureAuthenticatedSession.mockResolvedValue(null);
    mocks.getCurrentUser.mockResolvedValue({ data: null, error: 'no session' });
    mocks.signIn.mockResolvedValue({ data: null, error: null });
    mocks.signUp.mockResolvedValue({ data: null, error: null });
  });

  it('starts loading and settles to unauthenticated without a token', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    expect(result.current.status).toBe('loading');
    await waitFor(() => expect(result.current.status).toBe('unauthenticated'));
    expect(result.current.isAuthenticated).toBe(false);
  });

  it('authenticates a verified stored session', async () => {
    mocks.ensureAuthenticatedSession.mockResolvedValue('real.jwt.token');
    mocks.getCurrentUser.mockResolvedValue({ data: profile, error: null });

    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => expect(result.current.status).toBe('authenticated'));
    expect(result.current.user).toEqual(profile);
  });

  it('rejects a token the backend will not honour and clears it', async () => {
    localStorage.setItem(AUTH_TOKEN_KEY, 'real.jwt.token');
    mocks.ensureAuthenticatedSession.mockResolvedValue('real.jwt.token');
    mocks.getCurrentUser.mockResolvedValue({ data: null, error: '401' });

    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => expect(result.current.status).toBe('unauthenticated'));
    expect(localStorage.getItem(AUTH_TOKEN_KEY)).toBeNull();
  });

  it('signs in and confirms the profile before becoming authenticated', async () => {
    mocks.signIn.mockResolvedValue({
      data: { access_token: 'real.jwt.token', token_type: 'bearer' },
      error: null,
    });
    mocks.getCurrentUser.mockResolvedValue({ data: profile, error: null });

    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.status).toBe('unauthenticated'));

    let outcome: { error: string | null } = { error: 'not-run' };
    await act(async () => {
      outcome = await result.current.signIn('user@example.com', 'secret');
    });

    expect(outcome.error).toBeNull();
    expect(mocks.signIn).toHaveBeenCalledWith({ email: 'user@example.com', password: 'secret' });
    expect(result.current.status).toBe('authenticated');
    expect(result.current.user).toEqual(profile);
  });

  it('does not become authenticated when sign-in fails', async () => {
    mocks.signIn.mockResolvedValue({ data: null, error: 'Invalid email or password.' });

    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.status).toBe('unauthenticated'));

    let outcome: { error: string | null } = { error: 'not-run' };
    await act(async () => {
      outcome = await result.current.signIn('user@example.com', 'wrong');
    });

    expect(outcome.error).toBe('Invalid email or password.');
    expect(result.current.status).toBe('unauthenticated');
    expect(result.current.user).toBeNull();
  });

  it('drops to unauthenticated when the API client clears the session', async () => {
    mocks.ensureAuthenticatedSession.mockResolvedValue('real.jwt.token');
    mocks.getCurrentUser.mockResolvedValue({ data: profile, error: null });

    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.status).toBe('authenticated'));

    act(() => {
      window.dispatchEvent(new CustomEvent(AUTH_SESSION_CLEARED_EVENT));
    });

    expect(result.current.status).toBe('unauthenticated');
    expect(result.current.user).toBeNull();
  });

  it('signs out by clearing the token and state', async () => {
    localStorage.setItem(AUTH_TOKEN_KEY, 'real.jwt.token');
    mocks.ensureAuthenticatedSession.mockResolvedValue('real.jwt.token');
    mocks.getCurrentUser.mockResolvedValue({ data: profile, error: null });

    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.status).toBe('authenticated'));

    act(() => {
      result.current.signOut();
    });

    expect(localStorage.getItem(AUTH_TOKEN_KEY)).toBeNull();
    expect(result.current.status).toBe('unauthenticated');
  });

  it('registers then signs in with the same credentials', async () => {
    mocks.signUp.mockResolvedValue({ data: profile, error: null });
    mocks.signIn.mockResolvedValue({
      data: { access_token: 'real.jwt.token', token_type: 'bearer' },
      error: null,
    });
    mocks.getCurrentUser.mockResolvedValue({ data: profile, error: null });

    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.status).toBe('unauthenticated'));

    let outcome: { error: string | null } = { error: 'not-run' };
    await act(async () => {
      outcome = await result.current.signUp({
        email: 'new@example.com',
        full_name: 'New User',
        password: 'supersecret',
      });
    });

    expect(outcome.error).toBeNull();
    expect(mocks.signUp).toHaveBeenCalledWith({
      email: 'new@example.com',
      full_name: 'New User',
      password: 'supersecret',
    });
    expect(mocks.signIn).toHaveBeenCalledWith({ email: 'new@example.com', password: 'supersecret' });
    expect(result.current.status).toBe('authenticated');
  });
});
