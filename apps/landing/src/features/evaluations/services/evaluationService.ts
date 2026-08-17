/**
 * Services — Evaluation & Execution Service
 * Handles live benchmark execution dispatch (Milestone 3A), status query operations (Milestone 3B),
 * and execution cancellation operations (Milestone 3D).
 */

import { apiClient } from '@/core/api/client';
import type { ServiceResult } from '@/core/types/service';
import type { EvaluationRun } from '@/domain/evaluations/types';
import { ensureAuthenticatedSession } from '@/features/auth/services/authService';
import { getReportRuns } from '@/features/reporting/services/reportingService';

export interface BackendExecutionCreatePayload {
  benchmark_version_id: string;
  target_model: string;
  dataset_version_id?: string;
  execution_config?: Record<string, any>;
}

export interface BackendExecutionResponse {
  id: string;
  project_id: string;
  benchmark_version_id: string;
  status: string;
  target_model: string;
  completed_items?: number;
  total_items?: number;
  queued_at?: string;
  created_at: string;
}

export interface DispatchTarget {
  benchmark_version_id: string;
  benchmark_name: string;
  version_string: string;
  dataset_version_id: string | null;
}

export async function getDispatchTargets(): Promise<ServiceResult<DispatchTarget[]>> {
  try {
    await ensureAuthenticatedSession();
    const rawRes = await apiClient.get<any>('/api/v1/executions/dispatch-targets');
    let items: any[] = [];
    if (Array.isArray(rawRes)) {
      items = rawRes;
    } else if (rawRes && Array.isArray(rawRes.items)) {
      items = rawRes.items;
    } else if (rawRes && rawRes.data && Array.isArray(rawRes.data)) {
      items = rawRes.data;
    }
    return {
      data: items.map((d) => ({
        benchmark_version_id: d.benchmark_version_id,
        benchmark_name: d.benchmark_name,
        version_string: d.version_string,
        dataset_version_id: d.dataset_version_id ?? null,
      })),
      error: null,
    };
  } catch (err: any) {
    return { data: [], error: err?.message || 'Failed to load dispatch targets' };
  }
}

export async function dispatchExecution(
  benchmarkVersionId: string,
  targetModel: string,
  datasetVersionId?: string | null
): Promise<ServiceResult<BackendExecutionResponse>> {
  try {
    await ensureAuthenticatedSession();
    const payload: BackendExecutionCreatePayload = {
      benchmark_version_id: benchmarkVersionId,
      target_model: targetModel,
    };
    if (datasetVersionId) {
      payload.dataset_version_id = datasetVersionId;
    }

    let res: BackendExecutionResponse;
    try {
      res = await apiClient.post<BackendExecutionResponse>(
        `/api/v1/benchmarks/${benchmarkVersionId}/executions`,
        payload
      );
    } catch (err: any) {
      if (err?.status === 401) {
        await ensureAuthenticatedSession(true);
        res = await apiClient.post<BackendExecutionResponse>(
          `/api/v1/benchmarks/${benchmarkVersionId}/executions`,
          payload
        );
      } else {
        throw err;
      }
    }

    if (res && res.id) {
      return { data: res, error: null };
    }
    return { data: null as any, error: 'Failed to create execution on backend' };
  } catch (err: any) {
    return { data: null as any, error: err?.message || 'Execution dispatch failed' };
  }
}

export async function getExecutionStatus(
  id: string
): Promise<ServiceResult<BackendExecutionResponse | null>> {
  try {
    await ensureAuthenticatedSession();
    let res: BackendExecutionResponse;
    try {
      res = await apiClient.get<BackendExecutionResponse>(`/api/v1/executions/${id}`);
    } catch (err: any) {
      if (err?.status === 401) {
        await ensureAuthenticatedSession(true);
        res = await apiClient.get<BackendExecutionResponse>(`/api/v1/executions/${id}`);
      } else {
        throw err;
      }
    }
    if (res && res.id) {
      return { data: res, error: null };
    }
    return { data: null, error: `Execution ${id} not found` };
  } catch (err: any) {
    return { data: null, error: err?.message || 'Failed to fetch execution status' };
  }
}

