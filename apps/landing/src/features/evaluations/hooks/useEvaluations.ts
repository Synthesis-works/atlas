import { useMemo, useState, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useProjectStore } from '@/features/projects/store/projectStore';
import { executionApi } from '../api/executionApi';
import {
  MOCK_RUNTIME_LOGS,
  MOCK_REPORTS,
  MOCK_RUNTIME_DISTRIBUTION,
  MOCK_SUCCESS_RATE_TREND,
  MOCK_QUEUE_LENGTH_TREND,
  MOCK_FAILURE_DISTRIBUTION,
} from '@/domain/evaluations/mock';
import type { EvaluationRun, EvaluationReport } from '@/domain/evaluations/types';
import { filterEvaluations } from '../lib/searchParser';

type ViewMode = 'queue' | 'analytics';

export function useEvaluations() {
  const { activeProjectId } = useProjectStore();

  const { data: realExecutions, isLoading, refetch } = useQuery({
    queryKey: ['executions', activeProjectId],
    queryFn: () => activeProjectId 
      ? executionApi.getProjectExecutions(activeProjectId)
      : executionApi.getRecentExecutions(),
  });

  const evaluations = realExecutions || [];
  
  const [reports] = useState<EvaluationReport[]>(MOCK_REPORTS);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [selectedEvaluation, setSelectedEvaluation] = useState<EvaluationRun | null>(null);
  const [compareIds, setCompareIds] = useState<string[]>([]);
  const [isCompareOpen, setIsCompareOpen] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>('queue');
  const [runtimeLogs] = useState<string[]>(MOCK_RUNTIME_LOGS);
  const [terminalPaused, setTerminalPaused] = useState(false);

  // Combined filter: status tab + search query (key:value + comparators)
  const filteredEvaluations = useMemo(() => {
    let result = evaluations;
    if (statusFilter !== 'all') {
      result = result.filter(e => e.status.toLowerCase() === statusFilter.toLowerCase());
    }
    if (searchQuery.trim()) {
      result = filterEvaluations(result, searchQuery);
    }
    return result;
  }, [evaluations, searchQuery, statusFilter]);

  // KPI aggregations
  const kpis = useMemo(() => {
    const running = evaluations.filter(e => e.status === 'Running').length;
    const queued = evaluations.filter(e => e.status === 'Queued').length;
    const active = evaluations.filter(e => ['Running', 'Scoring', 'Aggregating', 'Reporting'].includes(e.status)).length;
    const completed = evaluations.filter(e => e.status === 'Completed');
    const failed = evaluations.filter(e => e.status === 'Failed').length;

    const successRate = (completed.length + failed) > 0
      ? (completed.length / (completed.length + failed)) * 100
      : 0;
    const failureRate = 100 - successRate;

    const avgDurationMs = completed.length > 0
      ? completed.reduce((s, e) => s + (e.durationMs ?? 0), 0) / completed.length
      : 0;

    const totalGpuHours = completed.reduce((s, e) => {
      const hrs = (e.durationMs ?? 0) / 3600000;
      const util = (e.metrics?.gpuUtilPct ?? 0) / 100;
      return s + hrs * util;
    }, 0);

    const totalTokens = completed.reduce((s, e) => {
      return s + ((e.metrics?.tokensPerSec ?? 0) * (e.durationMs ?? 0) / 1000);
    }, 0);

    const totalCost = completed.reduce((s, e) => s + (e.metrics?.costUsd ?? 0), 0);

    const activeWorkers = new Set(
      evaluations.filter(e => e.workerStatus === 'busy').map(e => e.worker)
    ).size;

    return {
      running,
      queued,
      active,
      completedToday: completed.length,
      failed,
      successRate: Math.round(successRate * 10) / 10,
      failureRate: Math.round(failureRate * 10) / 10,
      avgRuntimeMs: avgDurationMs,
      gpuHours: Math.round(totalGpuHours),
      tokensProcessed: Math.round(totalTokens),
      totalCostUsd: totalCost,
      activeWorkers,
      totalWorkers: 24,
    };
  }, [evaluations]);

  // Active evaluations (for live panel and timeline)
  const activeEvaluations = useMemo(
    () => evaluations.filter(e => !['Completed', 'Failed', 'Cancelled'].includes(e.status)).slice(0, 8),
    [evaluations]
  );

  // Comparison evaluations
  const compareEvaluations = useMemo(
    () => evaluations.filter(e => compareIds.includes(e.id)),
    [evaluations, compareIds]
  );

  const toggleCompare = useCallback((id: string) => {
    setCompareIds(prev =>
      prev.includes(id) ? prev.filter(i => i !== id) : prev.length < 4 ? [...prev, id] : prev
    );
  }, []);

    // Analytics data (static from mock)
  const analyticsData = {
    runtimeDistribution: MOCK_RUNTIME_DISTRIBUTION,
    successRateTrend: MOCK_SUCCESS_RATE_TREND,
    queueLengthTrend: MOCK_QUEUE_LENGTH_TREND,
    failureDistribution: MOCK_FAILURE_DISTRIBUTION,
  };

  return {
    evaluations: filteredEvaluations,
    allEvaluations: evaluations,
    activeEvaluations,
    reports,
    kpis,
    analyticsData,
    searchQuery,
    statusFilter,
    selectedEvaluation,
    compareIds,
    compareEvaluations,
    isCompareOpen,
    viewMode,
    runtimeLogs,
    terminalPaused,
    isLoading, // Export loading state
    refetch,

    setSearchQuery,
    setStatusFilter,
    setViewMode,
    setTerminalPaused,
    openDrawer: setSelectedEvaluation,
    closeDrawer: () => setSelectedEvaluation(null),
    toggleCompare,
    openCompare: () => setIsCompareOpen(true),
    closeCompare: () => setIsCompareOpen(false),
  };
}

export default useEvaluations;
