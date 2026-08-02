import type { RegistryModel, ModelHealth, ModelCost } from '../../../domain/models/types';
import type { 
  ModelCardModel, 
  ModelRowModel, 
  ModelPreviewModel, 
  ModelComparisonModel 
} from '../types/catalog';

// Helper to format large numbers
function formatContextWindow(num: number): string {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
  if (num >= 1000) return (num / 1000).toFixed(0) + 'K';
  return num.toString();
}

function formatDate(isoString: string): string {
  return new Date(isoString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  });
}

function getHealthLabel(score: number): string {
  if (score >= 90) return 'Excellent';
  if (score >= 70) return 'Good';
  if (score >= 50) return 'Fair';
  return 'Poor';
}

export function buildModelCard(
  model: RegistryModel,
  health?: ModelHealth
): ModelCardModel {
  const healthScore = health?.responseQuality ?? model.health.responseQuality ?? 0;
  
  return {
    id: model.id,
    name: model.name,
    provider: model.provider,
    status: model.status,
    license: model.license,
    overallScore: model.overallScore,
    latencyMs: model.latencyMs,
    contextWindowFormatted: formatContextWindow(model.contextWindow),
    healthStatus: health?.status ?? model.health.status,
    healthLabel: getHealthLabel(healthScore),
    modalities: model.modalities,
    updatedAt: formatDate(model.lastEvaluated)
  };
}

export function buildModelRow(
  model: RegistryModel,
  health?: ModelHealth
): ModelRowModel {
  return {
    ...buildModelCard(model, health),
    parameterCount: model.parameterCount
  };
}

export function buildModelPreview(
  model: RegistryModel,
  health?: ModelHealth,
  cost?: ModelCost
): ModelPreviewModel {
  const base = buildModelCard(model, health);
  
  return {
    ...base,
    description: model.description,
    architecture: model.architecture,
    parameterCount: model.parameterCount,
    capabilityTags: model.capabilityTags,
    availability: health?.availability ?? model.health.availability ?? 0,
    costEstimate: cost ? `$${cost.averageCostPerCall}/call` : `$${model.cost.averageCostPerCall}/call`,
  };
}

export function buildModelComparison(
  model: RegistryModel,
  health?: ModelHealth,
  cost?: ModelCost
): ModelComparisonModel {
  return {
    id: model.id,
    name: model.name,
    provider: model.provider,
    overallScore: model.overallScore,
    latencyMs: model.latencyMs,
    contextWindowFormatted: formatContextWindow(model.contextWindow),
    costEstimate: cost ? `$${cost.averageCostPerCall}/call` : `$${model.cost.averageCostPerCall}/call`,
    availability: health?.availability ?? model.health.availability ?? 0,
    parameterCount: model.parameterCount
  };
}
