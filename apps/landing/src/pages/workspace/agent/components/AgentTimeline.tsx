import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  PlayCircle,
  CheckCircle,
  AlertCircle,
  Clock,
  Search,
  EyeOff,
  ChevronDown,
  ChevronRight,
  Wrench,
  Network,
  ListChecks,
  GitBranch,
  FileJson,
} from 'lucide-react';
import type { AgentTask, AgentPlanStep } from '@/features/agent/types';
import { STATUS_TONES } from '@/features/agent/status';

interface AgentTimelineProps {
  task: AgentTask;
  inspectMode?: boolean;
  onToggleInspect?: () => void;
}

interface RoutingEvent {
  kind: 'attempted' | 'fallback';
  provider?: string;
  model?: string;
  latency_ms?: number;
  decision_type?: string;
  from?: string;
  to?: string;
  reason?: string;
  timestamp: string;
}

function buildRoutingTrail(task: AgentTask): RoutingEvent[] {
  const trace = task.execution_trace ?? [];
  const events = trace.filter(
    (ev) => ev.event_type.startsWith('provider_decision_') || ev.event_type === 'provider_fallback'
  );
  const sorted = [...events].sort((a, b) => (a.timestamp < b.timestamp ? -1 : a.timestamp > b.timestamp ? 1 : 0));
  return sorted.map((ev) => {
    if (ev.event_type === 'provider_fallback') {
      const d = ev.details ?? {};
      return {
        kind: 'fallback',
        from: d.failed_provider,
        to: d.next_provider,
        reason: d.reason,
        timestamp: ev.timestamp,
      };
    }
    const d = ev.details ?? {};
    return {
      kind: 'attempted',
      provider: d.provider,
      model: d.model,
      latency_ms: d.latency_ms,
      decision_type: d.decision_type,
      timestamp: ev.timestamp,
    };
  });
}

function formatTime(iso?: string) {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleTimeString();
}

function getStepStatusTone(status: AgentPlanStep['status']) {
  switch (status) {
    case 'RUNNING':
    case 'IN_PROGRESS':
      return 'working';
    case 'COMPLETED':
    case 'REPAIRED':
      return 'success';
    case 'FAILED':
      return 'danger';
    default:
      return 'neutral';
  }
}

function getStepIcon(status: AgentPlanStep['status']) {
  const tone = STATUS_TONES[getStepStatusTone(status)];
  switch (status) {
    case 'RUNNING':
    case 'IN_PROGRESS':
      return <PlayCircle className={`w-4 h-4 ${tone.text}`} />;
    case 'COMPLETED':
    case 'REPAIRED':
      return <CheckCircle className={`w-4 h-4 ${tone.text}`} />;
    case 'FAILED':
      return <AlertCircle className={`w-4 h-4 ${tone.text}`} />;
    default:
      return <Clock className={`w-4 h-4 ${tone.text}`} />;
  }
}

