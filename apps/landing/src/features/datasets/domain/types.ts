/**
 * Domain types for Datasets.
 * These are the pure domain entities.
 */

export type DatasetStatus = 'READY' | 'INDEXING' | 'ERROR' | 'ARCHIVED';

export interface Dataset {
  id: string;
  name: string;
  description: string;
  type: string;
  samples: number;
  sizeBytes: number;
  status: DatasetStatus;
  createdAt: string; // ISO8601
  updatedAt: string; // ISO8601
  thumbnailUrl?: string;
}

export interface DatasetHealth {
  datasetId: string;
  readinessScore: number; // 0-100
  issues: string[];
}

export interface DatasetStorage {
  datasetId: string;
  compressedSizeBytes: number;
  uncompressedSizeBytes: number;
}

export interface DatasetActivity {
  id: string;
  datasetId: string;
  action: string;
  timestamp: string; // ISO8601
  user: string;
}

export interface DatasetVersion {
  id: string;
  datasetId: string;
  version: string;
  createdAt: string;
}

export interface DatasetQuality {
  datasetId: string;
  annotationCoverage: number; // 0-100
  duplicateCount: number;
  classBalanceScore: number; // 0-100
}

/**
 * Presentation Models
 * These are strictly for the UI wrappers to consume.
 */
export interface HeroMetric {
  id: string;
  title: string;
  value: string;
  trend?: string;
  trendUp?: boolean;
  icon: string;
  description: string;
  status?: 'success' | 'warning' | 'error' | 'neutral';
}

export interface ChartPoint {
  x: string | number;
  y: number;
}

export interface LineSeries {
  id: string;
  name: string;
  data: ChartPoint[];
}

export interface PieSeries {
  id: string;
  label: string;
  value: number;
}

export interface RingMetric {
  id: string;
  label: string;
  value: number;
  color: string;
}

export interface RadarMetric {
  axis: string;
  value: number;
}

export interface RadarSeries {
  id: string;
  name: string;
  data: RadarMetric[];
}

export interface SunburstNode {
  name: string;
  value?: number;
  children?: SunburstNode[];
}
