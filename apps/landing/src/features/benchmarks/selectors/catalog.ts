import type { Benchmark } from '../../../domain/benchmarks/types';
import { 
  buildBenchmarkCardModel, 
  buildBenchmarkRowModel, 
  buildBenchmarkPreviewModel,
  buildBenchmarkComparisonModel
} from '../presentation/catalog';

export interface BenchmarkFilterState {
  searchQuery: string;
  category: string;
  status: string;
  difficulty: string;
}

export interface BenchmarkSortState {
  field: 'name' | 'verificationScore' | 'tasksCount' | 'updatedAt';
  direction: 'asc' | 'desc';
}

export function filterBenchmarks(benchmarks: Benchmark[], filters: BenchmarkFilterState): Benchmark[] {
  return benchmarks.filter(benchmark => {
    if (filters.searchQuery) {
      const q = filters.searchQuery.toLowerCase();
      if (!benchmark.name.toLowerCase().includes(q) && 
          !(benchmark.description && benchmark.description.toLowerCase().includes(q)) &&
          !(benchmark.tags && benchmark.tags.some(t => t.toLowerCase().includes(q)))) {
        return false;
      }
    }
    
    if (filters.category && filters.category !== 'all' && benchmark.category !== filters.category) {
      return false;
    }
    
    if (filters.status && filters.status !== 'all' && benchmark.status !== filters.status) {
      return false;
    }

    if (filters.difficulty && filters.difficulty !== 'all' && benchmark.difficulty !== filters.difficulty) {
      return false;
    }
    
    return true;
  });
}

export function sortBenchmarks(benchmarks: Benchmark[], sort: BenchmarkSortState): Benchmark[] {
  return [...benchmarks].sort((a, b) => {
    let comparison = 0;
    
    switch (sort.field) {
      case 'name':
        comparison = a.name.localeCompare(b.name);
        break;
      case 'verificationScore':
        comparison = (a.verificationScore ?? -1) - (b.verificationScore ?? -1);
        break;
      case 'tasksCount':
        comparison = (a.tasksCount ?? -1) - (b.tasksCount ?? -1);
        break;
      case 'updatedAt':
        comparison = new Date(a.updatedAt ?? 0).getTime() - new Date(b.updatedAt ?? 0).getTime();
        if (isNaN(comparison)) comparison = 0;
        break;
    }
    
    return sort.direction === 'asc' ? comparison : -comparison;
  });
}

export function selectBenchmarkCatalog(
  benchmarks: Benchmark[], 
  filters: BenchmarkFilterState, 
  sort: BenchmarkSortState,
  page: number,
  pageSize: number
) {
  const filtered = filterBenchmarks(benchmarks, filters);
  const sorted = sortBenchmarks(filtered, sort);
  
  const totalItems = sorted.length;
  const totalPages = Math.ceil(totalItems / pageSize);
  const offset = (page - 1) * pageSize;
  const paginated = sorted.slice(offset, offset + pageSize);

  return {
    cards: paginated.map(buildBenchmarkCardModel),
    rows: paginated.map(buildBenchmarkRowModel),
    rawVisibleIds: paginated.map(b => b.id),
    totalItems,
    totalPages,
    currentPage: page
  };
}

export function selectBenchmarkPreview(benchmark?: Benchmark) {
  if (!benchmark) return null;
  return buildBenchmarkPreviewModel(benchmark);
}

export function selectBenchmarkComparisons(benchmarks: Benchmark[], ids: string[]) {
  const selected = benchmarks.filter(b => ids.includes(b.id));
  return selected.map(buildBenchmarkComparisonModel);
}
