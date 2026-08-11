import { apiClient } from '@/core/api/client';


export interface ExecutionItem {
  id: string;
  model: string;
  benchmark: string;
  status: string;
  progress: number;
  is_verified: boolean;
  source: string;
}

export interface DashboardSummaryData {
  generated_at: string;
  version: string;
  summary: {
    active_runs_count: number;
    queued_runs_count: number;
    completed_runs_count: number;
    failed_runs_count: number;
    cancelled_runs_count?: number;
    total_runs_count?: number;
  };
  hierarchy: {
    models: number;
    benchmarks: number;
    datasets: number;
    evaluations: number;
    reports: number;
  };
  running_jobs?: ExecutionItem[];
  recent_verified_runs?: ExecutionItem[];
  active_executions: ExecutionItem[];

  activity: Array<{
    id: string;
    type: string;
    title: string;
    description: string;
    timestamp: string;
  }>;
  runtime: {
    engine_status: string;
    total_benchmarks: number;
    total_evaluations: number;
    total_models: number;
    avg_runtime_sec: number;
  };
  capability: {
    model_name: string;
    provider: string;
    rank: number;
    score: number;
    capabilities: Array<{ domain: string; score: number }>;
  };
}

export async function getDashboardSummary(): Promise<DashboardSummaryData | null> {
  try {
    const res = await apiClient.get<DashboardSummaryData>('/api/v1/dashboard');
    return res || null;
  } catch (err) {
    console.warn('Dashboard summary exception:', err);
    return null;
  }
}

