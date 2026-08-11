import type { Benchmark } from '../../../domain/benchmarks/types';
import type { 
  BenchmarkCardModel, 
  BenchmarkRowModel, 
  BenchmarkPreviewModel,
  BenchmarkComparisonModel 
} from '../types/catalog';

export function buildBenchmarkCardModel(benchmark: Benchmark): BenchmarkCardModel {
  return {
    id: benchmark.id,
    name: benchmark.name,
    description: benchmark.description,
    category: benchmark.category,
    difficulty: benchmark.difficulty,
    status: benchmark.status,
    verificationScore: benchmark.verificationScore,
    tasksCountFormatted: new Intl.NumberFormat().format(benchmark.tasksCount),
    estimatedRuntime: benchmark.estimatedRuntime,
  };
}

export function buildBenchmarkRowModel(benchmark: Benchmark): BenchmarkRowModel {
  return {
    id: benchmark.id,
    name: benchmark.name,
    category: benchmark.category,
    difficulty: benchmark.difficulty,
    status: benchmark.status,
    verificationScore: benchmark.verificationScore,
    tasksCountFormatted: new Intl.NumberFormat().format(benchmark.tasksCount),
    estimatedRuntime: benchmark.estimatedRuntime,
    updatedAt: benchmark.updatedAt,
  };
}

export function buildBenchmarkPreviewModel(benchmark: Benchmark): BenchmarkPreviewModel {
  return {
    id: benchmark.id,
    name: benchmark.name,
    description: benchmark.description,
    category: benchmark.category,
    difficulty: benchmark.difficulty,
    status: benchmark.status,
    version: benchmark.version,
    tasksCountFormatted: new Intl.NumberFormat().format(benchmark.tasksCount),
    estimatedRuntime: benchmark.estimatedRuntime,
    license: benchmark.license,
    author: benchmark.author,
    verificationScore: benchmark.verificationScore,
    tags: benchmark.tags,
    metrics: benchmark.metrics,
    compatibleModels: benchmark.compatibleModels,
    details: benchmark.details,
    updatedAt: benchmark.updatedAt,
  };
}

export function buildBenchmarkComparisonModel(benchmark: Benchmark): BenchmarkComparisonModel {
  return {
    id: benchmark.id,
    name: benchmark.name,
    category: benchmark.category,
    difficulty: benchmark.difficulty,
    tasksCountFormatted: new Intl.NumberFormat().format(benchmark.tasksCount),
    metrics: benchmark.metrics,
  };
}
