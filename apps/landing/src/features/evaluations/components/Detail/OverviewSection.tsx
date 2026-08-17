import React from 'react';
import type { EvaluationRun } from '@/domain/evaluations/types';
import { StatusBadge } from '@/shared/components';

interface Props { evaluation: EvaluationRun; }

function fmt(ms?: number) {
  if (!ms) return '—';
  const m = Math.floor(ms / 60000);
  const s = Math.floor((ms % 60000) / 1000);
  return `${m}m ${s}s`;
}

export const OverviewSection: React.FC<Props> = ({ evaluation }) => {
  const rows: { label: string; value: React.ReactNode }[] = [
    { label: 'Run ID', value: <span className="font-mono text-white/60">{evaluation.id}</span> },
    { label: 'Status', value: <StatusBadge status={evaluation.status} /> },
    { label: 'Model', value: <span className="font-semibold text-white">{evaluation.model}</span> },
    { label: 'Provider', value: evaluation.modelProvider },
    { label: 'Benchmark', value: evaluation.benchmark },
    { label: 'Dataset', value: evaluation.dataset },
    { label: 'Owner', value: <span className="font-mono">@{evaluation.owner}</span> },
    { label: 'Worker', value: <span className="font-mono">{evaluation.worker}</span> },
    { label: 'Priority', value: evaluation.priority },
    { label: 'Started', value: new Date(evaluation.startedAt).toLocaleString() },
    { label: 'Completed', value: evaluation.completedAt ? new Date(evaluation.completedAt).toLocaleString() : '—' },
    { label: 'Duration', value: fmt(evaluation.durationMs) },
    { label: 'ETA', value: fmt(evaluation.estimatedDurationMs) },
    { label: 'Progress', value: `${evaluation.progress}%` },
  ];

  return (
    <div className="space-y-3">
      <h4 className="text-xs font-semibold text-white">Evaluation Overview</h4>
      {evaluation.description && (
        <p className="text-xs text-white/40 leading-relaxed">{evaluation.description}</p>
      )}
      <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-xs font-mono p-4 rounded-xl border border-white/5 bg-black/40">
        {rows.map(row => (
          <div key={row.label} className="contents">
            <span className="text-white/40">{row.label}</span>
            <span className="text-white/80">{row.value}</span>
          </div>
        ))}
      </div>
      {evaluation.error && (
        <div className="p-3 rounded-xl border border-rose-500/20 bg-rose-500/5 text-xs font-mono text-rose-400">
          <span className="font-bold">Error: </span>{evaluation.error}
        </div>
      )}
      {evaluation.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5 pt-1">
          {evaluation.tags.map(tag => (
            <span key={tag} className="px-2 py-0.5 rounded bg-white/5 border border-white/5 text-[10px] font-mono text-white/50">
              {tag}
            </span>
          ))}
        </div>
      )}
    </div>
  );
};

export default OverviewSection;
