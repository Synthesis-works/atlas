import React, { useState } from 'react';
import type { EvaluationRun } from '@/domain/evaluations/types';
import { EVALUATION_STATUS_MAP } from '@/domain/evaluations/constants';
import { OverviewSection } from './OverviewSection';
import { MetricsSection } from './MetricsSection';
import { TimelineSection } from './TimelineSection';
import { LogsSection } from './LogsSection';
import { ConfigurationSection } from './ConfigurationSection';
import { ArtifactsSection } from './ArtifactsSection';
import { ReproducibilitySection } from './ReproducibilitySection';

interface Props {
  evaluation: EvaluationRun | null;
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
];

export const EvaluationDrawer: React.FC<Props> = ({ evaluation, onClose }) => {
  const [activeTab, setActiveTab] = useState('overview');

  if (!evaluation) return null;
  const sc = EVALUATION_STATUS_MAP[evaluation.status];

  return (
    <>
      {/* Overlay */}
      <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40" onClick={onClose} />

      {/* Panel */}
      <aside className="fixed right-0 top-0 h-full z-50 flex flex-col bg-ink-1 border-l border-white/8 w-full sm:w-[540px] md:w-[620px] lg:w-[680px] max-w-full">

        {/* Header */}
        <div className="flex items-start gap-4 p-6 border-b border-white/5 shrink-0">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1.5 flex-wrap">
              <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full border text-[10px] font-mono ${sc.badgeClass}`}>
                <span className={`w-1.5 h-1.5 rounded-full ${sc.dotClass}`} />
                {evaluation.status}
              </span>
              <span className="text-[10px] font-mono text-white/25">{evaluation.id}</span>
              <span className="text-[10px] font-mono text-white/20">·</span>
              <span className="text-[10px] font-mono text-white/25">{evaluation.benchmarkCategory}</span>
            </div>
            <h2 className="text-sm font-semibold text-white leading-snug line-clamp-2">{evaluation.name}</h2>
            <div className="flex items-center gap-2 mt-1 text-[10px] font-mono text-white/25">
              <span>@{evaluation.owner}</span>
              <span>·</span>
              <span>{evaluation.worker}</span>
            </div>
          </div>
          <button
            onClick={onClose}
            id="eval-drawer-close"
            className="w-8 h-8 rounded-lg flex items-center justify-center border border-white/10 text-white/40 hover:text-white hover:border-white/20 transition-colors shrink-0"
          >✕</button>
        </div>

        {/* Progress bar */}
        {!['Completed', 'Failed', 'Cancelled'].includes(evaluation.status) && (
          <div className="shrink-0 h-0.5 bg-white/5">
            <div
              className="h-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-700"
              style={{ width: `${evaluation.progress}%` }}
            />
          </div>
        )}
        {evaluation.status === 'Completed' && (
          <div className="shrink-0 h-0.5 bg-emerald-500/40" />
        )}
        {evaluation.status === 'Failed' && (
          <div className="shrink-0 h-0.5 bg-rose-500/40" />
        )}

        {/* Tabs */}
        <div className="flex items-center gap-0 px-6 border-b border-white/5 shrink-0 overflow-x-auto">
          {TABS.map(tab => (
            <button
              key={tab.id}
              id={`drawer-tab-${tab.id}`}
              onClick={() => setActiveTab(tab.id)}
              className={`px-3 py-3 text-[11px] font-mono border-b-2 transition-colors whitespace-nowrap ${
                activeTab === tab.id
                  ? 'border-blue-400 text-blue-400'
                  : 'border-transparent text-white/35 hover:text-white/60'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6">
          {activeTab === 'overview' && <OverviewSection evaluation={evaluation} />}
          {activeTab === 'metrics' && <MetricsSection evaluation={evaluation} />}
          {activeTab === 'timeline' && <TimelineSection evaluation={evaluation} />}
          {activeTab === 'logs' && <LogsSection evaluation={evaluation} />}
          {activeTab === 'config' && <ConfigurationSection evaluation={evaluation} />}
          {activeTab === 'artifacts' && <ArtifactsSection evaluation={evaluation} />}
          {activeTab === 'reproducibility' && <ReproducibilitySection evaluation={evaluation} />}
        </div>
      </aside>
    </>
  );
};

export default EvaluationDrawer;
