import { useRef, useEffect, useState } from 'react';
import { Search } from 'lucide-react';
import { useWorkspaceKeyboard } from '../../../workspace/hooks/useWorkspaceKeyboard';
import { useWorkspaceInteractionStore } from '@/store/workspace/interaction/store';

import { useExperimentCatalog } from '../../hooks/useExperimentCatalog';

import { AtlasExperimentGrid } from './AtlasExperimentGrid';
import { AtlasExperimentTable } from './AtlasExperimentTable';
import { AtlasExperimentPreview } from './AtlasExperimentPreview';
import { AtlasExperimentEmptyState } from './AtlasExperimentEmptyState';
import { AtlasExperimentErrorState } from './AtlasExperimentErrorState';
import { AtlasExperimentSkeleton } from './AtlasExperimentSkeleton';

export function AtlasExperimentCatalog() {
  const catalog = useExperimentCatalog();
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('table');
  const containerRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  const panelWidth = useWorkspaceInteractionStore(s => s.workspaces['experiments']?.view.panelWidth || 450);

  useWorkspaceKeyboard({
    namespace: 'experiments',
    itemIds: catalog.rawVisibleIds,
    containerRef,
    searchRef
  });

  useEffect(() => {
    if (!catalog.filters.searchQuery) {
      searchRef.current?.focus();
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const hasFilters = catalog.filters.searchQuery !== '' || catalog.filters.status !== 'all';
  const isEmpty = catalog.rows.length === 0;

  return (
    <div className="flex h-full min-h-0 bg-[#0A0C10] rounded-xl border border-white/10 overflow-hidden relative">
      <div 
        ref={containerRef}
        className="flex-1 flex flex-col min-w-0 h-full overflow-hidden focus:outline-none"
        tabIndex={-1}
      >
        {/* Toolbar */}
        <div className="flex-none p-4 border-b border-white/5 bg-[#0F1117] flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 flex-1">
            <div className="relative max-w-sm w-full group">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
              <input 
                ref={searchRef}
                type="text"
                placeholder="Search unavailable — backend support pending."
                className="w-full bg-[#1A1D24] border border-white/10 rounded-lg pl-9 pr-4 py-2 text-sm text-white/30 placeholder:text-white/30 focus:outline-none cursor-not-allowed transition-all"
                value=""
                readOnly
              />
            </div>

            <select
              className="bg-[#1A1D24] border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500/50 capitalize"
              value={catalog.filters.status}
              onChange={e => catalog.setFilters({ ...catalog.filters, status: e.target.value as any })}
            >
              <option value="all">All Status</option>
              <option value="Queued">Queued</option>
              <option value="Running">Running</option>
              <option value="Completed">Completed</option>
              <option value="Failed">Failed</option>
              <option value="Cancelled">Cancelled</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <div className="flex p-1 bg-[#1A1D24] border border-white/10 rounded-lg">
              <button
                onClick={() => setViewMode('table')}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                  viewMode === 'table' 
                    ? 'bg-white/10 text-white shadow-sm' 
                    : 'text-white/50 hover:text-white hover:bg-white/5'
                }`}
              >
                Queue
              </button>
              <button
                onClick={() => setViewMode('grid')}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                  viewMode === 'grid' 
                    ? 'bg-white/10 text-white shadow-sm' 
                    : 'text-white/50 hover:text-white hover:bg-white/5'
                }`}
              >
                Cards
              </button>
            </div>
          </div>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto min-h-0 relative">
          {catalog.error ? (
            <AtlasExperimentErrorState catalog={catalog} />
          ) : catalog.isLoading ? (
            <AtlasExperimentSkeleton />
          ) : isEmpty ? (
            <AtlasExperimentEmptyState 
              hasFilters={hasFilters} 
              onClearFilters={() => catalog.setFilters({ searchQuery: '', status: 'all' })}
            />
          ) : viewMode === 'grid' ? (
            <AtlasExperimentGrid catalog={catalog} />
          ) : (
            <AtlasExperimentTable catalog={catalog} />
          )}
        </div>
        
        {/* Pagination Footer */}
        {!catalog.isLoading && !isEmpty && !catalog.error && (
          <div className="flex-none p-4 border-t border-white/5 bg-[#0F1117] flex justify-between items-center text-sm text-white/50">
            <div>
              Showing {(catalog.pagination.currentPage - 1) * catalog.pagination.pageSize + 1} to {Math.min(catalog.pagination.currentPage * catalog.pagination.pageSize, catalog.pagination.totalItems)} of {catalog.pagination.totalItems}
            </div>
            <div className="flex gap-2">
              <button
                disabled={!catalog.pagination.hasPrevPage}
                onClick={() => catalog.setPage(catalog.pagination.currentPage - 1)}
                className="px-3 py-1.5 rounded bg-white/5 hover:bg-white/10 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Previous
              </button>
              <button
                disabled={!catalog.pagination.hasNextPage}
                onClick={() => catalog.setPage(catalog.pagination.currentPage + 1)}
                className="px-3 py-1.5 rounded bg-white/5 hover:bg-white/10 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Preview Drawer */}
      {catalog.previewId && (
        <>
          {/* Overlay for mobile/tablet */}
          <div 
            className="lg:hidden absolute inset-0 bg-black/40 z-10" 
            onClick={() => useWorkspaceInteractionStore.getState().closePreview('experiments')}
          />
          <div 
            className="absolute lg:relative right-0 top-0 bottom-0 border-l border-white/10 bg-[#0F1117] h-full shadow-2xl transition-transform duration-300 ease-out z-20 flex-shrink-0"
            style={{ width: `min(100%, ${panelWidth}px)` }}
          >
            <AtlasExperimentPreview catalog={catalog} />
          </div>
        </>
      )}
    </div>
  );
}
