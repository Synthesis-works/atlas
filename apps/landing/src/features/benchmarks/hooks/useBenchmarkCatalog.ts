import { useState, useMemo, useEffect, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useWorkspaceInteractionStore } from '@/store/workspace/interaction/store';
import { useProjectStore } from '@/features/projects/store/projectStore';
import { benchmarkApi } from '../api/benchmarkApi';

import type { BenchmarkFilterState, BenchmarkSortState } from '../selectors/catalog';
import { buildBenchmarkPreviewModel, buildBenchmarkComparisonModel, buildBenchmarkCardModel, buildBenchmarkRowModel } from '../presentation/catalog';

export function useBenchmarkCatalog() {
  // Coordinator State
  const [filters, setFilters] = useState<BenchmarkFilterState>({
    searchQuery: '',
    category: 'all',
    status: 'all',
    difficulty: 'all'
  });
  
  const [sort, setSort] = useState<BenchmarkSortState>({
    field: 'name',
    direction: 'asc'
  });

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(24);
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid');

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

  const { activeProjectId } = useProjectStore();

  useEffect(() => {
    initWorkspace(ns);
  }, [ns, initWorkspace]);

  const { data: serverData, isLoading, isError, error, refetch } = useQuery({
    queryKey: [
      'benchmarks', 
      activeProjectId, 
      page, 
      pageSize, 
      sort.field, 
      sort.direction
    ],
    queryFn: async () => {
      if (!activeProjectId) return { items: [], total: 0 };
      
      const offset = (page - 1) * pageSize;
      
      const res = await benchmarkApi.listBenchmarks(activeProjectId, pageSize, offset);

      
      return {
        items: res.items,
        total: res.total,
      };
    },
    enabled: !!activeProjectId,
  });

  const rawBenchmarks = serverData?.items || [];
  const totalItems = serverData?.total || 0;
  const totalPages = Math.ceil(totalItems / pageSize);

  // Compute Presentation Models
  const catalog = useMemo(() => {
    return {
      cards: rawBenchmarks.map(buildBenchmarkCardModel),
      rows: rawBenchmarks.map(buildBenchmarkRowModel),
      rawVisibleIds: rawBenchmarks.map((b: any) => b.id),
      totalItems,
      totalPages,
      currentPage: page
    };
  }, [rawBenchmarks, totalItems, totalPages, page]);

  // Fetch Versions for Active Preview
  const { data: previewVersions } = useQuery({
    queryKey: ['benchmark-versions', previewId],
    queryFn: async () => {
      if (!previewId) return [];
      return await benchmarkApi.getBenchmarkVersions(previewId);
    },
    enabled: !!previewId,
  });

  // Compute Active Preview Model
  const previewModel = useMemo(() => {
    if (!previewId) return null;
    const benchmark = rawBenchmarks.find((b: any) => b.id === previewId);
    if (!benchmark) return null;
    
    // Create base preview model
    const basePreview = buildBenchmarkPreviewModel(benchmark);
    
    // Augment with version if available
    if (previewVersions && previewVersions.length > 0) {
      // Sort versions or just pick the first/latest
      const latestVersion = previewVersions[0];
      basePreview.version = latestVersion.version_string;
    }
    
    return basePreview;
  }, [previewId, rawBenchmarks, previewVersions]);

  // Compute Comparison Models
  const comparisonModels = useMemo(() => {
    if (selectedIds.length === 0) return [];
    return rawBenchmarks.filter((b: any) => selectedIds.includes(b.id)).map(buildBenchmarkComparisonModel);
  }, [selectedIds, rawBenchmarks]);

  // Reset page on filter changes
  useEffect(() => {
    setPage(1);
  }, [filters]);

  // Event Handlers
  const handleSearch = useCallback((query: string) => {
    // Search is unsupported by the backend; state is updated but has no effect on remote data.
    setFilters(prev => ({ ...prev, searchQuery: query }));
  }, []);

  const handleFilterChange = useCallback((key: keyof BenchmarkFilterState, value: string) => {
    // Client-side filtering unsupported as per architectural rules for full datasets.
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
    refetch();
  }, [refetch]);

  return {
    ...catalog,
    filters,
    sort,
    page,
    pageSize,
    viewMode,
    isLoading,
    error: isError ? (error as Error) : null,
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
