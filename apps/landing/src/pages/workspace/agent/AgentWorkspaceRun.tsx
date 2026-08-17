import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useWorkspaceStore } from '@/store/workspaceStore';
import {
  sendAgentClarification,
  runAgentTaskAgain,
  approveAgentAction,
  fetchAgentTask,
  fetchAgentReport,
  downloadExecutionReport,
  buildExportFilename,
} from '@/features/agent/services/agentService';
import type { AgentReport, AgentTask } from '@/features/agent/types';
import { getExecutionStatus } from '@/features/evaluations/services/evaluationService';
import { getReportRunById } from '@/features/reporting/services/reportingService';
import { AgentStatusBadge } from '@/features/agent/status';
import { AgentTimeline } from './components/AgentTimeline';
import { AgentClarificationCard } from './components/AgentClarificationCard';
import { AgentApprovalCard } from './components/AgentApprovalCard';
import { GlassSurface } from '@/design/glass/GlassSurface';
import {
  AlertCircle,
  RotateCcw,
  CheckCircle,
  FileText,
  Download,
  ChevronDown,
  ChevronUp,
  Timer,
  Network,
  ArrowRight,
  Gauge,
  ListChecks,
  PackageCheck,
  Square,
} from 'lucide-react';

/**
 * Prefer the task snapshot that carries more telemetry (plan/tool_calls) and later progress,
 * so polling/full-fetch results are never regressed by reduced list shapes.
 */
function preferRicher(a: AgentTask | null | undefined, b: AgentTask | null | undefined): AgentTask | null {
  if (!a) return b ?? null;
  if (!b) return a;
  const score = (t: AgentTask) =>
    (t.plan?.length ?? 0) + (t.tool_calls?.length ?? 0) + (t.observations?.length ?? 0) + (t.step_count ?? 0);
  return score(b) > score(a) ? b : a;
}

function getFinalSummary(finalResult: AgentTask['final_result']): string {
  if (!finalResult) return '';
  if (typeof finalResult === 'string') return finalResult;
  return typeof finalResult.summary === 'string' ? finalResult.summary : '';
}

