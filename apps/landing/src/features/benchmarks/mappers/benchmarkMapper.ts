/**
 * Features — Benchmark Mapper
 * Transforms raw backend database DTOs into clean frontend domain models.
 * Keeps UI components completely decoupled from backend REST schema changes.
 */

import type { Benchmark, BenchmarkCategory } from '@/domain/benchmarks/types';

export interface BackendBenchmarkVersionRead {
  id: string;
  benchmark_id: string;
  version_string: string;
  config_schema?: Record<string, any>;
  evaluator_type?: string;
  is_active?: boolean;
  created_at?: string;
}

export interface BackendBenchmarkRead {
  id: string;
  project_id?: string;
  name: string;
  slug: string;
  description?: string;
  task_type?: string;
  modality?: string;
  is_public?: boolean;
  created_at?: string;
  updated_at?: string;
  versions?: BackendBenchmarkVersionRead[];
}

export class BenchmarkMapper {
  static toDomain(dto: BackendBenchmarkRead): Benchmark {
    const category = this.mapTaskTypeToCategory(dto.task_type || '');
    const activeVersion = dto.versions && dto.versions.length > 0
      ? dto.versions.find((v) => v.is_active) || dto.versions[0]
      : undefined;

    return {
      id: dto.id,
      slug: dto.slug,
      name: dto.name,
      description: dto.description || 'Enterprise evaluation suite for AI systems.',
      category,
      difficulty: 'expert',
      status: 'Ready',
      version: activeVersion?.version_string || '1.0.0',
      tasksCount: 0,
      samplesCount: 0,
      estimatedRuntime: '--',
      license: 'MIT',
      author: 'Atlas Core',
      verificationScore: 0,
      verification: {
        datasetLicense: false,
        metadata: true,
        promptSchema: true,
        outputSchema: true,
        referenceAnswers: false,
        evaluationScript: false,
        metricDefinitions: true,
        documentation: true,
        reproducibility: false,
      },
      tags: [category, 'enterprise'],
      metrics: [],
      compatibleModels: ['GPT-5', 'Claude-3.5-Sonnet', 'Gemini-2.0-Flash', 'Llama-3.3-70B'],
      details: dto.description || 'Enterprise benchmark dataset for model evaluation.',
      methodology: ['Standardized evaluation harness', 'Automated AST verification'],
      datasetSamples: [],
      versionsHistory: [],
      artifacts: [],
      relatedIds: [],
      updatedAt: dto.updated_at || new Date().toISOString(),
    };
  }

  static toDomainList(dtos: BackendBenchmarkRead[]): Benchmark[] {
    if (!Array.isArray(dtos)) return [];
    return dtos.map((dto) => this.toDomain(dto));
  }

  private static mapTaskTypeToCategory(taskType: string): BenchmarkCategory {
    const normalized = (taskType || '').toUpperCase();
    if (normalized.includes('CODE') || normalized.includes('CODING')) return 'coding';
    if (normalized.includes('SAFETY') || normalized.includes('GUARD')) return 'safety';
    if (normalized.includes('MULTI') || normalized.includes('VISION')) return 'multimodal';
    if (normalized.includes('AGENT')) return 'agents';
    return 'reasoning';
  }
}
