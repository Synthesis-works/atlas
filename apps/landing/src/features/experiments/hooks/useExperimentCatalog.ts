import { useState, useMemo, useEffect, useCallback } from 'react';
import { useWorkspaceInteractionStore } from '@/store/workspace/interaction/store';
import { MOCK_EXPERIMENTS } from '../mocks/mock';
import { selectExperimentCatalog, selectExperimentPreview } from '../selectors/catalog';
import type { ExperimentFilterState, ExperimentSortState } from '../types/catalog';

export function useExperimentCatalog() {
  // Local UI State
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const [filters, setFilters] = useState<ExperimentFilterState>({
    searchQuery: '',
    status: 'all'
  });

  const [sort, setSort] = useState<ExperimentSortState>({
    field: 'queuedAt',
    direction: 'desc'
  });

  // Global Interaction Store (IDs only)
  const ns = 'experiments';
  const initWorkspace = useWorkspaceInteractionStore(s => s.initWorkspace);
  const ws = useWorkspaceInteractionStore(s => s.workspaces[ns]);
  const selectItem = useWorkspaceInteractionStore(s => s.selectItem);
  const rangeSelectStore = useWorkspaceInteractionStore(s => s.rangeSelect);
  const clearSelectionStore = useWorkspaceInteractionStore(s => s.clearSelection);
  const openPreviewStore = useWorkspaceInteractionStore(s => s.openPreview);
  const closePreviewStore = useWorkspaceInteractionStore(s => s.closePreview);

  const selectedIds = ws?.selection.selectedIds || [];
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
    return selectExperimentCatalog(MOCK_EXPERIMENTS, filters, sort, page, pageSize);
  }, [filters, sort, page, pageSize]);

  // Compute Active Preview Model
  const previewModel = useMemo(() => {
    if (!previewId) return null;
    const experiment = MOCK_EXPERIMENTS.find(p => p.id === previewId);
    return selectExperimentPreview(experiment || null);
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
    isLoading,
    error,
    selectedIds,
    previewId,
    previewModel,
    setSort,
    setPage,
    setPageSize,
    setFilters,
    handleSelect,
    handleRangeSelect,
    handleSelectAll,
    handleClearSelection,
    handleOpenPreview,
    handleClosePreview,
    handleRetry
  };
}