function formatTimestamp(iso?: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

function formatDuration(started?: string | null, completed?: string | null): string {
  if (!started || !completed) return '';
  const a = new Date(started).getTime();
  const b = new Date(completed).getTime();
  if (Number.isNaN(a) || Number.isNaN(b) || b < a) return '';
  const totalSeconds = Math.round((b - a) / 1000);
  if (totalSeconds < 60) return `${totalSeconds}s`;
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}m ${seconds}s`;
}

/** Provider chain as actually recorded in the execution trace (plus the configured primary). */
function providerChain(task: AgentTask): string[] {
  const providers: string[] = [];
  if (task.primary_provider) providers.push(task.primary_provider);
  (task.execution_trace ?? []).forEach((ev) => {
    const d = ev.details ?? {};
    if (ev.event_type.startsWith('provider_decision_') && d.provider && !providers.includes(d.provider)) {
      providers.push(d.provider);
    }
    if (ev.event_type === 'provider_fallback' && d.next_provider && d.next_provider !== 'NONE' && !providers.includes(d.next_provider)) {
      providers.push(d.next_provider);
    }
  });
  return providers;
}

/** Concise, truthful one-liner for the failed-run normal view. */
function conciseFailure(task: AgentTask): string {
  const detail = task.error_detail;
  if (!detail) return 'An unexpected error occurred during execution.';
  const s = typeof detail === 'string' ? detail : JSON.stringify(detail);
  if (s.includes('All LLM providers in fallback chain failed')) {
    return 'All reasoning providers in the fallback chain failed. Open Inspect for the full routing trail.';
  }
  if (s.includes('RESOURCE_EXHAUSTED') || /429/.test(s)) {
    return 'The reasoning provider hit a rate limit. Retry execution to try again.';
  }
  return s.split('\n')[0].slice(0, 220);
}

export default function AgentWorkspaceRun() {
  const { taskId } = useParams();
  const navigate = useNavigate();
  const { agentTasks, setAgentTasks, addNotification } = useWorkspaceStore();
  const [task, setTask] = useState<AgentTask | null>(null);
  const [inspectMode, setInspectMode] = useState(false);
  const [report, setReport] = useState<AgentReport | null>(null);
  const [reportState, setReportState] = useState<'idle' | 'loading' | 'loaded' | 'missing'>('idle');
  const [downloading, setDownloading] = useState(false);
  const [executions, setExecutions] = useState<Array<{
    id: string;
    status: string;
    target_model: string;
    total_items: number;
    completed_items: number;
    benchmark_name: string | null;
    overall_score: number | null;
  }>>([]);

  // Represent ALL executions linked to this agent task, not just the most recent one.
  // Each execution gets its real persisted status/items plus, when a report run
  // summary exists, its real overall score.
  useEffect(() => {
    if (!taskId) return;
    let cancelled = false;
    const execIds = task?.execution_ids ?? [];
    setExecutions([]);
    if (execIds.length === 0) return;
    Promise.all(
      execIds.map((id) =>
        Promise.all([
          getExecutionStatus(id).then((res) => res.data ?? null),
          getReportRunById(id).then((res) => res.data ?? null),
        ]).then(([exec, report]) => ({ id, exec, report }))
      )
    ).then((results) => {
      if (cancelled) return;
      setExecutions(
        results
          .filter(({ exec }) => exec)
          .map(({ id, exec, report }) => ({
            id,
            status: exec?.status ?? 'QUEUED',
            target_model: exec?.target_model ?? '—',
            total_items: exec?.total_items ?? 0,
            completed_items: exec?.completed_items ?? 0,
            benchmark_name: report?.benchmark_name ?? null,
            overall_score: typeof report?.overall_score === 'number' ? report.overall_score : null,
          }))
      );
    });
    return () => { cancelled = true; };
  }, [taskId, task?.execution_ids]);

  // Sync task from store whenever agentTasks updates (live polling), preferring richer snapshots.
  useEffect(() => {
    if (!taskId) return;
    const found = agentTasks.find((t) => t.task_id === taskId);
    if (found) setTask((prev) => preferRicher(prev, found));
  }, [taskId, agentTasks]);

  // Always fetch the full task detail when the run changes. This guarantees the run page
  // has complete telemetry (plan, tool_calls, observations, execution_trace) even when the
  // store entry was hydrated from a reduced list shape.
  useEffect(() => {
    if (!taskId) return;
    let cancelled = false;
    fetchAgentTask(taskId).then(({ data }) => {
      if (cancelled || !data) return;
      setTask((prev) => preferRicher(prev, data));
      setAgentTasks((prev) => {
        const others = prev.filter((t) => t.task_id !== data.task_id);
        return [preferRicher(prev.find((t) => t.task_id === data.task_id) ?? null, data), ...others]
          .filter((t): t is AgentTask => t !== null);
      });
    });
    return () => { cancelled = true; };
  }, [taskId, setAgentTasks]);

  // Fetch the real report artifact once a completed task has one.
  const taskStatus = task?.status ?? null;
  const taskReportId = task?.report_id ?? null;
  useEffect(() => {
    if (!taskStatus || taskStatus !== 'COMPLETED' || !taskReportId) {
      setReport(null);
      setReportState('idle');
      return;
    }
    let cancelled = false;
    setReportState('loading');
    fetchAgentReport(taskReportId).then(({ data }) => {
      if (cancelled) return;
      if (data) {
        setReport(data);
        setReportState('loaded');
      } else {
        setReport(null);
        setReportState('missing');
      }
    });
    return () => { cancelled = true; };
  }, [taskStatus, taskReportId]);

  // Reset inspect mode whenever the active run changes.
  useEffect(() => {
    setInspectMode(false);
  }, [taskId]);

  const handleClarifySubmit = async (response: string) => {
    if (!taskId || !task) return;
    await sendAgentClarification(taskId, response, task.clarification_id ?? undefined);
    const { data } = await fetchAgentTask(taskId);
    if (data) {
      setTask((prev) => preferRicher(prev, data));
      setAgentTasks((prev) => prev.map((t) => (t.task_id === taskId ? data : t)));
    }
  };

  const handleApprove = async (approve: boolean) => {
    if (!taskId || !task) return;
    if (approve && task.approval_token) {
      await approveAgentAction(taskId, task.approval_token);
    }
    const { data } = await fetchAgentTask(taskId);
    if (data) {
      setTask((prev) => preferRicher(prev, data));
      setAgentTasks((prev) => prev.map((t) => (t.task_id === taskId ? data : t)));
    }
  };

  const handleRunAgain = async () => {
    if (!taskId) return;
    const { data } = await runAgentTaskAgain(taskId);
    if (data?.task_id) {
      const { data: newTask } = await fetchAgentTask(data.task_id);
      if (newTask) {
        setAgentTasks((prev) => [newTask, ...prev.filter((t) => t.task_id !== newTask.task_id)]);
      }
      navigate(`/dashboard/agent/run/${data.task_id}`);
    }
  };

  const handleDownloadReport = async () => {
    const execId = task?.execution_ids?.slice(-1)[0] || report?.execution_id || '';
    if (!execId) {
      addNotification('Download unavailable', 'No execution run is linked to this report yet.', 'warning');
      return;
    }
    setDownloading(true);
    try {
      const { data, error } = await downloadExecutionReport(execId, 'json');
      if (!data || error) {
        addNotification('Download failed', error?.message || 'Report export failed. Please try again.', 'error');
        return;
      }
      const filename = buildExportFilename('json', report?.title, report?.version_string);
      const url = URL.createObjectURL(data);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      addNotification('Report Downloaded', `${filename} saved.`, 'success');
    } finally {
      setDownloading(false);
    }
  };

  const handleDownloadExecution = async (execId: string) => {
    setDownloading(true);
    try {
      const { data, error } = await downloadExecutionReport(execId, 'json');
      if (!data || error) {
        addNotification('Download failed', error?.message || 'Report export failed. Please try again.', 'error');
        return;
      }
      const filename = buildExportFilename('json', report?.title, report?.version_string);
      const url = URL.createObjectURL(data);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      addNotification('Report Downloaded', `${filename} saved.`, 'success');
    } finally {
      setDownloading(false);
    }
  };

  if (!task) {
    return (
      <div className="flex h-full w-full items-center justify-center text-white/50">
        <div className="flex flex-col items-center gap-4">
          <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
          <div className="text-sm">Loading task state...</div>
        </div>
      </div>
    );
  }

  const isCompleted = task.status === 'COMPLETED';
  const isFailed = task.status === 'FAILED';
  const isStopped = task.status === 'CANCELLED';
  const isClarifying = task.status === 'WAITING_FOR_CLARIFICATION';
  const isPendingApproval = task.status === 'WAITING_FOR_APPROVAL';
  const isActive = !isCompleted && !isFailed && !isStopped && !isClarifying && !isPendingApproval;

  // "Failed at" — only real telemetry: a FAILED plan step, or the provider the run was on.
  const failedStep = task.plan?.find((s) => s.status === 'FAILED');
  const failedAt = isFailed
    ? failedStep
      ? `step ${failedStep.step_number} — ${failedStep.description}`
      : task.current_provider
        ? `provider ${task.current_provider}`
        : null
    : null;

  const clarificationQuestion = task.clarification_request || task.clarification_prompt || '';
  const finalSummary = getFinalSummary(task.final_result);
  const duration = formatDuration(task.started_at ?? task.created_at, task.completed_at);
  const providers = providerChain(task);
  const benchmarkId = task.benchmark_id ?? report?.benchmark_id ?? null;

  const metric = (name: string) => (report?.metrics ?? []).find((m) => m.metric_name === name)?.metric_value;
  const reportMetric = (rep: AgentReport | null, name: string) =>
    (rep?.metrics ?? []).find((m) => m.metric_name === name)?.metric_value;
  const accuracy = metric('accuracy');
  const evaluated = metric('total_evaluated');
  const passed = metric('total_passed');
  const failed = metric('total_failed');
  const hasEvaluation = (report?.metrics.length ?? 0) > 0;
  const reportTitle = report?.title || 'Benchmark Report';

  return (
    <div className="flex h-full w-full relative">
      {/* Center stage */}
      <div className="flex-1 min-w-0 h-full p-8 flex flex-col relative overflow-y-auto">
        {/* Goal header */}
        <div className="mb-8">
          <div className="flex items-start gap-4">
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">{task.goal}</h1>
              <div className="flex items-center gap-3 mt-2 text-sm text-white/50 flex-wrap">
                <span className="font-mono text-xs">ID: {task.task_id}</span>
                <AgentStatusBadge status={task.status} />
                {task.primary_provider && (
                  <span className="flex items-center gap-1.5 text-xs">
                    <Network className="w-3.5 h-3.5" /> {task.primary_provider}
                  </span>
                )}
                {duration && (
                  <span className="flex items-center gap-1.5 text-xs">
                    <Timer className="w-3.5 h-3.5" /> {duration}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-3 mt-1 text-xs text-white/30 flex-wrap">
                <span>Started: {formatTimestamp(task.started_at ?? task.created_at)}</span>
                {task.completed_at && <span>· Completed: {formatTimestamp(task.completed_at)}</span>}
                {task.run_mode === 'RERUN' && task.source_task_id && (
                  <span className="text-accent/80 flex items-center gap-1">
                    Rerun of <span className="font-mono">#{task.source_task_id.slice(0, 8)}</span>
                    <ArrowRight className="w-3 h-3" />
                    <span className="font-mono">#{task.task_id.slice(0, 8)}</span>
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="flex-1 flex flex-col items-center justify-center relative">
          {isClarifying && clarificationQuestion && (
            <AgentClarificationCard
              question={clarificationQuestion}
              options={undefined}
              onSubmit={handleClarifySubmit}
            />
          )}

          {isPendingApproval && task.pending_tool_call && (
            <AgentApprovalCard
              message={`Atlas Agent is requesting permission to execute: ${task.pending_tool_call?.tool_name ?? 'an action'}`}
              onApprove={() => handleApprove(true)}
              onReject={() => handleApprove(false)}
            />
          )}

          {isFailed && !inspectMode && (
            <GlassSurface variant="default" className="w-full max-w-2xl p-8 text-center">
              <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-4 text-red-400 border border-red-500/40">
                <AlertCircle className="w-8 h-8" />
              </div>
              <h3 className="text-xl font-bold text-white mb-2">✕ Execution Failed</h3>
              <p className="text-sm text-white/60 mb-2">{conciseFailure(task)}</p>
              {failedAt && (
                <p className="text-xs text-red-300/80 font-mono mb-6">
                  Failed at: {failedAt}
                </p>
              )}
              <div className="flex items-center justify-center gap-3">
                <button
                  onClick={() => setInspectMode((prev) => !prev)}
                  className="flex items-center gap-2 px-6 py-2.5 rounded-lg font-medium transition-colors border bg-white/5 text-white/80 border-white/10 hover:bg-white/10"
                >
                  <ChevronDown className="w-4 h-4" />
                  Inspect
                </button>
                <button
                  onClick={handleRunAgain}
                  className="flex items-center gap-2 px-6 py-2.5 rounded-lg bg-red-500/20 hover:bg-red-500/30 text-red-300 font-medium transition-colors border border-red-500/40"
                >
                  <RotateCcw className="w-4 h-4" />
                  Retry Execution
                </button>
              </div>
            </GlassSurface>
          )}

          {isStopped && !inspectMode && (
            <GlassSurface variant="default" className="w-full max-w-2xl p-8 text-center">
              <div className="w-16 h-16 bg-white/[0.06] rounded-full flex items-center justify-center mx-auto mb-4 text-white/60 border border-white/15">
                <Square className="w-7 h-7" />
              </div>
              <h3 className="text-xl font-bold text-white mb-2">■ Execution Stopped</h3>
              <p className="text-sm text-white/60 mb-6">
                {task.error_detail
                  ? typeof task.error_detail === 'string'
                    ? task.error_detail
                    : 'This run was stopped.'
                  : 'This run was stopped before completion.'}
              </p>
              <div className="flex items-center justify-center gap-3">
                <button
                  onClick={() => setInspectMode((prev) => !prev)}
                  className="flex items-center gap-2 px-6 py-2.5 rounded-lg font-medium transition-colors border bg-white/5 text-white/80 border-white/10 hover:bg-white/10"
                >
                  <ChevronDown className="w-4 h-4" />
                  Inspect
                </button>
                <button
                  onClick={handleRunAgain}
                  className="flex items-center gap-2 px-6 py-2.5 rounded-lg bg-white/10 hover:bg-white/15 text-white font-medium transition-colors border border-white/15"
                >
                  <RotateCcw className="w-4 h-4" />
                  Run Again
                </button>
              </div>
            </GlassSurface>
          )}

          {isFailed && inspectMode && (
            <div className="w-full max-w-2xl text-center pb-4">
              <p className="text-sm text-white/50">
                Execution failed. Full error details are available in the Inspect panel on the right.
              </p>
            </div>
          )}

          {isCompleted && (
            <GlassSurface variant="default" className="w-full max-w-4xl p-8">
              {/* ✓ Benchmark Complete header */}
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 bg-emerald-500/20 text-emerald-400 rounded-full flex items-center justify-center border border-emerald-500/40 shrink-0">
                  <CheckCircle className="w-6 h-6" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-3 flex-wrap">
                    <h2 className="text-2xl font-bold text-white">Benchmark Complete</h2>
                    <AgentStatusBadge status={task.status} />
                  </div>
                  <div className="flex items-center gap-2 mt-1 text-xs text-white/40 flex-wrap">
                    <span>{reportTitle}</span>
                    {reportState === 'loaded' && report?.version_string && (
                      <>
                        <span>·</span>
                        <span className="font-mono">v{report.version_string}</span>
                      </>
                    )}
                    {benchmarkId && (
                      <>
                        <span>·</span>
                        <span className="font-mono">Benchmark {benchmarkId.slice(0, 8)}</span>
                      </>
                    )}
                  </div>
                  {reportState === 'loaded' && report?.published !== false && (
                    <p className="text-[11px] text-emerald-400/80 flex items-center gap-1.5 mt-1.5">
                      <PackageCheck className="w-3.5 h-3.5" />
                      Published {formatTimestamp(report?.created_at)}
                    </p>
                  )}
                </div>
              </div>

              {/* Human-readable summary */}
              {(finalSummary || (report?.summary ?? '')) && (
                <div className="bg-black/30 rounded-xl border border-white/5 p-5 mt-6">
                  <p className="text-xs text-white/40 uppercase tracking-wider mb-2 font-semibold">Summary</p>
                  <p className="text-sm text-emerald-300/80 leading-relaxed whitespace-pre-wrap">
                    {finalSummary || report?.summary}
                  </p>
                </div>
              )}

              {reportState === 'loading' && (
                <div className="mt-5 p-4 bg-black/30 rounded-xl border border-white/5 text-sm text-white/40 animate-pulse">
                  Loading report data...
                </div>
              )}

              {/* RESULT — only real metric rows */}
              {reportState === 'loaded' && report && (
                <div className="mt-5 bg-black/30 rounded-xl border border-white/5 p-5">
                  <p className="text-xs text-white/40 uppercase tracking-wider mb-3 font-semibold flex items-center gap-2">
                    <Gauge className="w-3.5 h-3.5" /> Result
                  </p>
                  {hasEvaluation ? (
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      {accuracy !== undefined && (
                        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
                          <p className="text-[10px] text-white/40 uppercase tracking-wider mb-1">Accuracy</p>
                          <p className="text-2xl font-bold text-emerald-300">{accuracy}%</p>
                        </div>
                      )}
                      {evaluated !== undefined && (
                        <div className="p-4 rounded-xl bg-white/[0.03] border border-white/5">
                          <p className="text-[10px] text-white/40 uppercase tracking-wider mb-1">Evaluated</p>
                          <p className="text-2xl font-bold text-white">{evaluated}</p>
                        </div>
                      )}
                      {passed !== undefined && (
                        <div className="p-4 rounded-xl bg-sky-500/10 border border-sky-500/20">
                          <p className="text-[10px] text-white/40 uppercase tracking-wider mb-1">Passed</p>
                          <p className="text-2xl font-bold text-sky-300">{passed}</p>
                        </div>
                      )}
                      {failed !== undefined && (
                        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20">
                          <p className="text-[10px] text-white/40 uppercase tracking-wider mb-1">Failed</p>
                          <p className="text-2xl font-bold text-red-300">{failed}</p>
                        </div>
                      )}
                    </div>
                  ) : (
                    <p className="text-sm text-white/40">No numeric metrics recorded for this report.</p>
                  )}
                </div>
              )}

              {/* EXECUTION — only real counters */}
              <div className="mt-5 bg-black/30 rounded-xl border border-white/5 p-5">
                <p className="text-xs text-white/40 uppercase tracking-wider mb-3 font-semibold flex items-center gap-2">
                  <ListChecks className="w-3.5 h-3.5" /> Execution
                </p>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <div className="p-3 rounded-xl bg-white/[0.02] border border-white/5">
                    <p className="text-[10px] text-white/40 uppercase tracking-wider mb-0.5">Steps</p>
                    <p className="text-xl font-bold text-white">{task.step_count}</p>
                  </div>
                  <div className="p-3 rounded-xl bg-white/[0.02] border border-white/5">
                    <p className="text-[10px] text-white/40 uppercase tracking-wider mb-0.5">Tool Calls</p>
                    <p className="text-xl font-bold text-white">{task.total_tool_calls}</p>
                  </div>
                  <div className="p-3 rounded-xl bg-white/[0.02] border border-white/5">
                    <p className="text-[10px] text-white/40 uppercase tracking-wider mb-0.5">Duration</p>
                    <p className="text-xl font-bold text-white">{duration || '—'}</p>
                  </div>
                  <div className="p-3 rounded-xl bg-white/[0.02] border border-white/5">
                    <p className="text-[10px] text-white/40 uppercase tracking-wider mb-0.5">Providers</p>
                    <p className="text-sm font-semibold text-white/80 break-words leading-tight">
                      {providers.length > 0 ? providers.join(' → ') : task.primary_provider || '—'}
                    </p>
                  </div>
                </div>
              </div>

              {/* EXECUTIONS — every run linked to this task, each with its own result set */}
              {(task.execution_ids?.length ?? 0) > 0 && (
                <div className="mt-5 bg-black/30 rounded-xl border border-white/5 p-5 space-y-3">
                  <p className="text-xs text-white/40 uppercase tracking-wider mb-1 font-semibold flex items-center gap-2">
                    <ListChecks className="w-3.5 h-3.5" /> Executions ({executions.length || (task.execution_ids?.length ?? 0)})
                  </p>
                  <div className="space-y-3">
                    {(executions.length > 0
                      ? executions
                      : (task.execution_ids ?? []).map((id) => ({
                          id, status: 'QUEUED', target_model: '—', total_items: 0, completed_items: 0,
                          benchmark_name: null, overall_score: null,
                        }))
                    ).map((ex) => {
                      const exHasReport = report !== null && report.execution_id === ex.id && (report.metrics.length ?? 0) > 0;
                      const exAccuracy = exHasReport ? reportMetric(report, 'accuracy') : undefined;
                      const exEvaluated = exHasReport ? reportMetric(report, 'total_evaluated') : undefined;
                      const exPassed = exHasReport ? reportMetric(report, 'total_passed') : undefined;
                      const exFailed = exHasReport ? reportMetric(report, 'total_failed') : undefined;

                      return (
                        <div key={ex.id} className="p-4 rounded-xl border border-white/5 bg-white/[0.02] space-y-3">
                          <div className="flex items-center justify-between gap-3 flex-wrap">
                            <div className="min-w-0">
                              <div className="text-xs font-mono text-white/70 break-all truncate">{ex.id}</div>
                              <div className="text-[11px] text-white/40 mt-0.5 flex items-center gap-2 flex-wrap">
                                <span>{ex.target_model}</span>
                                <span>·</span>
                                <span>{ex.status.replace(/_/g, ' ')}</span>
                                {ex.benchmark_name && (
                                  <>
                                    <span>·</span>
                                    <span>{ex.benchmark_name}</span>
                                  </>
                                )}
                                {ex.total_items > 0 && (
                                  <>
                                    <span>·</span>
                                    <span>{ex.completed_items}/{ex.total_items} items</span>
                                  </>
                                )}
                              </div>
                            </div>
                            <button
                              onClick={() => handleDownloadExecution(ex.id)}
                              disabled={downloading}
                              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono text-white/60 hover:text-white bg-white/5 hover:bg-white/10 border border-white/10 transition-colors shrink-0 disabled:opacity-50"
                            >
                              <Download className="w-3.5 h-3.5" />
                              Export
                            </button>
                          </div>

                          {/* Per-execution result set — only real persisted values */}
                          {exHasReport ? (
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                              {exAccuracy !== undefined && (
                                <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
                                  <p className="text-[10px] text-white/40 uppercase tracking-wider mb-1">Accuracy</p>
                                  <p className="text-xl font-bold text-emerald-300">{exAccuracy}%</p>
                                </div>
                              )}
                              {exEvaluated !== undefined && (
                                <div className="p-3 rounded-xl bg-white/[0.03] border border-white/5">
                                  <p className="text-[10px] text-white/40 uppercase tracking-wider mb-1">Evaluated</p>
                                  <p className="text-xl font-bold text-white">{exEvaluated}</p>
                                </div>
                              )}
                              {exPassed !== undefined && (
                                <div className="p-3 rounded-xl bg-sky-500/10 border border-sky-500/20">
                                  <p className="text-[10px] text-white/40 uppercase tracking-wider mb-1">Passed</p>
                                  <p className="text-xl font-bold text-sky-300">{exPassed}</p>
                                </div>
                              )}
                              {exFailed !== undefined && (
                                <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20">
                                  <p className="text-[10px] text-white/40 uppercase tracking-wider mb-1">Failed</p>
                                  <p className="text-xl font-bold text-red-300">{exFailed}</p>
                                </div>
                              )}
                            </div>
                          ) : ex.overall_score != null ? (
                            <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                              <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
                                <p className="text-[10px] text-white/40 uppercase tracking-wider mb-1">Overall Score</p>
                                <p className="text-xl font-bold text-emerald-300">{Math.round(ex.overall_score)}%</p>
                              </div>
                            </div>
                          ) : (
                            <p className="text-xs font-mono text-white/30">
                              No evaluation results persisted for this execution.
                            </p>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* ARTIFACT — the report destination */}
              {reportState === 'loaded' && report && (
                <div className="mt-5 bg-black/30 rounded-xl border border-white/5 p-5">
                  <div className="flex items-center justify-between mb-3">
                    <p className="text-xs text-white/40 uppercase tracking-wider font-semibold flex items-center gap-2">
                      <FileText className="w-3.5 h-3.5" /> Artifact
                    </p>
                    <span className="text-[10px] text-white/30 font-mono">{formatTimestamp(report.created_at)}</span>
                  </div>
                  <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm text-white/70">
                    <span>
                      Report: <span className="font-semibold text-white/90">{reportTitle}</span>
                    </span>
                    {report.version_string && (
                      <span>
                        Version: <span className="font-mono">{report.version_string}</span>
                      </span>
                    )}
                    <span>
                      Status: <span className="text-emerald-400">Published</span>
                    </span>
                  </div>
                  <button
                    onClick={() => navigate(`/dashboard/agent/report/${report.report_id}`)}
                    className="mt-4 flex items-center gap-2 px-4 py-2 rounded-lg bg-accent/10 hover:bg-accent/20 border border-accent/30 text-accent text-sm font-medium transition-colors"
                  >
                    <FileText className="w-4 h-4" />
                    View Report
                  </button>
                </div>
              )}

              {reportState === 'missing' && (
                <div className="mt-5 p-4 bg-black/30 rounded-xl border border-white/5 text-sm text-white/40">
                  Report <span className="font-mono">{task.report_id}</span> was not found in the backend. No report data is available.
                </div>
              )}

              {/* Actions */}
              <div className="mt-7 flex justify-end gap-3 flex-wrap">
                {task.report_id && reportState !== 'loading' && (
                  <button
                    onClick={handleDownloadReport}
                    disabled={downloading}
                    className="flex items-center gap-2 px-6 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-white/80 font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {downloading ? (
                      <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                    ) : (
                      <Download className="w-4 h-4" />
                    )}
                    {downloading ? 'Preparing download…' : 'Download Report'}
                  </button>
                )}
                <button
                  onClick={() => setInspectMode((prev) => !prev)}
                  className={`flex items-center gap-2 px-6 py-2 rounded-lg font-medium transition-colors border ${
                    inspectMode
                      ? 'bg-accent/20 text-accent border-accent/40'
                      : 'bg-white/5 text-white/80 border-white/10 hover:bg-white/10'
                  }`}
                >
                  {inspectMode ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  {inspectMode ? 'Exit Inspect' : 'Inspect'}
                </button>
                <button
                  onClick={handleRunAgain}
                  className="px-6 py-2 rounded-lg bg-accent/10 hover:bg-accent/20 border border-accent/30 text-accent font-medium transition-colors"
                >
                  Run Again
                </button>
              </div>
            </GlassSurface>
          )}

          {/* Running/pending ambient animation */}
          {isActive && (
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none opacity-40">
              <div className="w-32 h-32 rounded-full border-t-2 border-accent/50 animate-spin" style={{ animationDuration: '3s' }} />
              <div className="w-24 h-24 rounded-full border-r-2 border-indigo-400/30 animate-spin absolute" style={{ animationDuration: '2s', animationDirection: 'reverse' }} />
            </div>
          )}
        </div>
      </div>

      {/* Right panel: execution checklist (normal) / inspect hierarchy (inspect) */}
      <div className="w-80 shrink-0 h-full border-l border-white/10 bg-black/20 backdrop-blur-sm">
        <AgentTimeline
          key={task.task_id}
          task={task}
          inspectMode={inspectMode}
          onToggleInspect={() => setInspectMode((prev) => !prev)}
        />
      </div>
    </div>
  );
}
