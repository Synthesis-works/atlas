/**
 * Domain — Benchmarks Types & Interfaces
 * Pure data models, status lifecycles, and verification schemas.
 */

export type BenchmarkCategory =
  | 'coding'
  | 'reasoning'
  | 'mathematics'
  | 'planning'
  | 'tool_use'
  | 'knowledge'
  | 'safety'
  | 'language'
  | 'vision'
  | 'multimodal'
  | 'agents';

export type BenchmarkStatus =
  | 'Draft'
  | 'Validating'
  | 'Ready'
  | 'Running'
  | 'Paused'
  | 'Completed'
  | 'Failed'
  | 'Archived';

export type BenchmarkDifficulty = 'beginner' | 'intermediate' | 'advanced' | 'expert';

export interface VerificationChecklist {
  datasetLicense: boolean;
  metadata: boolean;
  promptSchema: boolean;
  outputSchema: boolean;
  referenceAnswers: boolean;
  evaluationScript: boolean;
  metricDefinitions: boolean;
  documentation: boolean;
  reproducibility: boolean;
}

export interface DatasetSample {
  id: string;
  split: 'train' | 'validation' | 'test';
  prompt: string;
  expectedAnswer: string;
  metadata: Record<string, string | number | boolean>;
  difficulty: BenchmarkDifficulty;
  tags: string[];
}

export interface MetricCardItem {
  id: string;
  name: string;
  value: number | string;
  unit?: string;
  trend?: 'up' | 'down' | 'neutral';
  change?: string;
  description: string;
  status: 'optimal' | 'warning' | 'normal';
}

export interface VersionRecord {
  version: string;
  description: string;
  date: string;
  author: string;
  hash: string;
}

export interface ArtifactItem {
  id: string;
  filename: string;
  type: 'json' | 'csv' | 'pdf' | 'log' | 'folder';
  size: string;
  previewContent?: string;
  downloadUrl?: string;
}

export interface Benchmark {
  id: string;
  slug?: string;
  name: string;
  description: string;
  category: BenchmarkCategory;
  difficulty: BenchmarkDifficulty;
  status: BenchmarkStatus;
  version: string;
  tasksCount: number;
  samplesCount: number;
  estimatedRuntime: string;
  license: string;
  author: string;
  verificationScore: number; // Percentage (e.g. 100 for 9/9)
  verification: VerificationChecklist;
  tags: string[];
  metrics: MetricCardItem[];
  compatibleModels: string[];
  details: string;
  methodology: string[];
  datasetSamples: DatasetSample[];
  versionsHistory: VersionRecord[];
  artifacts: ArtifactItem[];
  relatedIds: string[];
  updatedAt: string;
}
