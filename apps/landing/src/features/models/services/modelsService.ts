/**
 * Services — Models Service
 * Resolves the repository's available execution models from the backend's
 * typed model catalog (`ModelRead`) via /api/v1/models. Used by the
 * benchmark run flow to pick an available target model; when the catalog is
 * unreachable or empty the caller falls back to the local default model.
 */

import { apiClient } from '@/core/api/client';
import type { ServiceResult } from '@/core/types/service';

export interface BackendModelRegistryEntry {
  id?: string;
  provider?: string;
  display_name?: string;
  status?: string;
  is_test_only?: boolean;
  [key: string]: unknown;
}

export interface ResolvedModel {
  name: string;
  provider?: string;
  status?: string;
}

export async function getModels(): Promise<ServiceResult<ResolvedModel[]>> {
  try {
    const rawRes = await apiClient.get<any>('/api/v1/models');

    let items: BackendModelRegistryEntry[] = [];
    if (Array.isArray(rawRes)) {
      items = rawRes;
    } else if (rawRes && Array.isArray(rawRes.data)) {
      items = rawRes.data;
    } else if (rawRes && Array.isArray(rawRes.items)) {
      items = rawRes.items;
    }

    const models = items
      .filter((m) => m && typeof m.id === 'string')
      .map((m) => ({
        name: m.id as string,
        provider: m.provider,
        status: m.status,
      }));

    return { data: models, error: null };
  } catch (err: any) {
    return { data: [], error: err?.message || 'Failed to fetch models' };
  }
}