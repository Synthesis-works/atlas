import { useState, useMemo, useEffect, useCallback } from 'react';
import type { Benchmark } from '../../../domain/benchmarks/types';
import type { BenchmarkFilterState, BenchmarkSortState } from '../selectors/catalog';
import { selectBenchmarkCatalog, selectBenchmarkPreview, selectBenchmarkComparisons } from '../selectors/catalog';
import { useWorkspaceInteractionStore } from '@/store/workspace/interaction/store';
import { getBenchmarks } from '../services/benchmarkService';

export function useBenchmarkCatalog() {
  // Coordinator State
  const [filters, setFilters] = useState<BenchmarkFilterState>({
    searchQuery: '',
    category: 'all',
    status: 'all',
    difficulty: 'all'
  });
  
  const [sort, setSort] = useState<BenchmarkSortState>({
    field: 'verificationScore',
    direction: 'desc'
  });

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(24);
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid');

  // Data State (real API-backed)
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [benchmarks, setBenchmarks] = useState<Benchmark[]>([]);

  const loadBenchmarks = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    const res = await getBenchmarks();
    if (res.error) {
      setError(new Error(res.error));
    } else {
      setBenchmarks(res.data);
    }
    setIsLoading(false);
  }, []);

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
  const expandedId = ws?.navigation.expandedIds?.[0] || null; // For grid, we just use the first expanded as the active overlay
  const previewId = ws?.view.previewId || null;

  useEffect(() => {
    initWorkspace(ns);
  }, [ns, initWorkspace]);

  // Initial Data Load
  useEffect(() => {
    let mounted = true;
    setIsLoading(true);
    setError(null);
    getBenchmarks().then((res) => {
      if (!mounted) return;
      if (res.error) {
        setError(new Error(res.error));
      } else {
        setBenchmarks(res.data);
      }
      setIsLoading(false);
    });
    return () => {
      mounted = false;
    };
  }, []);

  // Compute Presentation Models
  const catalog = useMemo(() => {
    return selectBenchmarkCatalog(benchmarks, filters, sort, page, pageSize);
  }, [benchmarks, filters, sort, page, pageSize]);

  // Compute Active Preview Model
  const previewModel = useMemo(() => {
    if (!previewId) return null;
    const benchmark = benchmarks.find(b => b.id === previewId);
    return selectBenchmarkPreview(benchmark);
  }, [previewId, benchmarks]);

  // Compute Comparison Models
  const comparisonModels = useMemo(() => {
    if (selectedIds.length === 0) return [];
    return selectBenchmarkComparisons(benchmarks, selectedIds);
  }, [selectedIds, benchmarks]);

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
    void loadBenchmarks();
  }, [loadBenchmarks]);

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
