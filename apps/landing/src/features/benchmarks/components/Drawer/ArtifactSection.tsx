import React, { useState } from 'react';
import { FileCode, FileSpreadsheet, FileText, Download } from 'lucide-react';
import type { Benchmark, ArtifactItem } from '@/domain/benchmarks/types';

interface Props {
  benchmark: Benchmark;
}

export const ArtifactSection: React.FC<Props> = ({ benchmark }) => {
  const artifacts = benchmark.artifacts || [];

  const [selectedArtifact, setSelectedArtifact] = useState<ArtifactItem | null>(
    artifacts[0] || null
  );

  const getIcon = (type: ArtifactItem['type']) => {
    if (type === 'json') return <FileCode className="w-4 h-4 text-amber-400" />;
    if (type === 'csv') return <FileSpreadsheet className="w-4 h-4 text-emerald-400" />;
    return <FileText className="w-4 h-4 text-blue-400" />;
  };

  if (artifacts.length === 0) return null;

  return (
    <div className="p-4 rounded-xl border border-white/5 bg-black/40 space-y-3">
      <h4 className="text-xs font-semibold text-white">Evaluation Artifacts & Exports</h4>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
        {artifacts.map((art) => (
          <button
            key={art.id}
            onClick={() => setSelectedArtifact(art)}
            className={`p-2.5 rounded-lg border text-left flex items-center justify-between transition-colors ${
              selectedArtifact?.id === art.id
                ? 'border-accent/40 bg-accent/10'
                : 'border-white/5 bg-white/[0.02] hover:bg-white/5'
            }`}
          >
            <div className="flex items-center gap-2 overflow-hidden">
              {getIcon(art.type)}
              <div className="truncate">
                <div className="text-xs font-mono text-white truncate">{art.filename}</div>
                <div className="text-[10px] text-white/30">{art.size}</div>
              </div>
            </div>
            <Download className="w-3.5 h-3.5 text-white/30 shrink-0 ml-1" />
          </button>
        ))}
      </div>

      {selectedArtifact && selectedArtifact.previewContent && (
        <div className="p-3 rounded-lg bg-neutral-950 border border-white/5 font-mono text-xs space-y-1">
          <div className="flex items-center justify-between text-[10px] text-white/40 pb-1 border-b border-white/5">
            <span>Previewing {selectedArtifact.filename}</span>
            <span>{selectedArtifact.type.toUpperCase()}</span>
          </div>
          <pre className="text-white/70 overflow-x-auto p-1 leading-relaxed text-[11px]">
            {selectedArtifact.previewContent}
          </pre>
        </div>
      )}
    </div>
  );
};

export default ArtifactSection;
