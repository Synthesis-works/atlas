import { RadarChart } from "@/components/charts/radar-chart";
import { RadarGrid } from "@/components/charts/radar-grid";
import { RadarLabels } from "@/components/charts/radar-labels";
import { RadarArea } from "@/components/charts/radar-area";
import type { RadarData, RadarMetric as BklitRadarMetric } from "@/components/charts/radar-context";
import type { RadarSeries, RadarMetric, IntelligenceRadarSeries, ChartBaseProps } from '../models/chart-models';
import { cn } from "@/lib/utils";

export interface AtlasRadarChartProps extends ChartBaseProps {
  data: (RadarSeries | IntelligenceRadarSeries)[];
  metrics?: RadarMetric[];
  size?: number;
  levels?: number;
  showGridLabels?: boolean;
  showAxisLabels?: boolean;
  showPoints?: boolean;
}

/**
 * Adapter to convert Atlas domain models to the official Bklit format.
 */
function toBklitRadarData(data: (RadarSeries | IntelligenceRadarSeries)[], explicitMetrics?: RadarMetric[]): { bklitData: RadarData[], bklitMetrics: BklitRadarMetric[] } {
  const metricAxes = new Set<string>();
  data.forEach((series: any) => {
    if (series.data) {
      series.data.forEach((d: any) => metricAxes.add(d.axis));
    } else if (series.values) {
      Object.keys(series.values).forEach(axis => metricAxes.add(axis));
    }
  });
  
  const bklitMetrics: BklitRadarMetric[] = explicitMetrics ? explicitMetrics : Array.from(metricAxes).map(axis => ({
    key: axis,
    label: axis
  }));

  const bklitData: RadarData[] = data.map((series: any) => {
    const values: Record<string, number> = series.values ? { ...series.values } : {};
    if (series.data) {
      series.data.forEach((d: any) => { values[d.axis] = d.value; });
    }
    return {
      label: series.name || series.label || 'Series',
      values,
      ...(series.color ? { color: series.color } : {})
    };
  });

  return { bklitData, bklitMetrics };
}

export function AtlasRadarChart({
  data,
  metrics,
  size = 320,
  showAxisLabels = true,
  showPoints = true,
  loading,
  empty,
  error,
  onRetry,
  className
}: AtlasRadarChartProps) {

  if (loading) {
    return (
      <div className={cn("flex flex-col items-center justify-center space-y-2 opacity-50", className)}>
        <div className="text-xs text-white/50 font-mono">Loading chart...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={cn("h-[200px] flex flex-col items-center justify-center border border-red-500/20 rounded-xl bg-red-500/5", className)}>
        <span className="text-red-400 text-sm mb-2">{error}</span>
        {onRetry && <button onClick={onRetry} className="text-xs text-white/70 hover:text-white">Retry</button>}
      </div>
    );
  }

  if (empty || !data || data.length === 0) {
    return (
      <div className={cn("flex flex-col items-center justify-center space-y-2 opacity-50", className)}>
        <div className="text-xs text-white/50 font-mono">No data available</div>
      </div>
    );
  }

  const { bklitData, bklitMetrics } = toBklitRadarData(data, metrics);

  return (
    <div className={cn("flex flex-col w-full h-full min-h-[300px]", className)}>
      <RadarChart data={bklitData} metrics={bklitMetrics} size={size}>
        <RadarGrid />
        {showAxisLabels && <RadarLabels />}
        {bklitData.map((_, index) => (
          <RadarArea 
            key={index} 
            index={index}
            showPoints={showPoints}
          />
        ))}
      </RadarChart>
    </div>
  );
}
