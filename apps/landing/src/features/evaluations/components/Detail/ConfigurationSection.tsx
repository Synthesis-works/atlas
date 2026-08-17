import React from 'react';
import type { EvaluationRun } from '@/domain/evaluations/types';

interface Props { evaluation: EvaluationRun; }

export const ConfigurationSection: React.FC<Props> = ({ evaluation }) => {
  if (!evaluation.config) {
    return (
      <div className="space-y-3">
        <h4 className="text-xs font-semibold text-white">Runtime Configuration</h4>
        <div className="p-6 rounded-xl border border-white/5 bg-black/40 text-center text-xs font-mono text-white/30">
          No execution configuration was persisted for this run.
        </div>
      </div>
    );
  }

  const c = evaluation.config;

  const rows = [
    { label: 'Provider', value: c.provider },
    { label: 'Temperature', value: String(c.temperature) },
    { label: 'Top P', value: String(c.topP) },
    { label: 'Seed', value: String(c.seed) },
    { label: 'Max Tokens', value: c.maxTokens.toLocaleString() },
    { label: 'Batch Size', value: String(c.batchSize) },
    { label: 'Threads', value: String(c.threads) },
    { label: 'Timeout', value: c.timeout },
    { label: 'Retries', value: String(c.retries) },
    ...(c.quantization ? [{ label: 'Quantization', value: c.quantization }] : []),
  ];

  return (
    <div className="space-y-4">
      <h4 className="text-xs font-semibold text-white">Runtime Configuration</h4>
      <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-xs font-mono p-4 rounded-xl border border-white/5 bg-black/40">
        {rows.map(row => (
          <React.Fragment key={row.label}>
            <span className="text-white/35">{row.label}</span>
            <span className={`text-white/80 ${row.label === 'Quantization' ? 'text-amber-400' : ''}`}>{row.value}</span>
          </React.Fragment>
        ))}
      </div>

      {/* JSON view */}
      <div>
        <div className="text-[10px] font-mono text-white/30 mb-1.5">Raw config.json</div>
        <pre className="p-3 rounded-xl bg-black/60 border border-white/5 text-[10px] font-mono text-emerald-400 overflow-auto max-h-40 leading-relaxed">
{JSON.stringify({
  provider: c.provider,
  temperature: c.temperature,
  top_p: c.topP,
  seed: c.seed,
  max_tokens: c.maxTokens,
  batch_size: c.batchSize,
  threads: c.threads,
  timeout: c.timeout,
  retries: c.retries,
  ...(c.quantization ? { quantization: c.quantization } : {}),
}, null, 2)}
        </pre>
      </div>
    </div>
  );
};

export default ConfigurationSection;
