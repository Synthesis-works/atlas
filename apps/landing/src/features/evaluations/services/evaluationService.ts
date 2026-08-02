import type { ServiceResult } from '@/core/types/service';
import type { EvaluationRun } from '@/domain/evaluations/types';
import { MOCK_EVALUATIONS } from '@/domain/evaluations/mock';

export async function getEvaluations(): Promise<ServiceResult<EvaluationRun[]>> {
  try {
    await new Promise(r => setTimeout(r, 80));
    return { data: MOCK_EVALUATIONS, error: null };
  } catch (err: any) {
    return { data: [], error: err?.message || 'Failed to fetch evaluations' };
  }
}

export async function getEvaluationById(id: string): Promise<ServiceResult<EvaluationRun | null>> {
  try {
    await new Promise(r => setTimeout(r, 40));
    const item = MOCK_EVALUATIONS.find(e => e.id === id) ?? null;
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
    let result = MOCK_EVALUATIONS;
    if (status && status !== 'all') {
      result = result.filter(e => e.status.toLowerCase() === status.toLowerCase());
    }
    if (query.trim()) {
      const q = query.toLowerCase();
      result = result.filter(e =>
        e.name.toLowerCase().includes(q) ||
        e.model.toLowerCase().includes(q) ||
        e.benchmark.toLowerCase().includes(q) ||
        e.dataset.toLowerCase().includes(q) ||
        e.owner.toLowerCase().includes(q) ||
        e.tags.some(t => t.includes(q))
      );
    }
    return { data: result, error: null };
  } catch (err: any) {
    return { data: [], error: err?.message || 'Filter failed' };
  }
}
