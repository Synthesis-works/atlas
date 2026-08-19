import { useState, useMemo, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import type { Dataset, DatasetHealth, DatasetQuality } from '../domain/types';
import type { FilterState, SortState, ViewMode, PaginationState } from '../types/catalog';
import { filterDatasets, sortDatasets, selectCatalogCards, selectCatalogRows, selectDatasetPreview, selectDatasetComparison } from '../selectors/catalog';
import { useWorkspaceInteractionStore } from '@/store/workspace/interaction/store';
import { getDatasets } from '../services/datasetService';
import { resolveProjectId } from '../services/projectService';

const EMPTY_HEALTH: Omit<DatasetHealth, 'datasetId'> = { readinessScore: 0, issues: [] };
const EMPTY_QUALITY: Omit<DatasetQuality, 'datasetId'> = {
  annotationCoverage: 0,
  duplicateCount: 0,
  classBalanceScore: 0,
};

function buildHealthMap(datasets: Dataset[]): Record<string, DatasetHealth> {
  return Object.fromEntries(
    datasets.map((ds) => [ds.id, { datasetId: ds.id, ...EMPTY_HEALTH }])
  );
}

function buildQualityMap(datasets: Dataset[]): Record<string, DatasetQuality> {
  return Object.fromEntries(
    datasets.map((ds) => [ds.id, { datasetId: ds.id, ...EMPTY_QUALITY }])
  );
}
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

  // 3.5 Loading, Error, and Data State (real API-backed)
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<{ message: string, recoverable: boolean } | null>(null);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [healthMap, setHealthMap] = useState<Record<string, DatasetHealth>>({});
  const [qualityMap, setQualityMap] = useState<Record<string, DatasetQuality>>({});

  const loadDatasets = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    const projectId = await resolveProjectId();
    if (!projectId) {
      setError({ message: 'No project available for this account', recoverable: false });
      setIsLoading(false);
      return;
    }
    const res = await getDatasets(projectId);
    if (res.error) {
      setError({ message: res.error, recoverable: true });
    } else {
      setDatasets(res.data);
      setHealthMap(buildHealthMap(res.data));
      setQualityMap(buildQualityMap(res.data));
    }
    setIsLoading(false);
  }, []);

  useEffect(() => {
    let mounted = true;
    setIsLoading(true);
    setError(null);
    (async () => {
      const projectId = await resolveProjectId();
      if (!mounted) return;
      if (!projectId) {
        setError({ message: 'No project available for this account', recoverable: false });
        setIsLoading(false);
        return;
      }
      const res = await getDatasets(projectId);
      if (!mounted) return;
      if (res.error) {
        setError({ message: res.error, recoverable: true });
      } else {
        setDatasets(res.data);
        setHealthMap(buildHealthMap(res.data));
        setQualityMap(buildQualityMap(res.data));
      }
      setIsLoading(false);
    })();
    return () => {
      mounted = false;
    };
  }, []);

  const handleRetry = () => {
    void loadDatasets();
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
    const rawData = datasets;
    const filtered = filterDatasets(rawData, filters);
    const sorted = sortDatasets(filtered, sort, healthMap);
    
    // Pagination slicing
    const startIndex = (pagination.page - 1) * pagination.pageSize;
    const paginated = sorted.slice(startIndex, startIndex + pagination.pageSize);

    // Presentation Mapping
    const cards = selectCatalogCards(paginated, healthMap);
    const rows = selectCatalogRows(paginated, healthMap);

    return {
      filteredCount: filtered.length,
      cards,
      rows,
      rawVisible: paginated // needed for select all filtered
    };
  }, [filters, sort, pagination.page, pagination.pageSize, datasets, healthMap]);

  // Update pagination total when filtered count changes
  useEffect(() => {
    setPagination(p => ({ ...p, total: pipelineResult.filteredCount }));
  }, [pipelineResult.filteredCount]);

  // Derive Preview & Comparison Datasets
  const previewModel = useMemo(() => {
    if (!previewId) return null;
    const ds = datasets.find(d => d.id === previewId);
    if (!ds) return null;
    return selectDatasetPreview(ds, healthMap[ds.id], qualityMap[ds.id]);
  }, [previewId, datasets, healthMap, qualityMap]);

  const comparisonModels = useMemo(() => {
    if (selectedIds.length !== 2) return [];
    const dsToCompare = datasets.filter(d => selectedIds.includes(d.id));
    return selectDatasetComparison(dsToCompare, healthMap, qualityMap);
  }, [selectedIds, datasets, healthMap, qualityMap]);

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
