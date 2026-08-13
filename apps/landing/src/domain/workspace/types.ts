/**
 * Domain — Workspace
 * Activity events, quick actions, and workspace state.
 */

/* ----------------------------------------------------------------------- */

export type ActivityType =
  | 'evaluation_completed'
  | 'evaluation_started'
  | 'benchmark_published'
  | 'report_generated'
  | 'model_registered'
  | 'dataset_imported';

export interface ActivityEvent {
  id: string;
  type: ActivityType;
  title: string;
  description: string;
  timestamp: string;        // ISO 8601
  meta?: {
    modelName?: string;
    benchmarkName?: string;
    correlationId?: string;
  };
}

export interface QuickAction {
  id: string;
  label: string;
  description: string;
  icon: string;              // lucide icon name
  href: string;
}

/* ----------------------------------------------------------------------- */

export const ACTIVITY_FEED: ActivityEvent[] = [
  {
    id: 'act-001',
    type: 'evaluation_completed',
    title: 'Evaluation completed',
    description: 'GPT-4o on MMLU — verified, 87.2% accuracy.',
    timestamp: '2026-07-19T10:12:00Z',
    meta: { modelName: 'GPT-4o', benchmarkName: 'MMLU', correlationId: 'ATL-RUN-2026-000191' },
  },
  {
    id: 'act-002',
    type: 'evaluation_started',
    title: 'Evaluation started',
    description: 'Claude 4 Sonnet on HumanEval — executing.',
    timestamp: '2026-07-19T10:28:00Z',
    meta: { modelName: 'Claude 4 Sonnet', benchmarkName: 'HumanEval', correlationId: 'ATL-RUN-2026-000193' },
  },
  {
    id: 'act-003',
    type: 'benchmark_published',
    title: 'Benchmark published',
    description: 'TruthfulQA v1.1.0 published to the registry.',
    timestamp: '2026-07-19T09:15:00Z',
  },
  {
    id: 'act-004',
    type: 'report_generated',
    title: 'Report generated',
    description: 'Safety audit for LLaMA 4 Maverick — draft.',
    timestamp: '2026-07-18T16:30:00Z',
    meta: { modelName: 'LLaMA 4 Maverick' },
  },
  {
    id: 'act-005',
    type: 'model_registered',
    title: 'Model registered',
    description: 'Gemini 2.5 Pro added to the model registry.',
    timestamp: '2026-07-18T14:00:00Z',
  },
  {
    id: 'act-006',
    type: 'evaluation_completed',
    title: 'Evaluation completed',
    description: 'Mistral Large on TruthfulQA — 84.1% truthfulness.',
    timestamp: '2026-07-18T09:48:00Z',
    meta: { modelName: 'Mistral Large', benchmarkName: 'TruthfulQA', correlationId: 'ATL-RUN-2026-000190' },
  },
];

export const QUICK_ACTIONS: QuickAction[] = [
  {
    id: 'qa-new-eval',
    label: 'New Evaluation',
    description: 'Run a benchmark against any registered model.',
    icon: 'Play',
    href: '/dashboard/evaluations/new',
  },
  {
    id: 'qa-browse',
    label: 'Browse Benchmarks',
    description: 'Explore the Atlas Benchmark Registry.',
    icon: 'Database',
    href: '/dashboard/benchmarks',
  },
  {
    id: 'qa-reports',
    label: 'View Reports',
    description: 'Read and compare evaluation reports.',
    icon: 'FileText',
    href: '/dashboard/reports',
  },
  {
    id: 'qa-leaderboard',
    label: 'Leaderboard',
    description: 'See how models rank across capabilities.',
    icon: 'BarChart3',
    href: '/dashboard/leaderboard',
  },
  {
    id: 'qa-datasets',
    label: 'Browse Datasets',
    description: 'Explore and manage dataset registry.',
    icon: 'FolderKanban',
    href: '/dashboard/datasets',
  },
  {
    id: 'qa-models',
    label: 'Model Registry',
    description: 'View and configure AI models.',
    icon: 'Cpu',
    href: '/dashboard/models',
  },
];
