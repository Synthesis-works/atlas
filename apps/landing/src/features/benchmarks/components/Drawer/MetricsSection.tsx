import React from 'react';
import type { Benchmark } from '@/domain/benchmarks/types';

interface Props {
  benchmark: Benchmark;
}

export const MetricsSection: React.FC<Props> = ({ benchmark }) => {
  return (
    <div className="space-y-3">
      <h4 className="text-xs font-semibold text-white">Evaluation Metrics Overview</h4>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
        {(benchmark.metrics || []).map((metric) => (
          <div
            key={metric.id}
            className="p-3 rounded-xl border border-white/5 bg-black/40 space-y-1 hover:border-white/10 transition-colors"
          >
            <div className="text-[10px] uppercase font-mono tracking-wider text-white/40 truncate">
              {metric.name}
            </div>
            <div className="text-base font-bold text-white font-mono flex items-baseline gap-1">
              {metric.value}
              {metric.unit && <span className="text-xs font-normal text-white/40">{metric.unit}</span>}
            </div>
            {metric.change && (
              <div className="text-[10px] font-mono text-emerald-400">{metric.change} vs baseline</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default MetricsSection;
