import { apiClient } from '@/infrastructure/api/client';

export interface ExecutionArtifactDto {
  id: string;
  type: string; // 'LOGS' | 'RESULTS' | ...
  storage_uri: string;
}

export interface ExecutionAttemptDto {
  id: string;
  attempt_number: number;
  status: string;
  started_at: string;
  finished_at: string | null;
  error_message: string | null;
  artifacts: ExecutionArtifactDto[];
}

export interface ExecutionReadDto {
  id: string;
  benchmark_version_id: string;
  status: string;
  created_at: string;
  updated_at: string;
  created_by: string;
  max_retries: number;
  total_items: number;
  completed_items: number;
  attempts: ExecutionAttemptDto[];
}

export interface ProjectExecutionListEntryDto {
  id: string;
  benchmark_name: string;
  target_model: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  duration: number | null;
  total_items: number;
  completed_items: number;
  created_at: string;
}

export interface CapabilityScoreRead {
  capability_name: string;
  score: number;
}

export interface ReportSummaryRead {
  run_id: string;
  benchmark_id: string;
  benchmark_name: string;
  benchmark_version: string;
  target_model: string;
  evaluation_status: string;
  started_at: string | null;
  completed_at: string | null;
  overall_score: number | null;
  scores: CapabilityScoreRead[];
}

export interface PageResponseDto<T> {
  items: T[];
  total: number;
}

export interface ApiResponseDto<T> {
  success: boolean;
  message: string;
  data: T;
  meta: {
    request_id: string;
    timestamp: string;
  };
}

export interface GetExecutionsParams {
  limit?: number;
  offset?: number;
  status?: string;
  target_model?: string;
  benchmark_version_id?: string;
}

export const experimentApi = {
  getExecutions: async (projectId: string, params: GetExecutionsParams): Promise<PageResponseDto<ProjectExecutionListEntryDto>> => {
    const response = await apiClient.get<ApiResponseDto<PageResponseDto<ProjectExecutionListEntryDto>>>(`/projects/${projectId}/executions`, { params });
    return response.data.data;
  },
  
  getExecution: async (projectId: string, executionId: string): Promise<ExecutionReadDto> => {
    const response = await apiClient.get<ApiResponseDto<ExecutionReadDto>>(`/projects/${projectId}/executions/${executionId}`);
    return response.data.data;
  },

  getReport: async (executionId: string): Promise<ReportSummaryRead> => {
    // Note: GET /reports/runs/{run_id} returns ReportSummaryRead directly wrapped in ApiResponseDto?
    const response = await apiClient.get(`/reports/runs/${executionId}`);
    return response.data.data ? response.data.data : response.data;
  }
};
