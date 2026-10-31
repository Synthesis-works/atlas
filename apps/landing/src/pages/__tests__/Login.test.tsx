/**
 * Tests for the Login page.
 *
 * The page must never fake success: it only enters the workspace after
 * AuthProvider reports a real session, and it surfaces generic errors.
 */

import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const auth = vi.hoisted(() => ({ signIn: vi.fn(), signUp: vi.fn() }));
const experience = vi.hoisted(() => ({ enterAtlas: vi.fn(), startLoader: vi.fn() }));

vi.mock('@/features/auth/AuthProvider', () => ({
  useAuth: () => auth,
}));

vi.mock('@/core/ExperienceController', () => ({
  useExperience: () => experience,
}));

vi.mock('@/components/network/EnterAtlasTransition', () => ({
  EnterAtlasTransition: () => null,
}));

import Login from '../Login';

function renderLogin() {
  return render(
    <MemoryRouter>
      <Login />
    </MemoryRouter>
  );
}

function fillCredentials(email = 'user@example.com', password = 'supersecret') {
  fireEvent.change(screen.getByLabelText('Email'), { target: { value: email } });
  fireEvent.change(screen.getByLabelText('Password'), { target: { value: password } });
}

async function submit() {
  await act(async () => {
    fireEvent.click(screen.getByRole('button', { name: /^sign in$/i }));
  });
}

describe('Login page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    auth.signIn.mockResolvedValue({ error: null });
    auth.signUp.mockResolvedValue({ error: null });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('validates required fields without calling the backend', async () => {
    renderLogin();
    await submit();

    expect(await screen.findByText('Email is required')).toBeTruthy();
    expect(screen.getByText('Password is required')).toBeTruthy();
    expect(auth.signIn).not.toHaveBeenCalled();
  });

  it('shows a generic error and stays on the login page when authentication fails', async () => {
    auth.signIn.mockResolvedValue({ error: 'Invalid email or password.' });
    renderLogin();

    fillCredentials();
    await submit();

    const alert = await screen.findByRole('alert');
    expect(alert.textContent).toBe('Invalid email or password.');
    expect(auth.signIn).toHaveBeenCalledWith('user@example.com', 'supersecret');
    expect(experience.startLoader).not.toHaveBeenCalled();
    expect(experience.enterAtlas).not.toHaveBeenCalled();
  });

  it('enters the workspace only after a successful sign-in', async () => {
    renderLogin();

    fillCredentials();
    await submit();

    await waitFor(() => expect(experience.startLoader).toHaveBeenCalledTimes(1), { timeout: 4000 });
    expect(auth.signIn).toHaveBeenCalledWith('user@example.com', 'supersecret');
  });

  it('creates an account with name, email, and password only', async () => {
    renderLogin();

    fireEvent.click(screen.getByRole('button', { name: /create one/i }));

    fireEvent.change(screen.getByLabelText('Full Name'), { target: { value: 'Jane Doe' } });
    fillCredentials('new@example.com', 'supersecret');
    fireEvent.change(screen.getByLabelText('Confirm Password'), {
      target: { value: 'supersecret' },
    });

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /^create account$/i }));
    });

    await waitFor(() =>
      expect(auth.signUp).toHaveBeenCalledWith({
        email: 'new@example.com',
        full_name: 'Jane Doe',
        password: 'supersecret',
      })
    );
    expect(auth.signIn).not.toHaveBeenCalled();
  });

  it('rejects mismatched passwords before calling the backend', async () => {
    renderLogin();

    fireEvent.click(screen.getByRole('button', { name: /create one/i }));
    fireEvent.change(screen.getByLabelText('Full Name'), { target: { value: 'Jane Doe' } });
    fillCredentials();
    fireEvent.change(screen.getByLabelText('Confirm Password'), { target: { value: 'different' } });

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /^create account$/i }));
    });

    expect(await screen.findByText('Passwords do not match')).toBeTruthy();
    expect(auth.signUp).not.toHaveBeenCalled();
  });

  it('does not offer demo or single-sign-on login paths', () => {
    renderLogin();

    expect(screen.queryByText(/demo/i)).toBeNull();
    expect(screen.queryByText(/google/i)).toBeNull();
    expect(screen.queryByText(/github/i)).toBeNull();
    expect(screen.queryByText(/forgot password/i)).toBeNull();
    expect(screen.queryByText(/remember me/i)).toBeNull();
  });
});
