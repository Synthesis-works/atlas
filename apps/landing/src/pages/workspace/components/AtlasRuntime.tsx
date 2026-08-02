import { motion } from 'framer-motion';
import { fadeUp } from '@/lib/motion';
import { Card } from '@/design/primitives';
import { Cpu, Server, Activity, Terminal } from 'lucide-react';

const RUNTIME_DATA = {
  engines: [
    { name: 'Benchmark Engine', status: 'Healthy' },
    { name: 'Execution Engine', status: 'Healthy' },
    { name: 'Evaluation Engine', status: 'Healthy' },
    { name: 'Reporting Engine', status: 'Healthy' },
  ],
  adapters: [
    { name: 'Ollama Local', status: 'Active', type: 'Local' },
    { name: 'API Gateway', status: 'Active', type: 'Gateway' },
  ],
  metrics: [
    { label: 'Benchmarks', value: '128' },
    { label: 'Evaluations', value: '42' },
    { label: 'Models', value: '18' },
    { label: 'Avg Runtime', value: '14.8 s' },
  ],
  metadata: [
    { label: 'Engine', value: 'Atlas v0.3' },
    { label: 'Schema', value: 'Evaluation v2.1' },
  ],
};

export function AtlasRuntime() {
  return (
    <motion.section variants={fadeUp} initial="hidden" animate="visible" className="space-y-4">
      <h2 className="text-xs tracking-[0.2em] uppercase text-white/20">
        Atlas Runtime
      </h2>

      <Card className="!p-5 space-y-5">
        {/* Subsystems Health */}
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-white/30">
            <Server className="w-3.5 h-3.5 text-accent/70" />
            <span>Engine Health</span>
          </div>
          <div className="grid grid-cols-2 gap-2">
            {RUNTIME_DATA.engines.map((eng) => (
              <div
                key={eng.name}
                className="p-2.5 rounded-xl border border-white/[0.03] bg-white/[0.01] flex items-center justify-between"
              >
                <span className="text-xs text-white/70">{eng.name}</span>
                <div className="flex items-center gap-1.5 shrink-0 ml-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  <span className="text-[10px] text-emerald-400 font-medium">{eng.status}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="h-px bg-white/[0.06]" />

        {/* Execution Adapters */}
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-white/30">
            <Cpu className="w-3.5 h-3.5 text-accent/70" />
            <span>Execution Adapters</span>
          </div>
          <div className="space-y-2">
            {RUNTIME_DATA.adapters.map((ad) => (
              <div
                key={ad.name}
                className="px-3 py-2 rounded-xl border border-white/[0.03] bg-white/[0.01] flex items-center justify-between"
              >
                <div className="flex flex-col">
                  <span className="text-xs font-medium text-white/80">{ad.name}</span>
                  <span className="text-[10px] text-white/25 mt-0.5">{ad.type}</span>
                </div>
                <span className="text-[10px] px-2 py-0.5 rounded-full border border-emerald-500/20 text-emerald-400 bg-emerald-500/5 font-medium">
                  {ad.status}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="h-px bg-white/[0.06]" />

        {/* Runtime Metrics */}
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-white/30">
            <Activity className="w-3.5 h-3.5 text-accent/70" />
            <span>Runtime Metrics</span>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {RUNTIME_DATA.metrics.map((m) => (
              <div
                key={m.label}
                className="p-3 rounded-xl border border-white/[0.03] bg-white/[0.01]/50 text-center flex flex-col justify-center"
              >
                <span className="text-lg font-semibold text-white tracking-tight leading-none">{m.value}</span>
                <span className="text-[10px] text-white/25 mt-1">{m.label}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="h-px bg-white/[0.06]" />

        {/* Engine Version metadata */}
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-white/30">
            <Terminal className="w-3.5 h-3.5 text-accent/70" />
            <span>Engine Version</span>
          </div>
          <div className="grid grid-cols-2 gap-4">
            {RUNTIME_DATA.metadata.map((meta) => (
              <div key={meta.label} className="flex flex-col">
                <span className="text-[10px] text-white/20 uppercase tracking-wider">{meta.label}</span>
                <span className="text-xs font-mono text-white/70 mt-1">{meta.value}</span>
              </div>
            ))}
          </div>
        </div>
      </Card>
    </motion.section>
  );
}
