import { useDatasetCatalog } from '../../hooks/useDatasetCatalog';
import { AtlasDatasetGrid } from './AtlasDatasetGrid';
import { AtlasDatasetTable } from './AtlasDatasetTable';
import { AtlasDatasetSearch } from './AtlasDatasetSearch';
import { AtlasDatasetFilters } from './AtlasDatasetFilters';
import { AtlasDatasetPreview } from './AtlasDatasetPreview';
import { AtlasDatasetComparison } from './AtlasDatasetComparison';
import { AtlasBulkActions } from './AtlasBulkActions';
import { AtlasPagination } from './AtlasPagination';
import { AnimatedSection } from '@/components/atlas/motion';
import { AnimatePresence } from 'framer-motion';
import { useWorkspaceKeyboard } from '../../../workspace/hooks/useWorkspaceKeyboard';
import { useRef } from 'react';
import { AtlasDatasetEmptyState } from './AtlasDatasetEmptyState';
import { AtlasDatasetErrorState } from './AtlasDatasetErrorState';
import { AtlasDatasetSkeleton } from './AtlasDatasetSkeleton';
import { useWorkspaceInteractionStore } from '@/store/workspace/interaction/store';
import { RotateCcw } from 'lucide-react';

export function AtlasDatasetCatalog() {
  const catalog = useDatasetCatalog();
  const containerRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  useWorkspaceKeyboard({
    namespace: 'datasets',
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
          // Clear selection if clicking empty space (not buttons, inputs, links)
          if ((e.target as HTMLElement).closest('button, a, input, [role="button"], .atlas-card')) return;
          catalog.handleClearSelection();
        }}
      >
      
      {/* 
        Toolbar: Search, Filters, View Switcher 
        (To be implemented)
      */}
      <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between min-h-[64px] py-4 lg:py-2 border border-white/10 rounded-xl px-4 bg-black/40 gap-4 w-full">
        <AtlasDatasetSearch catalog={catalog} inputRef={searchRef} />
        
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4 sm:gap-6 w-full lg:w-auto">
          <AtlasDatasetFilters catalog={catalog} />
          
          <div className="w-px h-8 bg-white/10 hidden sm:block"></div>
          
          {/* Reset Workspace */}
          <button
            onClick={() => {
              useWorkspaceInteractionStore.getState().resetWorkspace('datasets');
              // Clear URL search params since they are managed locally by catalog hook for URL sync
              catalog.handleSearch('');
              catalog.handleClearSelection();
              catalog.setSort({ field: 'updated', direction: 'desc' });
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

      <AnimatePresence>
        {catalog.selectedIds.length > 0 && (
          <AtlasBulkActions catalog={catalog} />
        )}
      </AnimatePresence>

      <div className="flex flex-col xl:flex-row items-start gap-6 w-full relative">
        <div className="flex-1 min-w-0 flex flex-col gap-4">
          {catalog.error ? (
            <AtlasDatasetErrorState catalog={catalog} />
          ) : catalog.isLoading ? (
            <AtlasDatasetSkeleton catalog={catalog} />
          ) : catalog.totalItems === 0 ? (
            <AtlasDatasetEmptyState catalog={catalog} />
          ) : catalog.viewMode === 'grid' ? (
            <AtlasDatasetGrid catalog={catalog} />
          ) : (
            <AtlasDatasetTable catalog={catalog} />
          )}
          
          {/* Pagination */}
          {!catalog.error && !catalog.isLoading && catalog.totalItems > 0 && <AtlasPagination catalog={catalog} />}
        </div>

        {/* Preview Panel */}
        <AnimatePresence>
          {catalog.previewId && <AtlasDatasetPreview catalog={catalog} />}
        </AnimatePresence>
      </div>

      {/* Comparison Panel */}
      <AnimatePresence>
        {catalog.selectedIds.length === 2 && <AtlasDatasetComparison catalog={catalog} />}
      </AnimatePresence>
      </div>
    </AnimatedSection>
  );
}
