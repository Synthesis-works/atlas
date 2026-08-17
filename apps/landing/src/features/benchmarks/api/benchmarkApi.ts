import { apiClient } from '../../../infrastructure/api/client';
import type { Benchmark } from '@/domain/benchmarks/types';

export interface BenchmarkRead {
  id: string;
  name: string;
  description: string;
  category: string;
  version: string;
  project_id: string;
  author_id: string;
  is_active: boolean;
  is_public: boolean;
  created_at: string;
  updated_at: string;
  version_count?: number;
  item_count?: number;
}

export interface PageResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export const benchmarkApi = {
  listBenchmarks: async (projectId: string, limit: number = 25, offset: number = 0): Promise<{ items: Benchmark[], total: number }> => {
    const response = await apiClient.get<PageResponse<BenchmarkRead>>(`/projects/${projectId}/benchmarks`, {
      params: { limit, offset }
    });
    
    // Map backend response to UI Benchmark type
    const mapped = (response.data.items || []).map(entry => ({
      id: entry.id,
      name: entry.name,
      description: entry.description,
      category: (entry.category || 'General') as any, // Cast to BenchmarkCategory
      version: entry.version || '1.0.0',
      updatedAt: entry.updated_at,
      metrics: [],
      suiteCount: 1,
      testCount: entry.item_count || 10,
      tags: [],
      isOfficial: entry.is_public || false,
      status: 'Ready' as const,
      difficulty: 'intermediate' as const,
      tasksCount: entry.item_count || 10,
      samplesCount: entry.item_count || 10,
      estimatedRuntime: 'Unknown',
      license: 'MIT',
      author: entry.author_id,
      verificationScore: 100,
      verification: {
        isCurated: true,
        communityRating: 5,
        lastVerified: entry.updated_at
      } as any,
      compatibleModels: [],
      details: entry.description,
      methodology: [],
      datasetSamples: [],
      versionsHistory: [],
      artifacts: [],
      relatedIds: []
    }));
    return { items: mapped, total: response.data.total };
  },
  getBenchmarkVersions: async (_id: string): Promise<any[]> => {
    return [];
  }
};
