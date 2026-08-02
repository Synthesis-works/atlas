export type MockExperimentStatus = 'Queued' | 'Running' | 'Completed' | 'Failed' | 'Cancelled';

export interface MockExperimentStage {
  id: string;
  name: string;
  status: 'pending' | 'active' | 'completed' | 'failed' | 'skipped';
  startedAt?: string;
  completedAt?: string;
  durationMs?: number;
}

export interface MockExperimentLog {
  id: string;
  timestamp: string;
  stageId: string;
  level: 'info' | 'warn' | 'error' | 'debug';
  message: string;
}

export interface MockExperimentMetrics {
  accuracy?: number;
  latencyMs?: number;
  costUsd?: number;
  tokensPerSec?: number;
}

export interface MockExperimentConfig {
  model: string;
  provider: string;
  dataset: string;
  temperature: number;
}

export interface MockExperimentEntity {
  id: string;
  name: string;
  status: MockExperimentStatus;
  progressPercentage: number;
  currentStageIndex: number;
  totalStages: number;
  etaMs?: number;
  
  startedAt: string;
  completedAt?: string;
  queuedAt: string;
  durationMs?: number;

  owner: string;
  tags: string[];

  stages: MockExperimentStage[];
  logs: MockExperimentLog[];
  metrics: MockExperimentMetrics;
  config: MockExperimentConfig;
}

const NOW = new Date().getTime();

