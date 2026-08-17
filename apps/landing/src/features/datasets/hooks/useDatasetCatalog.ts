import { useState, useMemo, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import type { DatasetHealth, DatasetQuality } from '../domain/types';
import type { FilterState, SortState, ViewMode, PaginationState } from '../types/catalog';
import { selectCatalogCards, selectCatalogRows, selectDatasetPreview, selectDatasetComparison } from '../selectors/catalog';
import { useWorkspaceInteractionStore } from '@/store/workspace/interaction/store';
import { useQuery } from '@tanstack/react-query';
import { datasetApi } from '../api/datasetApi';
import { mapDatasetDtoToDomain } from '../api/mapper';
import { useProjectStore } from '../../projects/store/projectStore';

const EMPTY_ARRAY: string[] = [];

export function useDatasetCatalog() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { activeProjectId } = useProjectStore();
  
  // 1. View Mode (URL -> localStorage -> default)
  const initialView = searchParams.get('view') as ViewMode 
    || localStorage.getItem('atlas_dataset_view') as ViewMode 
    || 'grid';
    
  const [viewMode, setViewModeState] = useState<ViewMode>(initialView);

  const setViewMode = (mode: ViewMode) => {
    setViewModeState(mode);
    localStorage.setItem('atlas_dataset_view', mode);
    setSearchParams(prev => {
      prev.set('view', mode);
      return prev;
    });
  };

  // 2. Filters & Sort State
  // Note: Client-side filtering over a paginated API response is misleading.
  // We maintain this state for UI compatibility but it does not filter the server data.
  const [filters, setFilters] = useState<FilterState>({
    searchQuery: searchParams.get('q') || '',
    status: [],
    provider: [],
    type: [],
    owner: [],
    tags: []
  });

  const [sort, setSort] = useState<SortState>({ field: 'updated', direction: 'desc' });

  // 3. Pagination
  const [pagination, setPagination] = useState<PaginationState>({ page: 1, pageSize: 25, total: 0 });

  const limit = pagination.pageSize;
  const offset = (pagination.page - 1) * limit;

  const { data: rawDtoData, isLoading, isError, refetch } = useQuery({
    queryKey: ['datasets', activeProjectId, limit, offset],
    queryFn: () => datasetApi.listDatasets(activeProjectId!, limit, offset),
    enabled: !!activeProjectId,
  });

  const handleRetry = () => {
    refetch();
  };

  // 4. Interaction State (Zustand)
  const ns = 'datasets';
  const initWorkspace = useWorkspaceInteractionStore(s => s.initWorkspace);
  const ws = useWorkspaceInteractionStore(s => s.workspaces[ns]);
  
  useEffect(() => {
    initWorkspace(ns);
  }, [initWorkspace]);

  const selectedIds = ws?.selection.selectedIds || EMPTY_ARRAY;
  const previewId = ws?.view.previewId || null;
  const expandedId = ws?.navigation.expandedIds[0] || null;

  // Sync search to URL
  useEffect(() => {
    setSearchParams(prev => {
      if (filters.searchQuery) prev.set('q', filters.searchQuery);
      else prev.delete('q');
      return prev;
    });
  }, [filters.searchQuery, setSearchParams]);

  // Interactivity Actions
  const handleSearch = (query: string) => {
    setFilters(f => ({ ...f, searchQuery: query }));
  };

  const selectItem = useWorkspaceInteractionStore(s => s.selectItem);
  const rangeSelect = useWorkspaceInteractionStore(s => s.rangeSelect);
  const clearSelectionStore = useWorkspaceInteractionStore(s => s.clearSelection);
  const openPreviewStore = useWorkspaceInteractionStore(s => s.openPreview);
  const closePreviewStore = useWorkspaceInteractionStore(s => s.closePreview);
  const toggleExpandedStore = useWorkspaceInteractionStore(s => s.toggleExpanded);

  const handleSelect = (id: string, multi: boolean = false) => {
    selectItem(ns, id, multi);
  };

  const handleRangeSelect = (id: string, visibleIds: string[]) => {
    rangeSelect(ns, id, visibleIds);
  };

  const handleSelectAll = (ids: string[]) => {
    const allSelected = ids.every(id => selectedIds.includes(id));
    if (allSelected) {
      clearSelectionStore(ns);
    } else {
      ids.forEach(id => {
        if (!selectedIds.includes(id)) {
          selectItem(ns, id, true);
        }
      });
    }
  };

  const handleClearSelection = () => clearSelectionStore(ns);

  const handleOpenPreview = (id: string) => {
    openPreviewStore(ns, id);
  };

  const handleClosePreview = () => closePreviewStore(ns);

  const handleToggleExpand = (id: string) => {
    toggleExpandedStore(ns, id);
  };

  // Pipeline execution (Memoized)
  const pipelineResult = useMemo(() => {
    const domainData = (rawDtoData || []).map(mapDatasetDtoToDomain);
    
    // We intentionally DO NOT apply client-side filterDatasets or sortDatasets here
    // because we only have a partial page from the backend.
    const paginated = domainData;
    
    // Mock health/quality maps (Since backend doesn't provide them, we provide empty records to safely avoid UI crashes)
    const emptyHealthMap: Record<string, DatasetHealth> = {};
    const emptyQualityMap: Record<string, DatasetQuality> = {};

    // Presentation Mapping
    const cards = selectCatalogCards(paginated, emptyHealthMap);
    const rows = selectCatalogRows(paginated, emptyHealthMap);

    return {
      fetchedCount: domainData.length,
      cards,
      rows,
      rawVisible: paginated,
      emptyHealthMap,
      emptyQualityMap
    };
  }, [rawDtoData]);

  // Update pagination total (approximation since backend has no count endpoint)
  useEffect(() => {
    setPagination(p => ({ 
      ...p, 
      total: offset + pipelineResult.fetchedCount + (pipelineResult.fetchedCount === limit ? 1 : 0) 
    }));
  }, [pipelineResult.fetchedCount, offset, limit]);

  // Derive Preview & Comparison Models
  const previewModel = useMemo(() => {
    if (!previewId || !rawDtoData) return null;
    const ds = rawDtoData.map(mapDatasetDtoToDomain).find(d => d.id === previewId);
    if (!ds) return null;
    return selectDatasetPreview(ds, pipelineResult.emptyHealthMap[ds.id], pipelineResult.emptyQualityMap[ds.id]);
  }, [previewId, rawDtoData, pipelineResult.emptyHealthMap, pipelineResult.emptyQualityMap]);

  const comparisonModels = useMemo(() => {
    if (selectedIds.length !== 2 || !rawDtoData) return [];
    const dsToCompare = rawDtoData.map(mapDatasetDtoToDomain).filter(d => selectedIds.includes(d.id));
    return selectDatasetComparison(dsToCompare, pipelineResult.emptyHealthMap, pipelineResult.emptyQualityMap);
  }, [selectedIds, rawDtoData, pipelineResult.emptyHealthMap, pipelineResult.emptyQualityMap]);

  return {
    // State
    viewMode,
    filters,
    sort,
    pagination,
    selectedIds,
    expandedId,
    previewId,
    
    // Derived UI Models
    cards: pipelineResult.cards,
    rows: pipelineResult.rows,
    previewModel,
    comparisonModels,
    totalItems: pagination.total,
    
    // Virtualization flag (>100 datasets)
    shouldVirtualize: false,

    // Actions
    setViewMode,
    setSort,
    setPagination,
    handleSearch,
    handleSelect,
    handleRangeSelect,
    handleSelectAll,
    handleClearSelection,
    handleOpenPreview,
    handleClosePreview,
    handleToggleExpand,
    
    // Expose raw visible for "Select All"
    rawVisibleIds: pipelineResult.rawVisible.map(d => d.id),

    // Data Fetching States
    isLoading,
    error: isError ? { message: 'Failed to fetch datasets', recoverable: true } : null,
    retry: handleRetry
  };
}
