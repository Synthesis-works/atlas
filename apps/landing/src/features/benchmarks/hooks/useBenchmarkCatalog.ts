import { useState, useMemo, useEffect, useCallback } from 'react';
import type { BenchmarkFilterState, BenchmarkSortState } from '../selectors/catalog';
import { selectBenchmarkCatalog, selectBenchmarkPreview, selectBenchmarkComparisons } from '../selectors/catalog';
import { useWorkspaceInteractionStore } from '@/store/workspace/interaction/store';
import { useBenchmarkStore } from '../store/benchmarkStore';

export function useBenchmarkCatalog() {
  const store = useBenchmarkStore();
  const rawBenchmarks = store.benchmarks;

  // Coordinator State
  const [filters, setFilters] = useState<BenchmarkFilterState>({
    searchQuery: store.searchQuery,
    category: store.selectedCategory,
    status: 'all',
    difficulty: 'all'
  });

  // Sync header search and category filters into catalog
  useEffect(() => {
    setFilters(prev => ({
      ...prev,
      searchQuery: store.searchQuery,
      category: store.selectedCategory,
    }));
  }, [store.searchQuery, store.selectedCategory]);
  
  const [sort, setSort] = useState<BenchmarkSortState>({
    field: 'verificationScore',
    direction: 'desc'
  });

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(24);
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid');

  // Async State directly from single source of truth store
  const isLoading = store.isLoading;
  const error = store.error ? new Error(store.error) : null;

  // Global Interaction Store (IDs only)
  const ns = 'benchmarks';
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

  // Compute Presentation Models
  const catalog = useMemo(() => {

    return selectBenchmarkCatalog(rawBenchmarks, filters, sort, page, pageSize);
  }, [rawBenchmarks, filters, sort, page, pageSize]);

  // Compute Active Preview Model
  const previewModel = useMemo(() => {
    if (!previewId) return null;
    const benchmark = rawBenchmarks.find(b => b.id === previewId);
    return selectBenchmarkPreview(benchmark);
  }, [previewId, rawBenchmarks]);

  // Compute Comparison Models
  const comparisonModels = useMemo(() => {
    if (selectedIds.length === 0) return [];
    return selectBenchmarkComparisons(rawBenchmarks, selectedIds);
  }, [selectedIds, rawBenchmarks]);

  // Reset page on filter changes
  useEffect(() => {
    setPage(1);
  }, [filters]);

  // Event Handlers
  const handleSearch = useCallback((query: string) => {
    setFilters(prev => ({ ...prev, searchQuery: query }));
  }, []);

  const handleFilterChange = useCallback((key: keyof BenchmarkFilterState, value: string) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  }, []);

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
    store.refresh();
  }, [store]);


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
    comparisonModels,
    setSort,
    setPage,
    setPageSize,
    setViewMode,
    handleSearch,
    handleFilterChange,
    handleSelect,
    handleRangeSelect,
    handleSelectAll,
    handleClearSelection,
    handleToggleExpand,
    handleOpenPreview,
    handleClosePreview,
    retry: handleRetry
  };
}
