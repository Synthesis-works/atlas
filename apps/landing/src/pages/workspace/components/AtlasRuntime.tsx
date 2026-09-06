import { motion } from 'framer-motion';
import { fadeUp } from '@/lib/motion';
import { Card } from '@/design/primitives';
import { Cpu, Server, Activity, Terminal } from 'lucide-react';

export interface RuntimeMetricsProps {
  engineStatus?: string;
  totalBenchmarks?: number;
  totalEvaluations?: number;
  totalModels?: number;
  avgRuntimeSec?: number;
  engineVersion?: string;
}

function statusDot(status?: string): string {
  const s = (status || '').toLowerCase();
  if (s.includes('health') || s === 'healthy' || s === 'ok') return 'bg-emerald-500';
  if (s.includes('degrad') || s.includes('warn')) return 'bg-amber-400';
  if (s) return 'bg-white/40';
  return 'bg-white/20';
}

export function AtlasRuntime({
  engineStatus,
  totalBenchmarks,
  totalEvaluations,
  totalModels,
  avgRuntimeSec,
  engineVersion,
}: RuntimeMetricsProps) {
  const metrics = [
    { label: 'Benchmarks', value: totalBenchmarks != null ? String(totalBenchmarks) : '—' },
    { label: 'Evaluations', value: totalEvaluations != null ? String(totalEvaluations) : '—' },
    { label: 'Models', value: totalModels != null ? String(totalModels) : '—' },
    { label: 'Avg Runtime', value: avgRuntimeSec != null ? `${avgRuntimeSec.toFixed(1)} s` : '—' },
  ];

  return (
    <motion.section variants={fadeUp} initial="hidden" animate="visible" className="space-y-4">
      <h2 className="text-xs tracking-[0.2em] uppercase text-white/20">Atlas Runtime</h2>

      <Card className="!p-5 space-y-5">
        {/* Subsystems Health */}
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-white/30">
            <Server className="w-3.5 h-3.5 text-accent/70" />
            <span>Engine Health</span>
          </div>
          <div className="p-2.5 rounded-xl border border-white/[0.03] bg-white/[0.01] flex items-center justify-between">
            <span className="text-xs text-white/70">Atlas Engine</span>
            <div className="flex items-center gap-1.5 shrink-0 ml-2">
              <div className={`w-1.5 h-1.5 rounded-full ${statusDot(engineStatus)}`} />
              <span className="text-[10px] text-white/50 font-medium">{engineStatus || '—'}</span>
            </div>
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
            {metrics.map((m) => (
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
            <Cpu className="w-3.5 h-3.5 text-accent/70" />
            <span>Engine Version</span>
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-[10px] text-white/20 uppercase tracking-wider">Version</span>
            <span className="text-xs font-mono text-white/70 mt-1">{engineVersion ? `Atlas v${engineVersion}` : '—'}</span>
          </div>
        </div>

        <div className="h-px bg-white/[0.06]" />

        {/* Execution Adapters (registration only, no health claims) */}
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-white/30">
            <Terminal className="w-3.5 h-3.5 text-accent/70" />
            <span>Execution Adapters</span>
          </div>
          <div className="space-y-2">
            {['Ollama Local', 'API Gateway'].map((ad) => (
              <div
                key={ad}
                className="px-3 py-2 rounded-xl border border-white/[0.03] bg-white/[0.01] flex items-center justify-between"
              >
                <span className="text-xs font-medium text-white/80">{ad}</span>
                <span className="text-[10px] px-2 py-0.5 rounded-full border border-white/10 text-white/40 bg-white/5 font-medium">
                  Registered
                </span>
              </div>
            ))}
          </div>
        </div>
      </Card>
    </motion.section>
  );
}

export default AtlasRuntime;