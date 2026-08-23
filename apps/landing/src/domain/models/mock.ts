/**
 * Domain — Models Marketing Showcase
 * Curated showcase entries for the public (unauthenticated) Research page only.
 * All authenticated catalog surfaces must use the real API via modelService.
 */

import type { RegistryModel, CapabilityDimension } from './types';

const base = (id: string, name: string, provider: string, capabilities: CapabilityDimension[]): RegistryModel => {
  const now = new Date().toISOString();
  return {
    id,
    name,
    provider,
    family: provider,
    version: id,
    description: `${name} via ${provider}`,
    architecture: '—',
    tokenizer: '—',
    parameterCount: '—',
    contextWindow: 0,
    modalities: ['text'],
    capabilityTags: ['Chat', 'Reasoning'],
    status: 'experimental',
    license: 'Proprietary',
    releaseDate: now.slice(0, 10),
    registeredAt: now,
    lastEvaluated: now,
    overallScore: 0,
    latencyMs: 0,
    evaluationCount: 0,
    profile: { modelId: id, profileVersion: '1.0', taxonomyVersion: '1.0', capabilities },
    health: { availability: 0, reliability: 0, errorRate: 0, responseQuality: 0, status: 'unknown', lastChecked: now },
    cost: { inputPer1kTokens: 0, outputPer1kTokens: 0, averageCostPerCall: 0, monthlyEstimate: 0, projectedMonthly: 0, currency: 'USD' },
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
};

export const AI_MODELS: RegistryModel[] = [
  base('gemini-3.5-flash-lite', 'Gemini 3.5 Flash Lite', 'gemini', [
    { domain: 'Reasoning', score: 92.4, label: 'Reasoning' },
    { domain: 'Code', score: 88.1, label: 'Code' },
    { domain: 'Chat', score: 94.7, label: 'Chat' },
    { domain: 'Vision', score: 90.2, label: 'Vision' },
  ]),
  base('gpt-4o', 'GPT-4o', 'openai', [
    { domain: 'Reasoning', score: 95.1, label: 'Reasoning' },
    { domain: 'Code', score: 91.8, label: 'Code' },
    { domain: 'Chat', score: 96.3, label: 'Chat' },
    { domain: 'Vision', score: 93.6, label: 'Vision' },
  ]),
  base('llama-3.3-70b-versatile', 'Llama 3.3 70b (Groq)', 'groq', [
    { domain: 'Reasoning', score: 89.6, label: 'Reasoning' },
    { domain: 'Code', score: 84.3, label: 'Code' },
    { domain: 'Chat', score: 91.2, label: 'Chat' },
    { domain: 'Vision', score: 72.8, label: 'Vision' },
  ]),
];