/**
 * Features — Benchmark Store
 * Single source of truth for the Benchmarks workspace with live backend synchronization.
 * Follows the architecture of ModelsStoreProvider.
 */

import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  useMemo,
  useEffect,
  useRef,
} from 'react';
import type { Benchmark, BenchmarkCategory } from '@/domain/benchmarks/types';
import { getBenchmarks, runBenchmark } from '../services/benchmarkService';

export interface BenchmarkStoreContextType {
  benchmarks: Benchmark[];
  isLoading: boolean;
  error: string | null;
  selectedBenchmark: Benchmark | null;
  searchQuery: string;
  selectedCategory: BenchmarkCategory | 'all';
  compareBenchmarkIds: string[];
  drawerOpen: boolean;
  refresh: () => Promise<void>;
  setSelectedBenchmark: (bm: Benchmark | null) => void;
  setSearchQuery: (q: string) => void;
  setSelectedCategory: (cat: BenchmarkCategory | 'all') => void;
  openDrawer: (bm: Benchmark) => void;
  closeDrawer: () => void;
  toggleCompare: (id: string) => void;
  clearCompare: () => void;
  triggerRun: (benchmarkVersionId: string, model: string, datasetVersionId?: string | null) => Promise<{ id: string; status: string } | null>;
}

const BenchmarkStoreContext = createContext<BenchmarkStoreContextType | null>(null);

const POLLING_INTERVAL_MS = 10000;

export const BenchmarkStoreProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [benchmarks, setBenchmarks] = useState<Benchmark[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedBenchmark, setSelectedBenchmark] = useState<Benchmark | null>(null);

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<BenchmarkCategory | 'all'>('all');
  const [compareBenchmarkIds, setCompareBenchmarkIds] = useState<string[]>([]);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const inFlightRef = useRef(false);

  const fetchBenchmarks = useCallback(async (showLoading = false) => {
    if (inFlightRef.current) return;
    inFlightRef.current = true;
    if (showLoading) setIsLoading(true);

    try {
      const res = await getBenchmarks();
      if (res.error) {
        setError(res.error);
        // Preserve last known real data on transient network error
      } else {
        setBenchmarks((prev) => {
          // Compare JSON stringification to prevent unnecessary rerenders
          const prevJson = JSON.stringify(prev);
          const nextJson = JSON.stringify(res.data);
          return prevJson === nextJson ? prev : res.data;
        });
        setError(null);

        // Keep selectedBenchmark synchronized
        setSelectedBenchmark((current) => {
          if (!current) return null;
          const updated = res.data.find((b) => b.id === current.id);
          return updated || current;
        });
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to synchronize benchmarks');
    } finally {
      setIsLoading(false);
      inFlightRef.current = false;
    }
  }, []);

  const refresh = useCallback(async () => {
    await fetchBenchmarks(true);
  }, [fetchBenchmarks]);

  // Initial fetch and 10-second polling + visibility change sync
  useEffect(() => {
    fetchBenchmarks(true);

    const intervalId = setInterval(() => {
      if (document.visibilityState === 'visible') {
        fetchBenchmarks(false);
      }
    }, POLLING_INTERVAL_MS);

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        fetchBenchmarks(false);
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      clearInterval(intervalId);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [fetchBenchmarks]);

  const openDrawer = useCallback((bm: Benchmark) => {
    setSelectedBenchmark(bm);
    setDrawerOpen(true);
  }, []);

  const closeDrawer = useCallback(() => {
    setSelectedBenchmark(null);
    setDrawerOpen(false);
  }, []);

  const toggleCompare = useCallback((id: string) => {
    setCompareBenchmarkIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    );
  }, []);

  const clearCompare = useCallback(() => {
    setCompareBenchmarkIds([]);
  }, []);

  const triggerRun = useCallback(
    async (benchmarkVersionId: string, model: string, datasetVersionId?: string | null) => {
      const res = await runBenchmark(benchmarkVersionId, model, datasetVersionId);
      if (res.data) {
        // Refresh immediately to capture newly queued execution
        fetchBenchmarks(false);
      }
      return res.data;
    },
    [fetchBenchmarks]
  );

  const value = useMemo(
    () => ({
      benchmarks,
      isLoading,
      error,
      selectedBenchmark,
      searchQuery,
      selectedCategory,
      compareBenchmarkIds,
      drawerOpen,
      refresh,
      setSelectedBenchmark,
      setSearchQuery,
      setSelectedCategory,
      openDrawer,
      closeDrawer,
      toggleCompare,
      clearCompare,
      triggerRun,
    }),
    [
      benchmarks,
      isLoading,
      error,
      selectedBenchmark,
      searchQuery,
      selectedCategory,
      compareBenchmarkIds,
      drawerOpen,
      refresh,
      openDrawer,
      closeDrawer,
      toggleCompare,
      clearCompare,
      triggerRun,
    ]
  );

  return (
    <BenchmarkStoreContext.Provider value={value}>
      {children}
    </BenchmarkStoreContext.Provider>
  );
};

export const useBenchmarkStore = () => {
  const ctx = useContext(BenchmarkStoreContext);
  if (!ctx) {
    throw new Error('useBenchmarkStore must be used within a BenchmarkStoreProvider');
  }
  return ctx;
};
