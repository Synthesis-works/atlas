import { AnimatedSection } from '@/components/atlas/motion/AnimatedSection';
import { AtlasInsightCard } from '@/components/atlas/charts/wrappers/AtlasInsightCard';
import { AtlasGauge } from '@/components/atlas/charts/wrappers/AtlasGauge';
import { AtlasRingChart, AtlasRadarChart } from '@/components/atlas/charts';
import { buildHealthPresentation } from '../../presentation/health';
import { OperationalImpactNode, RecommendationNode } from '@/components/atlas/charts/wrappers/AtlasPresentationNodes';

export const AtlasDatasetHealth = () => {
  const { readinessInsight, coverageInsight, qualityInsight, gaugeModel, ringSeries, radarMetrics, healthKpis, impacts } = buildHealthPresentation();

  return (
    <AnimatedSection className="flex flex-col gap-6 mt-12">
      <div className="flex flex-col gap-4">
        <h2 className="text-2xl font-bold text-white tracking-tight">Dataset Health</h2>
        
        {/* KPI Strip */}
        <div className="flex flex-wrap gap-8 items-center border border-white/10 bg-black/40 rounded-xl p-4">
          {healthKpis.map(kpi => (
            <div key={kpi.label} className="flex flex-col gap-1">
              <span className="text-[10px] text-white/50 uppercase tracking-wider">{kpi.label}</span>
              <div className="flex items-baseline gap-2">
                <span className="text-xl font-medium tabular-nums text-white tracking-tight">{kpi.value}</span>
                {kpi.trend && <span className="text-xs font-medium text-accent">{kpi.trend}</span>}
                {kpi.status && <span className="text-[10px] uppercase text-white/40">{kpi.status}</span>}
              </div>
            </div>
          ))}
        </div>
      </div>
      
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <AtlasInsightCard 
          insight={readinessInsight}
          operationalImpactNode={<OperationalImpactNode {...impacts.readiness} />}
          recommendationNode={<RecommendationNode recommendations={readinessInsight.recommendations} />}
        >
          <AtlasGauge 
            score={gaugeModel.score} 
            label={gaugeModel.label} 
            metric={{ id: gaugeModel.id, value: gaugeModel.total, label: gaugeModel.label }} 
          />
        </AtlasInsightCard>

        <AtlasInsightCard 
          insight={coverageInsight}
          operationalImpactNode={<OperationalImpactNode {...impacts.coverage} />}
          recommendationNode={<RecommendationNode recommendations={coverageInsight.recommendations} />}
        >
          <AtlasRingChart series={ringSeries} centerLabel="Coverage" />
        </AtlasInsightCard>

        {qualityInsight && (
          <AtlasInsightCard 
            insight={qualityInsight}
            operationalImpactNode={<OperationalImpactNode {...impacts.quality} />}
            recommendationNode={<RecommendationNode recommendations={qualityInsight.recommendations} />}
          >
            <AtlasRadarChart 
              data={[{ id: 'quality-radar', name: 'Dataset Quality', data: radarMetrics.map((m: any) => ({ axis: m.metric, value: m.value })) }]} 
            />
          </AtlasInsightCard>
        )}
      </div>

    </AnimatedSection>
  );
};
