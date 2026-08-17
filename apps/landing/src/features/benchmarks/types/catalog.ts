import type { BenchmarkStatus, MetricCardItem } from '../../../domain/benchmarks/types';

export interface BenchmarkCardModel {
  id: string;
  name: string;
  description: string;
  category: string;
  difficulty: string;
  status: BenchmarkStatus;
  verificationScore: string;
  tasksCountFormatted: string;
  estimatedRuntime: string;
}

export interface BenchmarkRowModel {
  id: string;
  name: string;
  category: string;
  difficulty: string;
  status: BenchmarkStatus;
  verificationScore: string;
  tasksCountFormatted: string;
  estimatedRuntime: string;
  updatedAt: string;
}

export interface BenchmarkPreviewModel {
  id: string;
  name: string;
  description: string;
  category: string;
  difficulty: string;
  status: BenchmarkStatus;
  version: string;
  tasksCountFormatted: string;
  estimatedRuntime: string;
  license: string;
  author: string;
  verificationScore: string;
  tags: string[];
  metrics: MetricCardItem[];
  compatibleModels: string[];
  details: string;
  updatedAt: string;
}

export interface BenchmarkComparisonModel {
  id: string;
  name: string;
  category: string;
  difficulty: string;
  tasksCountFormatted: string;
  metrics: MetricCardItem[];
}
