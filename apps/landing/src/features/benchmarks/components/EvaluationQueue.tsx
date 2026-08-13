import React from 'react';
import { Play, CheckCircle, AlertTriangle, Clock, XCircle } from 'lucide-react';
import type { QueueItem } from '@/store/workspaceStore';
import { useWorkspaceStore } from '@/store/workspaceStore';
import { cn } from '@/lib/utils';

interface EvaluationQueueProps {
  queue: QueueItem[];
}

export const EvaluationQueue: React.FC<EvaluationQueueProps> = ({ queue }) => {
  const { cancelEvaluationRun } = useWorkspaceStore();

  const getStatusIcon = (status: QueueItem['status']) => {
    if (status === 'Running') return <Play className="w-3.5 h-3.5 text-emerald-400 fill-current animate-pulse" />;
    if (status === 'Completed') return <CheckCircle className="w-3.5 h-3.5 text-teal-400" />;
    if (status === 'Failed') return <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />;
    return <Clock className="w-3.5 h-3.5 text-white/40" />;
  };

  return (
    <div className="p-5 rounded-2xl border border-white/5 bg-black/40 backdrop-blur-md space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xs font-semibold text-white tracking-tight">Evaluation Queue</h3>
          <p className="text-[11px] text-white/30 mt-0.5">Real-time model evaluation executions</p>
        </div>
        <span className="text-xs font-mono px-2 py-0.5 rounded bg-white/5 text-white/40 border border-white/5">
          {queue.filter((q) => q.status === 'Running').length} Running
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 font-mono text-xs">
        {queue.map((item) => (
          <div
            key={item.id}
            className="p-3.5 rounded-xl border border-white/5 bg-white/[0.02] space-y-2.5 hover:border-white/10 transition-colors"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {getStatusIcon(item.status)}
                <span className="font-semibold text-white">{item.model}</span>
                <span className="text-white/30">•</span>
                <span className="text-white/60">{item.benchmarkName}</span>
              </div>
              <div className="flex items-center gap-2">
                <span
                  className={cn(
                    'text-[10px] px-2 py-0.5 rounded font-mono',
                    item.status === 'Running' && 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20',
                    item.status === 'Queued' && 'bg-white/5 text-white/40',
                    item.status === 'Completed' && 'bg-teal-500/10 text-teal-400',
                    item.status === 'Failed' && 'bg-rose-500/10 text-rose-400'
                  )}
                >
                  {item.status}
                </span>
                {(item.status === 'Running' || item.status === 'Queued') && (
                  <button
                    onClick={() => cancelEvaluationRun(item.id)}
                    title="Cancel execution"
                    className="p-1 rounded hover:bg-rose-500/20 text-white/40 hover:text-rose-400 transition-colors"
                  >
                    <XCircle className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>

            {/* Progress bar */}
            <div className="space-y-1">
              <div className="flex justify-between text-[10px] text-white/40">
                <span>Progress</span>
                <span>{item.progress}%</span>
              </div>
              <div className="w-full h-1.5 rounded-full bg-white/5 overflow-hidden">
                <div
                  className={cn(
                    'h-full rounded-full transition-all duration-500',
                    item.status === 'Running' && 'bg-emerald-400',
                    item.status === 'Completed' && 'bg-teal-400',
                    item.status === 'Queued' && 'bg-white/20',
                    item.status === 'Failed' && 'bg-rose-400'
                  )}
                  style={{ width: `${item.progress}%` }}
                />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default EvaluationQueue;
