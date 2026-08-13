import { Cpu, Activity, Archive, Star, Server, TrendingUp, Clock, DollarSign, Zap, Play } from 'lucide-react';
import { useModelsStore } from '../store/modelsStore';

export function ModelsKPIs() {
  const { models } = useModelsStore();

  const active    = models.filter(m => m.status === 'active').length;
  const archived  = models.filter(m => m.status === 'archived').length;
  const openai    = models.filter(m => m.provider === 'OpenAI').length;
  const local     = models.filter(m => m.deployment.runtime === 'vLLM' || m.deployment.provider === 'Self-hosted').length;
  const deployed  = models.filter(m => m.deployment.status === 'deployed').length;
  const avgScore  = (models.reduce((s, m) => s + m.overallScore, 0) / models.length).toFixed(1);
  const avgLat    = Math.round(models.reduce((s, m) => s + m.latencyMs, 0) / models.length);
  const avgCost   = (models.reduce((s, m) => s + m.cost.averageCostPerCall, 0) / models.length * 1000).toFixed(3);

  const kpis = [
    { icon: Cpu,        label: 'Registered',      value: models.length,   unit: 'models',   color: 'text-white/60' },
    { icon: Activity,   label: 'Active',           value: active,          unit: 'models',   color: 'text-green-400' },
    { icon: Archive,    label: 'Archived',         value: archived,        unit: 'models',   color: 'text-white/30' },
    { icon: Star,       label: 'OpenAI Models',    value: openai,          unit: 'models',   color: 'text-cat-models' },
    { icon: Server,     label: 'Local Models',     value: local,           unit: 'deployed', color: 'text-cat-data' },
    { icon: TrendingUp, label: 'Avg Score',        value: avgScore,        unit: '/ 100',    color: 'text-cat-capabilities' },
    { icon: Clock,      label: 'Avg Latency',      value: avgLat,          unit: 'ms',       color: 'text-cat-benchmarks' },
    { icon: DollarSign, label: 'Avg Cost',         value: `$${avgCost}`,   unit: '/ 1k tok', color: 'text-cat-output' },
    { icon: Zap,        label: 'Deployments',      value: deployed,        unit: 'endpoints',color: 'text-cat-safety' },
    { icon: Play,       label: 'Running Models',   value: deployed,        unit: 'active',   color: 'text-accent' },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4 sm:gap-6">
      {kpis.map((k) => (
        <div
          key={k.label}
          className="liquid-glass-card rounded-xl p-4 sm:p-5 flex flex-col gap-2"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs text-white/30">{k.label}</span>
            <k.icon className={`w-3.5 h-3.5 ${k.color}`} />
          </div>
          <div className="flex items-baseline gap-1.5">
            <span className="text-xl font-semibold text-white tabular-nums">{k.value}</span>
            <span className="text-xs text-white/25">{k.unit}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
