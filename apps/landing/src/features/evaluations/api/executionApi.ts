import { apiClient } from '../../../infrastructure/api/client';
import type { EvaluationRun } from '@/domain/evaluations/types';

export interface ExecutionHistoryRead {
  id: string;
  benchmark_name: string;
  target_model: string;
  status: string;
  started_at?: string;
  completed_at?: string;
  duration?: number;
  project_id: string;
}

export interface ProjectExecutionListEntry {
  id: string;
  benchmark_name: string;
  target_model: string;
  status: string;
  started_at?: string;
  completed_at?: string;
  duration?: number;
  total_items: number;
  completed_items: number;
  created_at: string;
}

export interface ExecutionListResponse {
  items: ProjectExecutionListEntry[];
  total: number;
}

// Map backend status to UI status
function mapStatus(status: string): EvaluationRun['status'] {
  switch (status.toUpperCase()) {
    case 'QUEUED':
    case 'SCHEDULED': return 'Queued';
    case 'STARTING': return 'Preparing';
    case 'RUNNING': return 'Running';
    case 'EVALUATING': return 'Scoring';
    case 'COMPLETED': return 'Completed';
    case 'FAILED': return 'Failed';
    case 'RETRYING': return 'Retrying';
    case 'CANCELLING':
    case 'CANCELLED': return 'Cancelled';
    default: return 'Queued';
  }
}

export const executionApi = {
  // Get recent executions (for dashboard)
  getRecentExecutions: async (): Promise<EvaluationRun[]> => {
    const response = await apiClient.get<{ data: ExecutionHistoryRead[] }>('/history/executions/recent');
    // Map backend history format to UI format
    return (response.data.data || []).map(entry => ({
      id: entry.id,
      name: entry.benchmark_name + ' Execution',
      status: mapStatus(entry.status),
      priority: 'normal',
      model: entry.target_model,
      modelProvider: 'Unknown',
      dataset: 'Unknown',
      benchmark: entry.benchmark_name,
      benchmarkCategory: 'General',
      owner: 'System',
      progress: entry.status === 'COMPLETED' ? 100 : 0,
      currentStage: entry.status,
      worker: 'System Worker',
      workerStatus: 'idle',
      startedAt: entry.started_at || new Date().toISOString(),
      completedAt: entry.completed_at,
      durationMs: entry.duration,
      queuedAt: new Date().toISOString(),
      stages: [],
      logs: [],
      artifacts: [],
      config: {
        temperature: 0, topP: 0, seed: 0, maxTokens: 0, batchSize: 1, threads: 1, timeout: '', retries: 0, provider: ''
      },
      reproducibility: {
        modelVersion: '', datasetVersion: '', benchmarkVersion: '', promptVersion: '', commitSha: '', dockerImage: '', runtime: '', seed: 0, os: '', pythonVersion: '', cudaVersion: '', engineVersion: ''
      },
      tags: []
    }));
  },

  // Get executions for a project
  getProjectExecutions: async (projectId: string): Promise<EvaluationRun[]> => {
    const response = await apiClient.get<ExecutionListResponse>(`/projects/${projectId}/executions`);
    return (response.data.items || []).map(entry => ({
      id: entry.id,
      name: entry.benchmark_name + ' Execution',
      status: mapStatus(entry.status),
      priority: 'normal',
      model: entry.target_model,
      modelProvider: 'Unknown',
      dataset: 'Unknown',
      benchmark: entry.benchmark_name,
      benchmarkCategory: 'General',
      owner: 'System',
      progress: entry.total_items > 0 ? (entry.completed_items / entry.total_items) * 100 : (entry.status === 'COMPLETED' ? 100 : 0),
      currentStage: entry.status,
      worker: 'System Worker',
      workerStatus: 'idle',
      startedAt: entry.started_at || entry.created_at,
      completedAt: entry.completed_at,
      durationMs: entry.duration,
      queuedAt: entry.created_at,
      stages: [],
      logs: [],
      artifacts: [],
      config: {
        temperature: 0, topP: 0, seed: 0, maxTokens: 0, batchSize: 1, threads: 1, timeout: '', retries: 0, provider: ''
      },
      reproducibility: {
        modelVersion: '', datasetVersion: '', benchmarkVersion: '', promptVersion: '', commitSha: '', dockerImage: '', runtime: '', seed: 0, os: '', pythonVersion: '', cudaVersion: '', engineVersion: ''
      },
      tags: []
    }));
  }
};
