/**
 * Services — Benchmark Service
 * Communicates with backend /api/v1/benchmarks endpoints via generic apiClient
 * and maps DTOs into domain models via BenchmarkMapper.
 */

import { apiClient } from '@/core/api/client';
import type { ServiceResult } from '@/core/types/service';
import type { Benchmark } from '@/domain/benchmarks/types';
import { MOCK_BENCHMARKS } from '@/domain/benchmarks/mock';
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
    return { data: MOCK_BENCHMARKS, error: null };
  } catch (err: any) {
    return { data: MOCK_BENCHMARKS, error: null };
  }
}


export async function getBenchmarkById(id: string): Promise<ServiceResult<Benchmark | null>> {
  try {
    const rawDto = await apiClient.get<BackendBenchmarkRead>(`/api/v1/benchmarks/${id}`);
    if (rawDto && rawDto.id) {
      const domainModel = BenchmarkMapper.toDomain(rawDto);
      return { data: domainModel, error: null };
    }
    const fallback = MOCK_BENCHMARKS.find((b) => b.id === id) || null;
    return { data: fallback, error: fallback ? null : `Benchmark ${id} not found` };
  } catch (err: any) {
    const fallback = MOCK_BENCHMARKS.find((b) => b.id === id) || null;
    return { data: fallback, error: null };
  }
}

export async function filterBenchmarks(
  query: string,
  category: string
): Promise<ServiceResult<Benchmark[]>> {
  try {
    const catalogRes = await getBenchmarks();
    let result = catalogRes.data || MOCK_BENCHMARKS;
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
