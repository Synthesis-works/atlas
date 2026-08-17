import type { Benchmark, BenchmarkStatus } from '@/domain/benchmarks/types';
import type { BenchmarkRead } from './benchmarkApi';

export function mapBenchmarkDtoToDomain(dto: BenchmarkRead): Benchmark {
  // We only map the fields explicitly returned by the backend.
  // Other fields required by the frontend mock are mapped to honest "unavailable" representations.

  let status: BenchmarkStatus = 'Draft';
  if (['Draft', 'Validating', 'Ready', 'Running', 'Paused', 'Completed', 'Failed', 'Archived'].includes((dto as any).state)) {
    status = (dto as any).state as BenchmarkStatus;
  }

  return {
    id: dto.id,
    name: dto.name,
    status: status,
    
    // Explicitly unavailable fields mapped to undefined to indicate lack of backend support
    description: undefined,
    category: undefined,
    difficulty: undefined,
    version: undefined,
    tasksCount: undefined,
    samplesCount: undefined,
    estimatedRuntime: undefined,
    license: undefined,
    author: undefined,
    verificationScore: undefined,
    verification: undefined,
    tags: undefined,
    metrics: undefined,
    compatibleModels: undefined,
    details: undefined,
    methodology: undefined,
    datasetSamples: undefined,
    versionsHistory: undefined,
    artifacts: undefined,
    relatedIds: undefined,
    updatedAt: undefined,
  };
}
