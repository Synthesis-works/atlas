/**
 * Services — Benchmark Service
 * Communicates with backend /api/v1/benchmarks endpoints via generic apiClient
 * and maps DTOs into domain models via BenchmarkMapper.
 */

import { apiClient } from '@/core/api/client';
import type { ServiceResult } from '@/core/types/service';
import type { Benchmark } from '@/domain/benchmarks/types';
import { filterBenchmarksByQuery } from '../lib/searchParser';
import { normalizeBenchmarkPayload } from '@/domain/benchmarks/adapters';
import { BenchmarkMapper, type BackendBenchmarkRead } from '../mappers/benchmarkMapper';

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

    if (dtos.length > 0) {
      const domainModels = BenchmarkMapper.toDomainList(dtos);
      return { data: domainModels, error: null };
    }
    return { data: [], error: null };
  } catch (err: any) {
    return { data: [], error: err?.message || 'Failed to fetch benchmarks' };
  }
}


export async function getBenchmarkById(id: string): Promise<ServiceResult<Benchmark | null>> {
  try {
    const rawDto = await apiClient.get<BackendBenchmarkRead>(`/api/v1/benchmarks/${id}`);
    if (rawDto && rawDto.id) {
      const domainModel = BenchmarkMapper.toDomain(rawDto);
      return { data: domainModel, error: null };
    }
    return { data: null, error: `Benchmark ${id} not found` };
  } catch (err: any) {
    return { data: null, error: err?.message || `Benchmark ${id} not found` };
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
    return { data: result, error: catalogRes.error };
  } catch (err: any) {
    return { data: [], error: err?.message || 'Filter evaluation failed' };
  }
}

export async function createBenchmark(
  payload: Partial<Benchmark>
): Promise<ServiceResult<Benchmark>> {
  try {
    const normalized = normalizeBenchmarkPayload(payload);
    return { data: normalized, error: null };
  } catch (err: any) {
    return {
      data: null as any,
      error: err?.message || 'Benchmark creation failed',
    };
  }
}
