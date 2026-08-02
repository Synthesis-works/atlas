/**
 * Workspace Page — Benchmarks
 * Thin route wrapper connecting the workspace store provider to BenchmarksFeature.
 */


import { BenchmarksFeature } from '@/features/benchmarks';

export default function WorkspaceBenchmarksPage() {
  return (
    <BenchmarksFeature />
  );
}
