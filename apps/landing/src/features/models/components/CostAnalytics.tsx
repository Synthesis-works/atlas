import { useState } from 'react';
import { DollarSign, TrendingUp, Sparkles } from 'lucide-react';
import { useModelsStore } from '../store/modelsStore';
import { RingCard, type RingItem } from '@/design/charts/RingChart/RingChart';


export function CostAnalytics() {
  const { models } = useModelsStore();
  const [hoveredRingIndex, setHoveredRingIndex] = useState<number | null>(null);

  const sorted    = [...models].sort((a, b) => b.cost.averageCostPerCall - a.cost.averageCostPerCall);
  const monthly   = models.reduce((s, m) => s + m.cost.monthlyEstimate,  0);
  const projected = models.reduce((s, m) => s + m.cost.projectedMonthly, 0);

  const ringData: RingItem[] = sorted.slice(0, 5).map((m) => ({
    label: m.name,
    value: Math.round(m.cost.monthlyEstimate),
  }));

  return (
    <div className="liquid-glass-card rounded-2xl overflow-hidden h-full flex flex-col p-5 border border-white/[0.08] space-y-4 text-white">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-white/[0.07] pb-3 shrink-0">
        <div>
          <div className="flex items-center gap-1.5 font-mono text-xs text-emerald-400 font-bold uppercase tracking-wider mb-0.5">
            <DollarSign className="w-4 h-4" />
            <span>Fleet Cost &amp; Expenditure Analysis</span>
          </div>
          <h3 className="text-sm font-semibold text-white tracking-tight">Monthly Spend Distribution</h3>
        </div>
        <span className="text-xs font-mono text-white/40 bg-white/[0.04] px-2.5 py-1 rounded-md border border-white/[0.08]">
          {models.length} Endpoints
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 flex-1 min-h-0">
        {/* KPI cards + recommendation */}
        <div className="space-y-3 flex flex-col justify-between">
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-4 space-y-1.5">
              <span className="text-[10px] font-mono text-emerald-400 uppercase tracking-wider font-bold">Monthly Run Rate</span>
              <div className="text-xl font-black text-white font-mono tracking-tight">${monthly.toFixed(0)}</div>
              <span className="text-[10px] text-white/40 font-mono">Current active spend</span>
            </div>
            <div className="bg-violet-500/10 border border-violet-500/20 rounded-xl p-4 space-y-1.5">
              <span className="text-[10px] font-mono text-violet-400 uppercase tracking-wider font-bold">Projected Spend</span>
              <div className="text-xl font-black text-white font-mono tracking-tight">${projected.toFixed(0)}</div>
              <span className="text-[10px] text-violet-400 font-mono flex items-center gap-1 font-bold">
                <TrendingUp className="w-3 h-3" /> +4.2% next month
              </span>
            </div>
          </div>

          {/* Optimization recommendation */}
          <div className="p-4 rounded-xl border border-amber-500/20 bg-amber-500/10 space-y-2 font-mono text-xs">
            <div className="flex items-center gap-1.5 text-amber-400 font-bold text-[10px] uppercase tracking-wider">
              <Sparkles className="w-3.5 h-3.5" /> AI Cost Optimization
            </div>
            <p className="text-white/55 font-sans text-xs leading-relaxed">
              Migrating 30% of non-critical requests from Claude 4 Sonnet to GPT-4o Mini reduces monthly run rate by{' '}
              <span className="text-emerald-400 font-bold font-mono bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">
                $1,840/mo
              </span>{' '}
              without accuracy degradation.
            </p>
          </div>
        </div>

        {/* Bklit Ring Chart — dark themed */}
        <div className="flex flex-col min-h-0">
          <RingCard
            title="Fleet Cost Share"
            subtitle="Top 5 endpoints — monthly run rate"
            badge="Bklit Ring"
            prefix="$"
            data={ringData}
            hoveredIndex={hoveredRingIndex}
            onHoverChange={setHoveredRingIndex}
            size={180}
          />
        </div>
      </div>
    </div>
  );
}
