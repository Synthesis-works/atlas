import type { Dataset, DatasetHealth, DatasetQuality } from '../domain/types';
import type { 
  DatasetCardModel, 
  DatasetRowModel, 
  DatasetPreviewModel, 
  DatasetComparisonModel 
} from '../types/catalog';

// Helper to format bytes
function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

// Helper to format large numbers (e.g. samples)
function formatNumber(num: number): string {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
  return num.toString();
}

// Helper to format dates
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

/**
 * Transforms raw domain entities into the DatasetCardModel used by Grid/Table.
 */
export function buildDatasetCard(
  dataset: Dataset,
  health?: DatasetHealth
): DatasetCardModel {
  const healthScore = health?.readinessScore ?? 0;
  
  return {
    id: dataset.id,
    name: dataset.name,
    thumbnailUrl: dataset.thumbnailUrl || '/assets/dataset-placeholder.jpg',
    status: dataset.status,
    type: dataset.type,
    // Mocking some missing fields on the raw entity that are required for UI
    owner: 'Platform Team', 
    version: 'v1.0',
    provider: 'Atlas',
    healthScore,
    healthLabel: getHealthLabel(healthScore),
    sizeFormatted: formatBytes(dataset.sizeBytes),
    samplesFormatted: formatNumber(dataset.samples),
    updatedAt: formatDate(dataset.updatedAt)
  };
}

export function buildDatasetRow(
  dataset: Dataset,
  health?: DatasetHealth
): DatasetRowModel {
  // Currently sharing the same shape as Card, but separated for future extensibility
  return buildDatasetCard(dataset, health);
}

export function buildDatasetPreview(
  dataset: Dataset,
  health?: DatasetHealth,
  quality?: DatasetQuality
): DatasetPreviewModel {
  const base = buildDatasetCard(dataset, health);
  
  return {
    ...base,
    description: dataset.description,
    createdAt: formatDate(dataset.createdAt),
    duplicateCount: quality?.duplicateCount ?? 0,
    classBalanceScore: quality?.classBalanceScore ?? 0,
    annotationCoverage: quality?.annotationCoverage ?? 0,
  };
}

export function buildDatasetComparison(
  dataset: Dataset,
  health?: DatasetHealth,
  quality?: DatasetQuality
): DatasetComparisonModel {
  return {
    id: dataset.id,
    name: dataset.name,
    thumbnailUrl: dataset.thumbnailUrl || '/assets/dataset-placeholder.jpg',
    sizeFormatted: formatBytes(dataset.sizeBytes),
    healthScore: health?.readinessScore ?? 0,
    annotationCoverage: quality?.annotationCoverage ?? 0,
    duplicateCount: quality?.duplicateCount ?? 0,
    samplesFormatted: formatNumber(dataset.samples),
    version: 'v1.0'
  };
}
