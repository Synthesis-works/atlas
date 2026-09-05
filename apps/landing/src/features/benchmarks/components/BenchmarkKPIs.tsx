import React, { memo } from 'react';
import { Layers, Activity, ShieldCheck, Database, Info } from 'lucide-react';

interface BenchmarkKPIsProps {
  kpis: {
    total: number;
    categoriesCount: number;
    activeEvaluations: number;
    avgVerification: number | null;
    completedRuns?: number;
    totalExecutions?: number;
  };
}

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
                <span className="text-[10px] font-mono text-white/40">
                  {kpis.total === 0 ? 'No suites loaded' : `${kpis.total} registered in database`}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Categories */}
        <div className="liquid-glass-card p-4 sm:p-5 rounded-2xl border border-white/10 flex flex-col justify-between space-y-3 relative overflow-hidden group">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase tracking-wider text-white/40">Active Domains</span>
            <div className="w-7 h-7 rounded-lg bg-purple-500/10 border border-purple-500/20 flex items-center justify-center">
              <Layers className="w-3.5 h-3.5 text-purple-400" aria-hidden="true" />
            </div>
          </div>
          <div className="flex items-end justify-between">
            <div>
              <div className="text-2xl font-bold text-white font-mono tabular-nums">{kpis.categoriesCount}</div>
              <span className="text-[10px] font-mono text-white/40 mt-1 inline-block">
                {kpis.categoriesCount === 0 ? 'No categories assigned' : 'Evaluated domains'}
              </span>
            </div>
          </div>
        </div>

        {/* Active Executions */}
        <div className="liquid-glass-card p-4 sm:p-5 rounded-2xl border border-white/10 flex flex-col justify-between space-y-3 relative overflow-hidden group">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase tracking-wider text-white/40">Active Executions</span>
            <div className="w-7 h-7 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
              <Activity className="w-3.5 h-3.5 text-emerald-400" aria-hidden="true" />
            </div>
          </div>
          <div className="flex items-end justify-between">
            <div>
              <div className="text-2xl font-bold text-white font-mono tabular-nums">{kpis.activeEvaluations}</div>
              <div className="flex items-center gap-1.5 mt-1">
                <span className="text-[10px] font-mono text-white/40">
                  {kpis.activeEvaluations > 0 ? 'Worker jobs in progress' : 'No active jobs running'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Verification Index / Average Score */}
        <div className="liquid-glass-card p-4 sm:p-5 rounded-2xl border border-white/10 flex flex-col justify-between space-y-3 relative overflow-hidden group">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase tracking-wider text-white/40">Average Score</span>
            <div className="w-7 h-7 rounded-lg bg-teal-500/10 border border-teal-500/20 flex items-center justify-center">
              <ShieldCheck className="w-3.5 h-3.5 text-teal-400" aria-hidden="true" />
            </div>
          </div>
          <div className="flex items-end justify-between">
            <div>
              <div className="text-2xl font-bold text-white font-mono tabular-nums">
                {kpis.avgVerification != null ? `${kpis.avgVerification}%` : '—'}
              </div>
              <div className="flex items-center gap-1.5 mt-1">
                <span className="text-[10px] font-mono text-white/40">
                  {kpis.avgVerification != null ? 'Mean score across runs' : 'Trend data unavailable'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export const BenchmarkKPIs = memo(BenchmarkKPIsComponent);
export default BenchmarkKPIs;

