/**
 * Atlas Visualization System — Type Definitions
 * Shared primitives for data points, series, tooltips, legends, and interaction handlers.
 */

export interface ChartMargin {
  top?: number;
  right?: number;
  bottom?: number;
  left?: number;
}

export interface ChartDataPoint {
  label: string;
  value: number;
  secondaryValue?: number;
  color?: string;
  date?: Date | string;
  [key: string]: any;
}

export interface Series {
  key: string;
  name: string;
  color: string;
  strokeWidth?: number;
}

export interface LegendItem {
  label: string;
  value: number | string;
  color: string;
  percentage?: number;
}

export interface TooltipData {
  title?: string;
  items: { label: string; value: string | number; color?: string }[];
  x?: number;
  y?: number;
}

export interface ChartEvents {
  onHover?: (item: ChartDataPoint | null, index: number | null) => void;
  onSelect?: (item: ChartDataPoint, index: number) => void;
  onZoom?: (level: number) => void;
  onDrillDown?: (node: any) => void;
  onExport?: (format: 'csv' | 'json') => void;
}

export type ChartState = 'loading' | 'empty' | 'ready' | 'error';
