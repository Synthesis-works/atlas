import React, { useState, memo } from 'react';
import { Terminal } from '@/shared/components';
import { Clock, AlertTriangle, Sparkles, Terminal as TerminalIcon, Activity, ListFilter } from 'lucide-react';
import { EvaluationQueue } from './EvaluationQueue';
import { EvaluationTimeline } from './EvaluationTimeline';
import type { EvaluationRun } from '@/domain/evaluations/types';
import { cn } from '@/lib/utils';

interface EvaluationConsoleProps {
  evaluations: EvaluationRun[];
  activeEvaluations: EvaluationRun[];
  selectedId?: string;
  compareIds: string[];
  timelineEval: EvaluationRun | null;
  runtimeLogs: string[];
  onRowClick: (ev: EvaluationRun) => void;
  onToggleCompare: (id: string) => void;
  onAction: (action: 'pause' | 'resume' | 'cancel' | 'duplicate', ev: EvaluationRun) => void;
}

export const EvaluationConsoleComponent: React.FC<EvaluationConsoleProps> = ({
  evaluations,
  activeEvaluations,
  selectedId,
  compareIds,
  timelineEval,
  runtimeLogs,
  onRowClick,
  onToggleCompare,
  onAction,
}) => {
  const [activeTab, setActiveTab] = useState<'queue' | 'timeline' | 'terminal' | 'diagnostics'>('queue');

  const failedRuns = evaluations.filter((e) => e.status === 'Failed');
  const completedRuns = evaluations.filter((e) => e.status === 'Completed');
  const successRate =
    completedRuns.length + failedRuns.length > 0
      ? Math.round((completedRuns.length / (completedRuns.length + failedRuns.length)) * 100)
      : null;

  return (
    <section className="liquid-glass-card rounded-2xl border border-accent/30 shadow-[0_0_40px_rgba(99,102,241,0.12)] overflow-hidden flex flex-col h-full space-y-0 relative" aria-label="Execution Control Center">
      <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-emerald-400 via-accent to-purple-500 opacity-80" />
      {/* Control Header Bar */}
      <div className="px-5 py-3.5 border-b border-white/10 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white/[0.02]">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 font-mono text-xs text-white/90 font-semibold">
            <Activity className="w-4 h-4 text-emerald-400" aria-hidden="true" />
            <span>Step 4: Execute — Operational Control Center</span>
          </div>
          <span className="text-white/20">•</span>
          <span className="text-xs font-mono text-white/40">Atlas Execution Engine v2.4</span>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center gap-1 p-1 bg-white/5 border border-white/5 rounded-xl" role="tablist" aria-label="Execution Controls">
          <button
            role="tab"
            aria-selected={activeTab === 'queue'}
            id="tab-eval-queue"
            aria-controls="panel-eval-queue"
            onClick={() => setActiveTab('queue')}
            className={cn(
              'px-3 py-1 rounded-lg text-xs font-mono transition-colors cursor-pointer flex items-center gap-1.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent',
              activeTab === 'queue'
                ? 'bg-white/10 text-white font-semibold border border-white/10'
                : 'text-white/40 hover:text-white/70'
            )}
          >
            <ListFilter className="w-3.5 h-3.5" aria-hidden="true" />
            <span>Queue ({evaluations.length})</span>
            {activeEvaluations.length > 0 && (
              <span className="px-1.5 py-0.2 rounded-full bg-emerald-400/20 text-emerald-300 text-[10px]">
                {activeEvaluations.length} live
              </span>
            )}
          </button>

          <button
            role="tab"
            aria-selected={activeTab === 'timeline'}
            id="tab-eval-timeline"
            aria-controls="panel-eval-timeline"
            onClick={() => setActiveTab('timeline')}
            className={cn(
              'px-3 py-1 rounded-lg text-xs font-mono transition-colors cursor-pointer flex items-center gap-1.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent',
              activeTab === 'timeline'
                ? 'bg-white/10 text-white font-semibold border border-white/10'
                : 'text-white/40 hover:text-white/70'
            )}
          >
            <Clock className="w-3.5 h-3.5" aria-hidden="true" />
            <span>Timeline</span>
          </button>

          <button
            role="tab"
            aria-selected={activeTab === 'terminal'}
            id="tab-eval-terminal"
            aria-controls="panel-eval-terminal"
            onClick={() => setActiveTab('terminal')}
            className={cn(
              'px-3 py-1 rounded-lg text-xs font-mono transition-colors cursor-pointer flex items-center gap-1.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent',
              activeTab === 'terminal'
                ? 'bg-white/10 text-white font-semibold border border-white/10'
                : 'text-white/40 hover:text-white/70'
            )}
          >
            <TerminalIcon className="w-3.5 h-3.5" aria-hidden="true" />
            <span>Live Logs ({runtimeLogs.length})</span>
          </button>

          <button
            role="tab"
            aria-selected={activeTab === 'diagnostics'}
            id="tab-eval-diagnostics"
            aria-controls="panel-eval-diagnostics"
            onClick={() => setActiveTab('diagnostics')}
            className={cn(
              'px-3 py-1 rounded-lg text-xs font-mono transition-colors cursor-pointer flex items-center gap-1.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent',
              activeTab === 'diagnostics'
                ? 'bg-purple-500/20 text-purple-200 font-semibold border border-purple-500/30'
                : 'text-purple-300/50 hover:text-purple-300'
            )}
          >
            <Sparkles className="w-3.5 h-3.5 text-purple-400" aria-hidden="true" />
            <span>AI Diagnostics</span>
          </button>
        </div>
      </div>

      {/* Control Panels */}
      <div className="p-4 h-[500px] flex flex-col min-h-0">
        {/* Queue & Timeline Side-by-Side Panel */}
        {activeTab === 'queue' && (
          <div role="tabpanel" id="panel-eval-queue" aria-labelledby="tab-eval-queue" className="grid grid-cols-1 xl:grid-cols-[1fr_360px] gap-6 items-stretch h-full">
            <div className="rounded-xl border border-white/5 bg-white/[0.01] overflow-hidden flex flex-col h-full min-h-0">
              <div className="flex items-center justify-between px-4 py-2.5 border-b border-white/5 shrink-0 bg-white/[0.02]">
                <span className="text-xs font-mono text-white/70 font-semibold">Active Execution Queue ({evaluations.length})</span>
                <span className="text-[10px] font-mono text-white/30">Click row to inspect timeline & details</span>
              </div>
              <div className="flex-1 overflow-y-auto min-h-0">
                <EvaluationQueue
                  evaluations={evaluations}
                  selectedId={selectedId}
                  compareIds={compareIds}
                  onRowClick={onRowClick}
                  onToggleCompare={onToggleCompare}
                  onAction={onAction}
                />
              </div>
            </div>

            {/* Side Timeline Inspector */}
            <div className="rounded-xl border border-white/5 bg-white/[0.01] overflow-hidden flex flex-col h-full min-h-0">
              <div className="flex items-center justify-between px-4 py-2.5 border-b border-white/5 shrink-0 bg-white/[0.02]">
                <span className="text-xs font-mono text-white/70 font-semibold">Stage Inspector</span>
                <span className="text-[10px] font-mono text-accent">
                  {timelineEval ? timelineEval.name : 'No run selected'}
                </span>
              </div>
              <div className="p-4 overflow-y-auto flex-1 min-h-0">
                <EvaluationTimeline evaluation={timelineEval} />
              </div>
            </div>
          </div>
        )}

        {/* Timeline Dedicated Tab */}
        {activeTab === 'timeline' && (
          <div role="tabpanel" id="panel-eval-timeline" aria-labelledby="tab-eval-timeline" className="p-4 rounded-xl border border-white/5 bg-white/[0.01] h-full overflow-y-auto">
            <div className="text-xs font-mono text-white/40 mb-3 uppercase tracking-wider">
              Pipeline Stage Breakdown — {timelineEval ? timelineEval.name : 'Select a run from queue'}
            </div>
            <EvaluationTimeline evaluation={timelineEval} />
          </div>
        )}

        {/* Terminal Live Telemetry */}
        {activeTab === 'terminal' && (
          <div role="tabpanel" id="panel-eval-terminal" aria-labelledby="tab-eval-terminal" className="h-full flex flex-col justify-between">
            <Terminal title="Atlas Execution Telemetry — Live Stream" logs={runtimeLogs} />
          </div>
        )}

        {/* AI Anomaly Diagnostics */}
        {activeTab === 'diagnostics' && (
          <div role="tabpanel" id="panel-eval-diagnostics" aria-labelledby="tab-eval-diagnostics" className="p-5 rounded-xl border border-purple-500/20 bg-purple-950/20 space-y-4 font-mono text-xs">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-purple-300">
                <AlertTriangle className="w-4 h-4 text-amber-400" aria-hidden="true" />
                <span className="font-semibold text-sm">Evaluation Execution Diagnostics</span>
              </div>
              <span className="text-[10px] px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">
                {failedRuns.length > 0 ? `${failedRuns.length} failed` : 'No anomalies'}
              </span>
            </div>

            {failedRuns.length === 0 ? (
              <p className="text-white/70 text-xs leading-relaxed">
                No failed executions detected. {completedRuns.length} completed, {activeEvaluations.length} active,{' '}
                {successRate !== null ? `${successRate}% success rate` : 'no completed runs yet'}.
              </p>
            ) : (
              <>
                <p className="text-white/70 text-xs leading-relaxed">
                  {failedRuns.length} execution{failedRuns.length !== 1 ? 's' : ''} did not complete. Review the
                  failed runs below and the queue table for error context.
                </p>
                <div className="space-y-1.5">
                  {failedRuns.slice(0, 10).map((run) => (
                    <div
                      key={run.id}
                      className="flex items-center justify-between gap-3 p-2.5 rounded-lg border border-rose-500/20 bg-rose-500/5"
                    >
                      <div className="min-w-0">
                        <div className="text-white/80 truncate">{run.name}</div>
                        <div className="text-[10px] text-white/40 font-mono truncate">{run.model} · {run.benchmark}</div>
                      </div>
                      <span className="text-[10px] font-mono text-rose-400 shrink-0">Failed</span>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </section>
  );
};

export const EvaluationConsole = memo(EvaluationConsoleComponent);
export default EvaluationConsole;
