import { Navigate, Outlet } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { authApi } from '../api/authApi';
import { useQuery } from '@tanstack/react-query';
import { useEffect } from 'react';
import { PageLoader } from '@/components/layout/PageLoader';
import { projectApi } from '../../projects/api/projectApi';
import { useProjectStore } from '../../projects/store/projectStore';

export function ProtectedRoute() {
  const { user, setUser, isAuthenticated, logout } = useAuthStore();
  const token = localStorage.getItem('atlas_auth_token');

  const { data, isLoading: authLoading, isError } = useQuery({
    queryKey: ['auth', 'me'],
    queryFn: authApi.getMe,
    enabled: !!token && !isAuthenticated,
    retry: false,
  });

  const { activeProjectId, setActiveProjectId } = useProjectStore();

  const { data: projects } = useQuery({
    queryKey: ['projects', user?.org_id],
    queryFn: () => projectApi.listForOrg(user!.org_id!),
    enabled: !!user?.org_id && !activeProjectId,
  });

  useEffect(() => {
    if (projects && projects.length > 0 && !activeProjectId) {
      // TEMPORARY FRONTEND FALLBACK — NOT FINAL PROJECT UX
      setActiveProjectId(projects[0].id);
    }
  }, [projects, activeProjectId, setActiveProjectId]);

  useEffect(() => {
    if (data) {
      setUser(data);
    }
    if (isError) {
      localStorage.removeItem('atlas_auth_token');
      logout();
    }
  }, [data, isError, setUser, logout]);

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  if (authLoading && !isAuthenticated) {
    return <PageLoader />;
  }

  if (isError) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
