import React from 'react';
import type { EvaluationRun } from '@/domain/evaluations/types';
import { STAGE_PIPELINE } from '@/domain/evaluations/constants';

interface Props {
  evaluation: EvaluationRun | null;
}

function fmtDuration(ms?: number) {
  if (!ms) return undefined;
  const m = Math.floor(ms / 60000);
  const s = Math.floor((ms % 60000) / 1000);
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

function stageStatusForPipeline(
  pipelineName: string,
  ev: EvaluationRun
): 'completed' | 'active' | 'pending' | 'failed' {
  // Map pipeline stage names to eval stages by name similarity
  const stageMap: Record<string, string[]> = {
    'Queued': ['Queued'],
    'Downloading Dataset': ['Downloading Dataset'],
    'Preparing Runtime': ['Preparing Runtime'],
    'Loading Model': ['Loading Model'],
    'Running Tests': ['Running Tests'],
    'Scoring': ['Scoring'],
    'Aggregating': ['Aggregating'],
    'Generating Report': ['Generating Report'],
    'Completed': ['Completed'],
  };
  const names = stageMap[pipelineName] ?? [];
  const stages = ev.stages || [];
  const stage = stages.find(s => names.some(n => s.name?.includes(n.split(' ')[0])));
  if (!stage) {
    // Infer from overall status
    if (pipelineName === 'Completed' && ev.status === 'Completed') return 'completed';
    return 'pending';
  }
  return stage.status === 'active' ? 'active' : stage.status === 'completed' ? 'completed' : stage.status === 'failed' ? 'failed' : 'pending';
}

export const EvaluationTimeline: React.FC<Props> = ({ evaluation }) => {
  if (!evaluation) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-white/20 space-y-2">
        <span className="text-3xl">◎</span>
        <span className="text-xs font-mono">Select an evaluation to see its timeline</span>
      </div>
    );
  }

  const stages = evaluation.stages || [];

  return (
    <div className="space-y-3">
      {/* Eval title & rich operational telemetry inspector */}
      <div className="p-3 rounded-xl border border-white/10 bg-white/[0.02] space-y-2">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <div className="text-xs font-semibold text-white truncate">{evaluation.name}</div>
            <div className="text-[10px] font-mono text-white/40 mt-0.5">{evaluation.id}</div>
          </div>
          <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold shrink-0 ${
            evaluation.status === 'Completed' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
            evaluation.status === 'Running' ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20' :
            evaluation.status === 'Failed' ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' :
            'bg-amber-500/10 text-amber-400 border border-amber-500/20'
          }`}>
            {evaluation.status}
          </span>
        </div>
        <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[10px] font-mono border-t border-white/5 pt-2 text-white/60">
          <div className="truncate"><span className="text-white/30">Model:</span> {evaluation.model}</div>
          <div className="truncate"><span className="text-white/30">Bench:</span> {evaluation.benchmark}</div>
          <div className="truncate"><span className="text-white/30">Dataset:</span> {evaluation.dataset}</div>
          <div className="truncate"><span className="text-white/30">Worker:</span> {evaluation.worker}</div>
          <div className="truncate"><span className="text-white/30">Owner:</span> @{evaluation.owner}</div>
          <div className="truncate"><span className="text-white/30">Progress:</span> {evaluation.progress}%</div>
        </div>
      </div>

      {/* Pipeline */}
      <div className="relative pl-5">
        {/* Track */}
        <div className="absolute left-2 top-0 bottom-0 w-px bg-white/8" />

        {STAGE_PIPELINE.map((pStage, idx) => {
          const isLast = idx === STAGE_PIPELINE.length - 1;
          const status = stageStatusForPipeline(pStage.name, evaluation);
          const evStage = stages.find(s => s.name?.includes(pStage.name.split(' ')[0]));

          const dotColor =
            status === 'completed' ? 'bg-emerald-400 ring-emerald-400/20'
            : status === 'active' ? 'bg-blue-400 ring-blue-400/30 animate-pulse'
            : status === 'failed' ? 'bg-rose-400 ring-rose-400/20'
            : 'bg-white/10 ring-white/5';

          const labelColor =
            status === 'completed' ? 'text-white'
            : status === 'active' ? 'text-blue-300'
            : status === 'failed' ? 'text-rose-400'
            : 'text-white/25';

          const dockerImg = evaluation.reproducibility?.dockerImage ?? 'atlas-runner:v1';
          const stageDetailMap: Record<string, string> = {
            'Queued': `worker: ${evaluation.worker ?? 'node-01'} · prio: ${evaluation.priority ?? 'normal'}`,
            'Downloading Dataset': `16,000 samples indexed`,
            'Preparing Runtime': `container: ${dockerImg}`,
            'Loading Model': `vRAM: ${evaluation.metrics?.memoryGb ?? 18} GB · GPU util: ${evaluation.metrics?.gpuUtilPct ?? 72}%`,
            'Running Tests': `throughput: ${evaluation.metrics?.tokensPerSec ?? 65} tok/s`,
            'Scoring': evaluation.metrics ? `pass@1: ${Math.round((evaluation.metrics.passAt1 ?? 0.88) * 100)}%` : 'computing score',
            'Aggregating': `metrics aggregated`,
            'Generating Report': `report.pdf generated`,
          };
          const stageDetail = stageDetailMap[pStage.name] ?? '';

          return (
            <div key={pStage.id} className={`relative flex gap-3 ${isLast ? '' : 'pb-4'}`}>
              {/* Dot */}
              <div className={`absolute left-[-13px] top-1.5 w-3 h-3 rounded-full ring-2 ring-black/80 ${dotColor}`} />

              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="text-white/20 text-xs select-none shrink-0">{pStage.icon}</span>
                    <span className={`text-xs font-medium truncate ${labelColor}`}>{pStage.name}</span>
                  </div>
                  {evStage?.durationMs && (
                    <span className="text-white/40 text-[10px] font-mono shrink-0">{fmtDuration(evStage.durationMs)}</span>
                  )}
                </div>

                <div className="flex items-center gap-2 mt-0.5 text-[10px] font-mono text-white/40 flex-wrap">
                  {status === 'active' && (
                    <span className="text-blue-400 font-semibold animate-pulse">In progress…</span>
                  )}
                  {status === 'pending' && (
                    <span className="text-white/20">Pending</span>
                  )}
                  {status === 'failed' && (
                    <span className="text-rose-400 font-semibold">Failed</span>
                  )}
                  <span className="text-white/30 truncate">• {stageDetail}</span>
                  {status === 'active' && evaluation.estimatedDurationMs && (
                    <span className="text-white/25">ETA ~{fmtDuration(evaluation.estimatedDurationMs * (1 - evaluation.progress / 100))}</span>
                  )}
                </div>

                {/* Progress bar for active stage */}
                {status === 'active' && (
                  <div className="mt-1.5 h-1 w-full rounded-full bg-white/8 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-700"
                      style={{ width: `${evaluation.progress}%` }}
                    />
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default EvaluationTimeline;
