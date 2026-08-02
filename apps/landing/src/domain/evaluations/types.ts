/**
 * Domain — Evaluations Types v2
 */

export type EvaluationStatus =
  | 'Queued'
  | 'Loading'
  | 'Preparing'
  | 'Running'
  | 'Scoring'
  | 'Aggregating'
  | 'Reporting'
  | 'Completed'
  | 'Failed'
  | 'Cancelled'
  | 'Paused'
  | 'Retrying';

export type EvaluationPriority = 'critical' | 'high' | 'normal' | 'low';

export type WorkerStatus = 'idle' | 'busy' | 'offline' | 'error';

export type FailureReason =
  | 'Timeout'
  | 'GPU Error'
  | 'Dataset Error'
  | 'Model Crash'
  | 'Network'
  | 'OOM'
  | 'Rate Limit'
  | 'Config Error';

export interface EvaluationStageRecord {
  id: string;
  name: string;
  status: 'pending' | 'active' | 'completed' | 'failed' | 'skipped';
  startedAt?: string;
  completedAt?: string;
  durationMs?: number;
  etaMs?: number;
  logs?: string[];
}

export interface EvaluationMetrics {
  accuracy?: number;
  precision?: number;
  recall?: number;
  f1?: number;
  passAt1?: number;
  passAt10?: number;
  latencyMs?: number;
  tokensPerSec?: number;
  hallucinationRate?: number;
  truthfulnessScore?: number;
  toxicityScore?: number;
  costUsd?: number;
  gpuUtilPct?: number;
  memoryGb?: number;
  energyKwh?: number;
  overallScore?: number;
}

export interface EvaluationReproducibility {
  modelVersion: string;
  datasetVersion: string;
  benchmarkVersion: string;
  promptVersion: string;
  commitSha: string;
  dockerImage: string;
  runtime: string;
  seed: number;
  os: string;
  pythonVersion: string;
  cudaVersion: string;
  engineVersion: string;
}

export interface EvaluationConfig {
  temperature: number;
  topP: number;
  seed: number;
  maxTokens: number;
  batchSize: number;
  threads: number;
  timeout: string;
  retries: number;
  provider: string;
  quantization?: string;
}

export interface EvaluationArtifact {
  id: string;
  filename: string;
  type: 'pdf' | 'json' | 'csv' | 'txt' | 'log';
  size: string;
  downloadUrl?: string;
  previewContent?: string;
}

export interface EvaluationRun {
  id: string;
  name: string;
  status: EvaluationStatus;
  priority: EvaluationPriority;

  model: string;
  modelProvider: string;
  dataset: string;
  benchmark: string;
  benchmarkCategory: string;
  owner: string;

  progress: number;
  currentStage: string;
  worker: string;
  workerStatus: WorkerStatus;

  startedAt: string;
  completedAt?: string;
  durationMs?: number;
  estimatedDurationMs?: number;
  queuedAt: string;
  elapsedMs?: number;

  metrics?: EvaluationMetrics;
  stages: EvaluationStageRecord[];
  logs: string[];
  artifacts: EvaluationArtifact[];
  config: EvaluationConfig;
  reproducibility: EvaluationReproducibility;

  tags: string[];
  description?: string;
  error?: string;
  failureReason?: FailureReason;
  retryCount?: number;
}

export interface EvaluationReport {
  id: string;
  evaluationId: string;
  evaluationName: string;
  generatedAt: string;
  size: string;
  type: 'Full Report' | 'Summary' | 'Comparison' | 'Debug Log';
  format: 'pdf' | 'json' | 'csv';
  model: string;
  benchmark: string;
}

export interface EvaluationSparkPoint {
  time: string;
  value: number;
}
