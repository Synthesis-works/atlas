import React from 'react';
import type { EvaluationRun } from '@/domain/evaluations/types';

interface Props {
  evaluations: EvaluationRun[];
  onClose: () => void;
}

const METRICS = [
  { key: 'overallScore', label: 'Score', fmt: (v: number) => `${Math.round(v * 100)}%` },
  { key: 'accuracy', label: 'Accuracy', fmt: (v: number) => `${Math.round(v * 100)}%` },
  { key: 'precision', label: 'Precision', fmt: (v: number) => `${Math.round(v * 100)}%` },
  { key: 'recall', label: 'Recall', fmt: (v: number) => `${Math.round(v * 100)}%` },
  { key: 'latencyMs', label: 'Latency', fmt: (v: number) => `${v}ms` },
  { key: 'hallucinationRate', label: 'Hallucination', fmt: (v: number) => `${v.toFixed(1)}%` },
  { key: 'costUsd', label: 'Cost', fmt: (v: number) => `$${v.toFixed(2)}` },
  { key: 'gpuUtilPct', label: 'GPU Util', fmt: (v: number) => `${v}%` },
] as const;

type MetricKey = typeof METRICS[number]['key'];

function getVal(ev: EvaluationRun, key: MetricKey): number | undefined {
  return ev.metrics?.[key as keyof typeof ev.metrics] as number | undefined;
}

function best(evaluations: EvaluationRun[], key: MetricKey): number {
  const vals = evaluations.map(ev => getVal(ev, key) ?? 0);
  return key === 'latencyMs' || key === 'hallucinationRate' || key === 'costUsd'
    ? Math.min(...vals)
    : Math.max(...vals);
}

export const ComparisonView: React.FC<Props> = ({ evaluations, onClose }) => {
  const completed = evaluations.filter(e => e.metrics);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md">
      <div className="w-full max-w-5xl bg-ink-1 border border-white/10 rounded-2xl overflow-hidden shadow-2xl flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-white/5 shrink-0">
          <div>
            <h2 className="text-base font-bold text-white">Comparison View</h2>
            <p className="text-xs font-mono text-white/30 mt-0.5">
              Side-by-side evaluation metrics for {evaluations.length} runs
            </p>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg flex items-center justify-center border border-white/10 text-white/40 hover:text-white transition-colors"
          >
            ✕
          </button>
        </div>

        <div className="flex-1 overflow-auto p-6">
          {/* Overview row */}
          <div className="grid gap-4 mb-6" style={{ gridTemplateColumns: `160px repeat(${evaluations.length}, 1fr)` }}>
            <div />
            {evaluations.map(ev => (
              <div key={ev.id} className="p-4 rounded-xl border border-white/8 bg-white/[0.03] text-center">
                <div className="text-xs font-semibold text-white truncate">{ev.model}</div>
                <div className="text-[10px] font-mono text-white/40 mt-0.5">{ev.benchmark}</div>
                <div className={`text-[10px] font-mono mt-1 ${
                  ev.status === 'Completed' ? 'text-teal-400' :
                  ev.status === 'Failed' ? 'text-rose-400' : 'text-amber-400'
                }`}>
                  {ev.status}
                </div>
              </div>
            ))}
          </div>

          {/* Metrics comparison */}
          {completed.length > 0 && (
            <div className="space-y-2">
              {METRICS.map(metric => {
                const bestVal = best(completed, metric.key);
                return (
                  <div
                    key={metric.key}
                    className="grid gap-4 py-3 border-b border-white/[0.03] items-center"
                    style={{ gridTemplateColumns: `160px repeat(${evaluations.length}, 1fr)` }}
                  >
                    <span className="text-[10px] font-mono uppercase tracking-wider text-white/40">
                      {metric.label}
                    </span>
                    {evaluations.map(ev => {
                      const v = getVal(ev, metric.key);
                      const isBest = v !== undefined && v === bestVal;
                      return (
                        <div key={ev.id} className="text-center">
                          {v !== undefined ? (
                            <span className={`text-sm font-bold font-mono ${isBest ? 'text-emerald-400' : 'text-white/70'}`}>
                              {metric.fmt(v)}
                              {isBest && <span className="ml-1 text-[8px] text-emerald-400/70">BEST</span>}
                            </span>
                          ) : (
                            <span className="text-white/20 font-mono text-xs">—</span>
                          )}
                        </div>
                      );
                    })}
                  </div>
                );
              })}
            </div>
          )}

          {completed.length === 0 && (
            <div className="py-12 text-center text-xs font-mono text-white/30">
              Select completed evaluations to compare metrics.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ComparisonView;
