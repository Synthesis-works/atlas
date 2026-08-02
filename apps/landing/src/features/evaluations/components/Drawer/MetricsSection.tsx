import React from 'react';
import type { EvaluationRun } from '@/domain/evaluations/types';

interface Props { evaluation: EvaluationRun; }

export const MetricsSection: React.FC<Props> = ({ evaluation }) => {
  if (!evaluation.metrics) {
    return (
      <div className="p-8 text-center text-xs font-mono text-white/30">
        Metrics will appear after evaluation completes.
      </div>
    );
  }

  const m = evaluation.metrics;

  const cards = [
    { label: 'Overall Score', value: `${Math.round((m.overallScore ?? 0) * 100)}%`, color: 'text-emerald-400', accent: 'bg-emerald-500/10 border-emerald-500/20' },
    { label: 'Accuracy', value: `${Math.round((m.accuracy ?? 0) * 100)}%`, color: 'text-blue-400', accent: 'bg-blue-500/10 border-blue-500/20' },
    { label: 'Precision', value: `${Math.round((m.precision ?? 0) * 100)}%`, color: 'text-indigo-400', accent: 'bg-indigo-500/10 border-indigo-500/20' },
    { label: 'Recall', value: `${Math.round((m.recall ?? 0) * 100)}%`, color: 'text-purple-400', accent: 'bg-purple-500/10 border-purple-500/20' },
    { label: 'Truthfulness', value: `${Math.round((m.truthfulnessScore ?? 0) * 100)}%`, color: 'text-teal-400', accent: 'bg-teal-500/10 border-teal-500/20' },
    { label: 'Hallucination', value: `${(m.hallucinationRate ?? 0).toFixed(1)}%`, color: 'text-rose-400', accent: 'bg-rose-500/10 border-rose-500/20' },
    { label: 'Latency P50', value: `${m.latencyMs}ms`, color: 'text-amber-400', accent: 'bg-amber-500/10 border-amber-500/20' },
    { label: 'GPU Util.', value: `${m.gpuUtilPct}%`, color: 'text-cyan-400', accent: 'bg-cyan-500/10 border-cyan-500/20' },
    { label: 'Memory', value: `${m.memoryGb} GB`, color: 'text-violet-400', accent: 'bg-violet-500/10 border-violet-500/20' },
    { label: 'Inference Cost', value: `$${m.costUsd?.toFixed(2)}`, color: 'text-orange-400', accent: 'bg-orange-500/10 border-orange-500/20' },
  ];

  return (
    <div className="space-y-3">
      <h4 className="text-xs font-semibold text-white">Evaluation Metrics</h4>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
        {cards.map(card => (
          <div key={card.label} className={`p-3 rounded-xl border ${card.accent} space-y-1`}>
            <span className="text-[10px] font-mono uppercase tracking-wider text-white/40">{card.label}</span>
            <div className={`text-xl font-bold font-mono ${card.color}`}>{card.value}</div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default MetricsSection;
