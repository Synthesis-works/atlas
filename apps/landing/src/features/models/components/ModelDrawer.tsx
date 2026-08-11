import React, { useState } from 'react';
import { X, ExternalLink, GitBranch, Cpu, DollarSign, Activity, Settings, BookOpen, BarChart3, Clock, Trophy, GitCompare } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useModelsStore } from '../store/modelsStore';
import { CapabilityRadar } from './CapabilityRadar';
import { CapabilityGrid } from './CapabilityGrid';
import { ModelHealthPanel } from './HealthGauge';
import { ModelStatusBadge, DeployStatusBadge } from './StatusBadge';

const TABS = [
  { id: 'overview',    label: 'Overview',     icon: Cpu },
  { id: 'benchmarks',  label: 'Benchmarks',   icon: BarChart3 },
  { id: 'evaluations', label: 'Evaluations',  icon: Activity },
  { id: 'capabilities',label: 'Capabilities', icon: GitBranch },
  { id: 'compare',     label: 'Compare',      icon: GitCompare },
  { id: 'versions',    label: 'Versions',     icon: Clock },
  { id: 'pricing',     label: 'Pricing',      icon: DollarSign },
  { id: 'config',      label: 'Config',       icon: Settings },
  { id: 'docs',        label: 'Docs',         icon: BookOpen },
];

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 py-2 border-b border-white/[0.04] font-mono text-xs">
      <span className="text-white/40 shrink-0">{label}</span>
      <span className="text-white/80 text-right font-medium">{value}</span>
    </div>
  );
}

