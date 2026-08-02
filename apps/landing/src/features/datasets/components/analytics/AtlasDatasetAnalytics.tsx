import { AnimatedSection } from '@/components/atlas/motion/AnimatedSection';
import { AtlasInsightCard } from '@/components/atlas/charts/wrappers/AtlasInsightCard';
import { AtlasPieChart } from '@/components/atlas/charts';
import { buildAnalyticsPresentation } from '../../presentation/analytics';
import { OperationalImpactNode, RecommendationNode } from '@/components/atlas/charts/wrappers/AtlasPresentationNodes';

export const AtlasDatasetAnalytics = () => {
  const { distributionInsight, pieSeries, analyticsKpis, impacts } = buildAnalyticsPresentation();

  return (
    <AnimatedSection className="flex flex-col gap-6 mt-12">
      <div className="flex flex-col gap-4">
        <h2 className="text-2xl font-bold text-white tracking-tight">Dataset Analytics</h2>
        <p className="text-sm text-white/50 leading-relaxed max-w-3xl">
          Dataset growth accelerated after ingestion pipeline v4. Largest contributor: Synthetic data imports.
        </p>
        
        {/* KPI Strip */}
        <div className="flex flex-wrap gap-8 items-center border border-white/10 bg-black/40 rounded-xl p-4">
          {analyticsKpis.map(kpi => (
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
          insight={distributionInsight}
          operationalImpactNode={<OperationalImpactNode {...impacts.distribution} />}
          recommendationNode={<RecommendationNode recommendations={distributionInsight.recommendations} />}
        >
          <AtlasPieChart data={pieSeries} centerLabel="Modalities" />
        </AtlasInsightCard>
      </div>

    </AnimatedSection>
  );
};
