import { useMemo, useState, useCallback, useEffect } from 'react';
import type { EvaluationRun, EvaluationReport } from '@/domain/evaluations/types';
import { filterEvaluations } from '../lib/searchParser';
import { getEvaluations } from '../services/evaluationService';

type ViewMode = 'queue' | 'analytics';

export function useEvaluations() {
  const [evaluations, setEvaluations] = useState<EvaluationRun[]>([]);
  const [reports] = useState<EvaluationReport[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [selectedEvaluation, setSelectedEvaluation] = useState<EvaluationRun | null>(null);
  const [compareIds, setCompareIds] = useState<string[]>([]);
  const [isCompareOpen, setIsCompareOpen] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>('queue');
  const [runtimeLogs] = useState<string[]>([]);
  const [terminalPaused, setTerminalPaused] = useState(false);

  useEffect(() => {
    let isMounted = true;
    const fetchEvaluations = async () => {
      const res = await getEvaluations();
      if (isMounted && res.data && res.data.length > 0) {
        setEvaluations(res.data);
        // Keep the open detail surface live: re-attach the freshest snapshot of
        // the selected run so status/progress/metrics update without a reload.
        setSelectedEvaluation((prev) => {
          if (!prev) return prev;
          const fresh = res.data.find((e) => e.id === prev.id);
          return fresh ?? prev;
        });
      }
    };
    fetchEvaluations();
    const interval = setInterval(fetchEvaluations, 3000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const addExecutionRun = useCallback((newRun: EvaluationRun) => {
    setEvaluations((prev) => [newRun, ...prev.filter((e) => e.id !== newRun.id)]);
    setSelectedEvaluation(newRun);
  }, []);


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
      totalWorkers: activeWorkers,
    };
  }, [evaluations]);

  // Derived active evaluations
  const activeEvaluations = useMemo(
    () => evaluations.filter(e => ['Running', 'Scoring', 'Aggregating', 'Reporting'].includes(e.status)),
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

  // Analytics data derived dynamically from live evaluations
  const analyticsData = useMemo(() => {
    const completed = evaluations.filter(e => e.status === 'Completed');
    const queuedCount = evaluations.filter(e => e.status === 'Queued').length;
    const runningCount = evaluations.filter(e => e.status === 'Running').length;
    const passRate = completed.length > 0 ? (completed.filter(e => (e.metrics?.passAt1 ?? 0) > 50).length / completed.length) * 100 : 0;

    return {
      runtimeDistribution: [
        { label: '0-5s', count: completed.filter(e => (e.durationMs ?? 0) <= 5000).length },
        { label: '5-10s', count: completed.filter(e => (e.durationMs ?? 0) > 5000 && (e.durationMs ?? 0) <= 10000).length },
        { label: '10-20s', count: completed.filter(e => (e.durationMs ?? 0) > 10000 && (e.durationMs ?? 0) <= 20000).length },
        { label: '20-60s', count: completed.filter(e => (e.durationMs ?? 0) > 20000 && (e.durationMs ?? 0) <= 60000).length },
        { label: '60s+', count: completed.filter(e => (e.durationMs ?? 0) > 60000).length },
      ],
      successRateTrend: [
        { day: 'Current', rate: Math.round(passRate) },
        { day: 'Current', rate: Math.round(passRate) },
        { day: 'Current', rate: Math.round(passRate) },
      ],
      queueLengthTrend: [
        { hour: 'Now', length: queuedCount },
        { hour: 'Now', length: runningCount },
        { hour: 'Now', length: queuedCount },
      ],
      failureDistribution: evaluations.filter(e => e.status === 'Failed').length > 0
        ? [{ reason: 'Execution Failed', count: evaluations.filter(e => e.status === 'Failed').length }]
        : [{ reason: 'No Failures', count: 0 }],
    };
  }, [evaluations]);

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

    setSearchQuery,
    setStatusFilter,
    setViewMode,
    setTerminalPaused,
    openDrawer: setSelectedEvaluation,
    closeDrawer: () => setSelectedEvaluation(null),
    toggleCompare,
    openCompare: () => setIsCompareOpen(true),
    closeCompare: () => setIsCompareOpen(false),
    addExecutionRun,
  };
}

export default useEvaluations;
