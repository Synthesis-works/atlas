import React, { memo } from 'react';
import { Zap, ShieldCheck, Activity, BarChart2 } from 'lucide-react';

interface BarProps { label: string; count: number; maxCount: number; color: string; }

const Bar: React.FC<BarProps> = memo(({ label, count, maxCount, color }) => (
  <div className="flex items-center gap-3">
    <span className="text-[10px] font-mono text-white/40 w-16 shrink-0">{label}</span>
    <div className="flex-1 h-2 bg-white/5 rounded-full overflow-hidden">
      <div className={`h-full rounded-full ${color} transition-all duration-700`}
        style={{ width: `${(count / maxCount) * 100}%` }} />
    </div>
    <span className="text-[10px] font-mono text-white/40 w-6 text-right">{count}</span>
  </div>
));

Bar.displayName = 'Bar';

interface LineProps { data: { day?: string; hour?: string; rate?: number; length?: number }[]; valueKey: 'rate' | 'length'; color: string; height?: number; }

const MiniLineChart: React.FC<LineProps> = memo(({ data, valueKey, color, height = 72 }) => {
  const vals = data.map(d => (d as any)[valueKey] as number);
  const min = Math.min(...vals), max = Math.max(...vals);
  const W = 100, H = height;
  const step = W / (vals.length - 1);
  const ry = (v: number) => H - ((v - min) / (max - min || 1)) * (H - 4) - 2;
  const pts = vals.map((v, i) => `${(i * step).toFixed(1)},${ry(v).toFixed(1)}`).join(' ');
  const fill = vals.map((v, i) => `${(i * step).toFixed(1)},${ry(v).toFixed(1)}`).join(' ') +
    ` ${W},${H} 0,${H}`;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ height }} preserveAspectRatio="none" aria-hidden="true">
      <defs>
        <linearGradient id={`grad-${valueKey}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.3" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon points={fill} fill={`url(#grad-${valueKey})`} />
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5" strokeLinejoin="round" />
      <circle cx={(vals.length - 1) * step} cy={ry(vals[vals.length - 1])} r="2.5" fill={color} />
    </svg>
  );
});

MiniLineChart.displayName = 'MiniLineChart';

import { AtlasPieChart } from '@/components/atlas/charts';

interface PieProps { data: { reason: string; count: number }[]; }

