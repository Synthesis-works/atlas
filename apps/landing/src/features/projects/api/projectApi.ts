import { apiClient } from '../../../infrastructure/api/client';
import type { APIResponse } from '../../auth/api/authApi';

export interface ProjectRead {
  id: string;
  name: string;
  description?: string;
  organization_id: string;
}

export const projectApi = {
  listForOrg: async (orgId: string): Promise<ProjectRead[]> => {
    const response = await apiClient.get<APIResponse<ProjectRead[]>>(`/organizations/${orgId}/projects`);
    return response.data.data;
  }
};
