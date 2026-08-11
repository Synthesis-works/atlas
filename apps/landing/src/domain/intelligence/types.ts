export interface KPI {
  value: string | number;
  label: string;
  trend?: string;
  percentage?: string;
}

export interface Recommendation {
  priority: 1 | 2 | 3;
  text: string;
}

export interface Metadata {
  label: string;
  value: string;
}

export interface LegendItem {
  color: string;
  label: string;
  value: string | number;
  percentage?: string;
}

export interface AtlasInsight {
  id: string;
  title: string;
  description: string;
  priority: "critical" | "warning" | "healthy" | "info";
  confidence: number;
  source: "rule" | "computed" | "ai" | "manual";
  primaryKpi: KPI;
  secondaryKpi?: KPI;
  insight: string;
  recommendations: Recommendation[];
  metadata: Metadata[];
  legend?: LegendItem[];
}
