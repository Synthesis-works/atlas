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
    description: benchmark.description ?? "Description unavailable.",
    category: benchmark.category ?? "Unavailable",
    difficulty: benchmark.difficulty ?? "Unavailable",
    status: benchmark.status,
    verificationScore: benchmark.verificationScore !== undefined ? `${benchmark.verificationScore}%` : "—",
    tasksCountFormatted: benchmark.tasksCount !== undefined ? new Intl.NumberFormat().format(benchmark.tasksCount) : "—",
    estimatedRuntime: benchmark.estimatedRuntime ?? "—",
  };
}

export function buildBenchmarkRowModel(benchmark: Benchmark): BenchmarkRowModel {
  return {
    id: benchmark.id,
    name: benchmark.name,
    category: benchmark.category ?? "Unavailable",
    difficulty: benchmark.difficulty ?? "Unavailable",
    status: benchmark.status,
    verificationScore: benchmark.verificationScore !== undefined ? `${benchmark.verificationScore}%` : "—",
    tasksCountFormatted: benchmark.tasksCount !== undefined ? new Intl.NumberFormat().format(benchmark.tasksCount) : "—",
    estimatedRuntime: benchmark.estimatedRuntime ?? "—",
    updatedAt: benchmark.updatedAt ?? "—",
  };
}

export function buildBenchmarkPreviewModel(benchmark: Benchmark): BenchmarkPreviewModel {
  return {
    id: benchmark.id,
    name: benchmark.name,
    description: benchmark.description ?? "Description unavailable.",
    category: benchmark.category ?? "Unavailable",
    difficulty: benchmark.difficulty ?? "Unavailable",
    status: benchmark.status,
    version: benchmark.version ?? "Unavailable",
    tasksCountFormatted: benchmark.tasksCount !== undefined ? new Intl.NumberFormat().format(benchmark.tasksCount) : "—",
    estimatedRuntime: benchmark.estimatedRuntime ?? "—",
    license: benchmark.license ?? "Unavailable",
    author: benchmark.author ?? "Unavailable",
    verificationScore: benchmark.verificationScore !== undefined ? `${benchmark.verificationScore}%` : "—",
    tags: benchmark.tags ?? [],
    metrics: benchmark.metrics ?? [],
    compatibleModels: benchmark.compatibleModels ?? [],
    details: benchmark.details ?? "Details unavailable.",
    updatedAt: benchmark.updatedAt ?? "—",
  };
}

export function buildBenchmarkComparisonModel(benchmark: Benchmark): BenchmarkComparisonModel {
  return {
    id: benchmark.id,
    name: benchmark.name,
    category: benchmark.category ?? "Unavailable",
    difficulty: benchmark.difficulty ?? "Unavailable",
    tasksCountFormatted: benchmark.tasksCount !== undefined ? new Intl.NumberFormat().format(benchmark.tasksCount) : "—",
    metrics: benchmark.metrics ?? [],
  };
}
