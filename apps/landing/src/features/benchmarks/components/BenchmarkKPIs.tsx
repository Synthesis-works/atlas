import React, { memo } from 'react';
import { Layers, Activity, ShieldCheck, Database, TrendingUp, Info } from 'lucide-react';

interface BenchmarkKPIsProps {
  kpis: {
    total: number;
    categoriesCount: number;
    activeEvaluations: number;
    avgVerification: number;
  };
}

const SPARK_TOTAL = [
  { t: 1, v: 18 }, { t: 2, v: 20 }, { t: 3, v: 21 }, { t: 4, v: 22 }, { t: 5, v: 24 }
];
const SPARK_ACTIVE = [
  { t: 1, v: 4 }, { t: 2, v: 8 }, { t: 3, v: 6 }, { t: 4, v: 10 }, { t: 5, v: 12 }
];
const SPARK_SCORE = [
  { t: 1, v: 94.2 }, { t: 2, v: 95.8 }, { t: 3, v: 96.4 }, { t: 4, v: 97.9 }, { t: 5, v: 98.4 }
];

const MiniSparkline: React.FC<{ data: { t: number; v: number }[]; color: string }> = memo(({ data, color }) => {
  if (!data.length) return null;
  const W = 64, H = 20;
  const vs = data.map(d => d.v);
  const minV = Math.min(...vs), maxV = Math.max(...vs);
  const range = maxV - minV || 1;
  const pts = data.map((d, i) => {
    const x = (i / (data.length - 1)) * W;
    const y = H - ((d.v - minV) / range) * (H - 4) - 2;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-16 h-5 overflow-visible" preserveAspectRatio="none" aria-hidden="true">
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5" strokeLinejoin="round" />
    </svg>
  );
});

MiniSparkline.displayName = 'MiniSparkline';

export const BenchmarkKPIsComponent: React.FC<BenchmarkKPIsProps> = ({ kpis }) => {
  return (
    <section className="space-y-3" aria-label="Benchmark Core Metrics">
      <div className="flex items-center justify-between px-1">
        <span className="text-xs font-mono uppercase tracking-wider text-white/40 flex items-center gap-1.5">
          <Info className="w-3.5 h-3.5 text-accent" aria-hidden="true" />
          Step 2: Understand — Core Ecosystem Health Indicators
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
        {/* Total Benchmarks */}
        <div className="liquid-glass-card p-4 sm:p-5 rounded-2xl border border-white/10 flex flex-col justify-between space-y-3 relative overflow-hidden group">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase tracking-wider text-white/40">Total Benchmarks</span>
            <div className="w-7 h-7 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center">
              <Database className="w-3.5 h-3.5 text-blue-400" aria-hidden="true" />
            </div>
          </div>
          <div className="flex items-end justify-between">
            <div>
              <div className="text-2xl font-bold text-white font-mono tabular-nums">{kpis.total}</div>
              <div className="flex items-center gap-1.5 mt-1">
                <span className="text-[10px] font-mono text-emerald-400 flex items-center gap-0.5">
                  <TrendingUp className="w-3 h-3" aria-hidden="true" /> +12.4%
                </span>
                <span className="text-[10px] font-mono text-white/30">vs last month</span>
              </div>
            </div>
            <MiniSparkline data={SPARK_TOTAL} color="#60a5fa" />
          </div>
        </div>

        {/* Categories */}
        <div className="liquid-glass-card p-4 sm:p-5 rounded-2xl border border-white/10 flex flex-col justify-between space-y-3 relative overflow-hidden group">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase tracking-wider text-white/40">Domain Categories</span>
            <div className="w-7 h-7 rounded-lg bg-purple-500/10 border border-purple-500/20 flex items-center justify-center">
              <Layers className="w-3.5 h-3.5 text-purple-400" aria-hidden="true" />
            </div>
          </div>
          <div className="flex items-end justify-between">
            <div>
              <div className="text-2xl font-bold text-white font-mono tabular-nums">{kpis.categoriesCount}</div>
              <span className="text-[10px] font-mono text-white/40 mt-1 inline-block">Reasoning, Code, Safety, Vision</span>
            </div>
          </div>
        </div>

        {/* Active Executions */}
        <div className="liquid-glass-card p-4 sm:p-5 rounded-2xl border border-white/10 flex flex-col justify-between space-y-3 relative overflow-hidden group">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase tracking-wider text-white/40">Active Executions</span>
            <div className="w-7 h-7 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
              <Activity className="w-3.5 h-3.5 text-emerald-400 animate-pulse" aria-hidden="true" />
            </div>
          </div>
          <div className="flex items-end justify-between">
            <div>
              <div className="text-2xl font-bold text-white font-mono tabular-nums">{kpis.activeEvaluations}</div>
              <div className="flex items-center gap-1.5 mt-1">
                <span className="text-[10px] font-mono text-emerald-400 font-semibold">Running</span>
                <span className="text-[10px] font-mono text-white/30">• worker active</span>
              </div>
            </div>
            <MiniSparkline data={SPARK_ACTIVE} color="#34d399" />
          </div>
        </div>

        {/* Verification Index */}
        <div className="liquid-glass-card p-4 sm:p-5 rounded-2xl border border-white/10 flex flex-col justify-between space-y-3 relative overflow-hidden group">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase tracking-wider text-white/40">Verification Index</span>
            <div className="w-7 h-7 rounded-lg bg-teal-500/10 border border-teal-500/20 flex items-center justify-center">
              <ShieldCheck className="w-3.5 h-3.5 text-teal-400" aria-hidden="true" />
            </div>
          </div>
          <div className="flex items-end justify-between">
            <div>
              <div className="text-2xl font-bold text-white font-mono tabular-nums">{kpis.avgVerification}%</div>
              <div className="flex items-center gap-1.5 mt-1">
                <span className="text-[10px] font-mono text-teal-400 flex items-center gap-0.5">
                  <TrendingUp className="w-3 h-3" aria-hidden="true" /> +0.8%
                </span>
                <span className="text-[10px] font-mono text-white/30">quality benchmark</span>
              </div>
            </div>
            <MiniSparkline data={SPARK_SCORE} color="#2dd4bf" />
          </div>
        </div>
      </div>
    </section>
  );
};

export const BenchmarkKPIs = memo(BenchmarkKPIsComponent);
export default BenchmarkKPIs;
