import type { BenchmarkCategory, BenchmarkDifficulty, BenchmarkStatus, MetricCardItem } from '../../../domain/benchmarks/types';

export interface BenchmarkCardModel {
  id: string;
  name: string;
  description: string;
  category: BenchmarkCategory;
  difficulty: BenchmarkDifficulty;
  status: BenchmarkStatus;
  verificationScore: number;
  tasksCountFormatted: string;
  estimatedRuntime: string;
}

export interface BenchmarkRowModel {
  id: string;
  name: string;
  category: BenchmarkCategory;
  difficulty: BenchmarkDifficulty;
  status: BenchmarkStatus;
  verificationScore: number;
  tasksCountFormatted: string;
  estimatedRuntime: string;
  updatedAt: string;
}

export interface BenchmarkPreviewModel {
  id: string;
  name: string;
  description: string;
  category: BenchmarkCategory;
  difficulty: BenchmarkDifficulty;
  status: BenchmarkStatus;
  version: string;
  tasksCountFormatted: string;
  estimatedRuntime: string;
  license: string;
  author: string;
  verificationScore: number;
  tags: string[];
  metrics: MetricCardItem[];
  compatibleModels: string[];
  details: string;
  updatedAt: string;
}

export interface BenchmarkComparisonModel {
  id: string;
  name: string;
  category: BenchmarkCategory;
  difficulty: BenchmarkDifficulty;
  tasksCountFormatted: string;
  metrics: MetricCardItem[];
}
