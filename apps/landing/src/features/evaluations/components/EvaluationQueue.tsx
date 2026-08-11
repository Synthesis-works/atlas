import React from 'react';
import type { EvaluationRun } from '@/domain/evaluations/types';
import { EVALUATION_STATUS_MAP, EVALUATION_PRIORITY_MAP } from '@/domain/evaluations/constants';
import { DataTable } from '@/shared/components';
import type { Column } from '@/shared/components';

interface Props {
  evaluations: EvaluationRun[];
  selectedId?: string;
  compareIds: string[];
  onRowClick: (ev: EvaluationRun) => void;
  onToggleCompare: (id: string) => void;
  onAction: (action: 'pause' | 'resume' | 'cancel' | 'duplicate', ev: EvaluationRun) => void;
}

function fmtDuration(ms?: number): string {
  if (!ms) return '—';
  const m = Math.floor(ms / 60000);
  const s = Math.floor((ms % 60000) / 1000);
  return `${m}m ${s}s`;
}

function fmtElapsed(ev: EvaluationRun): string {
  if (ev.status === 'Completed') return fmtDuration(ev.durationMs);
  return ev.elapsedMs ? fmtDuration(ev.elapsedMs) : '—';
}

export const EvaluationQueue: React.FC<Props> = ({
  evaluations, selectedId: _selectedId, compareIds, onRowClick, onToggleCompare, onAction,
}) => {
  const columns: Column<EvaluationRun>[] = [
    {
      key: 'compare',
      header: '★',
      className: 'w-8 text-center',
      render: (ev) => (
        <div
          onClick={e => { e.stopPropagation(); onToggleCompare(ev.id); }}
          className={`mx-auto w-4 h-4 rounded border flex items-center justify-center text-[8px] cursor-pointer transition-colors ${
            compareIds.includes(ev.id)
              ? 'border-blue-400 bg-blue-500/20 text-blue-400'
              : 'border-white/10 text-white/20 hover:border-white/30'
          }`}
        >
          {compareIds.includes(ev.id) ? '✓' : ''}
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (ev) => {
        const sc = EVALUATION_STATUS_MAP[ev.status];
        return (
          <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full border text-[10px] whitespace-nowrap ${sc.badgeClass}`}>
            <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${sc.dotClass}`} />
            {ev.status}
          </span>
        );
      },
    },
    {
      key: 'name',
      header: 'Evaluation Name',
      className: 'min-w-[200px]',
      render: (ev) => (
        <div>
          <div className="text-white/90 font-medium truncate max-w-[220px]">{ev.name}</div>
          <div className="text-[10px] text-white/30 font-mono mt-0.5">{ev.id}</div>
        </div>
      ),
    },
    {
      key: 'benchmark',
      header: 'Benchmark',
      render: (ev) => (
        <div>
          <div className="text-white/70">{ev.benchmark}</div>
          <div className="text-[10px] text-white/30">{ev.benchmarkCategory}</div>
        </div>
      ),
    },
    {
      key: 'model',
      header: 'Model',
      render: (ev) => (
        <div>
          <div className="text-white/70 whitespace-nowrap">{ev.model}</div>
          <div className="text-[10px] text-white/30">{ev.modelProvider}</div>
        </div>
      ),
    },
    {
      key: 'dataset',
      header: 'Dataset',
      render: (ev) => <span className="text-white/50 text-[11px] truncate max-w-[140px] block">{ev.dataset}</span>,
    },
    {
      key: 'startedAt',
      header: 'Started',
      render: (ev) => (
        <span className="text-white/40 text-[10px] font-mono whitespace-nowrap">
          {new Date(ev.startedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      ),
    },
    {
      key: 'elapsed',
      header: 'Elapsed',
      render: (ev) => <span className="text-white/40 text-[10px] font-mono">{fmtElapsed(ev)}</span>,
    },
    {
      key: 'progress',
      header: 'Progress',
      render: (ev) => (
        <div className="flex items-center gap-2">
          <div className="w-16 h-1.5 rounded-full bg-white/10 overflow-hidden flex-shrink-0">
            <div
              className={`h-full rounded-full transition-all ${
                ev.status === 'Failed' ? 'bg-rose-500' :
                ev.status === 'Completed' ? 'bg-emerald-500' : 'bg-gradient-to-r from-blue-500 to-purple-500'
              }`}
              style={{ width: `${ev.progress}%` }}
            />
          </div>
          <span className="text-[10px] font-mono text-white/40">{ev.progress}%</span>
        </div>
      ),
    },
    {
      key: 'worker',
      header: 'Worker',
      render: (ev) => <span className="text-white/30 text-[10px] font-mono">{ev.worker}</span>,
    },
    {
      key: 'priority',
      header: 'Priority',
      render: (ev) => {
        const p = EVALUATION_PRIORITY_MAP[ev.priority];
        return (
          <span className={`inline-flex items-center gap-1 text-[10px] font-mono ${p.class}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${p.dot}`} />
            {p.label}
          </span>
        );
      },
    },
    {
      key: 'score',
      header: 'Score',
      render: (ev) => ev.metrics ? (
        <span className="text-emerald-400 font-bold font-mono text-xs">
          {Math.round((ev.metrics.overallScore ?? 0) * 100)}%
        </span>
      ) : <span className="text-white/20 text-xs">—</span>,
    },
    {
      key: 'actions',
      header: 'Actions',
      className: 'text-right',
      render: (ev) => (
        <div className="flex items-center gap-1 justify-end" onClick={e => e.stopPropagation()}>
          <button
            onClick={() => onRowClick(ev)}
            className="px-2 py-0.5 rounded-md border border-white/8 bg-white/[0.02] text-[10px] font-mono text-white/50 hover:text-white hover:border-white/20 transition-colors"
            title="View details"
          >View</button>
          {ev.status === 'Running' && (
            <button
              onClick={() => onAction('pause', ev)}
              className="px-2 py-0.5 rounded-md border border-amber-500/20 bg-amber-500/5 text-[10px] font-mono text-amber-400 hover:bg-amber-500/15 transition-colors"
            >Pause</button>
          )}
          {ev.status === 'Paused' && (
            <button
              onClick={() => onAction('resume', ev)}
              className="px-2 py-0.5 rounded-md border border-emerald-500/20 bg-emerald-500/5 text-[10px] font-mono text-emerald-400 hover:bg-emerald-500/15 transition-colors"
            >Resume</button>
          )}
          {['Running', 'Queued', 'Paused'].includes(ev.status) && (
            <button
              onClick={() => onAction('cancel', ev)}
              className="px-2 py-0.5 rounded-md border border-rose-500/20 bg-rose-500/5 text-[10px] font-mono text-rose-400 hover:bg-rose-500/15 transition-colors"
            >Cancel</button>
          )}
          <button
            onClick={() => onAction('duplicate', ev)}
            className="px-2 py-0.5 rounded-md border border-white/8 bg-white/[0.02] text-[10px] font-mono text-white/40 hover:text-white/70 transition-colors"
          >⊕</button>
        </div>
      ),
    },
  ];

  return (
    <DataTable
      columns={columns}
      data={evaluations}
      keyExtractor={(ev) => ev.id}
      onRowClick={onRowClick}
      emptyMessage="No evaluations match your search or filter."
    />
  );
};

export default EvaluationQueue;
