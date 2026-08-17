import { useState, useMemo, useEffect, useCallback } from 'react';
import { useWorkspaceInteractionStore } from '@/store/workspace/interaction/store';
import { selectProviderCatalog, selectProviderPreview } from '../selectors/catalog';
import type { ProviderFilterState, ProviderSortState } from '../types/catalog';

export function useProviderCatalog() {
  // Local UI State
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(12);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const [filters, setFilters] = useState<ProviderFilterState>({
    searchQuery: '',
    status: 'all',
    tier: 'all'
  });

  const [sort, setSort] = useState<ProviderSortState>({
    field: 'name',
    direction: 'asc'
  });

  // Global Interaction Store (IDs only)
  const ns = 'providers';
  const initWorkspace = useWorkspaceInteractionStore(s => s.initWorkspace);
  const ws = useWorkspaceInteractionStore(s => s.workspaces[ns]);
  const selectItem = useWorkspaceInteractionStore(s => s.selectItem);
  const rangeSelectStore = useWorkspaceInteractionStore(s => s.rangeSelect);
  const clearSelectionStore = useWorkspaceInteractionStore(s => s.clearSelection);
  const openPreviewStore = useWorkspaceInteractionStore(s => s.openPreview);
  const closePreviewStore = useWorkspaceInteractionStore(s => s.closePreview);
  const toggleExpandedStore = useWorkspaceInteractionStore(s => s.toggleExpanded);

  const selectedIds = ws?.selection.selectedIds || [];
  const expandedId = ws?.navigation.expandedIds?.[0] || null;
  const previewId = ws?.view.previewId || null;

  useEffect(() => {
    initWorkspace(ns);
  }, [ns, initWorkspace]);

  // Initial Data Load Simulation
  useEffect(() => {
    const timer = setTimeout(() => {
      setIsLoading(false);
    }, 800);
    return () => clearTimeout(timer);
  }, []);

  // Reset page on filter changes
  useEffect(() => {
    setPage(1);
  }, [filters]);

  // Compute Presentation Models
  const catalog = useMemo(() => {
    return selectProviderCatalog([], filters, sort, page, pageSize);
  }, [filters, sort, page, pageSize]);

  // Compute Active Preview Model
  const previewModel = useMemo(() => {
    if (!previewId) return null;
    const provider = [].find((p: any) => p.id === previewId);
    return selectProviderPreview(provider || null);
  }, [previewId]);



  // Event Handlers
  const handleSelect = useCallback((id: string, multi: boolean) => {
    selectItem(ns, id, multi);
  }, [selectItem]);

  const handleRangeSelect = useCallback((id: string, visibleIds: string[]) => {
    rangeSelectStore(ns, id, visibleIds);
  }, [rangeSelectStore]);

  const handleSelectAll = useCallback((ids: string[]) => {
    if (selectedIds.length === ids.length) {
      clearSelectionStore(ns);
    } else {
      ids.forEach(id => {
        if (!selectedIds.includes(id)) {
          selectItem(ns, id, true);
        }
      });
    }
  }, [selectedIds, selectItem, clearSelectionStore]);

  const handleClearSelection = useCallback(() => {
    clearSelectionStore(ns);
  }, [clearSelectionStore]);

  const handleToggleExpand = useCallback((id: string) => {
    toggleExpandedStore(ns, id);
  }, [toggleExpandedStore]);

  const handleOpenPreview = useCallback((id: string) => {
    openPreviewStore(ns, id);
  }, [openPreviewStore]);

  const handleClosePreview = useCallback(() => {
    closePreviewStore(ns);
  }, [closePreviewStore]);



  const handleRetry = useCallback(() => {
    setIsLoading(true);
    setError(null);
    setTimeout(() => setIsLoading(false), 800);
  }, []);

  return {
    ...catalog,
    filters,
    sort,
    page,
    pageSize,
    viewMode,
    isLoading,
    error,
    selectedIds,
    expandedId,
    previewId,
    previewModel,
    setSort,
    setPage,
    setPageSize,
    setFilters,
    setViewMode,
    handleSelect,
    handleRangeSelect,
    handleSelectAll,
    handleClearSelection,
    handleToggleExpand,
    handleOpenPreview,
    handleClosePreview,
    handleRetry
  };
}
