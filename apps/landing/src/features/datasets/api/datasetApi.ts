import { apiClient } from '../../../infrastructure/api/client';

export interface DatasetRead {
  id: string;
  name: string;
  description: string;
  type: string;
  samples: number;
  size_bytes: number;
  status: string;
  project_id: string;
  organization_id: string;
  created_at: string;
  updated_at: string;
  is_active: boolean;
}

export interface PageResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export const datasetApi = {
  listDatasets: async (projectId: string, limit: number = 25, offset: number = 0): Promise<DatasetRead[]> => {
    // The backend uses limit/offset for datasets as per Phase 1 Audit
    const response = await apiClient.get<DatasetRead[]>(`/projects/${projectId}/datasets`, {
      params: { limit, offset }
    });
    // Note: The backend router returns list[DatasetRead] directly for GET /projects/{project_id}/datasets, not PageResponse.
    return response.data;
  }
};