function OverviewTab() {
  const { selectedModel: m } = useModelsStore();
  if (!m) return null;
  return (
    <div className="space-y-6">
      {/* Industry Rank & Radar */}
      <div className="p-4 rounded-xl border border-accent/30 bg-accent/5 flex flex-col items-center justify-center space-y-3">
        <div className="flex items-center gap-1.5 px-3 py-0.5 rounded-full bg-accent/20 text-accent border border-accent/30 text-[10px] font-mono font-bold uppercase tracking-wider">
          <Trophy className="w-3 h-3 text-amber-400" /> Industry Rank: Top 5% Global Leader
        </div>
        <CapabilityRadar model={m} size={320} showLabels />
      </div>

      {/* Profile Info */}
      <div className="space-y-1">
        <div className="text-[10px] font-mono uppercase tracking-wider text-white/30 font-semibold mb-2">Model Specifications Profile</div>
        <Row label="Provider"     value={m.provider} />
        <Row label="Family"       value={m.family} />
        <Row label="Architecture" value={m.architecture} />
        <Row label="Tokenizer"    value={m.tokenizer} />
        <Row label="Parameters"   value={m.parameterCount} />
        <Row label="Context Window" value={`${(m.contextWindow / 1000).toFixed(0)}k tokens`} />
        <Row label="License"      value={m.license} />
        <Row label="Released"     value={m.releaseDate} />
        <Row label="Last Eval"    value={m.lastEvaluated.slice(0, 10)} />
        <Row label="Evals Run"    value={m.evaluationCount} />
        <Row label="Overall Score" value={<span className="text-accent font-bold font-mono">{m.overallScore.toFixed(1)} / 100</span>} />
        <Row label="p90 Latency"  value={`${m.latencyMs}ms`} />
        <Row label="Status"       value={<ModelStatusBadge status={m.status} />} />
        <Row label="Deployment"   value={<DeployStatusBadge status={m.deployment.status} />} />
      </div>

      {/* Intelligence Card */}
      <div className="space-y-3">
        <p className="text-xs text-white/30 uppercase font-mono tracking-wider">Model Intelligence Card</p>
        {[
          { title: 'Strengths',      items: m.intelligenceCard.strengths,    color: 'text-emerald-400', dot: 'bg-emerald-500' },
          { title: 'Weaknesses',     items: m.intelligenceCard.weaknesses,   color: 'text-rose-400',   dot: 'bg-rose-500' },
          { title: 'Best Use Cases', items: m.intelligenceCard.bestUseCases, color: 'text-accent',    dot: 'bg-accent' },
          { title: 'Avoid For',      items: m.intelligenceCard.avoidFor,     color: 'text-amber-400', dot: 'bg-amber-400' },
        ].map(({ title, items, color, dot }) => (
          <div key={title} className="bg-white/[0.02] rounded-xl p-3 border border-white/[0.05]">
            <p className={`text-xs font-mono font-semibold mb-2 ${color}`}>{title}</p>
            <ul className="space-y-1 font-sans">
              {items.map((item, i) => (
                <li key={i} className="flex items-start gap-2 text-xs text-white/60">
                  <span className={`w-1.5 h-1.5 rounded-full shrink-0 mt-1 ${dot}`} />
                  {item}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      {/* Health gauges */}
      <div>
        <p className="text-xs text-white/30 uppercase font-mono tracking-wider mb-3">Model Operational Health</p>
        <ModelHealthPanel
          availability={m.health.availability}
          reliability={m.health.reliability}
          errorRate={m.health.errorRate}
          responseQuality={m.health.responseQuality}
        />
      </div>
    </div>
  );
}

function BenchmarksTab() {
  const { selectedModel: m } = useModelsStore();
  if (!m) return null;
  return (
    <div className="space-y-3">
      <div className="text-[10px] font-mono uppercase tracking-wider text-white/30 font-semibold mb-2">Standardized Benchmark Records</div>
      {m.benchmarkScores.map(b => (
        <div key={b.benchmarkId} className="bg-white/[0.02] border border-white/[0.05] rounded-xl p-3 space-y-2 font-mono">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-bold text-white">{b.benchmarkName}</p>
              <p className="text-[10px] text-white/30">{b.category} · {b.evaluatedAt}</p>
            </div>
            <span className="text-base font-bold text-accent tabular-nums">{b.score.toFixed(1)}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex-1 h-1 bg-white/[0.06] rounded-full overflow-hidden">
              <div className="h-full rounded-full bg-accent" style={{ width: `${b.score}%` }} />
            </div>
            <span className="text-[10px] text-white/40">Percentile: p{b.percentile}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

function EvaluationsTab() {
  const { selectedModel: m } = useModelsStore();
  if (!m) return null;
  return (
    <div className="space-y-2 font-mono">
      <div className="text-[10px] font-mono uppercase tracking-wider text-white/30 font-semibold mb-2">Recent Run History</div>
      {m.evaluationHistory.map(e => (
        <div key={e.id} className="flex items-center gap-3 bg-white/[0.02] border border-white/[0.05] rounded-xl p-3">
          <div className={`w-2 h-2 rounded-full shrink-0 ${e.status === 'completed' ? 'bg-emerald-500' : 'bg-rose-500'}`} />
          <div className="flex-1 min-w-0">
            <p className="text-xs font-semibold text-white/80">{e.benchmarkName}</p>
            <p className="text-[10px] text-white/30">{e.runAt} · {e.duration}</p>
          </div>
          <span className="text-xs font-bold text-accent tabular-nums">{e.score.toFixed(1)}</span>
        </div>
      ))}
    </div>
  );
}

function CapabilitiesTab() {
  const { selectedModel: m } = useModelsStore();
  if (!m) return null;
  return (
    <div className="space-y-4 font-mono text-xs">
      <div>
        <p className="text-[10px] text-white/30 uppercase tracking-wider font-semibold mb-2">Supported Capabilities</p>
        <CapabilityGrid tags={m.capabilityTags} />
      </div>
      <div>
        <p className="text-[10px] text-white/30 uppercase tracking-wider font-semibold mb-3">Domain Capability Scores & Industry Rank</p>
        <div className="space-y-2.5">
          {m.profile.capabilities.map(c => (
            <div key={c.domain} className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-white/60 font-medium">{c.domain}</span>
                <span className="text-accent font-bold">{c.score.toFixed(1)} / 100</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="flex-1 h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
                  <div className="h-full rounded-full bg-accent" style={{ width: `${c.score}%` }} />
                </div>
                <span className="px-1.5 py-0.2 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 text-[9px] font-bold">Top 5%</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function CompareTab() {
  const { selectedModel: m, models } = useModelsStore();
  const [targetId, setTargetId] = useState(models.find(x => x.id !== m?.id)?.id || models[0]?.id);

  if (!m) return null;
  const targetModel = models.find(x => x.id === targetId) || models[0];

  return (
    <div className="space-y-4 font-mono text-xs">
      <div className="p-3 rounded-xl border border-accent/30 bg-accent/5 space-y-2">
        <div className="flex items-center gap-1.5 text-accent font-bold text-xs uppercase tracking-wider">
          <GitCompare className="w-4 h-4" /> Inline Model Comparison Tool
        </div>
        <p className="text-white/60 font-sans text-xs">
          Select a secondary model to compare latency, accuracy, and cost side-by-side.
        </p>
        <select
          value={targetId}
          onChange={(e) => setTargetId(e.target.value)}
          className="w-full p-2 rounded-lg bg-black/40 border border-white/10 text-white font-mono text-xs outline-none"
        >
          {models.filter(x => x.id !== m.id).map(x => (
            <option key={x.id} value={x.id}>{x.name} ({x.provider})</option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-2 gap-3 text-center">
        <div className="p-3 rounded-xl border border-white/10 bg-white/[0.02]">
          <div className="text-[10px] text-white/40 uppercase">Target (Selected)</div>
          <div className="text-sm font-bold text-accent truncate mt-1">{m.name}</div>
          <div className="text-xs text-emerald-400 mt-1">{m.overallScore.toFixed(1)} Score</div>
          <div className="text-xs text-blue-400 mt-0.5">{m.latencyMs}ms p90</div>
        </div>

        <div className="p-3 rounded-xl border border-white/10 bg-white/[0.02]">
          <div className="text-[10px] text-white/40 uppercase">Comparison Model</div>
          <div className="text-sm font-bold text-purple-300 truncate mt-1">{targetModel.name}</div>
          <div className="text-xs text-emerald-400 mt-1">{targetModel.overallScore.toFixed(1)} Score</div>
          <div className="text-xs text-blue-400 mt-0.5">{targetModel.latencyMs}ms p90</div>
        </div>
      </div>
    </div>
  );
}

function VersionsTab() {
  const { selectedModel: m } = useModelsStore();
  if (!m) return null;
  return (
    <div className="relative pl-5 border-l border-white/[0.06] space-y-5 font-mono">
      {m.versions.map((v) => (
        <div key={v.version} className="relative">
          <div className={`absolute -left-[calc(1.25rem+1px)] top-1 w-2.5 h-2.5 rounded-full border-2 ${
            v.isCurrent ? 'bg-accent border-accent/50' : 'bg-white/10 border-white/20'
          }`} />
          <div className="bg-white/[0.02] border border-white/[0.05] rounded-xl p-3">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-mono text-accent/70">v{v.version}</span>
              <span className="text-xs font-bold text-white">{v.name}</span>
            </div>
            <p className="text-[10px] text-white/30 mb-1">{v.releaseDate}</p>
            <p className="text-xs text-white/60 font-sans">{v.changes}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

function PricingTab() {
  const { selectedModel: m } = useModelsStore();
  if (!m) return null;
  const c = m.cost;
  return (
    <div className="space-y-3 font-mono text-xs">
      {[
        { label: 'Input cost',        value: `$${(c.inputPer1kTokens * 1000).toFixed(3)}`,  sub: '/ 1k tokens' },
        { label: 'Output cost',       value: `$${(c.outputPer1kTokens * 1000).toFixed(3)}`, sub: '/ 1k tokens' },
        { label: 'Avg cost / call',   value: `$${(c.averageCostPerCall * 1000).toFixed(3)}`,sub: 'average' },
        { label: 'Monthly estimate',  value: `$${c.monthlyEstimate.toFixed(2)}`,   sub: 'current usage' },
        { label: 'Projected monthly', value: `$${c.projectedMonthly.toFixed(2)}`,  sub: 'next 30 days' },
      ].map(r => (
        <div key={r.label} className="flex items-center justify-between p-3 bg-white/[0.02] border border-white/[0.05] rounded-xl">
          <div>
            <p className="text-xs font-semibold text-white/80">{r.label}</p>
            <p className="text-[10px] text-white/30">{r.sub}</p>
          </div>
          <span className="text-sm font-bold text-white tabular-nums">{r.value}</span>
        </div>
      ))}
    </div>
  );
}

function ConfigTab() {
  const { selectedModel: m } = useModelsStore();
  if (!m) return null;
  const d = m.deployment;
  return (
    <div className="space-y-4 font-mono text-xs">
      <div>
        <p className="text-[10px] text-white/30 uppercase tracking-wider font-semibold mb-2">Default Inference Config</p>
        <Row label="Temperature" value={m.defaultTemperature} />
        <Row label="Top P"       value={m.defaultTopP} />
        <Row label="Max Tokens"  value={m.defaultMaxTokens.toLocaleString()} />
      </div>
      <div>
        <p className="text-[10px] text-white/30 uppercase tracking-wider font-semibold mb-2 mt-4">Deployment Infrastructure Specs</p>
        {d.endpoint  && <Row label="Endpoint" value={<span className="font-mono text-accent break-all">{d.endpoint}</span>} />}
        {d.region    && <Row label="Region"   value={d.region} />}
        {d.runtime   && <Row label="Runtime"  value={d.runtime} />}
        {d.gpu       && <Row label="GPU"      value={d.gpu} />}
        {d.replicas  && <Row label="Replicas" value={d.replicas} />}
      </div>
    </div>
  );
}

function DocsTab() {
  const { selectedModel: m } = useModelsStore();
  if (!m) return null;
  const links = [
    { label: 'Model Card',      href: '#' },
    { label: 'License & Terms', href: '#' },
    { label: 'API Reference',   href: '#' },
    { label: 'Usage Examples',  href: '#' },
  ];
  return (
    <div className="space-y-2 font-mono text-xs">
      {links.map(l => (
        <a key={l.label} href={l.href}
          className="flex items-center justify-between p-3 bg-white/[0.02] border border-white/[0.05] rounded-xl hover:bg-white/[0.04] transition-colors group">
          <span className="text-xs text-white/60 group-hover:text-white transition-colors">{l.label}</span>
          <ExternalLink className="w-3.5 h-3.5 text-white/20 group-hover:text-accent transition-colors" />
        </a>
      ))}
    </div>
  );
}

const TAB_CONTENT: Record<string, React.FC> = {
  overview: OverviewTab, benchmarks: BenchmarksTab, evaluations: EvaluationsTab,
  capabilities: CapabilitiesTab, compare: CompareTab, versions: VersionsTab,
  pricing: PricingTab, config: ConfigTab, docs: DocsTab,
};

export function ModelDrawer() {
  const { selectedModel: m, drawerOpen, drawerTab, closeDrawer, setDrawerTab } = useModelsStore();

  const Content = TAB_CONTENT[drawerTab] ?? OverviewTab;

  return (
    <AnimatePresence>
      {drawerOpen && m && (
        <>
          {/* Backdrop */}
          <motion.div
            key="backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={closeDrawer}
            className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
          />
          {/* Drawer */}
          <motion.aside
            key="drawer"
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', stiffness: 320, damping: 32 }}
            className="fixed top-0 right-0 h-full w-full max-w-md z-50 flex flex-col border-l border-white/10"
            style={{ background: '#0a0a0f' }}
          >
            {/* Header */}
            <div className="px-5 pt-5 pb-4 border-b border-white/10 shrink-0 bg-white/[0.01]">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <ModelStatusBadge status={m.status} />
                    <DeployStatusBadge status={m.deployment.status} />
                  </div>
                  <h2 className="text-lg font-bold text-white font-mono truncate">{m.name}</h2>
                  <p className="text-xs text-white/40 font-mono">{m.provider} · {m.family}</p>
                </div>
                <button
                  onClick={closeDrawer}
                  className="p-2 rounded-lg hover:bg-white/10 text-white/40 hover:text-white transition-colors cursor-pointer shrink-0"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
              {/* Telemetry Bar */}
              <div className="flex items-center gap-4 mt-3 text-xs font-mono text-white/40 pt-3 border-t border-white/5">
                <span>Score: <span className="text-accent font-bold">{m.overallScore.toFixed(1)}</span></span>
                <span>p90: <span className="text-white font-semibold">{m.latencyMs}ms</span></span>
                <span>Evals: <span className="text-white font-semibold">{m.evaluationCount}</span></span>
              </div>
            </div>

            {/* Apple Settings-style Tab Profile Navigation Bar */}
            <div className="flex overflow-x-auto gap-1 px-3 py-2 border-b border-white/5 shrink-0 scrollbar-none bg-white/[0.005]">
              {TABS.map(t => {
                const Icon = t.icon;
                return (
                  <button
                    key={t.id}
                    onClick={() => setDrawerTab(t.id)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono whitespace-nowrap transition-colors cursor-pointer shrink-0 ${
                      drawerTab === t.id
                        ? 'bg-white/10 text-white font-semibold border border-white/15'
                        : 'text-white/40 hover:text-white/70'
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5 shrink-0" />
                    {t.label}
                  </button>
                );
              })}
            </div>

            {/* Content Profile Section */}
            <div className="flex-1 overflow-y-auto px-5 py-5 scrollbar-thin scrollbar-thumb-white/10">
              <Content />
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
