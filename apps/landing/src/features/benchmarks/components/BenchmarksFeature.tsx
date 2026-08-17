import React, { useCallback, useState } from 'react';
import { motion } from 'framer-motion';
import { pageCrossfade } from '@/lib/motion';
import { useBenchmarks } from '../hooks/useBenchmarks';
import {
  WorkspacePage,
  WorkspaceHero,
  WorkspaceAnalytics,
  WorkspaceOperations,
  WorkspaceRegistry,
} from '@/components/layout/WorkspacePage';
import BenchmarkHeader from './BenchmarkHeader';
import BenchmarkKPIs from './BenchmarkKPIs';
import BenchmarkAnalytics from './BenchmarkAnalytics';
import BenchmarkConsole from './BenchmarkConsole';
import BenchmarkRegistry from './BenchmarkRegistry';
import BenchmarkDrawer from './Drawer';
import BenchmarkCompareModal from './BenchmarkCompareModal';
import AtlasRuntimeWidget from './AtlasRuntimeWidget';

const DEFAULT_RUN_MODEL = 'groq/openai/gpt-oss-20b';

export const BenchmarksFeature: React.FC = () => {
  const {
    benchmarks: _benchmarks,
    kpis,
    searchQuery,
    selectedCategory: _selectedCategory,
    activeDrawerBenchmark,
    compareBenchmarkIds,
    compareBenchmarks,
    preferences,
    queue,
    terminalLogs,
    setSearchQuery,
    closeDrawer,
    toggleCompare,
    triggerRun,
    toggleViewMode,
  } = useBenchmarks();

  const [isCompareModalOpen, setIsCompareModalOpen] = useState(false);

  const handleRunBenchmark = useCallback(
    async (benchmarkName?: string) => {
      const { getDispatchTargets } = await import('@/features/evaluations/services/evaluationService');
      const res = await getDispatchTargets();
      const targets = res.data || [];
      const target = benchmarkName
        ? targets.find((t) => t.benchmark_name === benchmarkName)
        : targets[0];
      if (!target) return;
      await triggerRun(target.benchmark_version_id, DEFAULT_RUN_MODEL);
    },
    [triggerRun]
  );

  return (
    <motion.div variants={pageCrossfade} initial="initial" animate="animate" exit="exit" className="h-full flex flex-col min-h-0">
      <WorkspacePage>
        {/* 1. Header */}
        <WorkspaceHero>
          <BenchmarkHeader
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
            viewMode={preferences.viewMode}
            onToggleViewMode={toggleViewMode}
            compareCount={compareBenchmarkIds.length}
            onOpenCompare={() => setIsCompareModalOpen(true)}
            onRunClick={() => handleRunBenchmark()}
          />
        </WorkspaceHero>

        {/* 2. Key Metrics KPIs */}
        <BenchmarkKPIs kpis={kpis} />

        {/* 3. Analytics Charts Grid */}
        <WorkspaceAnalytics>
          <BenchmarkAnalytics />
        </WorkspaceAnalytics>

        {/* 4. Real-time Console Operations */}
        <WorkspaceOperations>
          <BenchmarkConsole logs={terminalLogs} queue={queue} />
        </WorkspaceOperations>

        {/* 5. Benchmark Registry Table */}
        <WorkspaceRegistry>
          <BenchmarkRegistry />
        </WorkspaceRegistry>

        {/* Supporting Drawers & Modals */}
        <BenchmarkDrawer
          benchmark={activeDrawerBenchmark}
          onClose={closeDrawer}
          onRun={(name) => handleRunBenchmark(name)}
        />

        <BenchmarkCompareModal
          isOpen={isCompareModalOpen}
          onClose={() => setIsCompareModalOpen(false)}
          benchmarks={compareBenchmarks}
          onRemove={toggleCompare}
        />

        <AtlasRuntimeWidget />
      </WorkspacePage>
    </motion.div>
  );
};

export default BenchmarksFeature;