const DonutChart: React.FC<PieProps> = memo(({ data }) => {
  const pieData = data.map(d => ({
    label: d.reason,
    value: d.count,
    // Relying entirely on Bklit default pie colors
  }));

  return (
    <div className="flex items-center gap-4">
      <div className="flex-shrink-0">
        <AtlasPieChart 
          data={pieData} 
          size={80} 
          innerRadius={25} 
          hoverEffect="grow" 
        />
      </div>
      <div className="space-y-1 flex-1 min-w-0">
        {pieData.slice(0, 5).map((s, i) => (
          <div key={i} className="flex items-center gap-1.5">
            <span 
              className="w-2 h-2 rounded-sm flex-shrink-0" 
              style={{ backgroundColor: `var(--chart-${(i % 5) + 1})` }} 
            />
            <span className="text-[10px] font-mono text-white/50 truncate">{s.label}</span>
            <span className="ml-auto text-[10px] font-mono text-white/35 tabular-nums">{s.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
});

DonutChart.displayName = 'DonutChart';

interface AnalyticsData {
  runtimeDistribution: { label: string; count: number }[];
  successRateTrend: { day: string; rate: number }[];
  queueLengthTrend: { hour: string; length: number }[];
  failureDistribution: { reason: string; count: number }[];
}

interface Props { data: AnalyticsData; }

export const AnalyticsGridComponent: React.FC<Props> = ({ data }) => {
  const maxRuntime = Math.max(...data.runtimeDistribution.map(d => d.count), 1);
  const latestSuccess = data.successRateTrend[data.successRateTrend.length - 1]?.rate ?? 0;
  const currentQueue = Math.round(data.queueLengthTrend[data.queueLengthTrend.length - 1]?.length ?? 0);

  const totalCompleted = data.runtimeDistribution.reduce((s, d) => s + d.count, 0);
  const MIDPOINTS: Record<string, number> = {
    '0-5s': 2.5, '5-10s': 7.5, '10-20s': 15, '20-60s': 40, '60s+': 90,
  };
  const meanSeconds = totalCompleted > 0
    ? data.runtimeDistribution.reduce((s, d) => s + d.count * (MIDPOINTS[d.label] ?? 30), 0) / totalCompleted
    : 0;
  const meanLabel = meanSeconds > 0
    ? meanSeconds >= 60 ? `${Math.floor(meanSeconds / 60)}m ${Math.round(meanSeconds % 60)}s` : `${Math.round(meanSeconds)}s`
    : '—';

  const topFailure = [...data.failureDistribution].sort((a, b) => b.count - a.count)[0];

  return (
    <section className="liquid-glass-card rounded-2xl p-5 sm:p-6 border border-white/10 space-y-5" aria-label="Evaluation Intelligence Surface">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/10 pb-4">
        <div>
          <div className="flex items-center gap-2 font-mono text-xs text-accent uppercase tracking-widest mb-1">
            <Zap className="w-3.5 h-3.5" aria-hidden="true" />
            <span>Step 3: Analyze — Evaluation Intelligence Surface</span>
          </div>
          <h2 className="text-lg font-bold text-white tracking-tight">Evaluation Intelligence & Performance Trends</h2>
          <p className="text-xs text-white/50 mt-0.5">
            Statistical runtime distribution, pass index trendlines, backlog history, and failure diagnostic breakdown.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 font-mono text-xs">
            <ShieldCheck className="w-3.5 h-3.5" aria-hidden="true" />
            Evaluation Pipeline Operational
          </span>
        </div>
      </div>

      {/* 4 Analytical Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 sm:gap-5 items-stretch">
        {/* Runtime Distribution */}
        <div className="p-4 sm:p-5 rounded-xl border border-white/5 bg-white/[0.02] flex flex-col justify-between space-y-4 h-full">
          <div>
            <div className="text-xs font-semibold text-white/90 flex items-center gap-1.5 font-mono">
              <BarChart2 className="w-3.5 h-3.5 text-blue-400" />
              Runtime Distribution
            </div>
            <div className="text-[10px] font-mono text-white/40 mt-1">Mean: {meanLabel} · {totalCompleted} completed runs</div>
          </div>
          <div className="space-y-2 pt-1 flex-1 flex flex-col justify-center">
            {data.runtimeDistribution.map(b => (
              <Bar key={b.label} label={b.label} count={b.count} maxCount={maxRuntime}
                color="bg-gradient-to-r from-blue-500 to-purple-500" />
            ))}
          </div>
          <div className="pt-1 text-[10px] font-mono text-white/30 border-t border-white/5 flex items-center justify-between">
            <span>Bucket counts from completed runs</span>
            <span className="text-blue-400 font-semibold">{totalCompleted} total</span>
          </div>
        </div>

        {/* Success Rate */}
        <div className="p-4 sm:p-5 rounded-xl border border-white/5 bg-white/[0.02] flex flex-col justify-between space-y-4 h-full">
          <div>
            <div className="text-xs font-semibold text-white/90 flex items-center gap-1.5 font-mono">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              Pass Index Trend
            </div>
            <div className="text-[10px] font-mono text-white/40 mt-1">{latestSuccess.toFixed(1)}% pass index (current)</div>
          </div>
          <div className="pt-1 space-y-2 flex-1 flex flex-col justify-end">
            <MiniLineChart data={data.successRateTrend} valueKey="rate" color="#34d399" height={76} />
            <div className="flex items-center justify-between text-[10px] font-mono text-white/40 pt-1 border-t border-white/5">
              <span>Current</span>
              <span className="text-emerald-400 font-semibold">{latestSuccess.toFixed(1)}%</span>
              <span>Current</span>
            </div>
          </div>
        </div>

        {/* Queue Length */}
        <div className="p-4 sm:p-5 rounded-xl border border-white/5 bg-white/[0.02] flex flex-col justify-between space-y-4 h-full">
          <div>
            <div className="text-xs font-semibold text-white/90 flex items-center gap-1.5 font-mono">
              <Activity className="w-3.5 h-3.5 text-indigo-400" />
              Queue Backlog History
            </div>
            <div className="text-[10px] font-mono text-white/40 mt-1">{currentQueue} jobs currently queued</div>
          </div>
<div className="pt-1 space-y-2 flex-1 flex flex-col justify-end">
              <MiniLineChart data={data.queueLengthTrend} valueKey="length" color="#818cf8" height={76} />
              <div className="flex items-center justify-between text-[10px] font-mono text-white/40 pt-1 border-t border-white/5">
                <span>Now</span>
                <span className="text-indigo-400 font-semibold">{currentQueue} queued</span>
                <span>Now</span>
              </div>
            </div>
          </div>

          {/* Failure Reasons */}
          <div className="p-4 sm:p-5 rounded-xl border border-white/5 bg-white/[0.02] flex flex-col justify-between space-y-3 h-full">
            <div>
              <div className="text-xs font-semibold text-white/90 font-mono">Failure Diagnostics</div>
              <div className="text-[10px] font-mono text-white/40 mt-1">
                {topFailure && topFailure.count > 0
                  ? `Top Failure: ${topFailure.reason} (${topFailure.count})`
                  : 'No failed executions recorded'}
              </div>
            </div>
            <div className="pt-1 flex-1 flex items-center">
              <DonutChart data={data.failureDistribution} />
            </div>
            <div className="space-y-1.5 pt-1 border-t border-white/5 text-[10px] font-mono">
              {topFailure && topFailure.count > 0 ? (
                <div className="flex items-center justify-between text-white/35">
                  <span>{topFailure.count} failed execution{topFailure.count !== 1 ? 's' : ''}</span>
                  <span>Review queue table for details</span>
                </div>
              ) : (
                <div className="flex items-center justify-between text-white/35">
                  <span>No failures</span>
                  <span>All executions healthy</span>
                </div>
              )}
            </div>
          </div>
      </div>
    </section>
  );
};

export const AnalyticsGrid = memo(AnalyticsGridComponent);
export default AnalyticsGrid;
