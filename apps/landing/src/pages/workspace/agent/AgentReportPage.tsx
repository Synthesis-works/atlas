import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useWorkspaceStore } from '@/store/workspaceStore';
import {
  fetchAgentReport,
  downloadExecutionReport,
  buildExportFilename,
} from '@/features/agent/services/agentService';
import type { AgentReport, AgentTask } from '@/features/agent/types';
import { GlassSurface } from '@/design/glass/GlassSurface';
import {
  FileText,
  Download,
  ArrowLeft,
  CheckCircle2,
  Link2,
  Timer,
  ListChecks,
  Wrench,
  Network,
  Gauge,
  ExternalLink,
  CalendarClock,
  BadgeCheck,
} from 'lucide-react';

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

export default function AgentReportPage() {
  const { reportId } = useParams();
  const navigate = useNavigate();
  const { agentTasks, addNotification } = useWorkspaceStore();
  const [report, setReport] = useState<AgentReport | null>(null);
  const [state, setState] = useState<'loading' | 'loaded' | 'missing'>('loading');
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    if (!reportId) return;
    let cancelled = false;
    setState('loading');
    fetchAgentReport(reportId).then(({ data }) => {
      if (cancelled) return;
      if (data) {
        setReport(data);
        setState('loaded');
      } else {
        setReport(null);
        setState('missing');
      }
    });
    return () => { cancelled = true; };
  }, [reportId]);

  // Link back to the originating run when the store knows it.
  const owningTask = reportId
    ? agentTasks.find((t) => t.report_id === reportId)
    : undefined;

  const handleDownload = async () => {
    const execId = report?.execution_id;
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

  if (state === 'loading') {
    return (
      <div className="flex h-full w-full items-center justify-center text-white/50">
        <div className="flex flex-col items-center gap-4">
          <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
          <div className="text-sm">Loading report...</div>
        </div>
      </div>
    );
  }

  if (state === 'missing' || !report) {
    return (
      <div className="flex h-full w-full items-center justify-center p-8">
        <GlassSurface variant="default" className="w-full max-w-xl p-8 text-center">
          <FileText className="w-10 h-10 text-white/30 mx-auto mb-4" />
          <h2 className="text-lg font-bold text-white mb-2">Report Not Found</h2>
          <p className="text-sm text-white/50 mb-6">
            Report <span className="font-mono">{reportId}</span> was not found in the backend.
          </p>
          <button
            onClick={() => navigate(-1)}
            className="flex items-center gap-2 px-6 py-2.5 rounded-lg bg-accent/10 hover:bg-accent/20 border border-accent/30 text-accent text-sm font-medium transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </button>
        </GlassSurface>
      </div>
    );
  }

  const hasMetrics = report.metrics.length > 0;
  const duration = owningTask
    ? formatDuration(owningTask.started_at ?? owningTask.created_at, owningTask.completed_at)
    : '';
  const providers = owningTask ? providerChain(owningTask) : [];
  const metric = (name: string) => report.metrics.find((m) => m.metric_name === name)?.metric_value;

  return (
    <div className="flex h-full w-full p-8 overflow-y-auto">
      <div className="w-full max-w-4xl mx-auto flex flex-col gap-6">
        {/* Header */}
        <div className="flex items-center justify-between gap-4">
          <button
            onClick={() => (owningTask ? navigate(`/dashboard/agent/run/${owningTask.task_id}`) : navigate(-1))}
            className="flex items-center gap-2 text-sm text-white/50 hover:text-white/80 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            {owningTask ? 'Back to run' : 'Back'}
          </button>
          <button
            onClick={handleDownload}
            disabled={downloading}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-white/80 text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {downloading ? (
              <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
            ) : (
              <Download className="w-4 h-4" />
            )}
            {downloading ? 'Preparing download…' : 'Download Report'}
          </button>
        </div>

        <GlassSurface variant="default" className="p-8">
          {/* Report header */}
          <div className="flex items-start gap-4 mb-6">
            <div className="w-12 h-12 bg-accent/20 text-accent rounded-full flex items-center justify-center border border-accent/30 shrink-0">
              <FileText className="w-6 h-6" />
            </div>
            <div className="min-w-0 flex-1">
              <h1 className="text-2xl font-bold text-white tracking-tight">{report.title}</h1>
              <div className="flex items-center gap-2 mt-1.5 text-xs text-white/40 flex-wrap">
                <span className="font-mono">v{report.version_string}</span>
                <span>·</span>
                <span className="flex items-center gap-1">
                  <CalendarClock className="w-3.5 h-3.5" /> {formatTimestamp(report.created_at)}
                </span>
                {report.published && (
                  <>
                    <span>·</span>
                    <span className="text-emerald-400 flex items-center gap-1">
                      <BadgeCheck className="w-3.5 h-3.5" /> Published
                    </span>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Summary */}
          {report.summary && (
            <div className="bg-black/30 rounded-xl border border-white/5 p-5">
              <p className="text-xs text-white/40 uppercase tracking-wider mb-2 font-semibold">Summary</p>
              <p className="text-sm text-white/80 leading-relaxed whitespace-pre-wrap">{report.summary}</p>
            </div>
          )}

          {/* Results */}
          <div className="mt-5 bg-black/30 rounded-xl border border-white/5 p-5">
            <p className="text-xs text-white/40 uppercase tracking-wider mb-3 font-semibold flex items-center gap-2">
              <Gauge className="w-3.5 h-3.5" /> Results
            </p>
            {hasMetrics ? (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
                  <p className="text-[10px] text-white/40 uppercase tracking-wider mb-1">Accuracy</p>
                  <p className="text-2xl font-bold text-emerald-300">{metric('accuracy')}%</p>
                </div>
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/5">
                  <p className="text-[10px] text-white/40 uppercase tracking-wider mb-1">Evaluated</p>
                  <p className="text-2xl font-bold text-white">{metric('total_evaluated')}</p>
                </div>
                <div className="p-4 rounded-xl bg-sky-500/10 border border-sky-500/20">
                  <p className="text-[10px] text-white/40 uppercase tracking-wider mb-1">Passed</p>
                  <p className="text-2xl font-bold text-sky-300">{metric('total_passed')}</p>
                </div>
                <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20">
                  <p className="text-[10px] text-white/40 uppercase tracking-wider mb-1">Failed</p>
                  <p className="text-2xl font-bold text-red-300">{metric('total_failed')}</p>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-start gap-1 py-2">
                <p className="text-sm text-white/40">No numeric metrics recorded for this report.</p>
                <p className="text-xs text-white/25">
                  This report was published without an evaluation pass, so there are no metric rows to display.
                </p>
              </div>
            )}
          </div>

          {/* Execution */}
          <div className="mt-5 bg-black/30 rounded-xl border border-white/5 p-5">
            <div className="flex items-center justify-between mb-3">
              <p className="text-xs text-white/40 uppercase tracking-wider font-semibold flex items-center gap-2">
                <Network className="w-3.5 h-3.5" /> Execution
              </p>
              {owningTask && (
                <button
                  onClick={() => navigate(`/dashboard/agent/run/${owningTask.task_id}`)}
                  className="flex items-center gap-1.5 text-xs text-accent hover:text-accent/80 transition-colors font-medium"
                >
                  <ExternalLink className="w-3.5 h-3.5" /> View Execution
                </button>
              )}
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="flex items-start gap-3 p-3 rounded-xl bg-white/[0.02] border border-white/5">
                <FileText className="w-4 h-4 text-white/40 shrink-0 mt-0.5" />
                <div className="min-w-0">
                  <p className="text-[10px] text-white/40 uppercase tracking-wider mb-0.5">Execution ID</p>
                  <p className="text-xs font-mono text-white/70 break-all">
                    {report.execution_id ?? 'Not linked to an execution'}
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-3 p-3 rounded-xl bg-white/[0.02] border border-white/5">
                <Timer className="w-4 h-4 text-white/40 shrink-0 mt-0.5" />
                <div className="min-w-0">
                  <p className="text-[10px] text-white/40 uppercase tracking-wider mb-0.5">Duration</p>
                  <p className="text-sm font-semibold text-white">{duration || '—'}</p>
                </div>
              </div>
              {owningTask && (
                <>
                  <div className="flex items-start gap-3 p-3 rounded-xl bg-white/[0.02] border border-white/5">
                    <ListChecks className="w-4 h-4 text-white/40 shrink-0 mt-0.5" />
                    <div className="min-w-0">
                      <p className="text-[10px] text-white/40 uppercase tracking-wider mb-0.5">Steps</p>
                      <p className="text-sm font-semibold text-white">{owningTask.step_count}</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3 p-3 rounded-xl bg-white/[0.02] border border-white/5">
                    <Wrench className="w-4 h-4 text-white/40 shrink-0 mt-0.5" />
                    <div className="min-w-0">
                      <p className="text-[10px] text-white/40 uppercase tracking-wider mb-0.5">Tool Calls</p>
                      <p className="text-sm font-semibold text-white">{owningTask.total_tool_calls}</p>
                    </div>
                  </div>
                </>
              )}
              {providers.length > 0 && (
                <div className="flex items-start gap-3 p-3 rounded-xl bg-white/[0.02] border border-white/5 md:col-span-2">
                  <Network className="w-4 h-4 text-white/40 shrink-0 mt-0.5" />
                  <div className="min-w-0">
                    <p className="text-[10px] text-white/40 uppercase tracking-wider mb-0.5">Provider Chain</p>
                    <p className="text-xs font-mono text-white/70 break-words">{providers.join(' → ')}</p>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Benchmark */}
          <div className="mt-5 bg-black/30 rounded-xl border border-white/5 p-5">
            <p className="text-xs text-white/40 uppercase tracking-wider mb-3 font-semibold flex items-center gap-2">
              <Link2 className="w-3.5 h-3.5" /> Benchmark
            </p>
            {report.benchmark_id ? (
              <div className="flex items-center gap-3">
                <span className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 flex items-center justify-center">
                  <CheckCircle2 className="w-4 h-4" />
                </span>
                <div>
                  <p className="text-sm font-mono text-white/80">{report.benchmark_id}</p>
                  <p className="text-[11px] text-emerald-400/70">Resolved to a persisted benchmark</p>
                </div>
              </div>
            ) : (
              <div className="flex items-start gap-3">
                <span className="w-8 h-8 rounded-lg bg-white/[0.06] border border-white/10 text-white/40 flex items-center justify-center shrink-0">
                  <Link2 className="w-4 h-4" />
                </span>
                <div>
                  <p className="text-sm text-white/60">No benchmark resolved</p>
                  <p className="text-[11px] text-white/35 leading-snug">
                    This report could not be linked to a benchmark. Benchmark resolution requires a persisted benchmark
                    version tied to the execution run.
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Report metadata */}
          <div className="mt-5 bg-black/30 rounded-xl border border-white/5 p-5">
            <p className="text-xs text-white/40 uppercase tracking-wider mb-3 font-semibold flex items-center gap-2">
              <FileText className="w-3.5 h-3.5" /> Report Metadata
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
              <div>
                <p className="text-[10px] text-white/40 uppercase tracking-wider mb-0.5">Version</p>
                <p className="font-mono text-white/80">v{report.version_string}</p>
              </div>
              <div>
                <p className="text-[10px] text-white/40 uppercase tracking-wider mb-0.5">Created</p>
                <p className="text-white/70">{formatTimestamp(report.created_at)}</p>
              </div>
              <div>
                <p className="text-[10px] text-white/40 uppercase tracking-wider mb-0.5">Status</p>
                <p className="text-emerald-400 flex items-center gap-1.5">
                  <BadgeCheck className="w-3.5 h-3.5" /> {report.published ? 'Published' : 'Unpublished'}
                </p>
              </div>
            </div>
          </div>
        </GlassSurface>
      </div>
    </div>
  );
}
