import React, { useState } from 'react';
import { Drawer as SharedDrawer } from '@/shared/components';
import type { Benchmark } from '@/domain/benchmarks/types';
import VerificationSection from './VerificationSection';
import DatasetSection from './DatasetSection';
import MetricsSection from './MetricsSection';
import ArtifactSection from './ArtifactSection';
import HistorySection from './HistorySection';
import { Play } from 'lucide-react';

interface BenchmarkDrawerProps {
  benchmark: Benchmark | null;
  onClose: () => void;
  onRun: (benchmarkName: string) => void;
}

export const BenchmarkDrawer: React.FC<BenchmarkDrawerProps> = ({
  benchmark,
  onClose,
  onRun,
}) => {
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleRunClick = async () => {
    if (isSubmitting || !benchmark) return;
    setIsSubmitting(true);
    try {
      await onRun(benchmark.name);
      onClose();
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!benchmark) return null;

  return (
    <SharedDrawer
      isOpen={!!benchmark}
      onClose={onClose}
      width="max-w-3xl"
      title={
        <div className="flex items-center gap-3">
          <span>{benchmark.name}</span>
          <span className="px-2 py-0.5 rounded text-xs font-mono bg-white/5 text-white/40 border border-white/5">
            v{benchmark.version}
          </span>
        </div>
      }
      subtitle={benchmark.description}
    >
      <div className="space-y-6 pb-12">
        {/* Quick Action Bar */}
        <div className="flex items-center justify-between p-4 rounded-xl border border-accent/20 bg-accent/5">
          <div className="text-xs">
            <span className="text-white font-medium block">Execute Evaluation Run</span>
            <span className="text-white/40 font-mono">Estimated runtime {benchmark.estimatedRuntime}</span>
          </div>
          <button
            disabled={isSubmitting}
            onClick={handleRunClick}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-accent text-neutral-950 text-xs font-semibold hover:bg-accent/90 transition-colors shadow-lg shadow-accent/20 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Play className={`w-3.5 h-3.5 fill-current ${isSubmitting ? 'animate-spin' : ''}`} />
            {isSubmitting ? 'Dispatching...' : 'Run Benchmark'}
          </button>
        </div>

        {/* 9-Point Verification Checklist */}
        <VerificationSection benchmark={benchmark} />

        {/* Grafana-style Metrics Overview */}
        <MetricsSection benchmark={benchmark} />

        {/* Dataset Split Explorer */}
        <DatasetSection benchmark={benchmark} />

        {/* Evaluation Artifacts & Exports */}
        <ArtifactSection benchmark={benchmark} />

        {/* Compatible Models */}
        <div className="p-4 rounded-xl border border-white/5 bg-black/40 space-y-2">
          <h4 className="text-xs font-semibold text-white">Compatible ML Models & Engines</h4>
          <div className="flex flex-wrap gap-1.5 pt-1">
            {benchmark.compatibleModels.map((model) => (
              <span
                key={model}
                className="px-2.5 py-1 rounded-lg text-xs font-mono bg-white/5 text-white/70 border border-white/5"
              >
                {model}
              </span>
            ))}
          </div>
        </div>

        {/* Version History Timeline */}
        <HistorySection benchmark={benchmark} />
      </div>
    </SharedDrawer>
  );
};

export default BenchmarkDrawer;
