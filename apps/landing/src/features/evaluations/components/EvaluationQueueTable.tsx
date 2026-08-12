import React from 'react';
import type { EvaluationRun } from '@/domain/evaluations/types';
import { EVALUATION_STATUS_MAP } from '@/domain/evaluations/constants';
import { VerificationBadge } from '@/components/badge/VerificationBadge';


interface Props {
  evaluations: EvaluationRun[];
  selectedId?: string;
  compareIds: string[];
  onRowClick: (evaluation: EvaluationRun) => void;
  onToggleCompare: (id: string) => void;
}

export const EvaluationQueueTable: React.FC<Props> = ({
  evaluations,
  selectedId,
  compareIds,
  onRowClick,
  onToggleCompare,
}) => {
  if (evaluations.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-white/20">
        <span className="text-4xl mb-3">◎</span>
        <span className="font-mono text-sm">No evaluations match your filter.</span>
      </div>
    );
  }

  const formatDuration = (ms?: number) => {
    if (!ms) return '—';
    const m = Math.floor(ms / 60000);
    const s = Math.floor((ms % 60000) / 1000);
    return `${m}m ${s}s`;
  };

  return (
    <div className="overflow-auto">
      <table className="w-full text-xs font-mono border-collapse">
        <thead>
          <tr className="border-b border-white/5">
            <th className="w-8 py-2 px-3 text-left text-[10px] text-white/20 font-normal uppercase tracking-wider">★</th>
            <th className="py-2 px-3 text-left text-[10px] text-white/20 font-normal uppercase tracking-wider">Status</th>
            <th className="py-2 px-3 text-left text-[10px] text-white/20 font-normal uppercase tracking-wider min-w-[200px]">Evaluation</th>
            <th className="py-2 px-3 text-left text-[10px] text-white/20 font-normal uppercase tracking-wider">Model</th>
            <th className="py-2 px-3 text-left text-[10px] text-white/20 font-normal uppercase tracking-wider">Benchmark</th>
            <th className="py-2 px-3 text-left text-[10px] text-white/20 font-normal uppercase tracking-wider">Progress</th>
            <th className="py-2 px-3 text-left text-[10px] text-white/20 font-normal uppercase tracking-wider">Score</th>
            <th className="py-2 px-3 text-left text-[10px] text-white/20 font-normal uppercase tracking-wider">Duration</th>
            <th className="py-2 px-3 text-left text-[10px] text-white/20 font-normal uppercase tracking-wider">Owner</th>
            <th className="py-2 px-3 text-left text-[10px] text-white/20 font-normal uppercase tracking-wider">Worker</th>
          </tr>
        </thead>
        <tbody>
          {evaluations.map(ev => {
            const sc = EVALUATION_STATUS_MAP[ev.status];
            const isSelected = selectedId === ev.id;
            const inCompare = compareIds.includes(ev.id);

            return (
              <tr
                key={ev.id}
                onClick={() => onRowClick(ev)}
                className={`border-b border-white/[0.03] cursor-pointer transition-colors ${
                  isSelected
                    ? 'bg-blue-500/10'
                    : 'hover:bg-white/[0.03]'
                }`}
              >
                {/* Compare toggle */}
                <td className="py-3 px-3" onClick={e => { e.stopPropagation(); onToggleCompare(ev.id); }}>
                  <div className={`w-4 h-4 rounded border flex items-center justify-center text-[8px] cursor-pointer transition-colors ${
                    inCompare
                      ? 'border-blue-400 bg-blue-500/20 text-blue-400'
                      : 'border-white/10 text-white/20 hover:border-white/30'
                  }`}>
                    {inCompare ? '✓' : ''}
                  </div>
                </td>

                {/* Status */}
                <td className="py-3 px-3">
                  <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full border text-[10px] whitespace-nowrap ${sc.badgeClass}`}>
                    <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${sc.dotClass}`} />
                    {ev.status}
                  </span>
                </td>

                {/* Name */}

                <td className="py-3 px-3">
                  <div className="flex items-center gap-2">
                    <div className="text-white/90 truncate max-w-[200px]">{ev.name}</div>
                    <VerificationBadge isVerified={ev.isVerified} source={ev.source} />
                  </div>
                  <div className="text-[10px] text-white/30 mt-0.5">{ev.id}</div>
                </td>


                {/* Model */}
                <td className="py-3 px-3 text-white/70 whitespace-nowrap">
                  <div>{ev.model}</div>
                  <div className="text-[10px] text-white/30">{ev.modelProvider}</div>
                </td>

                {/* Benchmark */}
                <td className="py-3 px-3 text-white/70 whitespace-nowrap">
                  <div>{ev.benchmark}</div>
                  <div className="text-[10px] text-white/30">{ev.benchmarkCategory}</div>
                </td>

                {/* Progress */}
                <td className="py-3 px-3">
                  <div className="flex items-center gap-2">
                    <div className="w-20 h-1.5 rounded-full bg-white/10 overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${
                          ev.status === 'Failed' ? 'bg-rose-500' :
                          ev.status === 'Completed' ? 'bg-emerald-500' : 'bg-blue-500'
                        }`}
                        style={{ width: `${ev.progress}%` }}
                      />
                    </div>
                    <span className="text-white/40 text-[10px]">{ev.progress}%</span>
                  </div>
                </td>

                {/* Score */}
                <td className="py-3 px-3">
                  {ev.metrics ? (
                    <span className="text-emerald-400 font-bold">
                      {Math.round((ev.metrics.overallScore ?? 0) * 100)}%
                    </span>
                  ) : (
                    <span className="text-white/20">—</span>
                  )}
                </td>

                {/* Duration */}
                <td className="py-3 px-3 text-white/40 whitespace-nowrap">
                  {formatDuration(ev.durationMs)}
                </td>

                {/* Owner */}
                <td className="py-3 px-3 text-white/50">@{ev.owner}</td>

                {/* Worker */}
                <td className="py-3 px-3 text-white/30">{ev.worker}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

export default EvaluationQueueTable;
