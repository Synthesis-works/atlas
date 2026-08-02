import React from 'react';
import { CheckCircle2, AlertCircle } from 'lucide-react';
import type { Benchmark } from '@/domain/benchmarks/types';

interface Props {
  benchmark: Benchmark;
}

const CHECKLIST_ITEMS: { key: keyof Benchmark['verification']; label: string }[] = [
  { key: 'datasetLicense', label: 'Dataset License Verified' },
  { key: 'metadata', label: 'Structured Metadata' },
  { key: 'promptSchema', label: 'Prompt Schema Defined' },
  { key: 'outputSchema', label: 'Output Schema Validated' },
  { key: 'referenceAnswers', label: 'Reference Answers Included' },
  { key: 'evaluationScript', label: 'Evaluation Script Executable' },
  { key: 'metricDefinitions', label: 'Metric Definitions Documented' },
  { key: 'documentation', label: 'Methodology Documentation' },
  { key: 'reproducibility', label: 'End-to-End Reproducibility' },
];

export const VerificationSection: React.FC<Props> = ({ benchmark }) => {
  const verifiedCount = Object.values(benchmark.verification).filter(Boolean).length;

  return (
    <div className="p-4 rounded-xl border border-white/5 bg-black/40 space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-semibold text-white">9-Point Verification Checklist</h4>
        <span className="text-xs font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          {verifiedCount} / 9 Verified ({benchmark.verificationScore}%)
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs pt-1">
        {CHECKLIST_ITEMS.map((item) => {
          const isPassed = benchmark.verification[item.key];
          return (
            <div
              key={item.key}
              className="flex items-center gap-2 p-2 rounded-lg bg-white/[0.02] border border-white/[0.03]"
            >
              {isPassed ? (
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
              ) : (
                <AlertCircle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
              )}
              <span className={isPassed ? 'text-white/80' : 'text-white/40'}>{item.label}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default VerificationSection;
