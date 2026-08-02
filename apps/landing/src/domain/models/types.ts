/**
 * Domain — Models Registry
 * Full type system for the Atlas Model Registry.
 */

/* ----------------------------------------------------------------------- */
/*  Enums & Union Types                                                      */
/* ----------------------------------------------------------------------- */

export type ModelStatus = 'active' | 'deprecated' | 'archived' | 'experimental' | 'beta';
export type ModelLicense = 'Apache-2.0' | 'MIT' | 'CC-BY' | 'Proprietary' | 'Llama' | 'Gemma' | 'GPT-4' | 'Custom';
export type ModelModality = 'text' | 'vision' | 'audio' | 'video' | 'code' | 'embedding';
export type DeploymentStatus = 'deployed' | 'stopped' | 'deploying' | 'error' | 'none';
export type HealthStatus = 'healthy' | 'degraded' | 'down' | 'unknown';

export type ModelCapabilityTag =
  | 'Chat'
  | 'Reasoning'
  | 'Vision'
  | 'Audio'
  | 'Tool Calling'
  | 'Embedding'
  | 'Code'
  | 'OCR'
  | 'Function Calling'
  | 'Long Context'
  | 'Streaming'
  | 'Fine-tunable'
  | 'Multimodal'
  | 'Agents';

/* ----------------------------------------------------------------------- */
/*  Sub-structures                                                           */
/* ----------------------------------------------------------------------- */

export interface CapabilityDimension {
  domain: string;
  score: number; // 0–100
  label: string;
}

export interface CapabilityProfile {
  modelId: string;
  profileVersion: string;
  taxonomyVersion: string;
  capabilities: CapabilityDimension[];
}

export interface ModelHealth {
  availability: number;   // 0–100
  reliability: number;    // 0–100
  errorRate: number;      // 0–100 (lower is better)
  responseQuality: number; // 0–100
  status: HealthStatus;
  lastChecked: string;
}

export interface ModelCost {
  inputPer1kTokens: number;   // USD
  outputPer1kTokens: number;  // USD
  averageCostPerCall: number;  // USD
  monthlyEstimate: number;     // USD
  projectedMonthly: number;    // USD
  currency: 'USD';
}

export interface ModelDeployment {
  status: DeploymentStatus;
  endpoint?: string;
  region?: string;
  runtime?: string;
  gpu?: string;
  provider?: string;
  deployedAt?: string;
  replicas?: number;
}

export interface ModelVersion {
  version: string;
  name: string;
  releaseDate: string;
  changes: string;
  isLatest?: boolean;
  isCurrent?: boolean;
}

export interface BenchmarkScore {
  benchmarkId: string;
  benchmarkName: string;
  category: string;
  score: number;       // 0–100
  percentile: number;  // rank percentile
  evaluatedAt: string;
  runId: string;
}

export interface EvaluationHistoryItem {
  id: string;
  benchmarkName: string;
  score: number;
  status: 'completed' | 'failed';
  runAt: string;
  duration: string;
}

export interface ModelIntelligenceCard {
  strengths: string[];
  weaknesses: string[];
  bestUseCases: string[];
  avoidFor: string[];
}

export interface PerformanceTrendPoint {
  date: string;
  accuracy: number;
  latencyMs: number;
  costUsd: number;
  hallucinationRate: number;
  benchmarkScore: number;
}

/* ----------------------------------------------------------------------- */
/*  Core Model Entity                                                        */
/* ----------------------------------------------------------------------- */

export interface RegistryModel {
  id: string;
  name: string;
  provider: string;
  family: string;
  version: string;
  description: string;
  architecture: string;
  tokenizer: string;
  parameterCount: string;
  contextWindow: number;      // tokens
  modalities: ModelModality[];
  capabilityTags: ModelCapabilityTag[];
  status: ModelStatus;
  license: ModelLicense;
  releaseDate: string;
  registeredAt: string;
  lastEvaluated: string;

  // Scores
  overallScore: number;       // 0–100 composite
  latencyMs: number;
  evaluationCount: number;

  // Sub-structures
  profile: CapabilityProfile;
  health: ModelHealth;
  cost: ModelCost;
  deployment: ModelDeployment;
  versions: ModelVersion[];
  benchmarkScores: BenchmarkScore[];
  evaluationHistory: EvaluationHistoryItem[];
  performanceTrend: PerformanceTrendPoint[];
  intelligenceCard: ModelIntelligenceCard;

  // Config
  defaultTemperature: number;
  defaultTopP: number;
  defaultMaxTokens: number;
}

/* ----------------------------------------------------------------------- */
/*  Legacy re-export — keeps old `import { AI_MODELS } from '@/domain/models/types'` working */
/* ----------------------------------------------------------------------- */
export { AI_MODELS } from './mock';