export async function cancelExecution(
  id: string
): Promise<ServiceResult<BackendExecutionResponse | null>> {
  try {
    await ensureAuthenticatedSession();
    const res = await apiClient.post<BackendExecutionResponse>(`/api/v1/executions/${id}/cancel`, {});
    if (res && res.id) {
      return { data: res, error: null };
    }
    return { data: null, error: `Failed to cancel execution ${id}` };
  } catch (err: any) {
    return { data: null, error: err?.message || 'Failed to cancel execution' };
  }
}

function deriveProvider(model: string | undefined | null): string {
  const lowered = (model ?? '').toLowerCase();
  if (lowered.includes('gemini')) return 'Google AI';
  if (lowered.includes('gpt')) return 'OpenAI';
  if (lowered.includes('claude')) return 'Anthropic';
  if (lowered.includes('grok')) return 'xAI';
  if (lowered.includes('llama') || lowered.includes('qwen') || lowered.includes('mistral') || lowered.includes('deepseek')) return 'Open Source';
  return 'Unknown';
}

export async function getEvaluations(): Promise<ServiceResult<EvaluationRun[]>> {
  try {
    await ensureAuthenticatedSession();
    const rawRes = await apiClient.get<any>('/api/v1/executions');
    let dtos: any[] = [];
    if (Array.isArray(rawRes)) {
      dtos = rawRes;
    } else if (rawRes && Array.isArray(rawRes.items)) {
      dtos = rawRes.items;
    } else if (rawRes && rawRes.data && Array.isArray(rawRes.data.items)) {
      dtos = rawRes.data.items;
    } else if (rawRes && rawRes.data && Array.isArray(rawRes.data)) {
      dtos = rawRes.data;
    }

    // Resolve real benchmark/version labels from dispatch targets (by benchmark_version_id)
    // and real persisted scores from the reporting service (by execution run id).
    const [targetsRes, reportRes] = await Promise.all([getDispatchTargets(), getReportRuns()]);

    const targetByBv = new Map<
      string,
      { benchmarkName: string; versionString: string; datasetVersionId: string | null }
    >();
    (targetsRes.data ?? []).forEach((t) => {
      targetByBv.set(t.benchmark_version_id, {
        benchmarkName: t.benchmark_name,
        versionString: t.version_string,
        datasetVersionId: t.dataset_version_id ?? null,
      });
    });

    const scoreByRun = new Map<string, number>();
    (reportRes.data?.items ?? []).forEach((r: any) => {
      if (r && r.run_id && typeof r.overall_score === 'number') {
        scoreByRun.set(r.run_id, r.overall_score);
      }
    });

    // Exact contract from packages/execution_engine ExecutionState. Unknown backend
    // statuses pass through verbatim so a real backend state is never relabelled or
    // silently collapsed into a fabricated value.
    const statusMap: Record<string, EvaluationRun['status']> = {
      QUEUED: 'Queued',
      SCHEDULED: 'Queued',
      STARTING: 'Running',
      RUNNING: 'Running',
      EVALUATING: 'Scoring',
      COMPLETED: 'Completed',
      FAILED: 'Failed',
      RETRYING: 'Retrying',
      CANCELLING: 'Cancelled',
      CANCELLED: 'Cancelled',
    };

    const mapped: EvaluationRun[] = dtos.map((dto: any, i: number) => {
      const config = dto.execution_config || {};
      const status = (statusMap[dto.status] ?? dto.status ?? 'Queued') as EvaluationRun['status'];

      const target = targetByBv.get(dto.benchmark_version_id);
      const benchmarkName = target?.benchmarkName ?? 'Unknown benchmark';
      const benchmarkVersion = target?.versionString ?? '';

      const passAt1 = typeof config.pass_at_1 === 'number' ? config.pass_at_1 : undefined;
      const latencyMs = typeof config.latency_ms === 'number' ? config.latency_ms : undefined;
      const reportScore = scoreByRun.get(dto.id);

      const startedAt = dto.started_at || dto.created_at;
      const completedAt = status === 'Completed' ? dto.completed_at || undefined : undefined;
      let durationMs: number | undefined;
      if (startedAt && dto.completed_at) {
        const ms = new Date(dto.completed_at).getTime() - new Date(startedAt).getTime();
        if (!Number.isNaN(ms) && ms >= 0) durationMs = ms;
      }

      const totalItems = typeof dto.total_items === 'number' ? dto.total_items : undefined;
      const completedItems =
        typeof dto.completed_items === 'number' ? dto.completed_items : undefined;
      const progress =
        status === 'Completed'
          ? 100
          : status === 'Queued'
            ? 0
            : totalItems && totalItems > 0 && completedItems !== undefined
              ? Math.min(100, Math.round((completedItems / totalItems) * 100))
              : 0;

      // Only persist real metric values. Nothing is invented here: a score comes from
      // the reporting service or the execution config; otherwise the run has no metrics.
      const metrics: any = {};
      if (reportScore !== undefined) metrics.overallScore = reportScore / 100;
      if (passAt1 !== undefined) {
        metrics.passAt1 = passAt1 / 100;
        metrics.accuracy = passAt1 / 100;
        if (metrics.overallScore === undefined) metrics.overallScore = passAt1 / 100;
      }
      if (latencyMs !== undefined) metrics.latencyMs = latencyMs;

      const isVerified = config.is_verified ?? false;
      const source = config.source ?? 'real';

      return {
        id: dto.id || `eval-${i}`,
        name: `${dto.target_model || 'Unknown model'} on ${benchmarkName}`,
        benchmark: benchmarkName,
        benchmarkCategory: '',
        benchmarkVersion,
        priority: 'normal',
        dataset: '',
        model: dto.target_model || 'Unknown model',
        modelProvider: deriveProvider(dto.target_model),
        status,
        progress,
        currentStage: status === 'Queued' ? 'Queued' : status,
        worker: '',
        workerStatus: 'idle',
        queuedAt: dto.created_at || new Date().toISOString(),
        startedAt,
        completedAt,
        durationMs,
        totalItems,
        completedItems,
        owner: '—',
        metrics: Object.keys(metrics).length > 0 ? metrics : undefined,
        stages: [],
        logs: [],
        artifacts: [],
        tags: [source],
        isVerified,
        source,
      };
    });

    return { data: mapped, error: null };
  } catch (err: any) {
    return { data: [], error: err?.message || 'Failed to fetch evaluations' };
  }
}

export async function getEvaluationById(id: string): Promise<ServiceResult<EvaluationRun | null>> {
  try {
    const listRes = await getEvaluations();
    const item = listRes.data?.find((e) => e.id === id) ?? null;
    return { data: item, error: item ? null : `Evaluation ${id} not found` };
  } catch (err: any) {
    return { data: null, error: err?.message || 'Error fetching evaluation' };
  }
}

export async function filterEvaluations(
  query: string,
  status: string
): Promise<ServiceResult<EvaluationRun[]>> {
  try {
    const listRes = await getEvaluations();
    let result = listRes.data || [];
    if (status && status !== 'all') {
      result = result.filter((e) => e.status.toLowerCase() === status.toLowerCase());
    }
    if (query.trim()) {
      const q = query.toLowerCase();
      result = result.filter(
        (e) =>
          e.name.toLowerCase().includes(q) ||
          e.model.toLowerCase().includes(q) ||
          e.benchmark.toLowerCase().includes(q)
      );
    }
    return { data: result, error: null };
  } catch (err: any) {
    return { data: [], error: err?.message || 'Filter failed' };
  }
}

