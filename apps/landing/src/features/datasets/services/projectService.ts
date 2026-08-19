/**
 * Services — Project Resolution
 * Resolves the user's first organization project so project-scoped catalog
 * endpoints can be queried. The resolved project id is cached in localStorage.
 */

import { apiClient } from '@/core/api/client';

const PROJECT_ID_KEY = 'atlas_project_id';

interface OrgRead {
  id: string;
  name: string;
  slug: string;
}

interface ProjectRead {
  id: string;
  name: string;
  slug: string;
  org_id?: string | null;
}

function unwrapList<T>(raw: any): T[] {
  if (Array.isArray(raw)) return raw as T[];
  if (raw && Array.isArray(raw.data)) return raw.data as T[];
  if (raw && Array.isArray(raw.items)) return raw.items as T[];
  return [];
}

export async function resolveProjectId(): Promise<string | null> {
  try {
    const cached = localStorage.getItem(PROJECT_ID_KEY);
    if (cached) return cached;

    const orgs = unwrapList<OrgRead>(await apiClient.get<any>('/api/v1/organizations'));
    const org = orgs[0];
    if (!org) return null;

    const projects = unwrapList<ProjectRead>(
      await apiClient.get<any>(`/api/v1/organizations/${org.id}/projects`)
    );
    const project = projects[0];
    if (!project) return null;

    localStorage.setItem(PROJECT_ID_KEY, project.id);
    return project.id;
  } catch (err: any) {
    console.warn('[ProjectService] Failed to resolve project:', err?.message);
    return null;
  }
}