import React from 'react';
import { Download, Play, Columns, LayoutGrid, List, Activity, ShieldCheck, Eye } from 'lucide-react';
import { SearchBar } from '@/shared/components';
import { SEARCH_HINTS } from '../config/filters';

interface BenchmarkHeaderProps {
  searchQuery: string;
  onSearchChange: (q: string) => void;
  viewMode: 'grid' | 'list';
  onToggleViewMode: () => void;
  compareCount: number;
  onOpenCompare: () => void;
  onRunClick: () => void;
}

export const BenchmarkHeader: React.FC<BenchmarkHeaderProps> = ({
  searchQuery,
  onSearchChange,
  viewMode,
  onToggleViewMode,
  compareCount,
  onOpenCompare,
  onRunClick,
}) => {
  return (
    <div className="liquid-glass-card rounded-2xl p-5 sm:p-6 border border-white/10 space-y-5">
      {/* Hero Header Top Row */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-5">
        <div className="space-y-1.5 flex-1 min-w-0">
          <div className="flex items-center gap-2 text-xs font-mono text-accent/80 uppercase tracking-widest">
            <span className="flex items-center gap-1.5 font-semibold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Cluster Live
            </span>
            <span className="text-white/20">•</span>
            <span className="flex items-center gap-1 text-white/60">
              <Eye className="w-3 h-3 text-accent" /> Step 1: Observe — Benchmark Control Center
            </span>
          </div>

          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white flex items-center gap-3">
            <span>Benchmark Registry</span>
            <span className="text-xs font-mono font-normal px-2.5 py-1 rounded-full bg-white/5 border border-white/10 text-white/50">
              24 Active Suites
            </span>
          </h1>

          <p className="text-xs sm:text-sm text-white/50 max-w-2xl leading-relaxed">
            Standardized evaluation suites for model capability profiling, safety alignment, and reasoning performance.
          </p>
        </div>

        {/* Hero Quick Telemetry & Actions */}
        <div className="flex flex-wrap items-center gap-3 shrink-0">
          <div className="hidden xl:flex items-center gap-4 px-4 py-2 rounded-xl bg-white/[0.03] border border-white/[0.08] text-xs font-mono">
            <div className="flex items-center gap-2">
              <Activity className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-white/40">Queue:</span>
              <span className="text-white font-semibold">12 Jobs</span>
            </div>
            <div className="w-px h-3 bg-white/10" />
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-3.5 h-3.5 text-teal-400" />
              <span className="text-white/40">Score:</span>
              <span className="text-white font-semibold">98.4%</span>
            </div>
          </div>

          {compareCount > 0 && (
            <button
              onClick={onOpenCompare}
              className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-purple-500/15 border border-purple-500/30 text-purple-300 text-xs font-mono font-semibold hover:bg-purple-500/25 transition-colors cursor-pointer"
            >
              <Columns className="w-3.5 h-3.5" />
              Compare ({compareCount})
            </button>
          )}

          <button className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-white/5 border border-white/10 text-white/80 text-xs font-mono hover:bg-white/10 transition-colors cursor-pointer">
            <Download className="w-3.5 h-3.5" />
            Import Suite
          </button>

          <button
            onClick={onRunClick}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-accent text-neutral-950 text-xs font-semibold hover:bg-accent-hover transition-colors shadow-lg shadow-accent/20 cursor-pointer"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            Run Evaluation
          </button>
        </div>
      </div>

      {/* Filter & Search Toolbar Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-3 border-t border-white/[0.06]">
        <SearchBar
          value={searchQuery}
          onChange={onSearchChange}
          hints={SEARCH_HINTS}
          onSelectHint={(hint) => onSearchChange(hint)}
        />

        <div className="flex items-center gap-2 shrink-0 justify-end">
          <button
            onClick={onToggleViewMode}
            className="p-2 rounded-xl bg-white/[0.04] border border-white/10 text-white/60 hover:text-white transition-colors cursor-pointer"
            aria-label="Toggle layout view"
          >
            {viewMode === 'grid' ? <List className="w-4 h-4" /> : <LayoutGrid className="w-4 h-4" />}
          </button>
        </div>
      </div>
    </div>
  );
};

export default BenchmarkHeader;
