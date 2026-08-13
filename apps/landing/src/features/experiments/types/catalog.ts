import type { MockExperimentStatus, MockExperimentStage, MockExperimentLog, MockExperimentMetrics, MockExperimentConfig } from '../mocks/mock';

export interface ExperimentRowModel {
  id: string;
  name: string;
  status: MockExperimentStatus;
  progressPercentage: number;
  currentStage: string;
  stageCountText: string;
  etaText: string;
  durationText: string;
  queuedAt: string;
  tags: string[];
}

export interface ExperimentPreviewModel {
  id: string;
  name: string;
  status: MockExperimentStatus;
  owner: string;
  startedAt: string | null;
  durationText: string;
  
  stages: MockExperimentStage[];
  logs: MockExperimentLog[];
  metrics: MockExperimentMetrics;
  config: MockExperimentConfig;
}

export interface ExperimentFilterState {
  searchQuery: string;
  status: 'all' | MockExperimentStatus;
}

export interface ExperimentSortState {
  field: 'name' | 'progress' | 'queuedAt';
  direction: 'asc' | 'desc';
}
