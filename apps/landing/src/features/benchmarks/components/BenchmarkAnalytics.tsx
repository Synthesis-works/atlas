import React, { useMemo } from 'react';
import {
  HeatmapCard,
  createHeatmapData,
} from '@/design/charts';
import { AtlasPieChart } from '@/components/atlas/charts';
import { ShieldCheck, Zap, Layers } from 'lucide-react';
import { useBenchmarkStore } from '../store/benchmarkStore';

const CATEGORY_COLORS: Record<string, string> = {
  coding: 'bg-cyan-400',
  reasoning: 'bg-indigo-500',
  mathematics: 'bg-emerald-400',
  planning: 'bg-amber-400',
  tool_use: 'bg-purple-400',
  knowledge: 'bg-blue-400',
  safety: 'bg-pink-400',
  language: 'bg-teal-400',
  vision: 'bg-orange-400',
  multimodal: 'bg-rose-400',
  agents: 'bg-violet-400',
};

export const BenchmarkAnalytics: React.FC = () => {
  const { benchmarks } = useBenchmarkStore();

  const scoredCount = benchmarks.filter((b) => b.averageScore != null || b.latestScore != null).length;

  // Aggregate real category distribution
  const { categoryDistribution, totalTasks, benchmarkTaxonomy } = useMemo(() => {
    if (!benchmarks || benchmarks.length === 0) {
      return {
        categoryDistribution: [],
        totalTasks: 0,
        benchmarkTaxonomy: [],
      };
    }

    const counts: Record<string, { count: number; cases: number; scores: number[] }> = {};
    let sumCases = 0;

    for (const b of benchmarks) {
      const cat = b.category || 'other';
      if (!counts[cat]) {
        counts[cat] = { count: 0, cases: 0, scores: [] };
      }
      counts[cat].count += 1;
      const cases = b.evaluationCaseCount ?? b.samplesCount ?? 0;
      counts[cat].cases += cases;
      sumCases += cases;
      if (b.averageScore != null) {
        counts[cat].scores.push(b.averageScore);
      }
    }

    const totalBenchmarks = benchmarks.length;
    const dist = Object.entries(counts).map(([cat, data]) => {
      const share = Math.round((data.count / totalBenchmarks) * 100);
      const avgScore =
        data.scores.length > 0
          ? `${(data.scores.reduce((a, b) => a + b, 0) / data.scores.length * 100).toFixed(1)}%`
          : '—';
      return {
        category: cat.charAt(0).toUpperCase() + cat.slice(1).replace('_', ' '),
        tasks: data.count.toString(),
        samples: data.cases > 0 ? data.cases.toLocaleString() : '—',
        share,
        color: CATEGORY_COLORS[cat] || 'bg-blue-500',
        trend: avgScore !== '—' ? `Avg: ${avgScore}` : `${data.count} suites`,
      };
    });

    const taxonomy = Object.entries(counts).map(([cat, data]) => ({
      label: cat.charAt(0).toUpperCase() + cat.slice(1).replace('_', ' '),
      value: data.count,
    }));

    return {
      categoryDistribution: dist,
      totalTasks: sumCases,
      benchmarkTaxonomy: taxonomy,
    };
  }, [benchmarks]);

  // Real capability matrix: only when benchmarks with scores and real model runs exist
  const capabilityHeatmapData = useMemo(() => {
    const scoredBenchmarks = benchmarks.filter(
      (b) => b.averageScore != null || b.latestScore != null
    );

    if (scoredBenchmarks.length === 0) {
      return null;
    }

    const benchmarkNames = scoredBenchmarks.map((b) => b.name).slice(0, 6);
    // Find models that have executed
    const models = Array.from(
      new Set(
        scoredBenchmarks
          .flatMap((b) => b.compatibleModels)
          .filter(Boolean)
      )
    );
    const modelLabels = models.length > 0 ? models.slice(0, 5) : ['Evaluated Model'];

    return createHeatmapData(
      modelLabels,
      benchmarkNames,
      (_model, bName) => {
        const found = scoredBenchmarks.find((b) => b.name === bName);
        const score = found?.latestScore ?? found?.averageScore;
        return score != null ? Math.round(score * 100) : 0;
      }
    );
  }, [benchmarks]);

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
            {scoredCount > 0 ? `${scoredCount} Scored` : 'Awaiting Telemetry'}
          </span>
          <span className="px-3 py-1 rounded-full bg-white/5 border border-white/10 text-white/40 font-mono text-xs hidden md:inline-block">
            {benchmarks.length} Total Suites
          </span>
        </div>
      </div>

      {/* Primary Analytical Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-stretch">
        {/* Capability Matrix / Honest Empty State */}
        <div className="xl:col-span-7 flex flex-col min-w-0">
          {capabilityHeatmapData ? (
            <HeatmapCard
              title="Model × Benchmark Capability Matrix"
              subtitle="Normalized accuracy scores (0–100) across real benchmark evaluations"
              badge="Evaluated Benchmarks"
              data={capabilityHeatmapData}
            />
          ) : (
            <div className="w-full h-full min-h-[260px] relative flex flex-col items-center justify-center gap-3 bg-[#0c0c0e] border border-white/[0.08] rounded-2xl p-8 shadow-xl text-center">
              <Layers className="w-8 h-8 text-white/20" />
              <div>
                <h4 className="text-sm font-semibold text-white/80 tracking-tight">
                  Model × Benchmark Capability Matrix
                </h4>
                <p className="text-xs text-white/40 mt-1">No capability evaluations recorded yet</p>
              </div>
            </div>
          )}
        </div>

        {/* Taxonomy Explorer — Structural Drilldown */}
        <div className="xl:col-span-5 flex flex-col min-w-0">
          <AtlasPieChart
            title="Benchmark Taxonomy Drilldown"
            description="Hierarchical distribution across registered benchmark categories"
            data={benchmarkTaxonomy}
            size={240}
            innerRadius={70}
            emptyMessage="No benchmark categories yet"
            centerLabel={`${benchmarks.length} Suites`}
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
            Domain Task Volume & Category Distribution
          </span>
          <span className="text-[10px] font-mono text-white/30">
            {totalTasks > 0 ? `${totalTasks.toLocaleString()} Total Cases Configured` : 'No Case Counts Reported'}
          </span>
        </div>

        {categoryDistribution.length > 0 ? (
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
                    <span className="text-white/30 block">Suites</span>
                    <span className="text-white/90 font-semibold">{c.tasks}</span>
                  </div>
                  <div className="text-right">
                    <span className="text-white/30 block">Cases</span>
                    <span className="text-white/70 font-semibold">{c.samples}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-6 rounded-xl border border-white/5 bg-white/[0.01] text-center text-xs font-mono text-white/40">
            No category distribution available
          </div>
        )}
      </div>
    </div>
  );
};

export default BenchmarkAnalytics;
