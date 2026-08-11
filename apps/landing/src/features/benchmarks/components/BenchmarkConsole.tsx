import React, { useState, memo } from 'react';
import { Terminal } from '@/shared/components';
import { Sparkles, AlertTriangle, Play, CheckCircle, Clock, Terminal as TerminalIcon } from 'lucide-react';
import type { QueueItem } from '@/store/workspaceStore';
import { cn } from '@/lib/utils';

interface BenchmarkConsoleProps {
  logs: string[];
  queue: QueueItem[];
}

export const BenchmarkConsoleComponent: React.FC<BenchmarkConsoleProps> = ({ logs, queue }) => {
  const [activeTab, setActiveTab] = useState<'terminal' | 'queue' | 'insights'>('terminal');

  const runningCount = queue.filter((q) => q.status === 'Running').length;

  return (
    <section className="liquid-glass-card rounded-2xl border border-white/10 overflow-hidden flex flex-col h-full space-y-0" aria-label="Operational Control Console">
      {/* Console Control Header Bar */}
      <div className="px-5 py-3.5 border-b border-white/10 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white/[0.02]">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 font-mono text-xs text-white/90 font-semibold">
            <TerminalIcon className="w-4 h-4 text-emerald-400" aria-hidden="true" />
            <span>Step 4: Act — Operational Control Console</span>
          </div>
          <span className="text-white/20">•</span>
          <span className="text-xs font-mono text-white/40">Atlas Execution Harness v2.4</span>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center gap-1 p-1 bg-white/5 border border-white/5 rounded-xl" role="tablist" aria-label="Console Views">
          <button
            role="tab"
            aria-selected={activeTab === 'terminal'}
            aria-controls="panel-terminal"
            id="tab-terminal"
            onClick={() => setActiveTab('terminal')}
            className={cn(
              'px-3 py-1 rounded-lg text-xs font-mono transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent',
              activeTab === 'terminal'
                ? 'bg-white/10 text-white font-semibold border border-white/10'
                : 'text-white/40 hover:text-white/70'
            )}
          >
            &gt;_ Live Logs ({logs.length})
          </button>
          <button
            role="tab"
            aria-selected={activeTab === 'queue'}
            aria-controls="panel-queue"
            id="tab-queue"
            onClick={() => setActiveTab('queue')}
            className={cn(
              'px-3 py-1 rounded-lg text-xs font-mono transition-colors cursor-pointer flex items-center gap-1.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent',
              activeTab === 'queue'
                ? 'bg-white/10 text-white font-semibold border border-white/10'
                : 'text-white/40 hover:text-white/70'
            )}
          >
            <span>Queue</span>
            {runningCount > 0 && (
              <span className="px-1.5 py-0.2 rounded-full bg-emerald-400/20 text-emerald-300 text-[10px]">
                {runningCount} live
              </span>
            )}
          </button>
          <button
            role="tab"
            aria-selected={activeTab === 'insights'}
            aria-controls="panel-insights"
            id="tab-insights"
            onClick={() => setActiveTab('insights')}
            className={cn(
              'px-3 py-1 rounded-lg text-xs font-mono transition-colors cursor-pointer flex items-center gap-1.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent',
              activeTab === 'insights'
                ? 'bg-purple-500/20 text-purple-200 font-semibold border border-purple-500/30'
                : 'text-purple-300/50 hover:text-purple-300'
            )}
          >
            <Sparkles className="w-3 h-3 text-purple-400" aria-hidden="true" />
            <span>AI Diagnostics</span>
          </button>
        </div>
      </div>

      {/* Tab Panels */}
      <div className="p-4 flex-1 min-h-[300px]">
        {/* Terminal Output */}
        {activeTab === 'terminal' && (
          <div role="tabpanel" id="panel-terminal" aria-labelledby="tab-terminal" className="h-full flex flex-col justify-between">
            <Terminal title="Atlas Execution Harness — Streaming Telemetry" logs={logs} />
          </div>
        )}

        {/* Execution Queue */}
        {activeTab === 'queue' && (
          <div role="tabpanel" id="panel-queue" aria-labelledby="tab-queue" className="space-y-4">
            <div className="flex items-center justify-between text-xs font-mono text-white/50 border-b border-white/5 pb-2">
              <span>{queue.length} Total Jobs in Execution Queue</span>
              <span>{runningCount} Active Executors</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {queue.map((item) => (
                <div
                  key={item.id}
                  className="p-3.5 rounded-xl border border-white/5 bg-white/[0.02] space-y-2.5 hover:border-white/10 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 font-mono text-xs">
                      {item.status === 'Running' ? (
                        <Play className="w-3.5 h-3.5 text-emerald-400 fill-current animate-pulse" aria-hidden="true" />
                      ) : item.status === 'Completed' ? (
                        <CheckCircle className="w-3.5 h-3.5 text-teal-400" aria-hidden="true" />
                      ) : (
                        <Clock className="w-3.5 h-3.5 text-white/40" aria-hidden="true" />
                      )}
                      <span className="font-semibold text-white">{item.model}</span>
                      <span className="text-white/30">•</span>
                      <span className="text-white/60">{item.benchmarkName}</span>
                    </div>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/5 text-white/40">
                      {item.status}
                    </span>
                  </div>

                  <div className="space-y-1">
                    <div className="flex justify-between text-[10px] font-mono text-white/40">
                      <span>Execution Progress</span>
                      <span>{item.progress}%</span>
                    </div>
                    <div className="w-full h-1.5 rounded-full bg-white/5 overflow-hidden">
                      <div
                        className={cn(
                          'h-full rounded-full transition-all duration-500',
                          item.status === 'Running' && 'bg-emerald-400',
                          item.status === 'Completed' && 'bg-teal-400',
                          item.status === 'Queued' && 'bg-white/20'
                        )}
                        style={{ width: `${item.progress}%` }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* AI Diagnostics & Insights */}
        {activeTab === 'insights' && (
          <div role="tabpanel" id="panel-insights" aria-labelledby="tab-insights" className="p-4 rounded-xl border border-purple-500/20 bg-purple-950/20 space-y-4 font-mono text-xs">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-purple-300">
                <AlertTriangle className="w-4 h-4 text-amber-400" aria-hidden="true" />
                <span className="font-semibold">Anomaly Diagnostic Detected in MMLU-Pro</span>
              </div>
              <span className="text-[10px] px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">
                Auto-Diagnostic Active
              </span>
            </div>

            <p className="text-white/70 text-xs leading-relaxed">
              Accuracy dropped by 4.2% and median latency increased by 21% following prompt template update v2.1.0 on GPT-5 runner. Likely caused by unconstrained Chain-of-Thought recursion.
            </p>

            <div className="flex items-center gap-4 pt-2 border-t border-purple-500/20 text-purple-300 text-xs">
              <button className="underline hover:text-white cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent">
                View Diagnostic Trace →
              </button>
              <button className="underline hover:text-white cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent">
                Rollback Prompt Template
              </button>
            </div>
          </div>
        )}
      </div>
    </section>
  );
};

export const BenchmarkConsole = memo(BenchmarkConsoleComponent);
export default BenchmarkConsole;
