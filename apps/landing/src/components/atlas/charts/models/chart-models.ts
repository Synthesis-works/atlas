/**
 * Chart Presentation Models
 * Defines the strict presentation layer contracts for all Atlas Charts.
 */

export interface ChartBaseProps {
  loading?: boolean;
  empty?: boolean;
  error?: string;
  onRetry?: () => void;
  title?: string;
  description?: string;
  className?: string;
  onSelectionChange?: (selectedId: string | null) => void;
}

export interface InsightPresentationModel {
  title: string;
  description: string;
  primaryKpi: { value: string | number; label: string; trend?: string; percentage?: string };
  secondaryKpi?: { value: string | number; label: string; trend?: string; percentage?: string };
  insight: string;
  action: string;
  metadata: { label: string; value: string }[];
  legend?: { color: string; label: string; value: string | number; percentage?: string }[];
}

export interface GaugeMetric {
  id: string;
  value: number; // 0-100
  label: string;
}

export interface ChartPoint {
  x?: string | number;
  y?: number;
  date?: string | number;
  [key: string]: any;
}

export interface LineSeries {
  id: string;
  name: string;
  data?: ChartPoint[];
  color?: string;
}

export interface PieSeries {
  id?: string;
  label: string;
  value: number;
  color?: string;
}

export interface RingSeries {
  id?: string;
  label: string;
  value: number;
  color?: string;
}

export interface RadarSeries {
  label: string;
  values: Record<string, number>;
  color?: string;
}

export interface RadarMetric {
  key: string;
  label: string;
}

export interface IntelligenceRadarMetric {
  axis: string;
  value: number;
}

export interface IntelligenceRadarSeries {
  id: string;
  name: string;
  data: IntelligenceRadarMetric[];
  color?: string;
}

export interface SunburstTree {
  name: string;
  value?: number;
  type?: 'dataset' | 'model' | 'benchmark' | 'evaluation' | 'experiment';
  id?: string;
  children?: SunburstTree[];
}

export type ChartPresentationModel =
  | GaugeMetric
  | LineSeries[]
  | PieSeries[]
  | RingSeries[]
  | RadarSeries[]
  | SunburstTree;
