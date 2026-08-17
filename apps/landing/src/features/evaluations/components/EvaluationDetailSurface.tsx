import React, { useState } from 'react';
import { ArrowLeft, Activity } from 'lucide-react';
import type { EvaluationRun } from '@/domain/evaluations/types';
import { getStatusStyle } from '@/domain/evaluations/constants';
import { OverviewSection } from './Detail/OverviewSection';
import { MetricsSection } from './Detail/MetricsSection';
import { TimelineSection } from './Detail/TimelineSection';
import { LogsSection } from './Detail/LogsSection';
import { ConfigurationSection } from './Detail/ConfigurationSection';
import { ArtifactsSection } from './Detail/ArtifactsSection';
import { ReproducibilitySection } from './Detail/ReproducibilitySection';

interface Props {
  evaluation: EvaluationRun;
  onClose: () => void;
}

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'metrics', label: 'Metrics' },
  { id: 'timeline', label: 'Timeline' },
  { id: 'logs', label: 'Logs' },
  { id: 'config', label: 'Configuration' },
  { id: 'artifacts', label: 'Artifacts' },
  { id: 'reproducibility', label: 'Reproducibility' },
] as const;

function fmtDuration(ms?: number): string {
  if (!ms) return '—';
  const m = Math.floor(ms / 60000);
  const s = Math.floor((ms % 60000) / 1000);
  return `${m}m ${s}s`;
}

/**
 * Full-workspace run detail surface. It replaces the evaluation workspace
 * entirely (no old canvas remains behind it) and renders live lifecycle data
 * straight from the store, which is refreshed every few seconds by the hook.
 */
export const EvaluationDetailSurface: React.FC<Props> = ({ evaluation, onClose }) => {
  const [activeTab, setActiveTab] = useState<(typeof TABS)[number]['id']>('overview');
  const sc = getStatusStyle(evaluation.status);
  const isLive = !['Completed', 'Failed', 'Cancelled'].includes(evaluation.status);

  return (
    <div className="w-full h-full flex flex-col min-h-0 text-white">
      {/* Surface header */}
      <div className="shrink-0 border-b border-white/10 bg-ink-2/60">
        <div className="flex items-start gap-4 p-5">
          <button
            onClick={onClose}
            id="eval-detail-back"
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl border border-white/10 bg-white/5 text-xs font-mono text-white/70 hover:text-white hover:bg-white/10 transition-colors shrink-0 cursor-pointer"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Back to Evaluations
          </button>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1.5 flex-wrap">
              <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full border text-[10px] font-mono ${sc.badgeClass}`}>
                <span className={`w-1.5 h-1.5 rounded-full ${sc.dotClass}`} />
                {evaluation.status}
              </span>
              {isLive && (
                <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full border border-emerald-500/20 bg-emerald-500/10 text-emerald-300 text-[10px] font-mono">
                  <Activity className="w-3 h-3 animate-pulse" />
                  LIVE
                </span>
              )}
              <span className="text-[10px] font-mono text-white/25">{evaluation.id}</span>
            </div>
            <h2 className="text-lg font-semibold text-white leading-snug line-clamp-2">{evaluation.name}</h2>
            <div className="flex items-center gap-2 mt-1 text-[10px] font-mono text-white/30 flex-wrap">
              <span>{evaluation.model}</span>
              <span>·</span>
              <span>{evaluation.modelProvider}</span>
              <span>·</span>
              <span>{evaluation.benchmark}</span>
              {evaluation.benchmarkVersion && (
                <>
                  <span>·</span>
                  <span>v{evaluation.benchmarkVersion}</span>
                </>
              )}
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 shrink-0 text-right">
            <div>
              <div className="text-[10px] font-mono text-white/30 uppercase tracking-wider">Started</div>
              <div className="text-[11px] font-mono text-white/70">
                {evaluation.startedAt ? new Date(evaluation.startedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—'}
              </div>
            </div>
            <div>
              <div className="text-[10px] font-mono text-white/30 uppercase tracking-wider">Completed</div>
              <div className="text-[11px] font-mono text-white/70">
                {evaluation.completedAt ? new Date(evaluation.completedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—'}
              </div>
            </div>
            <div>
              <div className="text-[10px] font-mono text-white/30 uppercase tracking-wider">Duration</div>
              <div className="text-[11px] font-mono text-white/70">{fmtDuration(evaluation.durationMs)}</div>
            </div>
            <div>
              <div className="text-[10px] font-mono text-white/30 uppercase tracking-wider">Progress</div>
              <div className="text-[11px] font-mono text-white/70">{evaluation.progress}%</div>
            </div>
          </div>
        </div>

        {/* Live progress bar */}
        <div className="h-0.5 bg-white/5">
          {isLive && (
            <div
              className="h-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-700"
              style={{ width: `${evaluation.progress}%` }}
            />
          )}
          {evaluation.status === 'Completed' && <div className="h-full bg-emerald-500/60" />}
          {evaluation.status === 'Failed' && <div className="h-full bg-rose-500/60" />}
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-0 px-5 overflow-x-auto scrollbar-none" role="tablist">
          {TABS.map(tab => (
            <button
              key={tab.id}
              role="tab"
              aria-selected={activeTab === tab.id}
              id={`detail-tab-${tab.id}`}
              onClick={() => setActiveTab(tab.id)}
              className={`px-3 py-3 text-[11px] font-mono border-b-2 transition-colors whitespace-nowrap cursor-pointer ${
                activeTab === tab.id
                  ? 'border-accent text-accent'
                  : 'border-transparent text-white/35 hover:text-white/60'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-6" role="tabpanel">
        {activeTab === 'overview' && <OverviewSection evaluation={evaluation} />}
        {activeTab === 'metrics' && <MetricsSection evaluation={evaluation} />}
        {activeTab === 'timeline' && <TimelineSection evaluation={evaluation} />}
        {activeTab === 'logs' && <LogsSection evaluation={evaluation} />}
        {activeTab === 'config' && <ConfigurationSection evaluation={evaluation} />}
        {activeTab === 'artifacts' && <ArtifactsSection evaluation={evaluation} />}
        {activeTab === 'reproducibility' && <ReproducibilitySection evaluation={evaluation} />}
      </div>
    </div>
  );
};

export default EvaluationDetailSurface;