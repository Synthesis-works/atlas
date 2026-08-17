import React, { useState } from 'react';
import type { Benchmark } from '@/domain/benchmarks/types';
import { Tabs } from '@/shared/components';

interface Props {
  benchmark: Benchmark;
}

export const DatasetSection: React.FC<Props> = ({ benchmark }) => {
  const [split, setSplit] = useState<'train' | 'validation' | 'test'>('test');

  const samples = benchmark.datasetSamples || [];
  const sample = samples.find((s) => s.split === split) || samples[0];

  return (
    <div className="p-4 rounded-xl border border-white/5 bg-black/40 space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-semibold text-white">Dataset Split Explorer</h4>
        <Tabs
          options={[
            { id: 'train', label: 'Train' },
            { id: 'validation', label: 'Val' },
            { id: 'test', label: 'Test' },
          ]}
          activeId={split}
          onChange={(id) => setSplit(id as any)}
        />
      </div>

      {sample ? (
        <div className="space-y-2.5 pt-1 text-xs">
          <div className="p-3 rounded-lg bg-neutral-950 border border-white/5 font-mono">
            <span className="text-[10px] uppercase text-white/30 tracking-wider block mb-1">
              Sample Prompt ({sample.id})
            </span>
            <p className="text-white/80 leading-relaxed whitespace-pre-wrap">{sample.prompt}</p>
          </div>

          <div className="p-3 rounded-lg bg-neutral-950 border border-white/5 font-mono">
            <span className="text-[10px] uppercase text-emerald-400/60 tracking-wider block mb-1">
              Expected Reference Answer
            </span>
            <p className="text-emerald-300/90 whitespace-pre-wrap">{sample.expectedAnswer}</p>
          </div>

          <div className="flex flex-wrap gap-2 text-[10px] font-mono text-white/40 pt-1">
            <span>Difficulty: <strong className="text-white/70">{sample.difficulty}</strong></span>
            {Object.entries(sample.metadata).map(([k, v]) => (
              <span key={k} className="px-2 py-0.5 rounded bg-white/5 text-white/50">
                {k}: {String(v)}
              </span>
            ))}
          </div>
        </div>
      ) : (
        <div className="text-xs text-white/30 italic py-4">No dataset sample available for this split.</div>
      )}
    </div>
  );
};

export default DatasetSection;
