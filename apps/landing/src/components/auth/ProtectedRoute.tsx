/**
 * Component — ProtectedRoute
 * Route guard protecting Workspace views from unauthenticated access.
 *
 * Authentication is decided exclusively by AuthProvider, which verifies the
 * backend-issued JWT via GET /auth/me. Local flags are never consulted.
 */

import React from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';

import { PageLoader } from '@/components/layout/PageLoader';
import { useAuth } from '@/features/auth/AuthProvider';

export const ProtectedRoute: React.FC = () => {
  const { status } = useAuth();
  const location = useLocation();

  if (status === 'loading') {
    return <PageLoader />;
  }

  if (status !== 'authenticated') {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return <Outlet />;
};
