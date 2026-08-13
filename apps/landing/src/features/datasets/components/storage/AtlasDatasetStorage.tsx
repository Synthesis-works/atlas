import { AnimatedSection } from '@/components/atlas/motion/AnimatedSection';
import { AtlasInsightCard } from '@/components/atlas/charts/wrappers/AtlasInsightCard';
import { AtlasGauge } from '@/components/atlas/charts/wrappers/AtlasGauge';
import { AtlasLineChart } from '@/components/atlas/charts/wrappers/AtlasLineChart';
import { buildStoragePresentation } from '../../presentation/storage';
import { OperationalImpactNode, RecommendationNode } from '@/components/atlas/charts/wrappers/AtlasPresentationNodes';

export const AtlasDatasetStorage = () => {
  const { capacityInsight, gaugeModel, lineData, lineSeries, storageKpis, impacts } = buildStoragePresentation();

  return (
    <AnimatedSection className="flex flex-col gap-6 mt-12">
      <div className="flex flex-col gap-4">
        <h2 className="text-2xl font-bold text-white tracking-tight">Dataset Storage</h2>
        <p className="text-sm text-white/50 leading-relaxed max-w-3xl">
          Where is the synthetic data stored, and what is the cost implication?
        </p>
        
        {/* KPI Strip */}
        <div className="flex flex-wrap gap-8 items-center border border-white/10 bg-black/40 rounded-xl p-4">
          {storageKpis.map(kpi => (
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
          insight={capacityInsight}
          operationalImpactNode={<OperationalImpactNode {...impacts.capacity} />}
          recommendationNode={<RecommendationNode recommendations={capacityInsight.recommendations} />}
        >
          <AtlasGauge 
            score={gaugeModel.score} 
            label={gaugeModel.label} 
            metric={{ id: gaugeModel.id, value: gaugeModel.total, label: gaugeModel.label }} 
          />
        </AtlasInsightCard>

        {/* Keeping a simple insight model for the growth chart for now to satisfy layout */}
        <AtlasInsightCard insight={{
          id: 'storage_growth',
          title: 'Growth Trend',
          description: 'Historical storage utilization over the last 5 months.',
          priority: 'healthy',
          confidence: 100,
          source: 'computed',
          primaryKpi: { value: '18.2 TB', label: 'Current' },
          secondaryKpi: { value: '12.0 TB', label: 'Start of Period', trend: '↑ 18%' },
          insight: 'Storage growth remains linear and predictable.',
          recommendations: [{ priority: 3, text: 'Review retention policies' }],
          metadata: [{ label: 'Observation Period', value: '5 Months' }],
          legend: [{ color: '#3B82F6', label: 'Storage', value: '18.2', percentage: 'TB' }]
        }}
        operationalImpactNode={<OperationalImpactNode affected="Growth Trend" businessEffect="Cloud spend will increase proportionally." urgency="Low" />}
        recommendationNode={<RecommendationNode recommendations={[{ priority: 3, text: 'Review retention policies' }]} />}
        >
          <AtlasLineChart data={lineData} series={lineSeries} />
        </AtlasInsightCard>
      </div>

    </AnimatedSection>
  );
};
