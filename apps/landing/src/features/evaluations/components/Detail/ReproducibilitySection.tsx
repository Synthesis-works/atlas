import React from 'react';
import type { EvaluationRun } from '@/domain/evaluations/types';

interface Props { evaluation: EvaluationRun; }

export const ReproducibilitySection: React.FC<Props> = ({ evaluation }) => {
  if (!evaluation.reproducibility) {
    return (
      <div className="space-y-3">
        <h4 className="text-xs font-semibold text-white">Reproducibility Manifest</h4>
        <div className="p-6 rounded-xl border border-white/5 bg-black/40 text-center text-xs font-mono text-white/30">
          No reproducibility manifest was persisted for this run.
        </div>
      </div>
    );
  }

  const r = evaluation.reproducibility;
  const rows = [
    { label: 'Model Version', value: r.modelVersion, mono: true },
    { label: 'Dataset Version', value: r.datasetVersion, mono: true },
    { label: 'Benchmark Version', value: r.benchmarkVersion, mono: true },
    { label: 'Prompt Version', value: r.promptVersion, mono: true },
    { label: 'Commit SHA', value: r.commitSha, mono: true, accent: true, truncate: true },
    { label: 'Docker Image', value: r.dockerImage, mono: true },
    { label: 'Eval Engine', value: r.engineVersion, mono: true },
    { label: 'Runtime', value: r.runtime, mono: true },
    { label: 'Seed', value: String(r.seed), mono: true },
    { label: 'OS', value: r.os, mono: false },
    { label: 'Python', value: r.pythonVersion, mono: true },
    { label: 'CUDA', value: r.cudaVersion, mono: true },
  ];

  return (
    <div className="space-y-4">
      <div>
        <h4 className="text-xs font-semibold text-white mb-1">Reproducibility Manifest</h4>
        <p className="text-[10px] font-mono text-white/30 leading-relaxed">
          Every run is fully reproducible using the information below. Use the commit SHA and Docker image to recreate the exact execution environment.
        </p>
      </div>

      <div className="p-4 rounded-xl border border-white/5 bg-black/40 space-y-2">
        {rows.map(row => (
          <div key={row.label} className="flex items-start gap-4 text-xs">
            <span className="font-mono text-white/30 w-32 shrink-0 leading-relaxed">{row.label}</span>
            <span className={`font-mono leading-relaxed break-all ${row.accent ? 'text-emerald-400' : 'text-white/70'} ${row.truncate ? 'truncate max-w-[240px]' : ''}`}>
              {row.value}
            </span>
          </div>
        ))}
      </div>

      {/* Reproduce button */}
      <button className="w-full py-2.5 rounded-xl border border-white/8 bg-white/[0.03] text-xs font-mono text-white/40 hover:text-white hover:border-white/15 hover:bg-white/[0.06] transition-all text-center">
        ↻ Re-run with Identical Configuration
      </button>
    </div>
  );
};

export default ReproducibilitySection;
