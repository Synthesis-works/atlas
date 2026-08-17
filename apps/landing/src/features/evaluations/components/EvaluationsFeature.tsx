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
import { EvaluationDetailSurface } from './EvaluationDetailSurface';
import { ComparisonView } from './ComparisonView';
import { NewEvaluationModal } from './NewEvaluationModal';
import type { EvaluationRun } from '@/domain/evaluations/types';

interface EvaluationsFeatureProps {
  openNewModal?: boolean;
}

function deriveProviderLabel(model: string): string {
  const lowered = (model || '').toLowerCase();
  if (lowered.includes('gemini')) return 'Google AI';
  if (lowered.includes('gpt')) return 'OpenAI';
  if (lowered.includes('claude')) return 'Anthropic';
  if (lowered.includes('grok')) return 'xAI';
  if (lowered.includes('llama') || lowered.includes('qwen') || lowered.includes('mistral') || lowered.includes('deepseek')) return 'Open Source';
  return 'Unknown';
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

  const handleRunDispatched = (dto: any, benchmark: { name: string; version: string }) => {
    const newRun: EvaluationRun = {
      id: dto.id,
      name: `${dto.target_model} on ${benchmark.name}`,
      benchmark: benchmark.name,
      benchmarkVersion: benchmark.version,
      benchmarkCategory: '',
      priority: 'normal',
      dataset: '',
      model: dto.target_model,
      modelProvider: deriveProviderLabel(dto.target_model),
      status: 'Queued',
      progress: 0,
      currentStage: 'Queued',
      worker: '',
      workerStatus: 'idle',
      queuedAt: dto.created_at || new Date().toISOString(),
      startedAt: dto.created_at || new Date().toISOString(),
      owner: '—',
      stages: [],
      logs: [],
      artifacts: [],
      tags: ['live'],
      source: 'live',
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

  // Full-workspace detail surface: replaces the evaluation workspace entirely so
  // no stale canvas remains behind it. Live lifecycle data flows from the hook's
  // 3s refresh through `selectedEvaluation`.
  if (selectedEvaluation) {
    return (
      <div className="w-full h-full text-white">
        <EvaluationDetailSurface evaluation={selectedEvaluation} onClose={closeDrawer} />
      </div>
    );
  }

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
            activeWorkers={kpis.activeWorkers}
            successRate={kpis.successRate}
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
            selectedId={undefined}
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

        {/* Comparison Modal */}
        {isCompareOpen && compareEvaluations.length > 0 && (
          <ComparisonView evaluations={compareEvaluations} onClose={closeCompare} />
        )}
      </WorkspacePage>
    </div>
  );
};

export default EvaluationsFeature;
