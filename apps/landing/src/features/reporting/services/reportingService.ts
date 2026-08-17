/**
 * Services — Reporting API Service (Milestone 5)
 * Handles REST operations for execution run reports and CSV/JSON export downloads.
 */

import { apiClient } from '@/core/api/client';
import type { ServiceResult } from '@/core/types/service';

export interface ReportRunSummaryDTO {
  run_id: string;
  benchmark_id: string;
  benchmark_name: string;
  benchmark_version: string;
  target_model: string;
  evaluation_status: string;
  started_at: string | null;
  completed_at: string | null;
  overall_score: number | null;
}

export interface PaginatedReportRunsDTO {
  items: ReportRunSummaryDTO[];
  total: number;
  page: number;
  size: number;
}

export async function getReportRuns(): Promise<ServiceResult<PaginatedReportRunsDTO | null>> {
  try {
    const res = await apiClient.get<PaginatedReportRunsDTO>('/api/v1/reports/runs');
    if (res && Array.isArray(res.items)) {
      return { data: res, error: null };
    }
    return { data: null, error: 'Failed to parse report runs' };
  } catch (err: any) {
    return { data: null, error: err?.message || 'Failed to fetch report runs' };
  }
}

export async function getReportRunById(runId: string): Promise<ServiceResult<ReportRunSummaryDTO | null>> {
  try {
    const res = await apiClient.get<ReportRunSummaryDTO>(`/api/v1/reports/runs/${runId}`);
    if (res && res.run_id) {
      return { data: res, error: null };
    }
    return { data: null, error: `Report for run ${runId} not found` };
  } catch (err: any) {
    return { data: null, error: err?.message || 'Failed to fetch report summary' };
  }
}
