import type { Recommendation } from '@/domain/intelligence/types';

export interface OperationalImpactProps {
  affected: string;
  businessEffect: string;
  urgency: 'High' | 'Medium' | 'Low';
}

export function OperationalImpactNode({ affected, businessEffect, urgency }: OperationalImpactProps) {
  return (
    <div className="flex flex-col gap-2 mt-4 p-4 bg-white/5 border border-white/10 rounded-xl">
      <h4 className="text-[10px] text-white/40 uppercase tracking-wider">Operational Impact</h4>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-2">
        <div className="flex flex-col gap-1">
          <span className="text-xs text-white/50">Affected</span>
          <span className="text-sm font-medium text-white">{affected}</span>
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-xs text-white/50">Business Effect</span>
          <span className="text-sm font-medium text-white">{businessEffect}</span>
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-xs text-white/50">Urgency</span>
          <span className="text-sm font-medium text-white">{urgency}</span>
        </div>
      </div>
    </div>
  );
}

export interface RecommendationNodeProps {
  recommendations: Recommendation[];
}

export function RecommendationNode({ recommendations }: RecommendationNodeProps) {
  const mapSeverity = (priority: number) => {
    switch (priority) {
      case 1: return { label: 'Critical', class: 'text-red-400 bg-red-400/10 border-red-400/20' };
      case 2: return { label: 'Warning', class: 'text-yellow-400 bg-yellow-400/10 border-yellow-400/20' };
      case 3: return { label: 'Suggestion', class: 'text-blue-400 bg-blue-400/10 border-blue-400/20' };
      default: return { label: 'Informational', class: 'text-white/70 bg-white/5 border-white/10' };
    }
  };

  if (!recommendations || recommendations.length === 0) return null;

  return (
    <div className="flex flex-col gap-3 mt-4">
      <h4 className="text-[10px] text-white/40 uppercase tracking-wider">Recommended Action</h4>
      <div className="flex flex-col gap-2">
        {recommendations.map((rec, idx) => {
          const sev = mapSeverity(rec.priority);
          return (
            <div key={idx} className="flex items-start gap-3">
              <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-medium border ${sev.class}`}>
                {sev.label}
              </span>
              <span className="text-sm text-accent hover:text-accent-hover cursor-pointer transition-colors mt-0.5">
                {rec.text}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
