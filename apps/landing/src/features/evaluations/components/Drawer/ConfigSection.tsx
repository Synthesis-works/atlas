import React from 'react';
import type { EvaluationRun } from '@/domain/evaluations/types';

interface Props { evaluation: EvaluationRun; }

export const ConfigSection: React.FC<Props> = ({ evaluation }) => {
  const c = evaluation.config;
  const r = evaluation.reproducibility;

  return (
    <div className="space-y-4">
      <div>
        <h4 className="text-xs font-semibold text-white mb-3">Runtime Configuration</h4>
        <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-xs font-mono p-4 rounded-xl border border-white/5 bg-black/40">
          <span className="text-white/40">Provider</span><span className="text-white/80">{c.provider}</span>
          <span className="text-white/40">Temperature</span><span className="text-white/80">{c.temperature}</span>
          <span className="text-white/40">Seed</span><span className="text-white/80">{c.seed}</span>
          <span className="text-white/40">Max Tokens</span><span className="text-white/80">{c.maxTokens.toLocaleString()}</span>
          <span className="text-white/40">Batch Size</span><span className="text-white/80">{c.batchSize}</span>
          <span className="text-white/40">Threads</span><span className="text-white/80">{c.threads}</span>
          <span className="text-white/40">Timeout</span><span className="text-white/80">{c.timeout}</span>
          <span className="text-white/40">Retries</span><span className="text-white/80">{c.retries}</span>
          {c.quantization && <>
            <span className="text-white/40">Quantization</span><span className="text-amber-400">{c.quantization}</span>
          </>}
        </div>
      </div>
      <div>
        <h4 className="text-xs font-semibold text-white mb-3">Reproducibility Manifest</h4>
        <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-xs font-mono p-4 rounded-xl border border-white/5 bg-black/40">
          <span className="text-white/40">Model Version</span><span className="text-white/80 truncate">{r.modelVersion}</span>
          <span className="text-white/40">Dataset Version</span><span className="text-white/80">{r.datasetVersion}</span>
          <span className="text-white/40">Benchmark Version</span><span className="text-white/80">{r.benchmarkVersion}</span>
          <span className="text-white/40">Prompt Version</span><span className="text-white/80">{r.promptVersion}</span>
          <span className="text-white/40">Commit SHA</span><span className="text-emerald-400 truncate">{r.commitSha.slice(0, 24)}…</span>
          <span className="text-white/40">Docker Image</span><span className="text-white/80">{r.dockerImage}</span>
          <span className="text-white/40">Runtime</span><span className="text-white/80">{r.runtime}</span>
          <span className="text-white/40">Seed</span><span className="text-white/80">{r.seed}</span>
        </div>
      </div>
    </div>
  );
};

export default ConfigSection;
