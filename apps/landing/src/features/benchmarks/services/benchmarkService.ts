/**
 * Services — Benchmark Service
 * Communicates with backend /api/v1/benchmarks and execution endpoints via apiClient.
 * Maps DTOs into domain models via BenchmarkMapper without synthetic fallbacks.
 */

import { apiClient } from '@/core/api/client';
import type { ServiceResult } from '@/core/types/service';
import type { Benchmark } from '@/domain/benchmarks/types';
import { filterBenchmarksByQuery } from '../lib/searchParser';
import { BenchmarkMapper, type BackendBenchmarkRead } from '../mappers/benchmarkMapper';

export interface BackendExecutionRunDTO {
  id: string;
  benchmark_version_id: string;
  target_model: string;
  status: string;
  completed_items: number;
  total_items: number;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  updated_at?: string | null;
  created_by?: string;
  score?: number | null;
  latency_ms?: number | null;
  token_usage?: number | null;
}

export async function getBenchmarks(): Promise<ServiceResult<Benchmark[]>> {
  try {
    const rawRes = await apiClient.get<any>('/api/v1/benchmarks');
    let dtos: BackendBenchmarkRead[] = [];
    if (Array.isArray(rawRes)) {
      dtos = rawRes;
    } else if (rawRes && Array.isArray(rawRes.items)) {
      dtos = rawRes.items;
    } else if (rawRes && rawRes.data && Array.isArray(rawRes.data.items)) {
      dtos = rawRes.data.items;
    } else if (rawRes && rawRes.data && Array.isArray(rawRes.data)) {
      dtos = rawRes.data;
    }

    const domainModels = BenchmarkMapper.toDomainList(dtos);
    return { data: domainModels, error: null };
  } catch (err: any) {
    return { data: [], error: err?.message || 'Failed to fetch benchmarks' };
  }
}

export async function getBenchmarkById(id: string): Promise<ServiceResult<Benchmark | null>> {
  try {
    const rawRes = await apiClient.get<any>(`/api/v1/benchmarks/${id}`);
    const rawDto: BackendBenchmarkRead | null =
      rawRes && rawRes.data ? rawRes.data : rawRes;

    if (rawDto && rawDto.id) {
      const domainModel = BenchmarkMapper.toDomain(rawDto);
      return { data: domainModel, error: null };
    }
    return { data: null, error: `Benchmark ${id} not found` };
  } catch (err: any) {
    return { data: null, error: err?.message || `Failed to fetch benchmark ${id}` };
  }
}

export async function createBenchmark(
  payload: {
    name: string;
    objective?: string;
    domain?: string;
    difficulty?: string;
    category_ids?: string[];
  }
): Promise<ServiceResult<Benchmark | null>> {
  try {
    const rawRes = await apiClient.post<any>('/api/v1/benchmarks', payload);
    const rawDto: BackendBenchmarkRead | null =
      rawRes && rawRes.data ? rawRes.data : rawRes;

    if (rawDto && rawDto.id) {
      const domainModel = BenchmarkMapper.toDomain(rawDto);
      return { data: domainModel, error: null };
    }
    return { data: null, error: 'Benchmark creation returned invalid response' };
  } catch (err: any) {
    return {
      data: null,
      error: err?.message || 'Benchmark creation failed on backend',
    };
  }
}

export async function runBenchmark(
  benchmarkVersionId: string,
  targetModel: string,
  datasetVersionId?: string | null
): Promise<ServiceResult<{ id: string; status: string } | null>> {
  try {
    const body: Record<string, any> = {
      benchmark_version_id: benchmarkVersionId,
      target_model: targetModel,
    };
    if (datasetVersionId) {
      body.dataset_version_id = datasetVersionId;
    }

    const res = await apiClient.post<any>(
      `/api/v1/benchmarks/${benchmarkVersionId}/executions`,
      body
    );
    const data = res?.data || res;
    if (data && data.id) {
      return { data: { id: data.id, status: data.status }, error: null };
    }
    return { data: null, error: 'Failed to start benchmark execution' };
  } catch (err: any) {
    return { data: null, error: err?.message || 'Execution dispatch failed' };
  }
}

export async function getBenchmarkRuns(
  benchmarkVersionId?: string
): Promise<ServiceResult<BackendExecutionRunDTO[]>> {
  try {
    const endpoint = benchmarkVersionId
      ? `/api/v1/executions?benchmark_version_id=${benchmarkVersionId}`
      : '/api/v1/executions';
    const rawRes = await apiClient.get<any>(endpoint);
    let items: any[] = [];
    if (Array.isArray(rawRes)) {
      items = rawRes;
    } else if (rawRes && Array.isArray(rawRes.items)) {
      items = rawRes.items;
    } else if (rawRes && rawRes.data && Array.isArray(rawRes.data.items)) {
      items = rawRes.data.items;
    } else if (rawRes && rawRes.data && Array.isArray(rawRes.data)) {
      items = rawRes.data;
    }
    return { data: items, error: null };
  } catch (err: any) {
    return { data: [], error: err?.message || 'Failed to load execution runs' };
  }
}

export async function filterBenchmarks(
  query: string,
  category: string
): Promise<ServiceResult<Benchmark[]>> {
  try {
    const catalogRes = await getBenchmarks();
    let result = catalogRes.data || [];
    if (category && category !== 'all') {
      result = result.filter((b) => b.category === category);
    }
    if (query) {
      result = filterBenchmarksByQuery(result, query);
    }
    return { data: result, error: null };
  } catch (err: any) {
    return { data: [], error: err?.message || 'Filter evaluation failed' };
  }
}

