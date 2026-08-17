import React, { memo } from 'react';
import { Activity, ShieldCheck, Clock, Cpu, Info } from 'lucide-react';

interface KPIsProps {
  kpis: {
    running: number; queued: number; completedToday: number;
    avgRuntimeMs: number; successRate: number; failureRate: number;
    gpuHours: number; tokensProcessed: number; totalCostUsd: number;
    activeWorkers: number; totalWorkers: number;
  };
}

const MiniSparkline: React.FC<{ data: { t: number; v: number }[]; color: string }> = memo(({ data, color }) => {
  if (!data.length) return null;
  const W = 80, H = 24;
  const vs = data.map(d => d.v);
  const minV = Math.min(...vs), maxV = Math.max(...vs);
  const range = maxV - minV || 1;
  const pts = data.map((d, i) => {
    const x = (i / (data.length - 1)) * W;
    const y = H - ((d.v - minV) / range) * (H - 4) - 2;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-20 h-6 overflow-visible shrink-0" preserveAspectRatio="none" aria-hidden="true">
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5" strokeLinejoin="round" />
    </svg>
  );
});

MiniSparkline.displayName = 'MiniSparkline';

function fmtRuntime(ms: number): string {
  const totalSec = ms / 1000;
  const mins = Math.floor(totalSec / 60);
  const secs = Math.floor(totalSec % 60);
  return `${mins}m ${secs}s`;
}

function fmtTokens(n: number): string {
  if (n >= 1e9) return `${(n / 1e9).toFixed(1)}B`;
  if (n >= 1e6) return `${(n / 1e6).toFixed(0)}M`;
  return `${n}`;
}

export const EvaluationKPIsComponent: React.FC<KPIsProps> = ({ kpis }) => {
  return (
    <section className="space-y-3" aria-label="Operational Health Metrics">
      <div className="flex items-center justify-between px-1">
        <span className="text-xs font-mono uppercase tracking-wider text-white/40 flex items-center gap-1.5 select-none">
          <Info className="w-3.5 h-3.5 text-accent" aria-hidden="true" />
          Step 2: Understand — Core Operational Health Metrics
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
        {/* 1. Active Pipelines */}
        <div className="liquid-glass-card p-4 sm:p-5 rounded-2xl border border-white/10 flex flex-col justify-between min-h-[115px] space-y-3 relative overflow-hidden group">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase tracking-wider text-white/40 whitespace-nowrap">Active Pipelines</span>
            <div className="w-7 h-7 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
              <Activity className="w-3.5 h-3.5 text-emerald-400 animate-pulse" aria-hidden="true" />
            </div>
          </div>
          <div className="flex items-end justify-between gap-2">
            <div className="min-w-0">
              <div className="text-2xl font-bold text-white font-mono tabular-nums leading-none flex items-baseline gap-1">
                {kpis.running}
                <span className="text-xs font-normal text-emerald-400">Running</span>
              </div>
              <div className="flex items-center gap-1.5 mt-2 whitespace-nowrap">
                <span className="text-[10px] font-mono text-white/40">{kpis.queued} queued in backlog</span>
              </div>
            </div>
            <MiniSparkline data={[]} color="#34d399" />
          </div>
        </div>

        {/* 2. Success Index */}
        <div className="liquid-glass-card p-4 sm:p-5 rounded-2xl border border-white/10 flex flex-col justify-between min-h-[115px] space-y-3 relative overflow-hidden group">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase tracking-wider text-white/40 whitespace-nowrap">Pass & Quality Index</span>
            <div className="w-7 h-7 rounded-lg bg-teal-500/10 border border-teal-500/20 flex items-center justify-center">
              <ShieldCheck className="w-3.5 h-3.5 text-teal-400" aria-hidden="true" />
            </div>
          </div>
          <div className="flex items-end justify-between gap-2">
            <div className="min-w-0">
              <div className="text-2xl font-bold text-white font-mono tabular-nums leading-none">{kpis.successRate}%</div>
              <div className="flex items-center gap-1.5 mt-2 whitespace-nowrap">
                <span className="text-[10px] font-mono text-emerald-400">{kpis.successRate}% pass index</span>
                <span className="text-[10px] font-mono text-white/30">• {kpis.failureRate}% failures</span>
              </div>
            </div>
            <MiniSparkline data={[]} color="#2dd4bf" />
          </div>
        </div>

        {/* 3. Latency & Throughput */}
        <div className="liquid-glass-card p-4 sm:p-5 rounded-2xl border border-white/10 flex flex-col justify-between min-h-[115px] space-y-3 relative overflow-hidden group">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase tracking-wider text-white/40 whitespace-nowrap">Average Latency</span>
            <div className="w-7 h-7 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center">
              <Clock className="w-3.5 h-3.5 text-amber-400" aria-hidden="true" />
            </div>
          </div>
          <div className="flex items-end justify-between gap-2">
            <div className="min-w-0">
              <div className="text-2xl font-bold text-white font-mono tabular-nums leading-none">{fmtRuntime(kpis.avgRuntimeMs)}</div>
              <div className="flex items-center gap-1.5 mt-2 whitespace-nowrap">
                <span className="text-[10px] font-mono text-white/40">{fmtTokens(kpis.tokensProcessed)} tokens processed</span>
              </div>
            </div>
            <MiniSparkline data={[]} color="#fbbf24" />
          </div>
        </div>

        {/* 4. Compute & Spend */}
        <div className="liquid-glass-card p-4 sm:p-5 rounded-2xl border border-white/10 flex flex-col justify-between min-h-[115px] space-y-3 relative overflow-hidden group">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase tracking-wider text-white/40 whitespace-nowrap">Compute & Spend</span>
            <div className="w-7 h-7 rounded-lg bg-purple-500/10 border border-purple-500/20 flex items-center justify-center">
              <Cpu className="w-3.5 h-3.5 text-purple-400" aria-hidden="true" />
            </div>
          </div>
          <div className="flex items-end justify-between gap-2">
            <div className="min-w-0">
              <div className="text-2xl font-bold text-white font-mono tabular-nums leading-none">${kpis.totalCostUsd}</div>
              <div className="flex items-center gap-1.5 mt-2 whitespace-nowrap">
                <span className="text-[10px] font-mono text-purple-300">{kpis.activeWorkers}/{kpis.totalWorkers} wrkrs</span>
                <span className="text-[10px] font-mono text-white/30">• {kpis.gpuHours} GPU hrs</span>
              </div>
            </div>
            <MiniSparkline data={[]} color="#c084fc" />
          </div>
        </div>
      </div>
    </section>
  );
};

export const EvaluationKPIs = memo(EvaluationKPIsComponent);
export default EvaluationKPIs;
