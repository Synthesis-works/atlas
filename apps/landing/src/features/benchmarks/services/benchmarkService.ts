/**
 * Services — Benchmark Service
 * Pure functional async service returning ServiceResult<T> responses.
 */

import type { ServiceResult } from '@/core/types/service';
import type { Benchmark } from '@/domain/benchmarks/types';
import { MOCK_BENCHMARKS } from '@/domain/benchmarks/mock';
import { filterBenchmarksByQuery } from '../lib/searchParser';
import { normalizeBenchmarkPayload } from '@/domain/benchmarks/adapters';

export async function getBenchmarks(): Promise<ServiceResult<Benchmark[]>> {
  try {
    // Simulate network resolution delay
    await new Promise((resolve) => setTimeout(resolve, 80));
    return { data: MOCK_BENCHMARKS, error: null };
  } catch (err: any) {
    return { data: [], error: err?.message || 'Failed to resolve benchmarks' };
  }
}

export async function getBenchmarkById(id: string): Promise<ServiceResult<Benchmark | null>> {
  try {
    await new Promise((resolve) => setTimeout(resolve, 50));
    const item = MOCK_BENCHMARKS.find((b) => b.id === id) || null;
    return { data: item, error: item ? null : `Benchmark ${id} not found` };
  } catch (err: any) {
    return { data: null, error: err?.message || 'Error fetching benchmark details' };
  }
}

export async function filterBenchmarks(
  query: string,
  category: string
): Promise<ServiceResult<Benchmark[]>> {
  try {
    let result = MOCK_BENCHMARKS;
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
