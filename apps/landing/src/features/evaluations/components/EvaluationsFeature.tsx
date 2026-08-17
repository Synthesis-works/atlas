import React, { useState } from 'react';
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
import { NewEvaluationModal } from './NewEvaluationModal';
import type { EvaluationRun } from '@/domain/evaluations/types';

interface EvaluationsFeatureProps {
  openNewModal?: boolean;
}

export const EvaluationsFeature: React.FC<EvaluationsFeatureProps> = ({ openNewModal = false }) => {
  const {
    evaluations, allEvaluations, activeEvaluations,
    reports, kpis, analyticsData,
    searchQuery, statusFilter,
    selectedEvaluation, compareIds, compareEvaluations, isCompareOpen,
    runtimeLogs,
    setSearchQuery, setStatusFilter,
    openDrawer, closeDrawer,
    toggleCompare, openCompare, closeCompare,
    addExecutionRun,
  } = useEvaluations();

  const [isNewModalOpen, setIsNewModalOpen] = useState(openNewModal);
  const [timelineEval, setTimelineEval] = useState<EvaluationRun | null>(null);

  React.useEffect(() => {
    if (openNewModal) {
      setIsNewModalOpen(true);
    }
  }, [openNewModal]);

  React.useEffect(() => {
    if (!timelineEval && (activeEvaluations[0] || evaluations[0])) {
      setTimelineEval(activeEvaluations[0] ?? evaluations[0] ?? null);
    }
  }, [activeEvaluations, evaluations, timelineEval]);

  const handleRunDispatched = (dto: any) => {
    const newRun: EvaluationRun = {
      id: dto.id,
      name: `${dto.target_model} on ${dto.benchmark_version_id === '00000000-0000-0000-0000-000000000005' ? 'HumanEval Benchmark' : dto.benchmark_version_id}`,
      benchmark: dto.benchmark_version_id === '00000000-0000-0000-0000-000000000005' ? 'HumanEval Benchmark' : dto.benchmark_version_id,
      benchmarkCategory: 'coding',
      priority: 'high',
      dataset: 'Test Set',
      model: dto.target_model,
      modelProvider: dto.target_model.includes('groq') ? 'Groq' : 'Live Provider',
      status: 'Queued',
      progress: 0,
      currentStage: 'Queued',
      worker: 'worker-node-01',
      workerStatus: 'busy',
      queuedAt: dto.created_at || new Date().toISOString(),
      startedAt: new Date().toISOString(),
      durationMs: 0,
      owner: 'Atlas Admin',
      metrics: { passAt1: 0, accuracy: 0, latencyMs: 0 },
      stages: [],
      logs: [],
      artifacts: [],
      config: { temperature: 0.2, topP: 0.9, seed: 42, maxTokens: 2048, batchSize: 8, threads: 4, timeout: '300s', retries: 3, provider: 'Live Provider' },
      reproducibility: { modelVersion: '1.0', datasetVersion: '1.0', benchmarkVersion: '1.0', promptVersion: '1.0', commitSha: 'a1b2c3d', dockerImage: 'atlas-runner:v1', runtime: 'python-3.11', seed: 42, os: 'Linux', pythonVersion: '3.11', cudaVersion: '12.1', engineVersion: '2.1.0' },
      isVerified: true,
      source: 'live',
      tags: ['live', 'groq', 'verified'],
    };

    addExecutionRun(newRun);
    setTimelineEval(newRun);
    setIsNewModalOpen(false);
  };

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
    <div className="w-full text-white">
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
            onOpenNewModal={() => setIsNewModalOpen(true)}
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

        {/* New Evaluation Modal */}
        <NewEvaluationModal
          isOpen={isNewModalOpen}
          onClose={() => setIsNewModalOpen(false)}
          onRunDispatched={handleRunDispatched}
        />

        {/* Detail Drawer */}
        {selectedEvaluation && (
          <EvaluationDrawer evaluation={selectedEvaluation} onClose={closeDrawer} />
        )}

        {/* Comparison Modal */}
        {isCompareOpen && compareEvaluations.length > 0 && (
          <ComparisonView evaluations={compareEvaluations} onClose={closeCompare} />
        )}
      </WorkspacePage>
    </div>
  );
};

export default EvaluationsFeature;
