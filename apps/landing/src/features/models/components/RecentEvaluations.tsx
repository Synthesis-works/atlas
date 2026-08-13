import { CheckCircle2, XCircle } from 'lucide-react';
import { useModelsStore } from '../store/modelsStore';

export function RecentEvaluations() {
  const { models } = useModelsStore();

  const allHistory = models
    .flatMap(m => m.evaluationHistory.map(e => ({ ...e, modelName: m.name })))
    .sort((a, b) => new Date(b.runAt).getTime() - new Date(a.runAt).getTime())
    .slice(0, 10);

  return (
    <div className="liquid-glass-card rounded-2xl overflow-hidden h-full flex flex-col">
      <div className="px-4 py-3 border-b border-white/[0.05] shrink-0">
        <span className="text-xs text-white/40 font-medium uppercase tracking-wider">Recent Evaluations</span>
      </div>
      <div className="divide-y divide-white/[0.04]">
        {allHistory.map(e => (
          <div key={e.id} className="px-4 py-3 flex items-center gap-3 hover:bg-white/[0.02] transition-colors">
            {e.status === 'completed'
              ? <CheckCircle2 className="w-4 h-4 text-green-400 shrink-0" />
              : <XCircle className="w-4 h-4 text-red-400 shrink-0" />}
            <div className="flex-1 min-w-0">
              <p className="text-sm text-white/70 truncate">
                <span className="text-white/90">{e.modelName}</span>
                {' '}on <span className="text-accent/80">{e.benchmarkName}</span>
              </p>
              <p className="text-xs text-white/25">{e.runAt} · {e.duration}</p>
            </div>
            <span className={`text-sm font-semibold tabular-nums shrink-0 ${
              e.score >= 90 ? 'text-green-400' : e.score >= 75 ? 'text-accent' : 'text-yellow-400'
            }`}>
              {e.score.toFixed(1)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
