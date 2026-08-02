import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { pageCrossfade } from '@/lib/motion';
import { useEvaluations } from '../hooks/useEvaluations';
import {
  WorkspacePage,
  WorkspaceHero,
  WorkspaceAnalytics,
  WorkspaceOperations,
  WorkspaceRegistry,
} from '@/components/layout/WorkspacePage';
import { EvaluationHeader } from './EvaluationHeader';
import { EvaluationKPIs } from './EvaluationKPIs';
import { AnalyticsGrid } from './AnalyticsGrid';
import { EvaluationConsole } from './EvaluationConsole';
import { ReportsTable } from './ReportsTable';
import { EvaluationDrawer } from './Drawer';
import { ComparisonView } from './ComparisonView';
import type { EvaluationRun } from '@/domain/evaluations/types';

export const EvaluationsFeature: React.FC = () => {
  const {
    evaluations, allEvaluations, activeEvaluations,
    reports, kpis, analyticsData,
    searchQuery, statusFilter,
    selectedEvaluation, compareIds, compareEvaluations, isCompareOpen,
    runtimeLogs,
    setSearchQuery, setStatusFilter,
    openDrawer, closeDrawer,
    toggleCompare, openCompare, closeCompare,
  } = useEvaluations();

  const [timelineEval, setTimelineEval] = useState<EvaluationRun | null>(
    activeEvaluations[0] ?? evaluations[0] ?? null
  );

  const handleRowClick = (ev: EvaluationRun) => {
    setTimelineEval(ev);
    openDrawer(ev);
  };

  const handleAction = (
    action: 'pause' | 'resume' | 'cancel' | 'duplicate',
    ev: EvaluationRun
  ) => {
    console.log(`[Atlas] Action: ${action} on ${ev.id}`);
  };

  const handleRefresh = () => {
    console.log('[Atlas] Refreshing evaluations state...');
  };

  return (
    <motion.div
      variants={pageCrossfade}
      initial="initial"
      animate="animate"
      exit="exit"
      className="w-full text-white"
    >
      <WorkspacePage>
        {/* 1. Step 1: Observe — Hero Overview */}
        <WorkspaceHero>
          <EvaluationHeader
            searchQuery={searchQuery}
            statusFilter={statusFilter}
            totalCount={allEvaluations.length}
            filteredCount={evaluations.length}
            compareCount={compareIds.length}
            onSearch={setSearchQuery}
            onStatusFilter={setStatusFilter}
            onOpenCompare={openCompare}
            onRefresh={handleRefresh}
          />
        </WorkspaceHero>

        {/* 2. Step 2: Understand — Core Health KPIs */}
        <EvaluationKPIs kpis={kpis} />

        {/* 3. Step 3: Analyze — Evaluation Intelligence Surface */}
        <WorkspaceAnalytics>
          <AnalyticsGrid data={analyticsData} />
        </WorkspaceAnalytics>

        {/* 4. Step 4: Execute — Operational Control Center */}
        <WorkspaceOperations>
          <EvaluationConsole
            evaluations={evaluations}
            activeEvaluations={activeEvaluations}
            selectedId={selectedEvaluation?.id}
            compareIds={compareIds}
            timelineEval={timelineEval}
            runtimeLogs={runtimeLogs}
            onRowClick={handleRowClick}
            onToggleCompare={toggleCompare}
            onAction={handleAction}
          />
        </WorkspaceOperations>

        {/* 5. Step 5: Manage — Run & Report Registry */}
        <WorkspaceRegistry>
          <ReportsTable reports={reports} />
        </WorkspaceRegistry>

        {/* Detail Drawer */}
        {selectedEvaluation && (
          <EvaluationDrawer evaluation={selectedEvaluation} onClose={closeDrawer} />
        )}

        {/* Comparison Modal */}
        {isCompareOpen && compareEvaluations.length > 0 && (
          <ComparisonView evaluations={compareEvaluations} onClose={closeCompare} />
        )}
      </WorkspacePage>
    </motion.div>
  );
};

export default EvaluationsFeature;
