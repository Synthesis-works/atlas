import React from 'react';
import { Search, Plus, GitCompare, Download, Activity, Cpu, ShieldCheck, Zap, DollarSign, Command } from 'lucide-react';
import { useModelsStore } from '../store/modelsStore';

const QUICK_FILTER_CHIPS = [
  { label: 'status:healthy', key: 'healthy' },
  { label: 'runtime:vllm', key: 'vllm' },
  { label: 'gpu:a100', key: 'a100' },
  { label: 'provider:openai', key: 'openai' },
  { label: 'cost>0.01', key: 'cost' },
];

export const FleetHealthHero: React.FC = () => {
  const { search, setSearch, toggleCommandPalette, toggleCompare, compareIds } = useModelsStore();

  return (
    <div className="liquid-glass-card rounded-2xl p-5 sm:p-6 border border-white/10 space-y-5">
      {/* Dominant Fleet Health Hero Header (Focal Point) */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-5 border-b border-white/[0.08] pb-5">
        <div className="space-y-2 min-w-0">
          <div className="flex items-center gap-2 text-xs font-mono text-emerald-400 uppercase tracking-widest font-semibold">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>AI Fleet Control Center</span>
            <span className="text-white/20">•</span>
            <span className="text-white/40">Updated 3s ago</span>
          </div>

          <div className="flex flex-wrap items-baseline gap-3">
            <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white flex items-center gap-3">
              <span className="text-emerald-400">🟢 FLEET HEALTHY</span>
            </h1>
            <span className="text-xl sm:text-2xl font-mono font-bold text-emerald-300 px-3 py-1 rounded-xl bg-emerald-500/15 border border-emerald-500/30">
              96.4% Index
            </span>
          </div>

          <p className="text-xs sm:text-sm text-white/50 max-w-2xl leading-relaxed">
            18 Active Endpoints · 2 Degraded · 0 Failed · Real-time inference routing and infrastructure health.
          </p>
        </div>

        {/* Hero Global Actions */}
        <div className="flex flex-wrap items-center gap-2.5 shrink-0">
          <button
            onClick={toggleCommandPalette}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-accent/15 border border-accent/40 text-accent hover:bg-accent/25 text-xs font-mono font-semibold transition-all cursor-pointer shadow-[0_0_15px_rgba(99,102,241,0.2)]"
          >
            <Command className="w-3.5 h-3.5" />
            <span>Command Palette</span>
            <kbd className="hidden sm:inline-block px-1.5 py-0.2 rounded text-[10px] bg-black/40 text-accent/80 border border-accent/30 font-mono">⌘K</kbd>
          </button>

          {compareIds.length > 0 && (
            <button
              onClick={() => toggleCompare('')}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-blue-500/15 border border-blue-500/30 text-blue-300 text-xs font-mono font-semibold hover:bg-blue-500/25 transition-colors cursor-pointer"
            >
              <GitCompare className="w-3.5 h-3.5" />
              Compare ({compareIds.length})
            </button>
          )}

          <button className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-white/5 border border-white/10 text-white/80 text-xs font-mono hover:bg-white/10 transition-colors cursor-pointer">
            <Download className="w-3.5 h-3.5" />
            Export
          </button>

          <button className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-emerald-400 text-neutral-950 text-xs font-semibold hover:bg-emerald-300 transition-colors shadow-lg shadow-emerald-400/20 cursor-pointer">
            <Plus className="w-3.5 h-3.5" />
            Deploy Model
          </button>
        </div>
      </div>

      {/* Secondary Operational Telemetry Ribbon */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono">
        <div className="p-3 rounded-xl border border-white/5 bg-white/[0.02] space-y-1">
          <div className="flex items-center gap-1.5 text-white/40">
            <Zap className="w-3.5 h-3.5 text-amber-400" />
            <span>Total Traffic</span>
          </div>
          <div className="text-base font-bold text-white font-mono">1,420 req/s</div>
        </div>

        <div className="p-3 rounded-xl border border-white/5 bg-white/[0.02] space-y-1">
          <div className="flex items-center gap-1.5 text-white/40">
            <Activity className="w-3.5 h-3.5 text-blue-400" />
            <span>p90 Latency</span>
          </div>
          <div className="text-base font-bold text-white font-mono">184 ms</div>
        </div>

        <div className="p-3 rounded-xl border border-white/5 bg-white/[0.02] space-y-1">
          <div className="flex items-center gap-1.5 text-white/40">
            <Cpu className="w-3.5 h-3.5 text-purple-400" />
            <span>GPU Saturation</span>
          </div>
          <div className="text-base font-bold text-white font-mono">78% Saturation</div>
        </div>

        <div className="p-3 rounded-xl border border-white/5 bg-white/[0.02] space-y-1">
          <div className="flex items-center gap-1.5 text-white/40">
            <DollarSign className="w-3.5 h-3.5 text-emerald-400" />
            <span>Monthly Run Rate</span>
          </div>
          <div className="text-base font-bold text-white font-mono">$14,820.50 / mo</div>
        </div>
      </div>

      {/* Search Bar & Filter Chips */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-2 border-t border-white/[0.06]">
        <div className="flex items-center gap-2 bg-white/[0.03] border border-white/[0.08] rounded-xl px-3.5 py-2 flex-1 max-w-xl">
          <Search className="w-4 h-4 text-white/30 shrink-0" />
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search model fleet by name, provider, runtime (vLLM, TensorRT), region…"
            className="bg-transparent text-xs font-mono text-white placeholder:text-white/30 outline-none flex-1"
          />
        </div>

        <div className="flex items-center gap-1.5 overflow-x-auto pb-0.5 scrollbar-none shrink-0">
          {QUICK_FILTER_CHIPS.map((chip) => (
            <button
              key={chip.key}
              onClick={() => setSearch(chip.label)}
              className="px-2.5 py-1 rounded-lg text-[10px] font-mono text-white/40 bg-white/[0.03] border border-white/[0.06] hover:border-white/20 hover:text-white transition-colors cursor-pointer"
            >
              {chip.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
