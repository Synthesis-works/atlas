import React from 'react';
import type { EvaluationRun } from '@/domain/evaluations/types';

interface Props { evaluation: EvaluationRun; }

const ICONS: Record<string, string> = {
  pdf: '📄',
  json: '{ }',
  csv: '📊',
  log: '📋',
  txt: '📝',
};

export const ArtifactsSection: React.FC<Props> = ({ evaluation }) => {
  if (evaluation.artifacts.length === 0) {
    return (
      <div className="p-8 text-center text-xs font-mono text-white/30">
        Artifacts will appear after evaluation completes.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <h4 className="text-xs font-semibold text-white">Artifacts</h4>
      <div className="space-y-2">
        {evaluation.artifacts.map(artifact => (
          <div
            key={artifact.id}
            className="group flex items-center gap-3 p-3 rounded-xl border border-white/5 bg-white/[0.02] hover:bg-white/[0.05] hover:border-white/10 transition-all"
          >
            <span className="w-8 h-8 flex items-center justify-center rounded-lg bg-white/5 text-sm font-mono text-white/60">
              {ICONS[artifact.type] || '📁'}
            </span>
            <div className="flex-1 min-w-0">
              <div className="text-xs font-mono text-white truncate">{artifact.filename}</div>
              <div className="text-[10px] font-mono text-white/30">{artifact.size} · {artifact.type.toUpperCase()}</div>
            </div>
            <button className="opacity-0 group-hover:opacity-100 transition-opacity px-2.5 py-1 rounded-lg border border-white/10 text-[10px] font-mono text-white/60 hover:text-white hover:border-white/20">
              Download
            </button>
          </div>
        ))}
      </div>
      {evaluation.artifacts.find(a => a.previewContent) && (
        <div className="mt-3">
          <div className="text-[10px] font-mono text-white/30 mb-1.5">Preview — metrics.json</div>
          <pre className="p-3 rounded-xl bg-black/60 border border-white/5 text-[10px] font-mono text-emerald-400 overflow-auto max-h-32">
            {evaluation.artifacts.find(a => a.previewContent)?.previewContent}
          </pre>
        </div>
      )}
    </div>
  );
};

export default ArtifactsSection;
