import type { Column } from '@/shared/components';
import type { Benchmark } from '@/domain/benchmarks/types';

export const BENCHMARK_TABLE_COLUMNS: Column<Benchmark>[] = [
  { key: 'name', header: 'Benchmark Name', className: 'font-semibold text-white' },
  { key: 'category', header: 'Category' },
  { key: 'version', header: 'Version' },
  { key: 'tasksCount', header: 'Tasks' },
  { key: 'samplesCount', header: 'Samples' },
  { key: 'verificationScore', header: 'Verification' },
  { key: 'status', header: 'Status' },
  { key: 'updatedAt', header: 'Updated' },
  { key: 'actions', header: 'Actions', className: 'text-right' },
];
