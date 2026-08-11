import { Search, Plus, GitCompare, Download, Cpu } from 'lucide-react';
import { useModelsStore } from '../store/modelsStore';

const FILTER_CHIPS = [
  { label: 'provider:openai', key: 'openai' },
  { label: 'family:llama', key: 'llama' },
  { label: 'status:active', key: 'active' },
  { label: 'context>128k', key: 'context128k' },
  { label: 'vision:true', key: 'vision' },
];

export function ModelsHeader() {
  const { search, setSearch } = useModelsStore();

  return (
    <div className="flex flex-col gap-4 mb-6">
      {/* Title row */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Cpu className="w-5 h-5 text-accent" />
            <h1 className="text-2xl font-semibold tracking-tight text-white">Model Registry</h1>
          </div>
          <p className="text-sm text-white/30">
            Every model known to Atlas — register, evaluate, compare, and deploy.
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-white/40 border border-white/[0.08] hover:bg-white/[0.04] hover:text-white/70 transition-colors cursor-pointer">
            <GitCompare className="w-3.5 h-3.5" /> Compare
          </button>
          <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-white/40 border border-white/[0.08] hover:bg-white/[0.04] hover:text-white/70 transition-colors cursor-pointer">
            <Download className="w-3.5 h-3.5" /> Import
          </button>
          <button
            className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-xs font-medium text-white transition-colors cursor-pointer"
            style={{ background: 'var(--color-accent)' }}
          >
            <Plus className="w-3.5 h-3.5" /> Register Model
          </button>
        </div>
      </div>

      {/* Search + filter chips */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2 bg-white/[0.03] border border-white/[0.06] rounded-xl px-4 py-2.5 max-w-xl">
          <Search className="w-4 h-4 text-white/30 shrink-0" />
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search models, providers, families…"
            className="bg-transparent text-sm text-white placeholder:text-white/25 outline-none flex-1"
          />
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {FILTER_CHIPS.map((chip) => (
            <button
              key={chip.key}
              className="px-2.5 py-1 rounded-md text-xs text-white/30 bg-white/[0.03] border border-white/[0.06] hover:border-white/[0.12] hover:text-white/60 transition-colors font-mono cursor-pointer"
            >
              {chip.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
