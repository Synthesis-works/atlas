/**
 * Services — Dataset API Service
 * Handles REST operations for Dataset catalog, details, versions, and samples
 * against the project-scoped backend endpoint /api/v1/projects/{id}/datasets.
 */

import { apiClient } from '@/core/api/client';
import type { ServiceResult } from '@/core/types/service';
import type { Dataset, DatasetStatus } from '../domain/types';

export interface BackendDatasetRead {
  id: string;
  project_id: string;
  name: string;
  description?: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

function mapStatus(status: string): DatasetStatus {
  switch (status) {
    case 'active':
      return 'READY';
    case 'archived':
      return 'ARCHIVED';
    case 'indexing':
      return 'INDEXING';
    case 'error':
      return 'ERROR';
    default:
      return 'READY';
  }
}

export function mapDataset(dto: BackendDatasetRead): Dataset {
  return {
    id: dto.id,
    name: dto.name,
    description: dto.description || '',
    type: 'generic',
    samples: 0,
    sizeBytes: 0,
    status: mapStatus(dto.status),
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

export async function getDatasets(projectId: string): Promise<ServiceResult<Dataset[]>> {
  try {
    const raw = await apiClient.get<any>(`/api/v1/projects/${projectId}/datasets`);
    let dtos: BackendDatasetRead[] = [];
    if (Array.isArray(raw)) {
      dtos = raw;
    } else if (raw && Array.isArray(raw.items)) {
      dtos = raw.items;
    } else if (raw && raw.data && Array.isArray(raw.data.items)) {
      dtos = raw.data.items;
    } else if (raw && raw.data && Array.isArray(raw.data)) {
      dtos = raw.data;
    }
    return { data: dtos.map(mapDataset), error: null };
  } catch (err: any) {
    return { data: [], error: err?.message || 'Failed to fetch datasets' };
  }
}

export async function getDatasetById(
  projectId: string,
  id: string
): Promise<ServiceResult<Dataset | null>> {
  try {
    const res = await apiClient.get<BackendDatasetRead>(
      `/api/v1/projects/${projectId}/datasets/${id}`
    );
    if (res && res.id) {
      return { data: mapDataset(res), error: null };
    }
    return { data: null, error: `Dataset with ID ${id} not found` };
  } catch (err: any) {
    return { data: null, error: err?.message || 'Failed to fetch dataset details' };
  }
}

export interface DatasetCreateDTO {
  name: string;
  description?: string;
  is_public?: boolean;
}

export async function createDataset(
  projectId: string,
  payload: DatasetCreateDTO
): Promise<ServiceResult<Dataset | null>> {
  try {
    const res = await apiClient.post<BackendDatasetRead>(
      `/api/v1/projects/${projectId}/datasets`,
      payload
    );
    if (res && res.id) {
      return { data: mapDataset(res), error: null };
    }
    return { data: null, error: 'Failed to create dataset' };
  } catch (err: any) {
    return { data: null, error: err?.message || 'Failed to create dataset' };
  }
}