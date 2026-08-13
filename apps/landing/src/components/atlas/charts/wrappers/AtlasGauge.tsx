import React from 'react';
import { Gauge } from '@/components/charts/gauge';
import type { GaugeMetric, ChartBaseProps } from '../models/chart-models';

export interface AtlasGaugeProps extends ChartBaseProps {
  score: number;
  label: string;
  metric: GaugeMetric;
}

export const AtlasGauge: React.FC<AtlasGaugeProps> = ({ 
  score,
  label,
  metric,
  loading, 
  empty, 
  error, 
  onRetry,
  onSelectionChange 
}) => {
  if (loading) {
    return <div className="h-[200px] w-[200px] animate-pulse bg-white/5 rounded-full" />;
  }

  if (error) {
    return (
      <div className="h-[200px] flex flex-col items-center justify-center border border-red-500/20 rounded-xl bg-red-500/5">
        <span className="text-red-400 text-sm mb-2">{error}</span>
        {onRetry && <button onClick={onRetry} className="text-xs text-white/70 hover:text-white">Retry</button>}
      </div>
    );
  }

  if (empty) {
    return <div className="h-[200px] flex items-center justify-center text-white/40 text-sm border border-white/10 rounded-xl border-dashed">No analytics available</div>;
  }

  return (
    <div 
      className="flex justify-center cursor-pointer transition-transform hover:scale-105"
      onClick={() => onSelectionChange?.(metric.id)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onSelectionChange?.(metric.id)}
    >
      <Gauge 
        value={score} 
        centerValue={metric.value} 
        defaultLabel={label}
        inactiveFillOpacity={0.2}
        spacing={2}
      />
    </div>
  );
};