export const MOCK_EXPERIMENTS: MockExperimentEntity[] = [
  {
    id: 'exp-001',
    name: 'Production LLM Gateway Eval',
    status: 'Running',
    progressPercentage: 72,
    currentStageIndex: 4,
    totalStages: 8,
    etaMs: 72000,
    queuedAt: new Date(NOW - 600000).toISOString(),
    startedAt: new Date(NOW - 500000).toISOString(),
    owner: 'alice@atlas.com',
    tags: ['production', 'regression'],
    stages: [
      { id: 's1', name: 'Queued', status: 'completed', startedAt: new Date(NOW - 600000).toISOString(), completedAt: new Date(NOW - 500000).toISOString(), durationMs: 100000 },
      { id: 's2', name: 'Environment Ready', status: 'completed', startedAt: new Date(NOW - 500000).toISOString(), completedAt: new Date(NOW - 490000).toISOString(), durationMs: 10000 },
      { id: 's3', name: 'Dataset Loaded', status: 'completed', startedAt: new Date(NOW - 490000).toISOString(), completedAt: new Date(NOW - 450000).toISOString(), durationMs: 40000 },
      { id: 's4', name: 'Model Initialized', status: 'completed', startedAt: new Date(NOW - 450000).toISOString(), completedAt: new Date(NOW - 400000).toISOString(), durationMs: 50000 },
      { id: 's5', name: 'Prompt Executed', status: 'active', startedAt: new Date(NOW - 400000).toISOString() },
      { id: 's6', name: 'Evaluation Running', status: 'pending' },
      { id: 's7', name: 'Metrics Calculated', status: 'pending' },
      { id: 's8', name: 'Completed', status: 'pending' }
    ],
    logs: [
      { id: 'l1', timestamp: new Date(NOW - 600000).toISOString(), stageId: 's1', level: 'info', message: 'Experiment queued by alice@atlas.com' },
      { id: 'l2', timestamp: new Date(NOW - 500000).toISOString(), stageId: 's2', level: 'info', message: 'Allocated 4x A100 instances' },
      { id: 'l3', timestamp: new Date(NOW - 490000).toISOString(), stageId: 's3', level: 'info', message: 'Loaded dataset: GSM8K (8.5K records)' },
      { id: 'l4', timestamp: new Date(NOW - 450000).toISOString(), stageId: 's4', level: 'info', message: 'Initialized model: GPT-4-turbo' },
      { id: 'l5', timestamp: new Date(NOW - 400000).toISOString(), stageId: 's5', level: 'info', message: 'Starting batch inference (Batch size: 64)' },
      { id: 'l6', timestamp: new Date(NOW - 350000).toISOString(), stageId: 's5', level: 'debug', message: 'Processing batch 10/132' },
      { id: 'l7', timestamp: new Date(NOW - 300000).toISOString(), stageId: 's5', level: 'debug', message: 'Processing batch 20/132' }
    ],
    metrics: {},
    config: {
      model: 'GPT-4-turbo',
      provider: 'OpenAI',
      dataset: 'GSM8K',
      temperature: 0.2
    }
  },
  {
    id: 'exp-002',
    name: 'Llama 3 70B Quantization Test',
    status: 'Completed',
    progressPercentage: 100,
    currentStageIndex: 7,
    totalStages: 8,
    queuedAt: new Date(NOW - 3600000).toISOString(),
    startedAt: new Date(NOW - 3500000).toISOString(),
    completedAt: new Date(NOW - 3000000).toISOString(),
    durationMs: 500000,
    owner: 'bob@atlas.com',
    tags: ['research', 'llama3'],
    stages: [
      { id: 's1', name: 'Queued', status: 'completed', durationMs: 100000 },
      { id: 's2', name: 'Environment Ready', status: 'completed', durationMs: 15000 },
      { id: 's3', name: 'Dataset Loaded', status: 'completed', durationMs: 25000 },
      { id: 's4', name: 'Model Initialized', status: 'completed', durationMs: 45000 },
      { id: 's5', name: 'Prompt Executed', status: 'completed', durationMs: 200000 },
      { id: 's6', name: 'Evaluation Running', status: 'completed', durationMs: 100000 },
      { id: 's7', name: 'Metrics Calculated', status: 'completed', durationMs: 15000 },
      { id: 's8', name: 'Completed', status: 'completed', durationMs: 0 }
    ],
    logs: [
      { id: 'l1', timestamp: new Date(NOW - 3500000).toISOString(), stageId: 's2', level: 'info', message: 'Starting quantization (AWQ 4-bit)' },
      { id: 'l2', timestamp: new Date(NOW - 3300000).toISOString(), stageId: 's5', level: 'info', message: 'Inference completed successfully' },
      { id: 'l3', timestamp: new Date(NOW - 3000000).toISOString(), stageId: 's7', level: 'info', message: 'Final accuracy: 89.4%' }
    ],
    metrics: {
      accuracy: 89.4,
      latencyMs: 125,
      costUsd: 4.25,
      tokensPerSec: 45
    },
    config: {
      model: 'Llama-3-70b',
      provider: 'HuggingFace',
      dataset: 'MMLU',
      temperature: 0.0
    }
  },
  {
    id: 'exp-003',
    name: 'Nightly Baseline Run',
    status: 'Failed',
    progressPercentage: 45,
    currentStageIndex: 3,
    totalStages: 8,
    queuedAt: new Date(NOW - 7200000).toISOString(),
    startedAt: new Date(NOW - 7100000).toISOString(),
    completedAt: new Date(NOW - 7000000).toISOString(),
    durationMs: 100000,
    owner: 'system@atlas.com',
    tags: ['nightly', 'automated'],
    stages: [
      { id: 's1', name: 'Queued', status: 'completed', durationMs: 100000 },
      { id: 's2', name: 'Environment Ready', status: 'completed', durationMs: 10000 },
      { id: 's3', name: 'Dataset Loaded', status: 'completed', durationMs: 20000 },
      { id: 's4', name: 'Model Initialized', status: 'failed', durationMs: 70000 },
      { id: 's5', name: 'Prompt Executed', status: 'skipped' },
      { id: 's6', name: 'Evaluation Running', status: 'skipped' },
      { id: 's7', name: 'Metrics Calculated', status: 'skipped' },
      { id: 's8', name: 'Completed', status: 'skipped' }
    ],
    logs: [
      { id: 'l1', timestamp: new Date(NOW - 7050000).toISOString(), stageId: 's4', level: 'info', message: 'Attempting to load weights into VRAM' },
      { id: 'l2', timestamp: new Date(NOW - 7000000).toISOString(), stageId: 's4', level: 'error', message: 'CUDA OutOfMemoryError: Failed to allocate 12GB on device 0' }
    ],
    metrics: {},
    config: {
      model: 'Claude-3-Opus',
      provider: 'Anthropic',
      dataset: 'HumanEval',
      temperature: 0.7
    }
  },
  {
    id: 'exp-004',
    name: 'RAG Pipeline Tuning',
    status: 'Queued',
    progressPercentage: 0,
    currentStageIndex: 0,
    totalStages: 8,
    queuedAt: new Date(NOW - 5000).toISOString(),
    owner: 'charlie@atlas.com',
    tags: ['rag', 'tuning'],
    stages: [
      { id: 's1', name: 'Queued', status: 'active', startedAt: new Date(NOW - 5000).toISOString() },
      { id: 's2', name: 'Environment Ready', status: 'pending' },
      { id: 's3', name: 'Dataset Loaded', status: 'pending' },
      { id: 's4', name: 'Model Initialized', status: 'pending' },
      { id: 's5', name: 'Prompt Executed', status: 'pending' },
      { id: 's6', name: 'Evaluation Running', status: 'pending' },
      { id: 's7', name: 'Metrics Calculated', status: 'pending' },
      { id: 's8', name: 'Completed', status: 'pending' }
    ],
    logs: [
      { id: 'l1', timestamp: new Date(NOW - 5000).toISOString(), stageId: 's1', level: 'info', message: 'Experiment queued by charlie@atlas.com. Waiting for available workers.' }
    ],
    metrics: {},
    config: {
      model: 'Cohere-Command-R+',
      provider: 'Cohere',
      dataset: 'Custom-RAG-Eval-v2',
      temperature: 0.1
    }
  }
];
