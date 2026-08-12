/**
 * Services — Leaderboard API Service (Milestone 5)
 * Handles REST operations for global and benchmark model leaderboards.
 */

import { apiClient } from '@/core/api/client';
import type { ServiceResult } from '@/core/types/service';

export interface ModelRankingEntry {
  rank: number;
  model_name: string;
  overall_score: number;
  total_evaluations: number;
}

export interface BackendLeaderboardResponse {
  benchmark_version_id: string;
  benchmark_name: string;
  total_models: number;
  rankings: ModelRankingEntry[];
}

export async function getGlobalLeaderboard(): Promise<ServiceResult<BackendLeaderboardResponse | null>> {
  try {
    const res = await apiClient.get<BackendLeaderboardResponse>('/api/v1/leaderboard');
    if (res && res.rankings) {
      return { data: res, error: null };
    }
    return { data: null, error: 'Failed to parse leaderboard payload' };
  } catch (err: any) {
    return { data: null, error: err?.message || 'Failed to fetch global leaderboard' };
  }
}
