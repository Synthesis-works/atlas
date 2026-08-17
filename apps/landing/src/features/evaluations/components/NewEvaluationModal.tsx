import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { Play, X, Cpu, Database, AlertCircle, CheckCircle2, ShieldCheck } from 'lucide-react';
import { dispatchExecution, getDispatchTargets, type DispatchTarget } from '../services/evaluationService';
import type { BackendExecutionResponse } from '../services/evaluationService';

interface NewEvaluationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onRunDispatched?: (
    execution: BackendExecutionResponse,
    benchmark: { name: string; version: string }
  ) => void;
}

/**
 * The only model identifier confirmed to be key-valid on this workspace's
 * runner. Anything else must be typed explicitly; it is sent as-is and the
 * backend either runs it or reports a real execution failure.
 */
const VERIFIED_MODEL = 'groq/openai/gpt-oss-20b';

interface BenchmarkOption {
  id: string;
  name: string;
  version: string;
  description: string;
  dataset_version_id: string | null;
}

export const NewEvaluationModal: React.FC<NewEvaluationModalProps> = ({
  isOpen,
  onClose,
  onRunDispatched,
}) => {
  const [benchmarkOptions, setBenchmarkOptions] = useState<BenchmarkOption[]>([]);
  const [isLoadingTargets, setIsLoadingTargets] = useState(false);
  const [datasetByVersion, setDatasetByVersion] = useState<Record<string, string | null>>({});
  const [selectedBenchmarkId, setSelectedBenchmarkId] = useState('');
  const [modelInput, setModelInput] = useState(VERIFIED_MODEL);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    let cancelled = false;
    setError(null);
    setSuccessMsg(null);
    setIsLoadingTargets(true);
    getDispatchTargets().then((res) => {
      if (cancelled) return;
      setIsLoadingTargets(false);
      if (res.data && res.data.length > 0) {
        const options: BenchmarkOption[] = res.data.map((t: DispatchTarget) => ({
          id: t.benchmark_version_id,
          name: t.benchmark_name,
          version: t.version_string || '—',
          description: 'Live benchmark version available for execution.',
          dataset_version_id: t.dataset_version_id ?? null,
        }));
        setBenchmarkOptions(options);
        setDatasetByVersion(
          Object.fromEntries(options.map((o) => [o.id, o.dataset_version_id]))
        );
        setSelectedBenchmarkId(options[0].id);
      } else {
        setBenchmarkOptions([]);
        setSelectedBenchmarkId('');
      }
    });
    return () => {
      cancelled = true;
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const activeTargetModel = modelInput.trim();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedBenchmarkId || !activeTargetModel) return;
    setIsSubmitting(true);
    setError(null);
    setSuccessMsg(null);

    try {
      // 1. Dispatch execution request to API
      const result = await dispatchExecution(
        selectedBenchmarkId,
        activeTargetModel,
        datasetByVersion[selectedBenchmarkId]
      );

      if (result.error) {
        setError(result.error);
        setIsSubmitting(false);
        return;
      }

      if (result.data) {
        setSuccessMsg(`Execution ${result.data.id.substring(0, 8)} queued successfully!`);

        const selected = benchmarkOptions.find((b) => b.id === selectedBenchmarkId);
        if (onRunDispatched) {
          onRunDispatched(result.data, {
            name: selected?.name ?? 'Unknown benchmark',
            version: selected?.version ?? '',
          });
        }

        setTimeout(() => {
          setIsSubmitting(false);
          onClose();
        }, 800);
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to dispatch evaluation execution');
      setIsSubmitting(false);
    }
  };

  return createPortal(
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
      <div
        className="relative w-full max-w-xl max-h-[90vh] flex flex-col bg-ink-1 border border-white/10 rounded-2xl shadow-2xl overflow-hidden text-white"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between p-6 border-b border-white/10 bg-ink-2/60 shrink-0">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
              <Play className="w-5 h-5 fill-current" />
            </div>
            <div>
              <h2 className="text-lg font-bold tracking-tight text-white">Run New Evaluation</h2>
              <p className="text-xs text-white/50">Dispatch a live benchmark execution against an LLM provider.</p>
            </div>
          </div>
          <button
            id="close-modal-btn"
            onClick={onClose}
            className="p-2 rounded-lg text-white/40 hover:text-white hover:bg-white/5 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-5 overflow-y-auto">
          {error && (
            <div className="flex items-start gap-3 p-3.5 rounded-xl bg-red-500/10 border border-red-500/20 text-red-300 text-xs">
              <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold">Dispatch Error</p>
                <p className="text-red-300/80 mt-0.5">{error}</p>
              </div>
            </div>
          )}

          {successMsg && (
            <div className="flex items-center gap-3 p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs font-mono">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>{successMsg}</span>
            </div>
          )}

          {/* 1. Benchmark Selection */}
          <div className="space-y-2">
            <label className="block text-xs font-mono uppercase tracking-wider text-white/60 flex items-center gap-2">
              <Database className="w-3.5 h-3.5 text-accent" /> Benchmark Suite
            </label>
            {isLoadingTargets ? (
              <div className="p-5 rounded-xl border border-white/10 bg-ink-2/60 text-center text-xs font-mono text-white/40">
                Loading available benchmark versions…
              </div>
            ) : benchmarkOptions.length === 0 ? (
              <div className="p-5 rounded-xl border border-white/10 bg-ink-2/60 text-center text-xs font-mono text-white/40">
                No dispatchable benchmark versions found.
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-2 max-h-[280px] overflow-y-auto pr-1 scrollbar-thin scrollbar-thumb-white/10">
                {benchmarkOptions.map((bm) => (
                  <label
                    key={bm.id}
                    className={`flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition-all ${
                      selectedBenchmarkId === bm.id
                        ? 'bg-white/10 border-accent/60 text-white'
                        : 'bg-ink-2/60 border-white/10 text-white/60 hover:bg-white/5 hover:text-white/80'
                    }`}
                  >
                    <input
                      type="radio"
                      name="benchmark"
                      value={bm.id}
                      checked={selectedBenchmarkId === bm.id}
                      onChange={() => setSelectedBenchmarkId(bm.id)}
                      className="mt-1 accent-emerald-400"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-white">{bm.name}</span>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/10 text-white/60">
                          v{bm.version}
                        </span>
                      </div>
                      <p className="text-[11px] text-white/40 mt-0.5 leading-relaxed">{bm.description}</p>
                    </div>
                  </label>
                ))}
              </div>
            )}
          </div>

          {/* 2. Target Model */}
          <div className="space-y-2">
            <label className="block text-xs font-mono uppercase tracking-wider text-white/60 flex items-center gap-2">
              <Cpu className="w-3.5 h-3.5 text-accent" /> Target LLM Model ID
            </label>
            <input
              id="target-model-input"
              type="text"
              value={modelInput}
              onChange={(e) => setModelInput(e.target.value)}
              placeholder="e.g. groq/openai/gpt-oss-20b"
              className="w-full bg-ink-3 border border-white/10 rounded-xl px-3.5 py-2.5 text-xs font-mono text-white placeholder:text-white/30 focus:outline-none focus:border-accent/60 transition-colors"
            />
            <div className="flex items-center justify-between gap-3 pt-1">
              <button
                type="button"
                onClick={() => setModelInput(VERIFIED_MODEL)}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-[10px] font-mono hover:bg-emerald-500/20 transition-colors cursor-pointer"
                title="Verified to run on this workspace's runner"
              >
                <ShieldCheck className="w-3 h-3" />
                Verified: {VERIFIED_MODEL}
              </button>
              <span className="text-[10px] font-mono text-white/30 text-right">
                Any model identifier supported by your configured runner is accepted.
              </span>
            </div>
          </div>

          {/* Active Model Indicator */}
          <div className="p-3 rounded-xl bg-ink-2/60 border border-white/5 flex items-center justify-between text-xs font-mono">
            <span className="text-white/40">Active Dispatch Payload:</span>
            <span className="text-emerald-400 font-semibold break-all text-right pl-3">{activeTargetModel}</span>
          </div>

          {/* Footer Actions */}
          <div className="flex items-center justify-end gap-3 pt-3 border-t border-white/10 shrink-0">
            <button
              type="button"
              id="cancel-eval-btn"
              onClick={onClose}
              className="px-4 py-2 rounded-xl bg-white/5 border border-white/10 text-xs font-mono text-white/70 hover:bg-white/10 hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              id="run-eval-submit-btn"
              disabled={isSubmitting || !selectedBenchmarkId || !activeTargetModel || benchmarkOptions.length === 0}
              className="flex items-center gap-2 px-5 py-2 rounded-xl bg-emerald-400 text-neutral-950 text-xs font-semibold hover:bg-emerald-300 transition-colors shadow-lg shadow-emerald-400/20 disabled:opacity-50"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              {isSubmitting ? 'Dispatching...' : 'Run Evaluation'}
            </button>
          </div>
        </form>
      </div>
    </div>,
    document.body
  );
};
export default NewEvaluationModal;