function Section({
  icon,
  title,
  defaultOpen = false,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border-t border-white/5">
      <button
        onClick={() => setOpen((prev) => !prev)}
        className="w-full flex items-center gap-2 py-2.5 text-left"
      >
        {open ? <ChevronDown className="w-3.5 h-3.5 text-white/30 shrink-0" /> : <ChevronRight className="w-3.5 h-3.5 text-white/30 shrink-0" />}
        <span className="text-white/40 shrink-0">{icon}</span>
        <span className="text-xs font-semibold text-white/60 uppercase tracking-wider">{title}</span>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="pb-3 flex flex-col gap-2">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export function AgentTimeline({ task, inspectMode: controlledInspect, onToggleInspect }: AgentTimelineProps) {
  const isControlled = controlledInspect !== undefined;
  const [internalInspect, setInternalInspect] = useState(false);
  const inspectMode = isControlled ? controlledInspect : internalInspect;

  useEffect(() => {
    setInternalInspect(false);
  }, [task.task_id]);

  const toggleInspect = () => {
    if (isControlled && onToggleInspect) onToggleInspect();
    else setInternalInspect((prev) => !prev);
  };

  const steps = task.plan ?? [];
  const toolCalls = task.tool_calls ?? [];
  const observations = task.observations ?? [];
  const executionTrace = task.execution_trace ?? [];
  const routing = buildRoutingTrail(task);

  const hasTelemetry = toolCalls.length > 0 || observations.length > 0 || executionTrace.length > 0;

  return (
    <div className="flex flex-col gap-4 w-full h-full p-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-white/90">
            {inspectMode ? 'Inspect' : 'Execution Checklist'}
          </h2>
          <p className="text-xs text-white/40 mt-0.5">
            {task.step_count} step{task.step_count !== 1 ? 's' : ''} · {task.total_tool_calls} tool call{task.total_tool_calls !== 1 ? 's' : ''}
          </p>
        </div>
        <button
          onClick={toggleInspect}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors border ${
            inspectMode
              ? 'bg-accent/20 border-accent/30 text-accent'
              : 'bg-white/5 border-white/10 text-white/50 hover:text-white/80'
          }`}
        >
          {inspectMode ? <EyeOff className="w-3.5 h-3.5" /> : <Search className="w-3.5 h-3.5" />}
          {inspectMode ? 'Exit Inspect' : 'Inspect'}
        </button>
      </div>

      {task.error_detail && task.status === 'FAILED' && (
        <div className="p-3 rounded-xl border border-red-500/30 bg-red-500/10">
          <p className="text-xs font-semibold text-red-300 uppercase tracking-wider mb-1.5">Error</p>
          <p className="text-xs text-red-200/80 whitespace-pre-wrap max-h-40 overflow-y-auto">
            {typeof task.error_detail === 'string' ? task.error_detail : JSON.stringify(task.error_detail, null, 2)}
          </p>
        </div>
      )}

      <div className="flex-1 overflow-y-auto">
        {!inspectMode && (
          <div className="flex flex-col gap-2">
            <AnimatePresence initial={false}>
              {steps.map((step, idx) => {
                const isActiveStep = step.status === 'RUNNING' || step.status === 'IN_PROGRESS';
                return (
                  <motion.div
                    key={step.step_number}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.05 }}
                    className={`flex gap-3 p-3 rounded-xl border transition-colors ${
                      isActiveStep
                        ? `${STATUS_TONES.working.bg} ${STATUS_TONES.working.border} shadow-[0_0_15px_rgba(56,189,248,0.06)]`
                        : step.status === 'FAILED'
                          ? `${STATUS_TONES.danger.bg} ${STATUS_TONES.danger.border}`
                          : 'bg-white/[0.02] border-white/5'
                    }`}
                  >
                    <div className="mt-0.5 shrink-0">{getStepIcon(step.status)}</div>
                    <div className="flex flex-col gap-1 w-full min-w-0">
                      <div className="font-medium text-sm text-white/80 flex items-center justify-between gap-2">
                        <span className="truncate">{step.description}</span>
                        <span className="flex items-center gap-1.5 shrink-0">
                          {isActiveStep && (
                            <span className="text-[10px] uppercase tracking-wider text-sky-300 font-bold animate-pulse">
                              Active
                            </span>
                          )}
                          {step.status === 'FAILED' && (
                            <span className="text-[10px] uppercase tracking-wider text-red-300 font-bold">
                              Failed
                            </span>
                          )}
                        </span>
                      </div>
                      {step.result_summary && (
                        <p className="text-xs text-white/40 mt-0.5 line-clamp-2">{step.result_summary}</p>
                      )}
                    </div>
                  </motion.div>
                );
              })}
            </AnimatePresence>

            {steps.length === 0 && (
              <div className="text-white/30 text-sm py-4">
                {task.status === 'PLANNING' ? 'Building execution plan...' : 'Waiting for execution plan...'}
              </div>
            )}
          </div>
        )}

        {inspectMode && (
          <div className="flex flex-col">
            <Section icon={<ListChecks className="w-3.5 h-3.5" />} title="Execution Plan" defaultOpen>
              <div className="flex flex-col gap-2">
                {steps.map((step) => (
                  <div key={step.step_number} className="p-2.5 rounded-lg border border-white/5 bg-black/20">
                    <div className="flex items-center gap-2">
                      <div className="shrink-0">{getStepIcon(step.status)}</div>
                      <span className="text-xs text-white/70">{step.description}</span>
                    </div>
                    <div className="mt-1.5 font-mono text-[10px] text-white/35">
                      Step {step.step_number} · {step.status}
                    </div>
                    {step.result_summary && (
                      <p className="text-[11px] text-white/45 mt-1">{step.result_summary}</p>
                    )}
                  </div>
                ))}
                {steps.length === 0 && <p className="text-xs text-white/30">No plan generated yet.</p>}
              </div>
            </Section>

            <Section icon={<Network className="w-3.5 h-3.5" />} title="Provider Routing" defaultOpen>
              {routing.length === 0 ? (
                <p className="text-xs text-white/30">
                  No provider routing recorded. {task.current_provider ? `Current: ${task.current_provider}.` : ''}
                </p>
              ) : (
                <div className="flex flex-col gap-1.5">
                  {routing.map((ev, i) => (
                    <div key={i} className="flex flex-col gap-1.5 p-2.5 rounded-lg border border-white/5 bg-black/20">
                      {ev.kind === 'attempted' ? (
                        <>
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md border bg-sky-500/10 border-sky-500/25 font-mono text-[11px] text-sky-300 shrink-0">
                              {ev.provider}
                            </span>
                            {ev.model && (
                              <span className="text-[10px] font-mono text-white/45 truncate max-w-[180px]">
                                {ev.model}
                              </span>
                            )}
                            <span className="text-[10px] text-white/35 ml-auto shrink-0 flex items-center gap-1">
                              <Clock className="w-3 h-3" />
                              {ev.latency_ms != null ? `${ev.latency_ms}ms` : '—'}
                            </span>
                          </div>
                          <div className="text-[10px] text-white/40 flex items-center justify-between gap-2">
                            <span className="truncate">{ev.decision_type ?? 'attempted'}</span>
                            <span className="text-white/25 shrink-0">{formatTime(ev.timestamp)}</span>
                          </div>
                        </>
                      ) : (
                        <>
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <AlertCircle className="w-3.5 h-3.5 text-red-400 shrink-0" />
                            <span className="inline-flex items-center px-1.5 py-0.5 rounded-md border border-red-500/30 bg-red-500/10 font-mono text-[11px] text-red-300">
                              {ev.from ?? 'unknown'}
                            </span>
                            <span className="text-[10px] text-white/30">→</span>
                            <span className="inline-flex items-center px-1.5 py-0.5 rounded-md border border-white/10 bg-white/5 font-mono text-[11px] text-white/60">
                              {ev.to ?? 'NONE'}
                            </span>
                          </div>
                          {ev.reason && (
                            <div className="text-[10px] text-white/40 leading-snug">{ev.reason}</div>
                          )}
                        </>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </Section>

            <Section icon={<Wrench className="w-3.5 h-3.5" />} title="Tool Calls">
              {toolCalls.length === 0 ? (
                <p className="text-xs text-white/30">No tool calls recorded.</p>
              ) : (
                <div className="flex flex-col gap-1.5">
                  {toolCalls.map((call, i) => {
                    const argsText =
                      typeof call.arguments === 'string'
                        ? call.arguments
                        : JSON.stringify(call.arguments ?? {});
                    const summary = argsText.length > 140 ? `${argsText.slice(0, 140)}…` : argsText;
                    return (
                      <div key={call.call_id || i} className="p-2.5 rounded-lg border border-white/5 bg-black/20">
                        <div className="flex items-center justify-between gap-2 mb-1">
                          <span className="text-xs font-semibold text-accent/80 truncate">{call.tool_name}</span>
                          <span className="text-[10px] text-white/30 shrink-0">{formatTime(call.timestamp)}</span>
                        </div>
                        <p className="text-[11px] text-white/55 font-mono truncate mb-1">{summary}</p>
                        <details className="group">
                          <summary className="cursor-pointer text-[10px] text-white/35 list-none">
                            <span className="group-open:hidden">Expand arguments</span>
                            <span className="hidden group-open:inline">Collapse arguments</span>
                          </summary>
                          <pre className="mt-1.5 text-[10px] text-white/45 whitespace-pre-wrap max-h-32 overflow-y-auto font-mono">
                            {argsText}
                          </pre>
                        </details>
                      </div>
                    );
                  })}
                </div>
              )}
            </Section>

            <Section icon={<GitBranch className="w-3.5 h-3.5" />} title="Observations">
              {observations.length === 0 ? (
                <p className="text-xs text-white/30">No observations recorded.</p>
              ) : (
                <div className="flex flex-col gap-1.5">
                  {observations.slice(-6).map((obs, i) => {
                    const outputText =
                      typeof obs.output === 'string' ? obs.output : JSON.stringify(obs.output ?? {});
                    const summary =
                      (obs.success
                        ? outputText.length > 120
                          ? `${outputText.slice(0, 120)}…`
                          : outputText
                        : obs.error || outputText.slice(0, 160)) || '';
                    return (
                      <div key={obs.call_id || i} className="p-2.5 rounded-lg border border-white/5 bg-black/20">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-[11px] text-white/50 font-medium truncate">{obs.tool_name}</span>
                          <span
                            className={`text-[10px] font-semibold ${
                              obs.success ? STATUS_TONES.success.text : STATUS_TONES.danger.text
                            }`}
                          >
                            {obs.success ? 'SUCCESS' : 'ERROR'}
                          </span>
                          <span className="text-white/25 text-[10px] ml-auto shrink-0">{formatTime(obs.timestamp)}</span>
                        </div>
                        <p className="text-[11px] text-white/45 font-mono truncate">{summary}</p>
                        <details className="group mt-1">
                          <summary className="cursor-pointer text-[10px] text-white/35 list-none">
                            <span className="group-open:hidden">Expand output</span>
                            <span className="hidden group-open:inline">Collapse output</span>
                          </summary>
                          <pre className="mt-1.5 text-[10px] text-white/45 whitespace-pre-wrap max-h-28 overflow-y-auto font-mono">
                            {outputText}
                          </pre>
                          {obs.error && (
                            <pre className="text-red-400 text-[10px] mt-1.5 whitespace-pre-wrap">{obs.error}</pre>
                          )}
                        </details>
                      </div>
                    );
                  })}
                </div>
              )}
            </Section>

            <Section icon={<Clock className="w-3.5 h-3.5" />} title="Execution Trace">
              {executionTrace.length === 0 ? (
                <p className="text-xs text-white/30">No trace events recorded.</p>
              ) : (
                <div className="flex flex-col gap-1.5">
                  {executionTrace.map((ev, i) => (
                    <div key={i} className="p-2.5 rounded-lg border border-white/5 bg-black/20">
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <span className="text-xs font-mono text-accent/80">{ev.event_type}</span>
                        <span className="text-[10px] text-white/30 shrink-0">{formatTime(ev.timestamp)}</span>
                      </div>
                      <pre className="text-[10px] text-white/45 whitespace-pre-wrap font-mono">
                        {typeof ev.details === 'string' ? ev.details : JSON.stringify(ev.details, null, 2)}
                      </pre>
                    </div>
                  ))}
                </div>
              )}
            </Section>

            <Section icon={<FileJson className="w-3.5 h-3.5" />} title="Raw Data">
              <details className="group">
                <summary className="cursor-pointer text-[11px] text-white/40 list-none">
                  <span className="group-open:hidden">Expand full task payload</span>
                  <span className="hidden group-open:inline">Collapse full task payload</span>
                </summary>
                <pre className="mt-2 p-3 bg-black/40 rounded-lg border border-white/5 font-mono text-[10px] text-white/40 whitespace-pre-wrap overflow-x-auto max-h-96 overflow-y-auto">
                  {JSON.stringify(task, null, 2)}
                </pre>
              </details>
            </Section>

            {!hasTelemetry && executionTrace.length === 0 && (
              <p className="text-[10px] text-white/25 mt-2">
                No execution telemetry available for this run yet.
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
