import { useDatasetCatalog } from '../../hooks/useDatasetCatalog';

export function AtlasDatasetFilters({ catalog }: { catalog: ReturnType<typeof useDatasetCatalog> }) {
  // In a full implementation, these would be rich dropdowns/popovers (e.g. Radix UI or shadcn/ui Select)
  // For this scaffold, we implement basic visual filters to demonstrate the data flow.

  const activeFiltersCount = 
    catalog.filters.status.length + 
    catalog.filters.type.length + 
    catalog.filters.provider.length;

  return (
    <div className="flex items-center gap-3">
      <div className="flex items-center gap-2">
        <button disabled title="Filter temporarily unavailable (Awaiting Backend Support)" className="px-3 py-1.5 border border-white/10 rounded-lg text-sm text-white/30 bg-black/20 cursor-not-allowed">
          Status <span className="ml-1 opacity-30">▼</span>
        </button>
        <button disabled title="Filter temporarily unavailable (Awaiting Backend Support)" className="px-3 py-1.5 border border-white/10 rounded-lg text-sm text-white/30 bg-black/20 cursor-not-allowed">
          Provider <span className="ml-1 opacity-30">▼</span>
        </button>
        <button disabled title="Filter temporarily unavailable (Awaiting Backend Support)" className="px-3 py-1.5 border border-white/10 rounded-lg text-sm text-white/30 bg-black/20 cursor-not-allowed">
          Type <span className="ml-1 opacity-30">▼</span>
        </button>
      </div>
      
      {activeFiltersCount > 0 && (
        <div className="flex items-center gap-2 pl-3 border-l border-white/10">
          <span className="text-xs text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded-full">
            {activeFiltersCount} applied
          </span>
          <button className="text-sm text-white/40 hover:text-white transition-colors">
            Clear all
          </button>
        </div>
      )}
    </div>
  );
}
