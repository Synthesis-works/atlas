export type ExperimentStatus = 'Queued' | 'Running' | 'Completed' | 'Failed' | 'Cancelled';

export interface ExperimentRowModel {
  id: string;
  name: string;
  status: ExperimentStatus;
  progressPercentage: number | null;
  currentStage: string;
  stageCountText: string | null;
  etaText: string | null;
  durationText: string;
  queuedAt: string;
  tags: string[];
}

export interface ExperimentTimelineEvent {
  id: string;
  name: string;
  status: 'pending' | 'active' | 'completed' | 'failed' | 'skipped';
  durationMs?: number;
}

export interface ExperimentLogEntry {
  id: string;
  timestamp: string;
  level: 'info' | 'warn' | 'error' | 'debug';
  message: string;
  eventId?: string;
}

export interface ExperimentPreviewModel {
  id: string;
  name: string;
  status: ExperimentStatus;
  owner: string;
  startedAt: string | null;
  durationText: string;
  
  timeline: ExperimentTimelineEvent[];
  logs: ExperimentLogEntry[] | null;
  metrics: Record<string, any>;
  config: Record<string, any>;
}

export interface ExperimentFilterState {
  searchQuery: string;
  status: 'all' | ExperimentStatus;
}

export interface ExperimentSortState {
  field: 'name' | 'progress' | 'queuedAt';
  direction: 'asc' | 'desc';
}
