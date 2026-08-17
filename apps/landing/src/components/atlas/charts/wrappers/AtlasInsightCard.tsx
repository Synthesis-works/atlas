import type { ReactNode } from 'react';
import type { AtlasInsight } from '@/domain/intelligence/types';
import { AnimatedCard } from '@/components/atlas/motion/AnimatedCard';
import { CheckCircle2, AlertTriangle, Info } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface AtlasInsightCardProps {
  insight?: AtlasInsight;
  title?: string;
  children: ReactNode;
  operationalImpactNode?: ReactNode;
  recommendationNode?: ReactNode;
  className?: string;
}

export function AtlasInsightCard({ insight, title, children, operationalImpactNode, recommendationNode, className }: AtlasInsightCardProps) {
  return (
    <AnimatedCard className={cn("pt-6 px-6 pb-4 border border-white/10 bg-black/40 rounded-2xl flex flex-col gap-5", className)}>
      
      {/* 1. Primary Decision */}
      <header className="flex flex-col gap-1">
        <h3 className="text-lg font-medium text-white tracking-tight">
          {insight ? insight.title : title}
        </h3>
      </header>

      {/* 2. Primary Metric */}
      {insight && (
        <div className="flex items-end gap-3">
          <div className="flex flex-col gap-1">
            <span className="text-4xl font-light tabular-nums tracking-tight text-white">{insight.primaryKpi.value}</span>
            <span className="text-xs text-white/50">{insight.primaryKpi.label}</span>
          </div>
          {insight.primaryKpi.trend && (
            <span className="text-sm text-accent mb-1">{insight.primaryKpi.trend}</span>
          )}
        </div>
      )}

      {/* 3. Supporting Visualization */}
      <div className="flex flex-col lg:flex-row gap-8 py-2">
        <div className="flex-1 flex flex-col min-h-[200px] w-full relative items-center justify-center">
          {children}
        </div>
        
        {/* Legend next to visualization if present */}
        {insight?.legend && insight.legend.length > 0 && (
          <div className="w-full lg:w-48 flex flex-col gap-3 justify-center border-l border-white/5 pl-6">
            <h4 className="text-[10px] uppercase tracking-wider text-white/30">Legend</h4>
            {insight.legend.map(item => (
              <div key={item.label} className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full" style={{ backgroundColor: item.color }} />
                  <span className="text-xs text-white/80">{item.label}</span>
                </div>
                <div className="flex gap-2 tabular-nums pl-4 items-baseline">
                  <span className="text-sm text-white">{item.value}</span>
                  {/* Since we inject status/trend into legend in presentation, we can render optional string fields here if we extend the type, but standard LegendItem doesn't have status yet. We will map percentage to status for now or add a custom node. */}
                  {item.percentage && <span className="text-xs text-white/50">{item.percentage}</span>}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 4. Operational Insight */}
      {insight && (
        <div className="flex items-start gap-3 pt-4 border-t border-white/5">
          <div className="mt-0.5">
            {insight.priority === 'critical' && <AlertTriangle className="w-4 h-4 text-red-500" />}
            {insight.priority === 'warning' && <AlertTriangle className="w-4 h-4 text-yellow-500" />}
            {insight.priority === 'healthy' && <CheckCircle2 className="w-4 h-4 text-green-500" />}
            {insight.priority === 'info' && <Info className="w-4 h-4 text-blue-500" />}
          </div>
          <div className="flex flex-col gap-1">
            <p className="text-sm font-medium text-white leading-relaxed">{insight.insight}</p>
            {insight.description && (
              <p className="text-xs text-white/50 leading-relaxed">{insight.description}</p>
            )}
          </div>
        </div>
      )}

      {/* 5. Operational Impact */}
      {operationalImpactNode && (
        <div className="pt-2">
          {operationalImpactNode}
        </div>
      )}

      {/* 6. Recommended Action */}
      {recommendationNode && (
        <div className="pt-2">
          {recommendationNode}
        </div>
      )}

      {/* 7. Supporting Metadata */}
      {insight?.metadata && insight.metadata.length > 0 && (
        <footer className="mt-4 pt-4 border-t border-white/5 flex flex-wrap gap-x-8 gap-y-4 items-center">
          {insight.metadata.map(m => (
            <div key={m.label} className="flex flex-col gap-1">
              <span className="text-[10px] text-white/30 uppercase tracking-wider">{m.label}</span>
              <span className="text-xs text-white/70">{m.value}</span>
            </div>
          ))}
          <div className="flex flex-col gap-1 ml-auto text-right">
             <span className="text-[10px] text-white/30 uppercase tracking-wider">Confidence / Source</span>
             <span className="text-xs text-white/50">{insight.confidence}% • {insight.source}</span>
          </div>
        </footer>
      )}

    </AnimatedCard>
  );
}
