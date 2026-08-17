import { useState, useMemo, useEffect, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useWorkspaceInteractionStore } from '@/store/workspace/interaction/store';
import { useProjectStore } from '../../projects/store/projectStore';
import { experimentApi } from '../api/experimentApi';
import { mapExecutionToRowModel, mapExecutionToPreviewModel } from '../api/mapper';
import type { ExperimentFilterState, ExperimentSortState } from '../types/catalog';

export function useExperimentCatalog() {
  // Local UI State
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  const [filters, setFilters] = useState<ExperimentFilterState>({
    searchQuery: '', // Backend doesn't support search natively on executions yet
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
  const { activeProjectId } = useProjectStore();

  const selectedIds = ws?.selection.selectedIds || [];
  const previewId = ws?.view.previewId || null;

  useEffect(() => {
    initWorkspace(ns);
  }, [ns, initWorkspace]);

  // Reset page on filter changes
  useEffect(() => {
    setPage(1);
  }, [filters]);

  // Main List Query
  const limit = pageSize;
  const offset = (page - 1) * pageSize;
  
  let statusParam: string | undefined;
  if (filters.status !== 'all') {
    // Reverse map ExperimentStatus to backend ExecutionState roughly for filtering
    if (filters.status === 'Queued') statusParam = 'QUEUED';
    if (filters.status === 'Running') statusParam = 'RUNNING'; // Will just filter explicitly running ones
    if (filters.status === 'Completed') statusParam = 'COMPLETED';
    if (filters.status === 'Failed') statusParam = 'FAILED';
    if (filters.status === 'Cancelled') statusParam = 'CANCELLED';
  }
  
  const { data: listData, isLoading: isListLoading, error: listError, refetch } = useQuery({
    queryKey: ['experiments', activeProjectId, limit, offset, statusParam],
    queryFn: () => experimentApi.getExecutions(activeProjectId!, {
      limit,
      offset,
      status: statusParam
    }),
    enabled: !!activeProjectId,
    refetchInterval: 5000, 
  });

  // Active Preview Query
  const { data: previewExecution, isLoading: isPreviewExecutionLoading } = useQuery({
    queryKey: ['experiment-execution', activeProjectId, previewId],
    queryFn: () => experimentApi.getExecution(activeProjectId!, previewId!),
    enabled: !!activeProjectId && !!previewId,
    refetchInterval: (query) => {
      const state = query.state.data?.status;
      if (state === 'COMPLETED' || state === 'FAILED' || state === 'CANCELLED' || state === 'TIMED_OUT') {
        return false;
      }
      return 3000;
    }
  });

  // Report Query (only if COMPLETED)
  const isCompleted = previewExecution?.status === 'COMPLETED';
  const { data: previewReport, isLoading: isPreviewReportLoading } = useQuery({
    queryKey: ['experiment-report', previewId],
    queryFn: () => experimentApi.getReport(previewId!),
    enabled: !!previewId && isCompleted,
    retry: false // Do not retry report immediately if it's 404 while generating
  });

  // Presentation Models
  const catalog = useMemo(() => {
    if (!listData) {
      return { 
        rows: [], 
        rawVisibleIds: [],
        pagination: {
          currentPage: page,
          pageSize,
          totalItems: 0,
          totalPages: 0,
          hasNextPage: false,
          hasPrevPage: false
        }
      };
    }
    
    const rows = listData.items.map(mapExecutionToRowModel);
    const totalItems = listData.total;
    const totalPages = Math.ceil(totalItems / pageSize);
    
    return {
      rows,
      rawVisibleIds: rows.map(r => r.id),
      pagination: {
        currentPage: page,
        pageSize,
        totalItems,
        totalPages,
        hasNextPage: page < totalPages,
        hasPrevPage: page > 1
      }
    };
  }, [listData, page, pageSize]);

  const previewModel = useMemo(() => {
    if (!previewExecution) return null;
    return mapExecutionToPreviewModel(previewExecution, previewReport || null);
  }, [previewExecution, previewReport]);

  const isLoading = !activeProjectId || isListLoading;
  const error = listError as Error | null;

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
    refetch();
  }, [refetch]);

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
    isPreviewLoading: isPreviewExecutionLoading || isPreviewReportLoading,
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
