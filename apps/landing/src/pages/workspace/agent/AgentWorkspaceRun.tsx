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
  Timer,
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
  return score(b) >= score(a) ? b : a;
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
    <div className="flex h-full w-full relative overflow-hidden">
      {/* Middle column: Chat/Timeline (mimicking the middle panel of Antigravity) */}
      <div className="flex-1 min-w-0 h-full flex flex-col relative bg-ink-1">
        {/* Header mimicking the top of the chat area */}
        <div className="flex-none px-6 py-3 border-b border-white/5 flex items-center justify-between bg-ink-2/80 backdrop-blur-md z-10">
          <div className="min-w-0 flex-1 pr-4">
            <h1 className="text-sm font-semibold text-white/90 truncate">{task.goal}</h1>
            <div className="flex items-center gap-2 mt-0.5 text-[10px] text-white/40 font-mono">
              <span>{task.task_id.slice(0, 8)}</span>
              <span>·</span>
              <AgentStatusBadge status={task.status} />
              {duration && (
                <>
                  <span>·</span>
                  <span className="flex items-center gap-1"><Timer className="w-3 h-3" /> {duration}</span>
                </>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
             <button onClick={handleRunAgain} className="px-4 py-1.5 rounded-full bg-accent text-white text-xs font-medium hover:bg-accent-hover transition-colors shadow-sm shadow-accent/20">
               Restart to Update
             </button>
             {task.report_id && reportState !== 'loading' && (
                <button onClick={handleDownloadReport} disabled={downloading} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 text-white/80 text-xs font-medium hover:bg-white/10 transition-colors border border-white/10 disabled:opacity-50">
                  <Download className="w-3.5 h-3.5" />
                  {downloading ? 'Exporting...' : 'Export'}
                </button>
             )}
          </div>
        </div>

        {/* Chat/Timeline area */}
        <div className="flex-1 overflow-y-auto px-4 py-6">
          <div className="max-w-4xl mx-auto w-full flex flex-col gap-6">
            <AgentTimeline
              key={task.task_id}
              task={task}
              inspectMode={inspectMode}
              onToggleInspect={() => setInspectMode((prev) => !prev)}
            />
            
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
              <GlassSurface variant="default" className="w-full p-6 text-center border-red-500/20 bg-red-500/5">
                <div className="w-12 h-12 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-3 text-red-400 border border-red-500/40">
                  <AlertCircle className="w-6 h-6" />
                </div>
                <h3 className="text-lg font-bold text-white mb-2">Execution Failed</h3>
                <p className="text-sm text-white/60 mb-2">{conciseFailure(task)}</p>
                {failedAt && (
                  <p className="text-xs text-red-300/80 font-mono mb-4">Failed at: {failedAt}</p>
                )}
                <div className="flex items-center justify-center gap-3">
                  <button onClick={() => setInspectMode((prev) => !prev)} className="flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors border bg-white/5 text-white/80 border-white/10 hover:bg-white/10 text-sm">
                    <ChevronDown className="w-4 h-4" /> Inspect
                  </button>
                  <button onClick={handleRunAgain} className="flex items-center gap-2 px-4 py-2 rounded-lg bg-red-500/20 hover:bg-red-500/30 text-red-300 font-medium transition-colors border border-red-500/40 text-sm">
                    <RotateCcw className="w-4 h-4" /> Retry
                  </button>
                </div>
              </GlassSurface>
            )}

            {isStopped && !inspectMode && (
              <GlassSurface variant="default" className="w-full p-6 text-center">
                <div className="w-12 h-12 bg-white/[0.06] rounded-full flex items-center justify-center mx-auto mb-3 text-white/60 border border-white/15">
                  <Square className="w-6 h-6" />
                </div>
                <h3 className="text-lg font-bold text-white mb-2">Execution Stopped</h3>
                <p className="text-sm text-white/60 mb-4">
                  {task.error_detail ? (typeof task.error_detail === 'string' ? task.error_detail : 'This run was stopped.') : 'This run was stopped before completion.'}
                </p>
                <button onClick={handleRunAgain} className="flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-white/10 hover:bg-white/15 text-white font-medium transition-colors border border-white/15 mx-auto text-sm">
                  <RotateCcw className="w-4 h-4" /> Run Again
                </button>
              </GlassSurface>
            )}

            {isCompleted && !inspectMode && (
              <div className="w-full p-4 rounded-xl border border-emerald-500/20 bg-emerald-500/5 flex items-center gap-3">
                 <CheckCircle className="w-5 h-5 text-emerald-400 shrink-0" />
                 <div>
                   <p className="text-sm font-medium text-emerald-300">Task Completed Successfully</p>
                   <p className="text-xs text-emerald-400/60 mt-0.5">See results in the right panel.</p>
                 </div>
              </div>
            )}
            
            {isActive && (
              <div className="flex justify-center py-4">
                <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-white/[0.02] border border-white/5 text-white/40 text-xs">
                  <div className="w-3 h-3 rounded-full border-t-2 border-accent/50 animate-spin" />
                  Agent is reasoning...
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Right panel: Artifacts / Results (mimicking Antigravity right panel) */}
      <div className="w-[450px] shrink-0 h-full border-l border-white/10 bg-ink-2/30 backdrop-blur-sm flex flex-col">
        {/* Right Header (Tabs) */}
        <div className="flex-none px-4 py-3 border-b border-white/5 flex items-center gap-4 text-xs font-medium bg-ink-2/50 backdrop-blur">
          <div className="text-white pb-3 -mb-3 border-b-2 border-accent">Run Report</div>
          {hasEvaluation && <div className="text-white/40 hover:text-white/60 cursor-pointer">Metrics</div>}
          {(task.execution_ids?.length ?? 0) > 0 && <div className="text-white/40 hover:text-white/60 cursor-pointer">Executions</div>}
        </div>

        {/* Right Body */}
        <div className="flex-1 overflow-y-auto p-5 space-y-6">
          {/* Summary */}
          {(finalSummary || (report?.summary ?? '')) && (
            <div className="space-y-2">
              <p className="text-[10px] text-white/40 uppercase tracking-wider font-semibold">Summary</p>
              <div className="text-sm text-emerald-300/90 leading-relaxed whitespace-pre-wrap bg-emerald-500/10 p-4 rounded-xl border border-emerald-500/20">
                {finalSummary || report?.summary}
              </div>
            </div>
          )}

          {/* Execution Counters */}
          <div className="space-y-2">
            <p className="text-[10px] text-white/40 uppercase tracking-wider font-semibold">Execution Stats</p>
            <div className="grid grid-cols-2 gap-2">
              <div className="p-3 rounded-xl bg-white/[0.03] border border-white/5">
                <p className="text-[10px] text-white/40 uppercase tracking-wider mb-0.5">Steps</p>
                <p className="text-lg font-bold text-white">{task.step_count}</p>
              </div>
              <div className="p-3 rounded-xl bg-white/[0.03] border border-white/5">
                <p className="text-[10px] text-white/40 uppercase tracking-wider mb-0.5">Tool Calls</p>
                <p className="text-lg font-bold text-white">{task.total_tool_calls}</p>
              </div>
              <div className="p-3 rounded-xl bg-white/[0.03] border border-white/5">
                <p className="text-[10px] text-white/40 uppercase tracking-wider mb-0.5">Duration</p>
                <p className="text-lg font-bold text-white">{duration || '—'}</p>
              </div>
              <div className="p-3 rounded-xl bg-white/[0.03] border border-white/5">
                <p className="text-[10px] text-white/40 uppercase tracking-wider mb-0.5">Providers</p>
                <p className="text-xs font-semibold text-white/80 leading-tight line-clamp-2">
                  {providers.length > 0 ? providers.join(' → ') : task.primary_provider || '—'}
                </p>
              </div>
            </div>
          </div>

          {/* Result Metrics */}
          {reportState === 'loaded' && report && hasEvaluation && (
            <div className="space-y-2">
              <p className="text-[10px] text-white/40 uppercase tracking-wider font-semibold">Evaluation Results</p>
              <div className="grid grid-cols-2 gap-2">
                {accuracy !== undefined && (
                  <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
                    <p className="text-[10px] text-white/40 uppercase tracking-wider mb-1">Accuracy</p>
                    <p className="text-xl font-bold text-emerald-300">{accuracy}%</p>
                  </div>
                )}
                {evaluated !== undefined && (
                  <div className="p-3 rounded-xl bg-white/[0.03] border border-white/5">
                    <p className="text-[10px] text-white/40 uppercase tracking-wider mb-1">Evaluated</p>
                    <p className="text-xl font-bold text-white">{evaluated}</p>
                  </div>
                )}
                {passed !== undefined && (
                  <div className="p-3 rounded-xl bg-sky-500/10 border border-sky-500/20">
                    <p className="text-[10px] text-white/40 uppercase tracking-wider mb-1">Passed</p>
                    <p className="text-xl font-bold text-sky-300">{passed}</p>
                  </div>
                )}
                {failed !== undefined && (
                  <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20">
                    <p className="text-[10px] text-white/40 uppercase tracking-wider mb-1">Failed</p>
                    <p className="text-xl font-bold text-red-300">{failed}</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Artifact Report Info */}
          {reportState === 'loaded' && report && (
            <div className="space-y-2">
               <p className="text-[10px] text-white/40 uppercase tracking-wider font-semibold">Artifact</p>
               <div className="bg-white/[0.03] rounded-xl border border-white/5 p-4">
                  <div className="flex items-center gap-2 mb-2 text-white/90 font-medium text-sm">
                    <FileText className="w-4 h-4 text-accent" />
                    {reportTitle}
                  </div>
                  <div className="text-xs text-white/50 mb-4 space-y-1">
                    {report.version_string && <div>Version: <span className="font-mono text-white/70">{report.version_string}</span></div>}
                    <div>Published: {formatTimestamp(report.created_at)}</div>
                  </div>
                  <button onClick={() => navigate(`/dashboard/agent/report/${report.report_id}`)} className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-accent/10 hover:bg-accent/20 border border-accent/30 text-accent text-xs font-medium transition-colors">
                    <FileText className="w-3.5 h-3.5" /> Open Full Report
                  </button>
               </div>
            </div>
          )}

          {/* Execution List */}
          {(task.execution_ids?.length ?? 0) > 0 && (
            <div className="space-y-2">
              <p className="text-[10px] text-white/40 uppercase tracking-wider font-semibold">Executions ({executions.length || (task.execution_ids?.length ?? 0)})</p>
              <div className="space-y-2">
                {(executions.length > 0 ? executions : (task.execution_ids ?? []).map(id => ({ id, status: 'QUEUED', target_model: '—', total_items: 0, completed_items: 0, benchmark_name: null, overall_score: null }))).map(ex => {
                   const exHasReport = report !== null && report.execution_id === ex.id && (report.metrics.length ?? 0) > 0;
                   const exAccuracy = exHasReport ? reportMetric(report, 'accuracy') : undefined;
                   const exPassed = exHasReport ? reportMetric(report, 'total_passed') : undefined;

                   return (
                   <div key={ex.id} className="p-3 rounded-xl border border-white/5 bg-white/[0.02]">
                      <div className="flex items-center justify-between gap-2 mb-2">
                         <span className="text-[10px] font-mono text-white/60 truncate">{ex.id.slice(0, 12)}...</span>
                         <span className="text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-white/10 text-white/70">{ex.status.replace(/_/g, ' ')}</span>
                      </div>
                      <div className="text-[11px] text-white/40 mb-3 flex items-center gap-2 flex-wrap">
                        <span>{ex.target_model}</span>
                        {ex.total_items > 0 && <span>· {ex.completed_items}/{ex.total_items} items</span>}
                      </div>

                      {exHasReport && (
                        <div className="grid grid-cols-2 gap-2 mb-3">
                          {exAccuracy !== undefined && (
                            <div className="p-2 rounded bg-emerald-500/10 border border-emerald-500/20">
                              <p className="text-[9px] text-white/40 uppercase tracking-wider mb-0.5">Accuracy</p>
                              <p className="text-sm font-bold text-emerald-300">{exAccuracy}%</p>
                            </div>
                          )}
                          {exPassed !== undefined && (
                            <div className="p-2 rounded bg-sky-500/10 border border-sky-500/20">
                              <p className="text-[9px] text-white/40 uppercase tracking-wider mb-0.5">Passed</p>
                              <p className="text-sm font-bold text-sky-300">{exPassed}</p>
                            </div>
                          )}
                        </div>
                      )}

                      <button onClick={() => handleDownloadExecution(ex.id)} disabled={downloading} className="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-white/70 hover:text-white bg-white/5 hover:bg-white/10 border border-white/10 transition-colors disabled:opacity-50">
                        <Download className="w-3 h-3" /> Export Results
                      </button>
                   </div>
                 )})}
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
