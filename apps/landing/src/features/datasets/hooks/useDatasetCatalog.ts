import { useState, useMemo, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import type { DatasetHealth, DatasetQuality } from '../domain/types';
import type { FilterState, SortState, ViewMode, PaginationState } from '../types/catalog';
import { filterDatasets, sortDatasets, selectCatalogCards, selectCatalogRows, selectDatasetPreview, selectDatasetComparison } from '../selectors/catalog';
import { useWorkspaceInteractionStore } from '@/store/workspace/interaction/store';

// Normally these would come from an API hook (e.g. useQuery)
import { mockDatasets } from '../domain/mock';

// We mock related data maps for health and quality
const mockHealthMap: Record<string, DatasetHealth> = mockDatasets.reduce((acc, ds) => {
  acc[ds.id] = { datasetId: ds.id, readinessScore: Math.floor(Math.random() * 40) + 60, issues: [] };
  return acc;
}, {} as Record<string, DatasetHealth>);

const mockQualityMap: Record<string, DatasetQuality> = mockDatasets.reduce((acc, ds) => {
  acc[ds.id] = { datasetId: ds.id, annotationCoverage: 85, duplicateCount: 12, classBalanceScore: 92 };
  return acc;
}, {} as Record<string, DatasetQuality>);
/**
 * The Dataset Catalog Coordinator Hook.
 * 
 * Responsible for orchestrating domain data fetching, filtering, sorting, and pagination.
 * Delegates all interaction state (selection, preview, expansion) to the global 
 * Workspace Interaction Store to prevent local state duplication and ensure generic interaction logic.
 *
 * @returns Catalog state, derived presentation models, and explicit interaction handlers.
 */
export function useDatasetCatalog() {
  const [searchParams, setSearchParams] = useSearchParams();
  
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

  // 3.5 Loading and Error State (Mocking async behavior)
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<{ message: string, recoverable: boolean } | null>(null);

  useEffect(() => {
    let mounted = true;
    setIsLoading(true);
    setError(null);
    
    // Simulate network delay
    const timer = setTimeout(() => {
      if (mounted) {
        setIsLoading(false);
      }
    }, 1200);

    return () => {
      mounted = false;
      clearTimeout(timer);
    };
  }, []);

  const handleRetry = () => {
    setIsLoading(true);
    setError(null);
    setTimeout(() => {
      setIsLoading(false);
    }, 1200);
  };

  // 4. Interaction State (Zustand)
  const ns = 'datasets';
  const initWorkspace = useWorkspaceInteractionStore(s => s.initWorkspace);
  const ws = useWorkspaceInteractionStore(s => s.workspaces[ns]);
  
  useEffect(() => {
    initWorkspace(ns);
  }, [initWorkspace]);

  const selectedIds = ws?.selection.selectedIds || [];
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
      // If all selected, clear those
      // (This requires custom logic, but for simplicity, if all are selected, we just clear)
      clearSelectionStore(ns);
    } else {
      // Add all
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
    const rawData = mockDatasets; // In real life, from data source
    const filtered = filterDatasets(rawData, filters);
    const sorted = sortDatasets(filtered, sort, mockHealthMap);
    
    // Pagination slicing
    const startIndex = (pagination.page - 1) * pagination.pageSize;
    const paginated = sorted.slice(startIndex, startIndex + pagination.pageSize);

    // Presentation Mapping
    const cards = selectCatalogCards(paginated, mockHealthMap);
    const rows = selectCatalogRows(paginated, mockHealthMap);

    return {
      filteredCount: filtered.length,
      cards,
      rows,
      rawVisible: paginated // needed for select all filtered
    };
  }, [filters, sort, pagination.page, pagination.pageSize]);

  // Update pagination total when filtered count changes
  useEffect(() => {
    setPagination(p => ({ ...p, total: pipelineResult.filteredCount }));
  }, [pipelineResult.filteredCount]);

  // Derive Preview & Comparison Models
  const previewModel = useMemo(() => {
    if (!previewId) return null;
    const ds = mockDatasets.find(d => d.id === previewId);
    if (!ds) return null;
    return selectDatasetPreview(ds, mockHealthMap[ds.id], mockQualityMap[ds.id]);
  }, [previewId]);

  const comparisonModels = useMemo(() => {
    if (selectedIds.length !== 2) return [];
    const dsToCompare = mockDatasets.filter(d => selectedIds.includes(d.id));
    return selectDatasetComparison(dsToCompare, mockHealthMap, mockQualityMap);
  }, [selectedIds]);

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
    totalItems: pipelineResult.filteredCount,
    
    // Virtualization flag (>100 datasets)
    shouldVirtualize: pipelineResult.filteredCount > 100,

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
    error,
    retry: handleRetry
  };
}
