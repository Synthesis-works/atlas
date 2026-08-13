/**
 * Domain — Benchmarks Adapters
 * Transformation functions for API and raw payloads.
 */

import type { Benchmark } from './types';

export function normalizeBenchmarkPayload(raw: any): Benchmark {
  return {
    id: raw.id || `bm-${Date.now()}`,
    name: raw.name || 'Untitled Benchmark',
    description: raw.description || '',
    category: raw.category || 'reasoning',
    difficulty: raw.difficulty || 'intermediate',
    status: raw.status || 'Ready',
    version: raw.version || '1.0.0',
    tasksCount: Number(raw.tasksCount || raw.tasks || 0),
    samplesCount: Number(raw.samplesCount || raw.samples || 0),
    estimatedRuntime: raw.estimatedRuntime || '~5 min',
    license: raw.license || 'MIT',
    author: raw.author || 'Atlas Community',
    verificationScore: Number(raw.verificationScore || 100),
    verification: raw.verification || {
      datasetLicense: true,
      metadata: true,
      promptSchema: true,
      outputSchema: true,
      referenceAnswers: true,
      evaluationScript: true,
      metricDefinitions: true,
      documentation: true,
      reproducibility: true,
    },
    tags: Array.isArray(raw.tags) ? raw.tags : [],
    metrics: Array.isArray(raw.metrics) ? raw.metrics : [],
    compatibleModels: Array.isArray(raw.compatibleModels) ? raw.compatibleModels : [],
    details: raw.details || '',
    methodology: Array.isArray(raw.methodology) ? raw.methodology : [],
    datasetSamples: Array.isArray(raw.datasetSamples) ? raw.datasetSamples : [],
    versionsHistory: Array.isArray(raw.versionsHistory) ? raw.versionsHistory : [],
    artifacts: Array.isArray(raw.artifacts) ? raw.artifacts : [],
    relatedIds: Array.isArray(raw.relatedIds) ? raw.relatedIds : [],
    updatedAt: raw.updatedAt || 'Just now',
  };
}
