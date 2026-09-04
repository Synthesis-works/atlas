/**
 * Features — Benchmark Mapper
 * Transforms raw backend database DTOs into clean frontend domain models.
 * Strictly preserves real database fields and nullable telemetry.
 */

import type { Benchmark, BenchmarkCategory, BenchmarkStatus, BenchmarkDifficulty } from '@/domain/benchmarks/types';

export interface BackendBenchmarkVersionRead {
  id: string;
  benchmark_id: string;
  version_string: string;
  state?: string;
  config_schema?: Record<string, any>;
  evaluator_type?: string;
  dataset_version_ids?: string[];
  evaluation_strategy_id?: string | null;
  evaluation_case_count?: number | null;
  execution_count?: number | null;
  average_score?: number | null;
  latest_score?: number | null;
  created_at?: string;
}

export interface BackendBenchmarkRead {
  id: string;
  project_id?: string;
  name: string;
  slug?: string;
  description?: string;
  objective?: string;
  domain?: string;
  difficulty?: string;
  type?: string;
  task_type?: string;
  state?: string;
  modality?: string;
  is_public?: boolean;
  created_at?: string;
  updated_at?: string;
  versions?: BackendBenchmarkVersionRead[];

  // Database telemetry metrics
  primary_dataset_id?: string | null;
  primary_dataset_version_id?: string | null;
  evaluation_case_count?: number | null;
  execution_count?: number | null;
  completed_execution_count?: number | null;
  failed_execution_count?: number | null;
  evaluation_count?: number | null;
  passed_evaluation_count?: number | null;
  average_score?: number | null;
  latest_score?: number | null;
  latest_execution_at?: string | null;
  average_latency_ms?: number | null;
}

export class BenchmarkMapper {
  static toDomain(dto: BackendBenchmarkRead): Benchmark {
    const category = this.mapDomainToCategory(dto.domain || dto.task_type || dto.type || '');
    const activeVersion = dto.versions && dto.versions.length > 0
      ? dto.versions[0]
      : undefined;

    const mappedStatus = this.mapStateToStatus(dto.state || '');
    const difficulty = this.mapDifficulty(dto.difficulty || '');

    const verificationScore =
      dto.latest_score != null
        ? Math.round(dto.latest_score)
        : dto.average_score != null
        ? Math.round(dto.average_score)
        : 0;

    return {
      id: dto.id,
      slug: dto.slug || dto.id,
      name: dto.name,
      description: dto.description || dto.objective || '',
      category,
      difficulty,
      status: mappedStatus,
      version: activeVersion?.version_string || '1.0.0',
      versionId: activeVersion?.id,
      datasetId: dto.primary_dataset_id || null,
      datasetVersionId: dto.primary_dataset_version_id || null,
      tasksCount: dto.evaluation_case_count ?? 0,
      samplesCount: dto.evaluation_case_count ?? 0,
      estimatedRuntime: dto.average_latency_ms != null ? `${dto.average_latency_ms}ms` : '—',
      license: 'Enterprise',
      author: 'Atlas Engine',
      verificationScore,
      verification: {
        datasetLicense: Boolean(dto.primary_dataset_id),
        metadata: Boolean(dto.name),
        promptSchema: true,
        outputSchema: true,
        referenceAnswers: (dto.evaluation_case_count ?? 0) > 0,
        evaluationScript: Boolean(activeVersion?.evaluation_strategy_id),
        metricDefinitions: true,
        documentation: Boolean(dto.description || dto.objective),
        reproducibility: (dto.execution_count ?? 0) > 0,
      },
      tags: [category].filter(Boolean),
      metrics: [],
      compatibleModels: [],
      details: dto.description || dto.objective || '',
      methodology: [],
      datasetSamples: [],
      versionsHistory: [],
      artifacts: [],
      relatedIds: [],
      updatedAt: dto.updated_at || dto.created_at || new Date().toISOString(),

      // Telemetry fields
      evaluationCaseCount: dto.evaluation_case_count ?? null,
      executionCount: dto.execution_count ?? 0,
      completedExecutionCount: dto.completed_execution_count ?? 0,
      failedExecutionCount: dto.failed_execution_count ?? 0,
      evaluationCount: dto.evaluation_count ?? 0,
      passedEvaluationCount: dto.passed_evaluation_count ?? 0,
      averageScore: dto.average_score ?? null,
      latestScore: dto.latest_score ?? null,
      latestExecutionAt: dto.latest_execution_at ?? null,
      averageLatencyMs: dto.average_latency_ms ?? null,
      versions: (dto.versions || []).map((v) => ({
        id: v.id,
        version_string: v.version_string,
        state: v.state || 'READY',
      })),
    };
  }

  static toDomainList(dtos: BackendBenchmarkRead[]): Benchmark[] {
    if (!Array.isArray(dtos)) return [];
    return dtos.map((dto) => this.toDomain(dto));
  }

  private static mapDomainToCategory(domain: string): BenchmarkCategory {
    const normalized = (domain || '').toLowerCase();
    if (normalized.includes('code') || normalized.includes('coding') || normalized.includes('software')) return 'coding';
    if (normalized.includes('math')) return 'mathematics';
    if (normalized.includes('safety') || normalized.includes('guard') || normalized.includes('align')) return 'safety';
    if (normalized.includes('vision') || normalized.includes('multi') || normalized.includes('image')) return 'multimodal';
    if (normalized.includes('agent') || normalized.includes('tool')) return 'agents';
    if (normalized.includes('plan')) return 'planning';
    if (normalized.includes('know') || normalized.includes('fact')) return 'knowledge';
    return 'reasoning';
  }

  private static mapStateToStatus(state: string): BenchmarkStatus {
    const upper = (state || '').toUpperCase();
    if (upper.includes('RUN') || upper === 'EVALUATING') return 'Running';
    if (upper.includes('COMPLET') || upper === 'SUCCESS') return 'Completed';
    if (upper.includes('FAIL')) return 'Failed';
    if (upper.includes('DRAFT')) return 'Draft';
    if (upper.includes('ARCHIV')) return 'Archived';
    return 'Ready';
  }

  private static mapDifficulty(diff: string): BenchmarkDifficulty {
    const lower = (diff || '').toLowerCase();
    if (lower === 'beginner' || lower === 'easy') return 'beginner';
    if (lower === 'advanced' || lower === 'hard') return 'advanced';
    if (lower === 'expert') return 'expert';
    return 'intermediate';
  }
}

