export const EVALUATION_STATUS_TABS = [
  { id: 'all', label: 'All' },
  { id: 'running', label: 'Running' },
  { id: 'queued', label: 'Queued' },
  { id: 'completed', label: 'Completed' },
  { id: 'failed', label: 'Failed' },
  { id: 'paused', label: 'Paused' },
  { id: 'cancelled', label: 'Cancelled' },
];

export const EVALUATION_SEARCH_HINTS = [
  'status:running',
  'model:gpt-5',
  'benchmark:mmlu',
  'dataset:humaneval',
  'owner:tushar',
  'status:failed',
  'status:queued',
];
