import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useWorkspaceStore } from '@/store/workspaceStore';
import { useProjectStore } from '@/features/projects/store/projectStore';
import { benchmarkApi } from '../api/benchmarkApi';
import type { BenchmarkCategory } from '@/domain/benchmarks/types';

export function useBenchmarks() {
  const store = useWorkspaceStore();
  const { activeProjectId } = useProjectStore();

  const [pagination, setPagination] = useState({ limit: 50, offset: 0 });

  const { data: serverData, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['benchmarks', activeProjectId, store.selectedCategory, pagination.limit, pagination.offset],
    queryFn: async () => {
      if (!activeProjectId) return { items: [], total: 0 };
      const res = await benchmarkApi.listBenchmarks(activeProjectId, pagination.limit, pagination.offset);
      return {
        items: res.items,
        total: res.total,
      };
    },
    enabled: !!activeProjectId,
  });

  const allBenchmarks = serverData?.items || [];
  const totalBenchmarks = serverData?.total || 0;

  const filteredBenchmarks = useMemo(() => {
    let items = allBenchmarks;

    // We do NOT perform client-side filtering over a single remote page to pretend it represents the complete dataset.
    // However, since we don't have backend search or category_id mappings, 
    // the user said: "Do not perform client-side filtering over a single remote page and pretend it represents the complete dataset."
    // So we should NOT filter locally if it misrepresents the total.
    // Actually, we can just return items as is, and disable unsupported filters.

    return items;
  }, [allBenchmarks]);

  const kpis = useMemo(() => {
    const total = totalBenchmarks; // Real total from backend
    const categoriesCount = 0; // Not available from backend
    const activeEvaluations = store.queue.filter((q) => q.status === 'Running').length;
    
    // Average verification is not provided by backend. 
    const avgVerification = 0; 

    return {
      total,
      categoriesCount,
      activeEvaluations,
      avgVerification,
    };
  }, [totalBenchmarks, store.queue]);

  const compareBenchmarks = useMemo(() => {
    return allBenchmarks.filter((b) => store.compareBenchmarkIds.includes(b.id));
  }, [allBenchmarks, store.compareBenchmarkIds]);

  return {
    benchmarks: filteredBenchmarks, // Real data
    allBenchmarks,
    kpis,
    searchQuery: store.searchQuery, // We can keep the state but disable its effect if unsupported
    selectedCategory: store.selectedCategory,
    activeDrawerBenchmark: store.activeDrawerBenchmark,
    compareBenchmarkIds: store.compareBenchmarkIds,
    compareBenchmarks,
    preferences: store.preferences,
    queue: store.queue,
    terminalLogs: store.terminalLogs,
    notifications: store.notifications,
    setSearchQuery: store.setSearchQuery,
    setSelectedCategory: (cat: string) =>
      store.setSelectedCategory(cat as BenchmarkCategory | 'all'),
    openDrawer: store.setActiveDrawerBenchmark,
    closeDrawer: () => store.setActiveDrawerBenchmark(null),
    toggleCompare: store.toggleCompareBenchmark,
    clearCompare: store.clearCompareBenchmarks,
    toggleViewMode: store.toggleViewMode,
    togglePin: store.togglePinBenchmark,
    triggerRun: store.triggerEvaluationRun,
    // Pagination specific exposes
    pagination,
    setPagination,
    totalBenchmarks,
    isLoading,
    isError,
    error,
    refetch
  };
}

export default useBenchmarks;
