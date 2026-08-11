import type { ModelStatus, ModelModality, ModelCapabilityTag, HealthStatus, ModelLicense } from '../../../domain/models/types';

// ============================================================================
// PRESENTATION MODELS (UI purely consumes these, never raw entities)
// ============================================================================

export interface ModelCardModel {
  id: string;
  name: string;
  provider: string;
  status: ModelStatus;
  license: ModelLicense;
  overallScore: number;
  latencyMs: number;
  contextWindowFormatted: string;
  healthStatus: HealthStatus;
  healthLabel: string;
  modalities: ModelModality[];
  updatedAt: string; // Formatted date string
}

export interface ModelRowModel extends ModelCardModel {
  // Can extend if table needs specific row metrics
  parameterCount: string;
}

export interface ModelPreviewModel extends ModelCardModel {
  description: string;
  architecture: string;
  parameterCount: string;
  capabilityTags: ModelCapabilityTag[];
  availability: number;
  costEstimate: string;
}

export interface ModelComparisonModel {
  id: string;
  name: string;
  provider: string;
  overallScore: number;
  latencyMs: number;
  contextWindowFormatted: string;
  costEstimate: string;
  availability: number;
  parameterCount: string;
}

// ============================================================================
// STATE & CONFIG MODELS
// ============================================================================

export type ViewMode = 'grid' | 'table';

export interface FilterState {
  searchQuery: string;
  status: string[];
  provider: string[];
  modalities: string[];
  capabilities: string[];
  license: string[];
}

export interface SortState {
  field: 'name' | 'score' | 'latency' | 'context' | 'updated';
  direction: 'asc' | 'desc';
}

export interface PaginationState {
  page: number;
  pageSize: number; // 10, 25, 50, 100
  total: number;
}
