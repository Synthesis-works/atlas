/**
 * Services — Model Registry Service
 * Fetches the real execution model registry from GET /api/v1/models and maps
 * backend provider/model entries into frontend domain models.
 */

import { apiClient } from '@/core/api/client';
import type { ServiceResult } from '@/core/types/service';
import type { RegistryModel, ModelCapabilityTag, ModelHealth, ModelCost, ModelModality } from '@/domain/models/types';

export interface BackendModelEntry {
  provider: string;
  model: string;
  display_name?: string;
  source?: string;
  available?: boolean;
  status?: string;
  capabilities?: string[];
}

const CAPABILITY_TAG_MAP: Record<string, ModelCapabilityTag> = {
  chat: 'Chat',
  reasoning: 'Reasoning',
  vision: 'Vision',
  code: 'Code',
  audio: 'Audio',
  embedding: 'Embedding',
  'function calling': 'Function Calling',
  'tool calling': 'Tool Calling',
  'long context': 'Long Context',
  multimodal: 'Multimodal',
};

function mapCapabilities(capabilities: string[] = []): ModelCapabilityTag[] {
  const tags = capabilities
    .map((c) => CAPABILITY_TAG_MAP[c.toLowerCase()])
    .filter((t): t is ModelCapabilityTag => Boolean(t));
  return tags.length > 0 ? tags : ['Chat'];
}

function mapModality(capabilities: string[] = []): ModelModality[] {
  if (capabilities.some((c) => c.toLowerCase() === 'vision')) return ['vision'];
  if (capabilities.some((c) => c.toLowerCase() === 'code')) return ['code'];
  if (capabilities.some((c) => c.toLowerCase() === 'audio')) return ['audio'];
  return ['text'];
}

function mapEntry(dto: BackendModelEntry): RegistryModel {
  const available = Boolean(dto.available);
  const capabilities = dto.capabilities || [];
  const now = new Date().toISOString();

  const health: ModelHealth = {
    availability: available ? 100 : 0,
    reliability: 0,
    errorRate: 0,
    responseQuality: 0,
    status: available ? 'healthy' : 'unknown',
    lastChecked: now,
  };

  const cost: ModelCost = {
    inputPer1kTokens: 0,
    outputPer1kTokens: 0,
    averageCostPerCall: 0,
    monthlyEstimate: 0,
    projectedMonthly: 0,
    currency: 'USD',
  };

  const displayName = dto.display_name || `${dto.provider}/${dto.model}`;
  const id = `${dto.provider}/${dto.model}`;

  return {
    id,
    name: displayName,
    provider: dto.provider,
    family: dto.provider,
    version: dto.model,
    description: `${displayName} via ${dto.provider}`,
    architecture: '—',
    tokenizer: '—',
    parameterCount: '—',
    contextWindow: 0,
    modalities: mapModality(capabilities),
    capabilityTags: mapCapabilities(capabilities),
    status: available ? 'active' : 'deprecated',
    license: 'Proprietary',
    releaseDate: now.slice(0, 10),
    registeredAt: now,
    lastEvaluated: now,
    overallScore: 0,
    latencyMs: 0,
    evaluationCount: 0,
    profile: { modelId: id, profileVersion: 'registry', taxonomyVersion: 'registry', capabilities: [] },
    health,
    cost,
    deployment: { status: 'none' },
    versions: [],
    benchmarkScores: [],
    evaluationHistory: [],
    performanceTrend: [],
    intelligenceCard: { strengths: [], weaknesses: [], bestUseCases: [], avoidFor: [] },
    defaultTemperature: 0.7,
    defaultTopP: 1,
    defaultMaxTokens: 4096,
  };
}

export async function getModels(): Promise<ServiceResult<RegistryModel[]>> {
  try {
    const raw = await apiClient.get<any>('/api/v1/models');
    let entries: BackendModelEntry[] = [];
    if (Array.isArray(raw)) {
      entries = raw;
    } else if (raw && raw.data && Array.isArray(raw.data)) {
      entries = raw.data;
    } else if (raw && Array.isArray(raw.items)) {
      entries = raw.items;
    }
    const models = entries.map(mapEntry);
    return { data: models, error: null };
  } catch (err: any) {
    return { data: [], error: err?.message || 'Failed to fetch models' };
  }
}