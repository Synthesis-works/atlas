import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { Play, X, Cpu, Database, AlertCircle, CheckCircle2 } from 'lucide-react';
import { dispatchExecution, getDispatchTargets, type DispatchTarget } from '../services/evaluationService';
import { useWorkspaceStore } from '@/store/workspaceStore';
import type { BackendExecutionResponse } from '../services/evaluationService';

interface NewEvaluationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onRunDispatched?: (execution: BackendExecutionResponse) => void;
}

const FALLBACK_BENCHMARK_OPTIONS = [
  {
    id: '00000000-0000-0000-0000-000000000005',
    name: 'HumanEval Benchmark',
    version: '1.0.0',
    description: 'Python functional correctness & code synthesis evaluation suite (164 tasks).',
  },
  {
    id: 'mmlu-pro',
    name: 'MMLU-Pro',
    version: '1.2.0',
    description: 'Massive Multitask Language Understanding professional reasoning benchmark.',
  },
  {
    id: 'truthful-qa',
    name: 'TruthfulQA',
    version: '2.0.0',
    description: 'Truthfulness and hallucination resistance benchmark across 817 questions.',
  },
  {
    id: 'gsm8k',
    name: 'GSM8K Math',
    version: '1.1.0',
    description: 'Grade school math word problems requiring multi-step quantitative reasoning.',
  },
];

const PRESET_MODELS = [
  { id: 'groq/llama-3.1-8b-instant', name: 'Groq — Llama 3.1 8B Instant (Live API)', provider: 'Groq', badge: 'Live Provider' },
  { id: 'groq/llama-3.3-70b-versatile', name: 'Groq — Llama 3.3 70B Versatile (Live API)', provider: 'Groq', badge: 'Live Provider' },
  { id: 'mistral-small-latest', name: 'Mistral — Small Latest (Live API)', provider: 'Mistral', badge: 'Live Provider' },
  { id: 'nvidia/meta/llama-3.1-8b-instruct', name: 'NVIDIA — Llama 3.1 8B Instruct (Live API)', provider: 'NVIDIA', badge: 'Live Provider' },
  { id: 'invalid-provider/non-existent-model', name: 'Invalid Model (Controlled Failure Test)', provider: 'Invalid', badge: 'Failure Test' },
];

export const NewEvaluationModal: React.FC<NewEvaluationModalProps> = ({
  isOpen,
  onClose,
  onRunDispatched,
}) => {
  const [benchmarkOptions, setBenchmarkOptions] = useState(FALLBACK_BENCHMARK_OPTIONS);
  const [datasetByVersion, setDatasetByVersion] = useState<Record<string, string | null>>({});
  const [selectedBenchmarkId, setSelectedBenchmarkId] = useState(FALLBACK_BENCHMARK_OPTIONS[0].id);
  const [selectedModel, setSelectedModel] = useState(PRESET_MODELS[0].id);
  const [customModel, setCustomModel] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const { triggerEvaluationRun } = useWorkspaceStore();

  useEffect(() => {
    if (!isOpen) return;
    let cancelled = false;
    getDispatchTargets().then((res) => {
      if (cancelled) return;
      if (res.data && res.data.length > 0) {
        const options = res.data.map((t: DispatchTarget) => ({
          id: t.benchmark_version_id,
          name: t.benchmark_name,
          version: t.version_string || '1.0.0',
          description: 'Live benchmark version available for execution.',
          dataset_version_id: t.dataset_version_id,
        }));
        setBenchmarkOptions(options);
        setDatasetByVersion(
          Object.fromEntries(options.map((o: any) => [o.id, o.dataset_version_id]))
        );
        setSelectedBenchmarkId(options[0].id);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const activeTargetModel = customModel.trim() || selectedModel;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
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
        
        // 2. Register with workspace store
        triggerEvaluationRun(selectedBenchmarkId, activeTargetModel);

        if (onRunDispatched) {
          onRunDispatched(result.data);
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
        className="relative w-full max-w-xl bg-[#0F1117] border border-white/15 rounded-2xl shadow-2xl overflow-hidden text-white"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between p-6 border-b border-white/10 bg-white/[0.02]">
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
        <form onSubmit={handleSubmit} className="p-6 space-y-5">
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
            <div className="grid grid-cols-1 gap-2">
              {benchmarkOptions.map((bm) => (
                <label
                  key={bm.id}
                  className={`flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition-all ${
                    selectedBenchmarkId === bm.id
                      ? 'bg-white/10 border-accent/60 text-white'
                      : 'bg-white/[0.02] border-white/10 text-white/60 hover:bg-white/5 hover:text-white/80'
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
          </div>

          {/* 2. Target Model Selection */}
          <div className="space-y-2">
            <label className="block text-xs font-mono uppercase tracking-wider text-white/60 flex items-center gap-2">
              <Cpu className="w-3.5 h-3.5 text-accent" /> Target LLM Model Provider
            </label>
            <select
              id="model-preset-select"
              value={selectedModel}
              onChange={(e) => {
                setSelectedModel(e.target.value);
                setCustomModel('');
              }}
              className="w-full bg-[#161922] border border-white/15 rounded-xl px-3.5 py-2.5 text-xs text-white focus:outline-none focus:border-accent/60 transition-colors"
            >
              {PRESET_MODELS.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name}
                </option>
              ))}
            </select>

            {/* Custom Model Input Fallback */}
            <div className="pt-1">
              <input
                id="custom-model-input"
                type="text"
                placeholder="Or enter custom model identifier (e.g. groq/llama-3.1-8b-instant)..."
                value={customModel}
                onChange={(e) => setCustomModel(e.target.value)}
                className="w-full bg-[#161922] border border-white/10 rounded-xl px-3.5 py-2 text-xs text-white placeholder:text-white/30 focus:outline-none focus:border-accent/50"
              />
            </div>
          </div>

          {/* Active Model Indicator */}
          <div className="p-3 rounded-xl bg-white/[0.02] border border-white/5 flex items-center justify-between text-xs font-mono">
            <span className="text-white/40">Active Dispatch Payload:</span>
            <span className="text-emerald-400 font-semibold">{activeTargetModel}</span>
          </div>

          {/* Footer Actions */}
          <div className="flex items-center justify-end gap-3 pt-3 border-t border-white/10">
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
              disabled={isSubmitting}
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
