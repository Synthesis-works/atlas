import React from 'react';
import { AtlasPieChart } from './AtlasPieChart';
import type { RingSeries, ChartBaseProps } from '../models/chart-models';

export interface AtlasRingChartProps extends ChartBaseProps {
  series: RingSeries[];
  centerLabel?: string;
}

export const AtlasRingChart: React.FC<AtlasRingChartProps> = ({
  series,
  loading,
  error,
  onRetry,
  onSelectionChange,
  centerLabel
}) => {
  // We reuse our PieChart wrapper but enforce an innerRadius to create a Ring.
  
  if (error) {
    return (
      <div className="h-[200px] flex flex-col items-center justify-center border border-red-500/20 rounded-xl bg-red-500/5">
        <span className="text-red-400 text-sm mb-2">{error}</span>
        {onRetry && <button onClick={onRetry} className="text-xs text-white/70 hover:text-white">Retry</button>}
      </div>
    );
  }

  return (
    <div onClick={() => onSelectionChange?.(series[0]?.id ?? null)}>
      <AtlasPieChart 
        data={series} 
        innerRadius={60} 
        loading={loading}
        emptyMessage="No data available" 
        centerLabel={centerLabel}
      />
    </div>
  );
};
