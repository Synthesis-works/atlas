import React from 'react';

const pulse = 'animate-pulse bg-white/5 rounded';

// ── Skeleton KPI Cards ───────────────────────────────────────────────────────
export const SkeletonKPIs: React.FC = () => (
  <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 xl:grid-cols-10 gap-3">
    {Array.from({ length: 10 }).map((_, i) => (
      <div key={i} className="p-4 rounded-2xl border border-white/5 bg-white/[0.02] space-y-2.5">
        <div className={`h-2.5 w-16 ${pulse}`} />
        <div className={`h-7 w-12 ${pulse}`} />
        <div className={`h-2 w-20 ${pulse}`} />
      </div>
    ))}
  </div>
);

// ── Skeleton Table ───────────────────────────────────────────────────────────
export const SkeletonTable: React.FC<{ rows?: number }> = ({ rows = 8 }) => (
  <div className="rounded-2xl border border-white/5 bg-white/[0.02] overflow-hidden">
    <div className="p-4 border-b border-white/5">
      <div className={`h-3 w-28 ${pulse}`} />
    </div>
    <div className="divide-y divide-white/[0.03]">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-center gap-4 px-4 py-3.5">
          <div className={`h-2 w-2 rounded-full ${pulse}`} />
          <div className={`h-2.5 w-20 rounded-full ${pulse}`} />
          <div className={`h-2.5 flex-1 max-w-[180px] rounded-full ${pulse}`} />
          <div className={`h-2.5 w-24 rounded-full ${pulse}`} />
          <div className={`h-2.5 w-20 rounded-full ${pulse}`} />
          <div className="ml-auto flex gap-2">
            <div className={`h-2 w-16 rounded-full ${pulse}`} />
            <div className={`h-2 w-12 rounded-full ${pulse}`} />
          </div>
        </div>
      ))}
    </div>
  </div>
);

// ── Skeleton Timeline ────────────────────────────────────────────────────────
export const SkeletonTimeline: React.FC = () => (
  <div className="space-y-4 pl-5 relative">
    <div className="absolute left-2 top-0 bottom-0 w-px bg-white/5" />
    {Array.from({ length: 8 }).map((_, i) => (
      <div key={i} className="flex gap-3 pb-4">
        <div className={`absolute left-[-5px] top-1.5 w-3 h-3 rounded-full ${pulse}`} />
        <div className="space-y-1.5 flex-1">
          <div className={`h-2.5 w-32 rounded-full ${pulse}`} />
          <div className={`h-2 w-16 rounded-full ${pulse}`} />
        </div>
      </div>
    ))}
  </div>
);

// ── Skeleton Terminal ────────────────────────────────────────────────────────
export const SkeletonTerminal: React.FC = () => (
  <div className="flex flex-col h-full rounded-2xl border border-white/5 bg-black/60 overflow-hidden">
    <div className="flex items-center gap-2 px-4 py-2.5 bg-white/[0.03] border-b border-white/5">
      <div className="w-2.5 h-2.5 rounded-full bg-rose-400/30" />
      <div className="w-2.5 h-2.5 rounded-full bg-amber-400/30" />
      <div className="w-2.5 h-2.5 rounded-full bg-emerald-400/30" />
      <div className={`ml-3 h-2 w-40 rounded ${pulse}`} />
    </div>
    <div className="flex-1 p-4 space-y-2">
      {Array.from({ length: 12 }).map((_, i) => (
        <div key={i} className={`h-2 rounded ${pulse}`} style={{ width: `${40 + (i * 17) % 55}%` }} />
      ))}
    </div>
  </div>
);

// ── Skeleton Charts ──────────────────────────────────────────────────────────
export const SkeletonCharts: React.FC = () => (
  <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
    {Array.from({ length: 4 }).map((_, i) => (
      <div key={i} className="p-5 rounded-2xl border border-white/5 bg-white/[0.02] space-y-4">
        <div className="space-y-1.5">
          <div className={`h-3 w-28 rounded ${pulse}`} />
          <div className={`h-2 w-20 rounded ${pulse}`} />
        </div>
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, j) => (
            <div key={j} className="flex items-center gap-3">
              <div className={`h-2 w-12 rounded ${pulse}`} />
              <div className={`h-2 flex-1 rounded-full ${pulse}`} style={{ maxWidth: `${30 + (j * 20) % 60}%` }} />
            </div>
          ))}
        </div>
      </div>
    ))}
  </div>
);

// ── Skeleton Drawer ──────────────────────────────────────────────────────────
export const SkeletonDrawer: React.FC = () => (
  <div className="p-6 space-y-6">
    <div className="space-y-2">
      <div className={`h-4 w-3/4 rounded ${pulse}`} />
      <div className={`h-2.5 w-1/2 rounded ${pulse}`} />
    </div>
    <div className="grid grid-cols-2 gap-3">
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} className={`h-2.5 rounded ${pulse}`} />
      ))}
    </div>
    <div className="grid grid-cols-3 gap-3">
      {Array.from({ length: 9 }).map((_, i) => (
        <div key={i} className="p-3 rounded-xl border border-white/5 bg-white/[0.02] space-y-2">
          <div className={`h-2 w-full rounded ${pulse}`} />
          <div className={`h-5 w-12 rounded ${pulse}`} />
        </div>
      ))}
    </div>
  </div>
);

// ── Empty State ──────────────────────────────────────────────────────────────
export const EvaluationEmptyState: React.FC = () => (
  <div className="flex flex-col items-center justify-center py-24 space-y-4 text-center">
    <div className="w-16 h-16 rounded-full bg-white/5 border border-white/10 flex items-center justify-center">
      <span className="text-3xl text-white/20">◎</span>
    </div>
    <div>
      <h3 className="text-sm font-semibold text-white/60">No evaluations have been executed.</h3>
      <p className="text-xs font-mono text-white/30 mt-1">Run your first evaluation to get started.</p>
    </div>
    <button
      id="eval-empty-run-btn"
      className="mt-2 flex items-center gap-2 px-5 py-2.5 rounded-xl border border-emerald-500/30 bg-emerald-500/10 text-emerald-400 text-xs font-mono hover:bg-emerald-500/20 transition-all"
    >
      ▶ Run Evaluation
    </button>
  </div>
);

// ── Error State ──────────────────────────────────────────────────────────────
export const EvaluationErrorState: React.FC<{ onRetry: () => void }> = ({ onRetry }) => (
  <div className="flex flex-col items-center justify-center py-24 space-y-4 text-center">
    <div className="w-16 h-16 rounded-full bg-rose-500/10 border border-rose-500/20 flex items-center justify-center">
      <span className="text-3xl text-rose-400">✕</span>
    </div>
    <div>
      <h3 className="text-sm font-semibold text-rose-400">Unable to load evaluations.</h3>
      <p className="text-xs font-mono text-white/30 mt-1">Check your connection and try again.</p>
    </div>
    <button
      id="eval-error-retry-btn"
      onClick={onRetry}
      className="mt-2 flex items-center gap-2 px-5 py-2.5 rounded-xl border border-white/10 bg-white/5 text-white/60 text-xs font-mono hover:bg-white/10 hover:text-white transition-all"
    >
      ↻ Retry
    </button>
  </div>
);
