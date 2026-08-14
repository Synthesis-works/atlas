/**
 * Component — ProtectedRoute
 * Route guard component protecting Workspace Dashboard views from unauthorized access.
 */

import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { getAuthToken } from '@/core/api/client';

export const ProtectedRoute: React.FC = () => {
  const token = getAuthToken();
  const isLoggedIn = Boolean(token) || localStorage.getItem('atlas_logged_in') === 'true';

  if (!isLoggedIn) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
};
