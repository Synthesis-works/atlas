import type { DatasetStatus } from '../domain/types';

// ============================================================================
// PRESENTATION MODELS (UI purely consumes these, never raw entities)
// ============================================================================

export interface DatasetCardModel {
  id: string;
  name: string;
  thumbnailUrl: string;
  status: DatasetStatus;
  type: string;
  owner: string;
  version: string;
  healthScore: number;
  healthLabel: string;
  sizeFormatted: string;
  samplesFormatted: string;
  provider: string;
  updatedAt: string; // Formatted date string
}

export interface DatasetRowModel extends DatasetCardModel {
  // Can extend if table needs specific row metrics
}

export interface DatasetPreviewModel extends DatasetCardModel {
  description: string;
  createdAt: string; // Formatted date string
  duplicateCount: number;
  classBalanceScore: number;
  annotationCoverage: number;
}

export interface DatasetComparisonModel {
  id: string;
  name: string;
  thumbnailUrl: string;
  sizeFormatted: string;
  healthScore: number;
  annotationCoverage: number;
  duplicateCount: number;
  samplesFormatted: string;
  version: string;
}

// ============================================================================
// STATE & CONFIG MODELS
// ============================================================================

export type ViewMode = 'grid' | 'table';

export interface FilterState {
  searchQuery: string;
  status: string[];
  provider: string[];
  type: string[];
  owner: string[];
  tags: string[];
}

export interface SortState {
  field: 'name' | 'updated' | 'storage' | 'samples' | 'health';
  direction: 'asc' | 'desc';
}

export interface PaginationState {
  page: number;
  pageSize: number; // 10, 25, 50, 100
  total: number;
}
