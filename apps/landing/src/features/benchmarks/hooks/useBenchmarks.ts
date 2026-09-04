import { useMemo } from 'react';
import { useBenchmarkStore } from '../store/benchmarkStore';
import { useWorkspaceStore } from '@/store/workspaceStore';
import { filterBenchmarksByQuery } from '../lib/searchParser';
import type { BenchmarkCategory } from '@/domain/benchmarks/types';

export function useBenchmarks() {
  const benchmarkStore = useBenchmarkStore();
  let workspaceStore: any = null;
  try {
    // Optional workspace store consumption for queue/notifications
    // eslint-disable-next-line react-hooks/rules-of-hooks
    workspaceStore = useWorkspaceStore();
  } catch (_) {
    // Fallback gracefully if used outside WorkspaceStoreProvider
  }

  const benchmarks = benchmarkStore.benchmarks;

  const filteredBenchmarks = useMemo(() => {
    let items = benchmarks;

    if (benchmarkStore.selectedCategory && benchmarkStore.selectedCategory !== 'all') {
      items = items.filter((b) => b.category === benchmarkStore.selectedCategory);
    }

    if (benchmarkStore.searchQuery) {
      items = filterBenchmarksByQuery(items, benchmarkStore.searchQuery);
    }

    return items;
  }, [benchmarks, benchmarkStore.selectedCategory, benchmarkStore.searchQuery]);

  const kpis = useMemo(() => {
    const total = benchmarks.length;
    const categoriesCount = new Set(benchmarks.map((b) => b.category)).size;
    const queue = workspaceStore?.queue || [];
    const activeEvaluations = queue.filter((q: any) => q.status === 'Running').length;

    // Real score calculation: only consider benchmarks that have real scores recorded
    const scored = benchmarks.filter(
      (b) => b.latestScore != null || b.averageScore != null
    );
    const avgVerification =
      scored.length > 0
        ? Math.round(
            scored.reduce(
              (acc, b) => acc + (b.latestScore ?? b.averageScore ?? 0),
              0
            ) / scored.length
          )
        : null;

    const completedRuns = benchmarks.reduce(
      (acc, b) => acc + (b.completedExecutionCount ?? 0),
      0
    );
    const totalExecutions = benchmarks.reduce(
      (acc, b) => acc + (b.executionCount ?? 0),
      0
    );

    return {
      total,
      categoriesCount,
      activeEvaluations,
      avgVerification,
      completedRuns,
      totalExecutions,
    };
  }, [benchmarks, workspaceStore?.queue]);

  const compareBenchmarks = useMemo(() => {
    return benchmarks.filter((b) => benchmarkStore.compareBenchmarkIds.includes(b.id));
  }, [benchmarks, benchmarkStore.compareBenchmarkIds]);

  return {
    benchmarks: filteredBenchmarks,
    allBenchmarks: benchmarks,
    isLoading: benchmarkStore.isLoading,
    error: benchmarkStore.error,
    refresh: benchmarkStore.refresh,
    kpis,
    searchQuery: benchmarkStore.searchQuery,
    selectedCategory: benchmarkStore.selectedCategory,
    activeDrawerBenchmark: benchmarkStore.selectedBenchmark,
    compareBenchmarkIds: benchmarkStore.compareBenchmarkIds,
    compareBenchmarks,
    preferences: workspaceStore?.preferences || { viewMode: 'grid', compactMode: false, pinnedIds: [] },
    queue: workspaceStore?.queue || [],
    terminalLogs: workspaceStore?.terminalLogs || [],
    notifications: workspaceStore?.notifications || [],
    setSearchQuery: benchmarkStore.setSearchQuery,
    setSelectedCategory: (cat: string) =>
      benchmarkStore.setSelectedCategory(cat as BenchmarkCategory | 'all'),
    openDrawer: benchmarkStore.openDrawer,
    closeDrawer: benchmarkStore.closeDrawer,
    toggleCompare: benchmarkStore.toggleCompare,
    clearCompare: benchmarkStore.clearCompare,
    toggleViewMode: workspaceStore?.toggleViewMode || (() => {}),
    togglePin: workspaceStore?.togglePinBenchmark || (() => {}),
    triggerRun: benchmarkStore.triggerRun,
  };
}

export default useBenchmarks;

