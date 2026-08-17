import React from 'react';
import type { EvaluationRun } from '@/domain/evaluations/types';

interface Props { evaluation: EvaluationRun; }

function fmt(ms?: number) {
  if (!ms) return undefined;
  const m = Math.floor(ms / 60000);
  const s = Math.floor((ms % 60000) / 1000);
  return `${m}m ${s}s`;
}

export const TimelineSection: React.FC<Props> = ({ evaluation }) => {
  return (
    <div className="space-y-3">
      <h4 className="text-xs font-semibold text-white">Execution Timeline</h4>
      <div className="relative pl-6 space-y-0">
        {evaluation.stages.map((stage, i) => {
          const isLast = i === evaluation.stages.length - 1;
          const dotColor =
            stage.status === 'completed' ? 'bg-emerald-400'
            : stage.status === 'active' ? 'bg-blue-400 animate-pulse'
            : stage.status === 'failed' ? 'bg-rose-400'
            : stage.status === 'skipped' ? 'bg-white/20'
            : 'bg-white/10';

          const labelColor =
            stage.status === 'completed' ? 'text-white'
            : stage.status === 'active' ? 'text-blue-300'
            : stage.status === 'failed' ? 'text-rose-400'
            : 'text-white/30';

          return (
            <div key={stage.id} className="relative flex gap-4">
              {/* Track line */}
              {!isLast && (
                <div
                  className={`absolute left-[5px] top-4 w-0.5 h-full -translate-x-1/2 ${
                    stage.status === 'completed' ? 'bg-emerald-500/40' : 'bg-white/5'
                  }`}
                />
              )}
              {/* Dot */}
              <div className={`absolute left-0 top-1.5 w-3 h-3 rounded-full -translate-x-1/2 ring-2 ring-black/60 ${dotColor}`} />
              <div className="pb-6">
                <span className={`text-xs font-medium ${labelColor}`}>{stage.name}</span>
                <div className="flex gap-3 mt-0.5 text-[10px] font-mono text-white/30">
                  {stage.status === 'active' && <span className="text-blue-400 animate-pulse">In Progress</span>}
                  {stage.status === 'pending' && <span>Pending</span>}
                  {stage.status === 'failed' && <span className="text-rose-400">Failed</span>}
                  {fmt(stage.durationMs) && (
                    <span className="text-white/40">{fmt(stage.durationMs)}</span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default TimelineSection;
