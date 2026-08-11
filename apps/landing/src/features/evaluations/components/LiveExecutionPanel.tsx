import React from 'react';
import type { EvaluationRun } from '@/domain/evaluations/types';
import { EVALUATION_STATUS_MAP } from '@/domain/evaluations/constants';

interface Props {
  activeEvaluations: EvaluationRun[];
  onSelect: (ev: EvaluationRun) => void;
}

export const LiveExecutionPanel: React.FC<Props> = ({ activeEvaluations, onSelect }) => {
  if (activeEvaluations.length === 0) {
    return (
      <div className="flex items-center justify-center h-32 border border-white/5 rounded-2xl bg-white/[0.02]">
        <span className="font-mono text-xs text-white/20">No active evaluations</span>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {activeEvaluations.map(ev => {
        const sc = EVALUATION_STATUS_MAP[ev.status];

        return (
          <div
            key={ev.id}
            onClick={() => onSelect(ev)}
            className="group relative p-4 rounded-2xl border border-white/5 bg-white/[0.02] hover:bg-white/[0.05] hover:border-white/10 cursor-pointer transition-all overflow-hidden"
          >
            {/* Animated shimmer on running */}
            {ev.status === 'Running' && (
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-emerald-500/[0.03] to-transparent translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-1000 pointer-events-none" />
            )}

            <div className="flex items-center gap-3">
              {/* Status dot */}
              <div className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${sc.dotClass}`} />

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono text-white/90 truncate">{ev.model}</span>
                  <span className="text-[10px] font-mono text-white/30">×</span>
                  <span className="text-[10px] font-mono text-white/50 truncate">{ev.benchmark}</span>
                </div>
                <div className="flex items-center gap-2 mt-0.5 text-[10px] font-mono text-white/30">
                  <span>{ev.currentStage}</span>
                  <span>·</span>
                  <span>{ev.worker}</span>
                </div>
              </div>

              <div className="text-right flex-shrink-0">
                <div className="text-xs font-mono font-bold text-white">{ev.progress}%</div>
                <div className="text-[10px] font-mono text-white/30">{ev.id}</div>
              </div>
            </div>

            {/* Progress track */}
            <div className="mt-3 h-1 rounded-full bg-white/5 overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-700"
                style={{ width: `${ev.progress}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default LiveExecutionPanel;
