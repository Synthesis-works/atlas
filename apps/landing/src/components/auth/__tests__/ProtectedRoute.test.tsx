/**
 * Tests for ProtectedRoute — access is decided by AuthProvider only.
 */

import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ProtectedRoute } from '../ProtectedRoute';

const authState = vi.hoisted(() => ({ status: 'loading' as 'loading' | 'authenticated' | 'unauthenticated' }));

vi.mock('@/features/auth/AuthProvider', () => ({
  useAuth: () => ({ status: authState.status }),
}));

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<div>Workspace</div>} />
        </Route>
        <Route path="/login" element={<div>Login page</div>} />
      </Routes>
    </MemoryRouter>
  );
}

describe('ProtectedRoute', () => {
  beforeEach(() => {
    authState.status = 'loading';
  });

  it('waits while the session is being verified', () => {
    renderAt('/dashboard');
    expect(screen.getByText('Loading')).toBeTruthy();
    expect(screen.queryByText('Workspace')).toBeNull();
  });

  it('redirects unauthenticated visitors to /login', () => {
    authState.status = 'unauthenticated';
    renderAt('/dashboard');
    expect(screen.getByText('Login page')).toBeTruthy();
    expect(screen.queryByText('Workspace')).toBeNull();
  });

  it('renders the workspace for an authenticated session', () => {
    authState.status = 'authenticated';
    renderAt('/dashboard');
    expect(screen.getByText('Workspace')).toBeTruthy();
  });
});
