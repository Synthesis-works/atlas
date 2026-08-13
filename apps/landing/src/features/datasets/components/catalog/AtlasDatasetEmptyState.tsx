import { Database } from 'lucide-react';
import { useDatasetCatalog } from '../../hooks/useDatasetCatalog';

export function AtlasDatasetEmptyState({ catalog }: { catalog: ReturnType<typeof useDatasetCatalog> }) {
  return (
    <div className="w-full h-64 flex flex-col items-center justify-center border border-dashed border-white/10 rounded-2xl bg-white/[0.02]">
      <div className="flex flex-col items-center max-w-sm text-center">
        <div className="h-12 w-12 rounded-xl bg-white/5 flex items-center justify-center mb-4">
          <Database className="w-6 h-6 text-white/40" />
        </div>
        
        {/* Flow: Current Situation -> Reason -> Recommended Action -> Primary Button */}
        <h3 className="text-white font-medium text-lg mb-1">No datasets found</h3>
        <p className="text-white/40 text-sm mb-6">
          There are no datasets matching your current filters: "{catalog.filters.searchQuery}".
        </p>
        
        <button 
          onClick={() => catalog.handleSearch('')}
          className="px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white text-sm font-medium rounded-lg transition-colors"
        >
          Clear Filters
        </button>
      </div>
    </div>
  );
}
