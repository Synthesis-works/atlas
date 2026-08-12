/**
 * Services — Dataset API Service (Milestone 4)
 * Handles REST operations for Dataset catalog, details, versions, and samples.
 */

import { apiClient } from '@/core/api/client';
import type { ServiceResult } from '@/core/types/service';

export interface BackendDatasetResponse {
  id: string;
  project_id: string;
  name: string;
  description?: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export async function getDatasets(): Promise<ServiceResult<BackendDatasetResponse[]>> {
  try {
    const rawRes = await apiClient.get<any>('/api/v1/datasets');
    let dtos: BackendDatasetResponse[] = [];
    if (Array.isArray(rawRes)) {
      dtos = rawRes;
    } else if (rawRes && Array.isArray(rawRes.items)) {
      dtos = rawRes.items;
    } else if (rawRes && rawRes.data && Array.isArray(rawRes.data.items)) {
      dtos = rawRes.data.items;
    } else if (rawRes && rawRes.data && Array.isArray(rawRes.data)) {
      dtos = rawRes.data;
    }

    return { data: dtos, error: null };
  } catch (err: any) {
    return { data: [], error: err?.message || 'Failed to fetch datasets' };
  }
}


export async function getDatasetById(id: string): Promise<ServiceResult<BackendDatasetResponse | null>> {
  try {
    const res = await apiClient.get<BackendDatasetResponse>(`/api/v1/datasets/${id}`);
    if (res && res.id) {
      return { data: res, error: null };
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

export async function createDataset(payload: DatasetCreateDTO): Promise<ServiceResult<BackendDatasetResponse | null>> {
  try {
    const res = await apiClient.post<BackendDatasetResponse>('/api/v1/datasets', payload);
    if (res && res.id) {
      return { data: res, error: null };
    }
    return { data: null, error: 'Failed to create dataset' };
  } catch (err: any) {
    return { data: null, error: err?.message || 'Failed to create dataset' };
  }
}

