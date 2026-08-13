import { useState, useMemo, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import type { ModelHealth, ModelCost } from '../../../domain/models/types';
import type { FilterState, SortState, ViewMode, PaginationState } from '../types/catalog';
import { filterModels, sortModels, selectCatalogCards, selectCatalogRows, selectModelPreview, selectModelComparison } from '../selectors/catalog';
import { useWorkspaceInteractionStore } from '@/store/workspace/interaction/store';

// Normally these would come from an API hook (e.g. useQuery)
import { MOCK_MODELS } from '../../../domain/models/mock';

// We mock related data maps for health and cost
const mockHealthMap: Record<string, ModelHealth> = MOCK_MODELS.reduce((acc, model) => {
  acc[model.id] = model.health;
  return acc;
}, {} as Record<string, ModelHealth>);

const mockCostMap: Record<string, ModelCost> = MOCK_MODELS.reduce((acc, model) => {
  acc[model.id] = model.cost;
  return acc;
}, {} as Record<string, ModelCost>);

/**
 * The Model Catalog Coordinator Hook.
 * 
 * Responsible for orchestrating domain data fetching, filtering, sorting, and pagination.
 * Delegates all interaction state (selection, preview, expansion) to the global 
 * Workspace Interaction Store to prevent local state duplication and ensure generic interaction logic.
 *
 * @returns Catalog state, derived presentation models, and explicit interaction handlers.
 */
export function useModelCatalog() {
  const [searchParams, setSearchParams] = useSearchParams();
  
  // 1. View Mode (URL -> localStorage -> default)
  const initialView = searchParams.get('view') as ViewMode 
    || localStorage.getItem('atlas_model_view') as ViewMode 
    || 'grid';
    
  const [viewMode, setViewModeState] = useState<ViewMode>(initialView);

  const setViewMode = (mode: ViewMode) => {
    setViewModeState(mode);
    localStorage.setItem('atlas_model_view', mode);
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
    modalities: [],
    capabilities: [],
    license: []
  });

  const [sort, setSort] = useState<SortState>({ field: 'score', direction: 'desc' });

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
  const ns = 'models';
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
    const rawData = MOCK_MODELS; // In real life, from data source
    const filtered = filterModels(rawData, filters);
    const sorted = sortModels(filtered, sort, mockHealthMap);
    
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
    const model = MOCK_MODELS.find(m => m.id === previewId);
    if (!model) return null;
    return selectModelPreview(model, mockHealthMap[model.id], mockCostMap[model.id]);
  }, [previewId]);

  const comparisonModels = useMemo(() => {
    if (selectedIds.length < 2) return [];
    const modelsToCompare = MOCK_MODELS.filter(m => selectedIds.includes(m.id));
    return selectModelComparison(modelsToCompare, mockHealthMap, mockCostMap);
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
    
    // Virtualization flag (>100 models)
    shouldVirtualize: pipelineResult.filteredCount > 100,

    // Actions
    setViewMode,
    setSort,
    setPagination,
    handleSearch,
    setFilters,
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
