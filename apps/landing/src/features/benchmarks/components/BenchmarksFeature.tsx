import React, { useState } from 'react';
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

export const BenchmarksFeature: React.FC = () => {
  const {
    benchmarks,
    kpis,
    searchQuery,
    selectedCategory,
    activeDrawerBenchmark,
    compareBenchmarkIds,
    compareBenchmarks,
    preferences,
    queue,
    terminalLogs,
    setSearchQuery,
    setSelectedCategory,
    openDrawer,
    closeDrawer,
    toggleCompare,
    toggleViewMode,
    triggerRun,
  } = useBenchmarks();

  const [isCompareModalOpen, setIsCompareModalOpen] = useState(false);

  return (
    <motion.div
      variants={pageCrossfade}
      initial="initial"
      animate="animate"
      exit="exit"
      className="w-full"
    >
      <WorkspacePage>
        {/* 1. Hero Overview */}
        <WorkspaceHero>
          <BenchmarkHeader
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
            viewMode={preferences.viewMode}
            onToggleViewMode={toggleViewMode}
            compareCount={compareBenchmarkIds.length}
            onOpenCompare={() => setIsCompareModalOpen(true)}
            onRunClick={() => triggerRun('mmlu-pro', 'GPT-5')}
          />
        </WorkspaceHero>

        {/* 2. Critical Enriched KPIs */}
        <BenchmarkKPIs kpis={kpis} />

        {/* 3. Primary Data Analytics */}
        <WorkspaceAnalytics>
          <BenchmarkAnalytics />
        </WorkspaceAnalytics>

        {/* 4. Operational Control Console */}
        <WorkspaceOperations>
          <BenchmarkConsole logs={terminalLogs} queue={queue} />
        </WorkspaceOperations>

        {/* 5. Benchmark Registry Table */}
        <WorkspaceRegistry>
          <BenchmarkRegistry
            benchmarks={benchmarks}
            selectedCategory={selectedCategory}
            onSelectCategory={setSelectedCategory}
            onRowClick={openDrawer}
            onRunClick={(id) => triggerRun(id, 'GPT-5')}
            onToggleCompare={toggleCompare}
            compareIds={compareBenchmarkIds}
          />
        </WorkspaceRegistry>

        {/* Supporting Drawers & Modals */}
        <BenchmarkDrawer
          benchmark={activeDrawerBenchmark}
          onClose={closeDrawer}
          onRun={(id) => triggerRun(id, 'GPT-5')}
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
