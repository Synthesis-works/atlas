/**
 * Auth Provider — the single client-side authority for authentication state.
 *
 * The only credential is the backend-issued JWT stored under `atlas_token`.
 * A session is considered authenticated only after `GET /auth/me` confirms it.
 * When the API client clears a rejected session it emits
 * `atlas:auth-session-cleared`; this provider reacts by becoming
 * unauthenticated. ProtectedRoute then routes the user to /login.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';

import {
  AUTH_SESSION_CLEARED_EVENT,
  AUTH_TOKEN_KEY,
  clearAuthSession,
  getAuthToken,
} from '@/core/api/client';
import {
  ensureAuthenticatedSession,
  getCurrentUser,
  signIn as signInRequest,
  signUp as signUpRequest,
  type SignUpPayload,
  type UserProfile,
} from './services/authService';

export type AuthStatus = 'loading' | 'authenticated' | 'unauthenticated';

export interface AuthActionResult {
  error: string | null;
}

export interface AuthContextValue {
  status: AuthStatus;
  user: UserProfile | null;
  isAuthenticated: boolean;
  signIn: (email: string, password: string) => Promise<AuthActionResult>;
  signUp: (payload: SignUpPayload) => Promise<AuthActionResult>;
  signOut: () => void;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth must be used inside <AuthProvider>');
  return value;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>('loading');
  const [user, setUser] = useState<UserProfile | null>(null);
  // Guards against out-of-order verification responses (e.g. a slow bootstrap
  // finishing after an explicit sign-in or sign-out).
  const requestRef = useRef(0);

  const markUnauthenticated = useCallback(() => {
    requestRef.current += 1;
    setUser(null);
    setStatus('unauthenticated');
  }, []);

  const verifySession = useCallback(async () => {
    const requestId = requestRef.current + 1;
    requestRef.current = requestId;

    const token = await ensureAuthenticatedSession();
    if (requestId !== requestRef.current) return;

    if (!token) {
      setUser(null);
      setStatus('unauthenticated');
      return;
    }

    const profile = await getCurrentUser();
    if (requestId !== requestRef.current) return;

    if (profile.error || !profile.data) {
      // A token the backend will not honour is not a session.
      clearAuthSession();
      setUser(null);
      setStatus('unauthenticated');
      return;
    }

    setUser(profile.data);
    setStatus('authenticated');
  }, []);

  useEffect(() => {
    void verifySession();
  }, [verifySession]);

  // The API client emits this when a protected endpoint rejects the token.
  useEffect(() => {
    const handleCleared = () => markUnauthenticated();
    window.addEventListener(AUTH_SESSION_CLEARED_EVENT, handleCleared);
    return () => window.removeEventListener(AUTH_SESSION_CLEARED_EVENT, handleCleared);
  }, [markUnauthenticated]);

  // Keep tabs in sync: signing out in one tab must not leave another tab
  // showing a workspace backed by a token that no longer exists.
  useEffect(() => {
    const handleStorage = (event: StorageEvent) => {
      if (event.key !== null && event.key !== AUTH_TOKEN_KEY) return;
      if (!getAuthToken()) {
        markUnauthenticated();
        return;
      }
      void verifySession();
    };
    window.addEventListener('storage', handleStorage);
    return () => window.removeEventListener('storage', handleStorage);
  }, [markUnauthenticated, verifySession]);

  const signIn = useCallback(async (email: string, password: string): Promise<AuthActionResult> => {
    const result = await signInRequest({ email, password });
    if (result.error || !result.data) {
      return { error: result.error ?? 'Unable to sign in right now. Please try again.' };
    }

    // A token alone is not enough: confirm it represents a usable account.
    const profile = await getCurrentUser();
    if (profile.error || !profile.data) {
      clearAuthSession();
      setUser(null);
      setStatus('unauthenticated');
      return { error: 'Unable to sign in right now. Please try again.' };
    }

    requestRef.current += 1;
    setUser(profile.data);
    setStatus('authenticated');
    return { error: null };
  }, []);

  const signUp = useCallback(
    async (payload: SignUpPayload): Promise<AuthActionResult> => {
      const created = await signUpRequest(payload);
      if (created.error || !created.data) {
        return { error: created.error ?? 'Unable to create your account. Please try again.' };
      }
      return signIn(payload.email, payload.password);
    },
    [signIn]
  );

  const signOut = useCallback(() => {
    clearAuthSession();
    markUnauthenticated();
  }, [markUnauthenticated]);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      isAuthenticated: status === 'authenticated',
      signIn,
      signUp,
      signOut,
      refresh: verifySession,
    }),
    [status, user, signIn, signUp, signOut, verifySession]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
