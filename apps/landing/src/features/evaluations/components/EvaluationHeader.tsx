import React from 'react';
import { Play, RotateCw, Download, Calendar, Eye, Activity, ShieldCheck, Layers } from 'lucide-react';
import { SearchBar } from '@/shared/components';

const SEARCH_HINTS = [
  'status:running', 'model:llama3', 'dataset:mmlu', 'benchmark:reasoning',
  'runtime>20m', 'score>85', 'owner:tushar', 'status:failed', 'provider:openai',
];

const STATUS_TABS = [
  { id: 'all', label: 'All Runs' },
  { id: 'running', label: 'Running' },
  { id: 'queued', label: 'Queued' },
  { id: 'scoring', label: 'Scoring' },
  { id: 'completed', label: 'Completed' },
  { id: 'failed', label: 'Failed' },
  { id: 'paused', label: 'Paused' },
];

interface Props {
  searchQuery: string;
  statusFilter: string;
  totalCount: number;
  filteredCount: number;
  compareCount: number;
  onSearch: (q: string) => void;
  onStatusFilter: (s: string) => void;
  onOpenCompare: () => void;
  onRefresh: () => void;
}

export const EvaluationHeader: React.FC<Props> = ({
  searchQuery,
  statusFilter,
  totalCount,
  filteredCount,
  compareCount,
  onSearch,
  onStatusFilter,
  onOpenCompare,
  onRefresh,
}) => {
  return (
    <div className="liquid-glass-card rounded-2xl p-5 sm:p-6 border border-white/10 space-y-5">
      {/* Hero Header Top Row */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-5">
        <div className="space-y-1.5 flex-1 min-w-0">
          <div className="flex items-center gap-2 text-xs font-mono text-accent/80 uppercase tracking-widest">
            <span className="flex items-center gap-1.5 font-semibold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Execution Cluster Active
            </span>
            <span className="text-white/20">•</span>
            <span className="flex items-center gap-1 text-white/60">
              <Eye className="w-3.5 h-3.5 text-accent" /> Step 1: Observe — Pipeline Control
            </span>
          </div>

          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white flex items-center gap-3">
            <span>Evaluation Operations</span>
            <span className="text-xs font-mono font-normal px-2.5 py-1 rounded-full bg-white/5 border border-white/10 text-white/50">
              {filteredCount} / {totalCount} Runs
            </span>
          </h1>

          <p className="text-xs sm:text-sm text-white/50 max-w-2xl leading-relaxed">
            Real-time evaluation pipeline monitoring, automated benchmark execution, and diagnostic analysis.
          </p>
        </div>

        {/* Hero Quick Telemetry & Actions */}
        <div className="flex flex-wrap items-center gap-3 shrink-0">
          <div className="hidden xl:flex items-center gap-4 px-4 py-2 rounded-xl bg-white/[0.03] border border-white/[0.08] text-xs font-mono">
            <div className="flex items-center gap-2">
              <Activity className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-white/40">Active Workers:</span>
              <span className="text-white font-semibold">12 / 16</span>
            </div>
            <div className="w-px h-3 bg-white/10" />
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-3.5 h-3.5 text-teal-400" />
              <span className="text-white/40">Pass Index:</span>
              <span className="text-white font-semibold">96.8%</span>
            </div>
          </div>

          {compareCount > 0 && (
            <button
              onClick={onOpenCompare}
              className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-blue-500/15 border border-blue-500/30 text-blue-300 text-xs font-mono font-semibold hover:bg-blue-500/25 transition-colors cursor-pointer"
            >
              <Layers className="w-3.5 h-3.5" />
              Compare Runs ({compareCount})
            </button>
          )}

          <button className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-white/5 border border-white/10 text-white/80 text-xs font-mono hover:bg-white/10 transition-colors cursor-pointer">
            <Calendar className="w-3.5 h-3.5" />
            Schedule
          </button>

          <button className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-white/5 border border-white/10 text-white/80 text-xs font-mono hover:bg-white/10 transition-colors cursor-pointer">
            <Download className="w-3.5 h-3.5" />
            Export
          </button>

          <button
            onClick={onRefresh}
            className="p-2 rounded-xl bg-white/5 border border-white/10 text-white/60 hover:text-white transition-colors cursor-pointer"
            title="Refresh Evaluation State"
          >
            <RotateCw className="w-4 h-4" />
          </button>

          <button className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-400 text-neutral-950 text-xs font-semibold hover:bg-emerald-300 transition-colors shadow-lg shadow-emerald-400/20 cursor-pointer">
            <Play className="w-3.5 h-3.5 fill-current" />
            New Evaluation Run
          </button>
        </div>
      </div>

      {/* Search Bar & Status Tabs Bar */}
      <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3 pt-3 border-t border-white/[0.06]">
        <div className="flex-1 min-w-0">
          <SearchBar
            value={searchQuery}
            onChange={onSearch}
            hints={SEARCH_HINTS}
            onSelectHint={(hint) => onSearch(hint)}
          />
        </div>

        {/* Status Filter Tabs */}
        <div className="flex items-center gap-1 overflow-x-auto pb-0.5 scrollbar-none shrink-0" role="tablist">
          {STATUS_TABS.map((tab) => (
            <button
              key={tab.id}
              role="tab"
              aria-selected={statusFilter === tab.id}
              onClick={() => onStatusFilter(tab.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-mono whitespace-nowrap transition-colors cursor-pointer ${
                statusFilter === tab.id
                  ? 'bg-white/10 text-white font-semibold border border-white/15'
                  : 'text-white/40 hover:text-white/70 border border-transparent hover:bg-white/5'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

export default EvaluationHeader;
