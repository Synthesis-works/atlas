import React, { useEffect, useState } from 'react';
import type { Benchmark } from '@/domain/benchmarks/types';
import {
  getBenchmarkRuns,
  type BackendExecutionRunDTO,
} from '../../services/benchmarkService';
import { Play, CheckCircle, XCircle, Clock, AlertCircle } from 'lucide-react';

interface Props {
  benchmark: Benchmark;
}

export const HistorySection: React.FC<Props> = ({ benchmark }) => {
  const [runs, setRuns] = useState<BackendExecutionRunDTO[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    async function loadRuns() {
      setLoading(true);
      const res = await getBenchmarkRuns(benchmark.versionId);
      if (mounted) {
        setRuns(res.data || []);
        setLoading(false);
      }
    }
    loadRuns();
    return () => {
      mounted = false;
    };
  }, [benchmark.versionId]);

  return (
    <div className="space-y-6">
      {/* Real Execution History */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="text-xs font-semibold text-white">Execution Run History</h4>
          <span className="text-[10px] font-mono text-white/40">
            {runs.length} Runs Recorded
          </span>
        </div>

        {loading ? (
          <div className="p-4 rounded-xl border border-white/5 bg-black/40 text-center text-xs font-mono text-white/40">
            Loading execution runs...
          </div>
        ) : runs.length === 0 ? (
          <div className="p-6 rounded-xl border border-white/5 bg-black/40 text-center text-xs font-mono text-white/40 space-y-1">
            <AlertCircle className="w-5 h-5 mx-auto text-white/20 mb-2" />
            <p className="text-white/70">No benchmark runs recorded yet</p>
            <p className="text-[11px] text-white/30">
              Dispatch a benchmark run to evaluate models against this test suite.
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {runs.map((run) => {
              const isCompleted = run.status === 'COMPLETED' || run.status === 'Completed';
              const isFailed = run.status === 'FAILED' || run.status === 'Failed';
              const isRunning = run.status === 'RUNNING' || run.status === 'Running';

              return (
                <div
                  key={run.id}
                  className="p-3 rounded-xl border border-white/5 bg-black/40 hover:border-white/10 transition-colors space-y-2"
                >
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      {isCompleted ? (
                        <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                      ) : isFailed ? (
                        <XCircle className="w-3.5 h-3.5 text-rose-400" />
                      ) : isRunning ? (
                        <Play className="w-3.5 h-3.5 text-accent animate-pulse" />
                      ) : (
                        <Clock className="w-3.5 h-3.5 text-white/40" />
                      )}
                      <span className="font-mono font-semibold text-white">
                        {run.target_model}
                      </span>
                      <span className="text-white/20">•</span>
                      <span className="text-white/40 font-mono text-[10px]">
                        {run.id.slice(0, 8)}...
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      {run.score != null && (
                        <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 font-mono text-xs font-bold border border-emerald-500/20">
                          {(run.score * 100).toFixed(1)}%
                        </span>
                      )}
                      <span
                        className={`text-[10px] font-mono px-2 py-0.5 rounded ${
                          isCompleted
                            ? 'bg-emerald-500/10 text-emerald-400'
                            : isFailed
                            ? 'bg-rose-500/10 text-rose-400'
                            : 'bg-white/5 text-white/40'
                        }`}
                      >
                        {run.status}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center justify-between text-[11px] font-mono text-white/40 border-t border-white/5 pt-1.5">
                    <span>
                      {run.created_at ? new Date(run.created_at).toLocaleString() : '—'}
                    </span>
                    <div className="flex items-center gap-3">
                      {run.latency_ms != null && (
                        <span>{Math.round(run.latency_ms)}ms</span>
                      )}
                      {run.completed_items != null && (
                        <span>
                          {run.completed_items}/{run.total_items} items
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Immutable Version History */}
      <div className="space-y-3 pt-2">
        <h4 className="text-xs font-semibold text-white">Immutable Benchmark Versions</h4>
        <div className="space-y-1.5">
          {(benchmark.versions && benchmark.versions.length > 0
            ? benchmark.versions
            : [
                {
                  id: benchmark.versionId || benchmark.id,
                  version_string: benchmark.version || '1.0.0',
                  state: benchmark.status,
                },
              ]
          ).map((ver) => (
            <div
              key={ver.id}
              className="p-2.5 rounded-lg border border-white/5 bg-white/[0.02] flex items-center justify-between text-xs font-mono"
            >
              <div className="flex items-center gap-2">
                <span className="text-white font-semibold">v{ver.version_string}</span>
                <span className="text-white/30 text-[10px]">({ver.id})</span>
              </div>
              <span className="text-[10px] px-2 py-0.5 rounded bg-white/5 text-white/50">
                {ver.state}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default HistorySection;
