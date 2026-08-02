import { useRef } from 'react';
import { AnimatePresence } from 'framer-motion';
import { RotateCcw } from 'lucide-react';
import { useBenchmarkCatalog } from '../../hooks/useBenchmarkCatalog';
import { AtlasBenchmarkGrid } from './AtlasBenchmarkGrid';
import { AtlasBenchmarkTable } from './AtlasBenchmarkTable';
import { AtlasBenchmarkPreview } from './AtlasBenchmarkPreview';
import { AtlasBenchmarkEmptyState } from './AtlasBenchmarkEmptyState';
import { AtlasBenchmarkErrorState } from './AtlasBenchmarkErrorState';
import { AtlasBenchmarkSkeleton } from './AtlasBenchmarkSkeleton';
import { AnimatedSection } from '@/components/atlas/motion';
import { useWorkspaceKeyboard } from '../../../workspace/hooks/useWorkspaceKeyboard';
import { useWorkspaceInteractionStore } from '@/store/workspace/interaction/store';

export function AtlasBenchmarkCatalog() {
  const catalog = useBenchmarkCatalog();
  const containerRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  useWorkspaceKeyboard({
    namespace: 'benchmarks',
    itemIds: catalog.rawVisibleIds,
    containerRef,
    searchRef
  });

  return (
    <AnimatedSection className="flex flex-col gap-6 w-full relative" delay={100}>
      <div 
        ref={containerRef}
        className="flex flex-col gap-6 w-full"
        onClick={(e) => {
          if ((e.target as HTMLElement).closest('button, a, input, [role="button"], .atlas-card')) return;
          catalog.handleClearSelection();
        }}
      >
      
      {/* Toolbar */}
      <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between min-h-[64px] py-4 lg:py-2 border border-white/10 rounded-xl px-4 bg-black/40 gap-4 w-full">
        <div className="flex-1 w-full lg:max-w-md">
          <input
            ref={searchRef}
            type="text"
            placeholder="Search benchmarks..."
            className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-sm text-white placeholder-white/40 focus:outline-none focus:border-indigo-500"
            value={catalog.filters.searchQuery}
            onChange={(e) => catalog.handleSearch(e.target.value)}
          />
        </div>
        
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4 sm:gap-6 w-full lg:w-auto">
          <div className="w-px h-8 bg-white/10 hidden sm:block"></div>
          
          <button
            onClick={() => {
              useWorkspaceInteractionStore.getState().resetWorkspace('benchmarks');
              catalog.handleSearch('');
              catalog.handleClearSelection();
              catalog.setSort({ field: 'verificationScore', direction: 'desc' });
            }}
            className="flex items-center justify-center h-8 w-8 rounded-lg text-white/40 hover:text-white hover:bg-white/10 transition-colors"
            title="Reset Workspace"
          >
            <RotateCcw className="w-4 h-4" />
          </button>

          <div className="w-px h-8 bg-white/10 hidden sm:block"></div>
          <button 
            className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${catalog.viewMode === 'grid' ? 'bg-white/10 text-white' : 'text-white/40 hover:text-white/80'}`}
            onClick={() => catalog.setViewMode('grid')}
          >
            Grid
          </button>
          <button 
            className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${catalog.viewMode === 'table' ? 'bg-white/10 text-white' : 'text-white/40 hover:text-white/80'}`}
            onClick={() => catalog.setViewMode('table')}
          >
            Table
          </button>
        </div>
      </div>

      <div className="flex flex-col xl:flex-row items-start gap-6 w-full relative">
        <div className="flex-1 min-w-0 flex flex-col gap-4">
          {catalog.error ? (
            <AtlasBenchmarkErrorState catalog={catalog} />
          ) : catalog.isLoading ? (
            <AtlasBenchmarkSkeleton />
          ) : catalog.totalItems === 0 ? (
            <AtlasBenchmarkEmptyState />
          ) : catalog.viewMode === 'grid' ? (
            <AtlasBenchmarkGrid catalog={catalog} />
          ) : (
            <AtlasBenchmarkTable catalog={catalog} />
          )}
        </div>

        {/* Preview Panel */}
        <AnimatePresence>
          {catalog.previewId && <AtlasBenchmarkPreview catalog={catalog} />}
        </AnimatePresence>
      </div>

      </div>
    </AnimatedSection>
  );
}
