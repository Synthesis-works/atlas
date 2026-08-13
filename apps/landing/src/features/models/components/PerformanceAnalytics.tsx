import { useState } from 'react';
import { useModelsStore } from '../store/modelsStore';
import { CapabilityRadar } from './CapabilityRadar';
import { AtlasLineChart } from '@/components/atlas/charts';

type Metric = 'benchmarkScore' | 'latencyMs' | 'costUsd' | 'hallucinationRate' | 'accuracy';
const METRICS: { key: Metric; label: string; color: string; unit: string }[] = [
  { key: 'benchmarkScore',  label: 'Benchmark Score', color: '#6366f1', unit: '' },
  { key: 'accuracy',        label: 'Accuracy',        color: '#22c55e', unit: '%' },
  { key: 'latencyMs',       label: 'Latency',         color: '#67e8f9', unit: 'ms' },
  { key: 'costUsd',         label: 'Cost',            color: '#fbbf24', unit: '$' },
  { key: 'hallucinationRate', label: 'Hallucination', color: '#f472b6', unit: '%' },
];

interface PerformanceLineChartProps {
  data: { date: string; value: number }[];
  label: string;
  unit: string;
}

function PerformanceLineChart({ data, label }: PerformanceLineChartProps) {
  return (
    <div className="liquid-glass-card rounded-xl p-4">
      <p className="text-xs text-white/30 mb-3">{label}</p>
      <div className="h-[160px] w-full">
        <AtlasLineChart data={data} dataKey="value" />
      </div>
    </div>
  );
}

export function PerformanceAnalytics() {
  const { models } = useModelsStore();
  const [activeMetric, setActiveMetric] = useState<Metric>('benchmarkScore');
  const top3 = models.slice(0, 3);

  // Build aggregated trend by averaging across all models
  const trend = models[0]?.performanceTrend.map((pt, i) => ({
    date: pt.date,
    value: models.slice(0, 5).reduce((s, m) => s + (m.performanceTrend[i]?.[activeMetric] ?? 0), 0) / 5,
  })) ?? [];

  const active = METRICS.find(m => m.key === activeMetric)!;

  return (
    <div className="liquid-glass-card rounded-2xl overflow-hidden h-full flex flex-col">
      <div className="px-4 py-3 border-b border-white/[0.05] flex items-center justify-between shrink-0">
        <span className="text-xs text-white/40 font-medium uppercase tracking-wider">Performance Analytics</span>
      </div>
      <div className="p-4 grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: trend chart */}
        <div>
          {/* Metric tabs */}
          <div className="flex gap-1.5 flex-wrap mb-4">
            {METRICS.map(m => (
              <button
                key={m.key}
                onClick={() => setActiveMetric(m.key)}
                className={`px-2.5 py-1 rounded-md text-xs transition-colors cursor-pointer ${
                  activeMetric === m.key
                    ? 'text-white bg-white/[0.08] border border-white/[0.12]'
                    : 'text-white/30 hover:text-white/60'
                }`}
              >
                {m.label}
              </button>
            ))}
          </div>
          <PerformanceLineChart data={trend} label={`${active.label} — Top 5 avg`} unit={active.unit} />
        </div>

        {/* Right: capability radar for top model */}
        <div>
          <p className="text-xs text-white/30 mb-3">Capability Radar — Top Models</p>
          <div className="flex flex-wrap items-center justify-center gap-6">
            {top3.map(m => (
              <div key={m.id} className="flex flex-col items-center gap-1">
                <CapabilityRadar model={m} size={250} showLabels={true} />
                <p className="text-xs text-white/40">{m.name}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
