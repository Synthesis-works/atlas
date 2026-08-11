import { useMemo } from 'react';
import { useWorkspaceStore } from '@/store/workspaceStore';
import { filterBenchmarksByQuery } from '../lib/searchParser';
import type { BenchmarkCategory } from '@/domain/benchmarks/types';

export function useBenchmarks() {
  const store = useWorkspaceStore();

  const filteredBenchmarks = useMemo(() => {
    let items = store.benchmarks;

    if (store.selectedCategory && store.selectedCategory !== 'all') {
      items = items.filter((b) => b.category === store.selectedCategory);
    }

    if (store.searchQuery) {
      items = filterBenchmarksByQuery(items, store.searchQuery);
    }

    return items;
  }, [store.benchmarks, store.selectedCategory, store.searchQuery]);

  const kpis = useMemo(() => {
    const total = store.benchmarks.length;
    const categoriesCount = new Set(store.benchmarks.map((b) => b.category)).size;
    const activeEvaluations = store.queue.filter((q) => q.status === 'Running').length;
    const avgVerification =
      total > 0
        ? Math.round(
            store.benchmarks.reduce((acc, b) => acc + b.verificationScore, 0) / total
          )
        : 100;

    return {
      total,
      categoriesCount,
      activeEvaluations,
      avgVerification,
    };
  }, [store.benchmarks, store.queue]);

  const compareBenchmarks = useMemo(() => {
    return store.benchmarks.filter((b) => store.compareBenchmarkIds.includes(b.id));
  }, [store.benchmarks, store.compareBenchmarkIds]);

  return {
    benchmarks: filteredBenchmarks,
    allBenchmarks: store.benchmarks,
    kpis,
    searchQuery: store.searchQuery,
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
  };
}

export default useBenchmarks;
