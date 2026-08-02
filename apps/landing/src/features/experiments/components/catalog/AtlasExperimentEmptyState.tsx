import { SearchX, FilterX, RotateCcw } from 'lucide-react';

interface Props {
  hasFilters: boolean;
  onClearFilters: () => void;
}

export function AtlasExperimentEmptyState({ hasFilters, onClearFilters }: Props) {
  return (
    <div className="flex flex-col items-center justify-center py-20 px-4 text-center">
      <div className="h-12 w-12 rounded-full bg-white/5 border border-white/10 flex items-center justify-center mb-4">
        {hasFilters ? (
          <FilterX className="w-6 h-6 text-white/40" />
        ) : (
          <SearchX className="w-6 h-6 text-white/40" />
        )}
      </div>
      
      <h3 className="text-lg font-medium text-white mb-2">
        {hasFilters ? 'No matching experiments found' : 'No experiments available'}
      </h3>
      
      <p className="text-sm text-white/40 max-w-[280px] mb-6">
        {hasFilters 
          ? "We couldn't find any experiments matching your current filter criteria."
          : "There are currently no experiments queued or running."}
      </p>

      {hasFilters && (
        <button
          onClick={onClearFilters}
          className="inline-flex items-center gap-2 px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-sm text-white transition-colors"
        >
          <RotateCcw className="w-4 h-4" />
          Clear all filters
        </button>
      )}
    </div>
  );
}
