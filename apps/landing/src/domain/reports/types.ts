/**
 * Domain — Reports
 * Types and mock data for evaluation reports.
 */

/* ----------------------------------------------------------------------- */

export interface Report {
  id: string;
  title: string;
  description: string;
  evaluationRunId: string;
  modelId: string;
  modelName: string;
  benchmarkId: string;
  benchmarkName: string;
  createdAt: string;
  status: 'draft' | 'verified' | 'archived';
  type: 'full' | 'comparison' | 'leaderboard';
}

/* ----------------------------------------------------------------------- */

export const REPORTS: Report[] = [
  {
    id: 'rpt-001',
    title: 'GPT-4o on MMLU — Full Evaluation',
    description: 'Comprehensive capability profile across 57 knowledge domains.',
    evaluationRunId: 'run-004',
    modelId: 'gpt-4o',
    modelName: 'GPT-4o',
    benchmarkId: 'mmlu',
    benchmarkName: 'MMLU',
    createdAt: '2026-07-19T10:12:00Z',
    status: 'verified',
    type: 'full',
  },
  {
    id: 'rpt-002',
    title: 'Claude vs GPT-4o — Coding Comparison',
    description: 'Head-to-head comparison on HumanEval and MBPP.',
    evaluationRunId: 'run-005',
    modelId: 'claude-4-sonnet',
    modelName: 'Claude 4 Sonnet',
    benchmarkId: 'humaneval',
    benchmarkName: 'HumanEval',
    createdAt: '2026-07-19T09:48:00Z',
    status: 'verified',
    type: 'comparison',
  },
  {
    id: 'rpt-003',
    title: 'Safety Evaluation — Open Models',
    description: 'Safety audit across TruthfulQA and custom bias benchmarks.',
    evaluationRunId: 'run-005',
    modelId: 'llama-4-maverick',
    modelName: 'LLaMA 4 Maverick',
    benchmarkId: 'truthfulqa',
    benchmarkName: 'TruthfulQA',
    createdAt: '2026-07-18T16:30:00Z',
    status: 'draft',
    type: 'full',
  },
];
