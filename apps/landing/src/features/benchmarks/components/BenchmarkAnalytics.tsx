import React from 'react';
import {
  HeatmapCard,
  createHeatmapData,
} from '@/design/charts';
import { AtlasPieChart } from '@/components/atlas/charts';
import { ShieldCheck, Zap, Layers } from 'lucide-react';

const benchmarkMatrix = createHeatmapData(
  ['GPT-5', 'Claude 3.5', 'Gemini 2.0', 'Llama 3.3', 'Qwen 2.5'],
  ['Reasoning', 'Math', 'Code', 'Safety', 'Vision', 'Tools'],
  (m, b) => (m.charCodeAt(0) * b.charCodeAt(0) * 11) % 40 + 60,
);

const benchmarkTaxonomy = [
  { label: 'Reasoning', value: 3 },
  { label: 'Coding', value: 3 },
  { label: 'Safety', value: 3 },
];

const categoryDistribution = [
  { category: 'Reasoning & Logic', tasks: '16,400', samples: '1.2M', share: 42, color: 'bg-indigo-500', trend: 'Optimal' },
  { category: 'Code Synthesis & Agentic', tasks: '12,800', samples: '850K', share: 32, color: 'bg-cyan-400', trend: 'High Density' },
  { category: 'Safety & Red-Teaming', tasks: '8,400', samples: '420K', share: 18, color: 'bg-pink-400', trend: 'Guarded' },
  { category: 'Vision & Multimodal', tasks: '4,200', samples: '210K', share: 8, color: 'bg-emerald-400', trend: 'Expanding' },
];

export const BenchmarkAnalytics: React.FC = () => {
  return (
    <div className="liquid-glass-card rounded-2xl p-5 sm:p-6 border border-white/10 space-y-6">
      {/* Performance Intelligence Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/10 pb-4">
        <div>
          <div className="flex items-center gap-2 font-mono text-xs text-accent uppercase tracking-widest mb-1">
            <Zap className="w-3.5 h-3.5" />
            <span>Step 3: Analyze — Performance Intelligence Surface</span>
          </div>
          <h2 className="text-lg font-bold text-white tracking-tight">Model Capability & Category Intelligence</h2>
          <p className="text-xs text-white/50 mt-0.5">
            Cross-domain benchmark validation, capability coverage matrix, and structural hierarchy.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 font-mono text-xs">
            <ShieldCheck className="w-3.5 h-3.5" />
            Ecosystem Healthy
          </span>
          <span className="px-3 py-1 rounded-full bg-white/5 border border-white/10 text-white/40 font-mono text-xs hidden md:inline-block">
            5 Models × 6 Domains
          </span>
        </div>
      </div>

      {/* Primary Analytical Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-stretch">
        {/* Heatmap Card — Capability Matrix */}
        <div className="xl:col-span-7 flex flex-col min-w-0">
          <HeatmapCard
            title="Model × Benchmark Capability Matrix"
            subtitle="Normalized accuracy scores (0–100) across benchmark disciplines"
            badge="Model Frontier"
            data={benchmarkMatrix}
          />
        </div>

        {/* Taxonomy Explorer — Structural Drilldown */}
        <div className="xl:col-span-5 flex flex-col min-w-0">
          <AtlasPieChart
            title="Benchmark Taxonomy Drilldown"
            description="Hierarchical structure from discipline to task suites"
            data={benchmarkTaxonomy}
            size={240}
            innerRadius={70}
            centerLabel="9 Suites"
            showLegend={true}
            hoverEffect="grow"
            className="liquid-glass-card rounded-2xl p-5 border border-white/10 w-full"
          />
        </div>
      </div>

      {/* Category Task Density Matrix */}
      <div className="pt-2">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-mono uppercase tracking-wider text-white/40 flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5 text-white/30" />
            Domain Task Volume & Sample Weight Distribution
          </span>
          <span className="text-[10px] font-mono text-white/30">41,800 Total Tasks Configured</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          {categoryDistribution.map((c) => (
            <div
              key={c.category}
              className="p-4 rounded-xl border border-white/5 bg-white/[0.02] hover:bg-white/[0.04] transition-colors space-y-3 flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-white">{c.category}</span>
                  <span className="text-xs font-mono font-bold text-accent">{c.share}%</span>
                </div>
                <div className="mt-2 w-full h-1.5 rounded-full bg-white/5 overflow-hidden">
                  <div className={`h-full rounded-full ${c.color}`} style={{ width: `${c.share}%` }} />
                </div>
              </div>

              <div className="flex items-center justify-between text-[11px] font-mono text-white/40 pt-2 border-t border-white/5">
                <div>
                  <span className="text-white/30 block">Tasks</span>
                  <span className="text-white/90 font-semibold">{c.tasks}</span>
                </div>
                <div className="text-right">
                  <span className="text-white/30 block">Status</span>
                  <span className="text-emerald-400 font-semibold">{c.trend}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default BenchmarkAnalytics;
