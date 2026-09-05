/**
 * Services — Models Service
 * Resolves the repository's available execution models from the backend
 * ModelRegistry via /api/v1/models. Used by the benchmark run flow to pick
 * an available target model; when the registry is unreachable or empty the
 * caller falls back to the local default model.
 */

import { apiClient } from '@/core/api/client';
import type { ServiceResult } from '@/core/types/service';

export interface BackendModelRegistryEntry {
  provider?: string;
  model?: string;
  display_name?: string;
  source?: string;
  available?: boolean;
  status?: string;
  capabilities?: string[];
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
      .filter((m) => m && typeof m.model === 'string')
      .map((m) => ({
        name: m.model as string,
        provider: m.provider,
        status: m.status,
      }));

    return { data: models, error: null };
  } catch (err: any) {
    return { data: [], error: err?.message || 'Failed to fetch models' };
  }
}