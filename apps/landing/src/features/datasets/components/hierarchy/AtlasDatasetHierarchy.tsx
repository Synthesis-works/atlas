import { AnimatedSection } from '@/components/atlas/motion/AnimatedSection';
import { AtlasInsightCard } from '@/components/atlas/charts/wrappers/AtlasInsightCard';
import { AtlasSunburstChart } from '@/components/atlas/charts/wrappers/AtlasSunburstChart';
import { buildHierarchyPresentation } from '../../presentation/hierarchy';
import { OperationalImpactNode, RecommendationNode } from '@/components/atlas/charts/wrappers/AtlasPresentationNodes';

const HierarchyInspector = () => {
  return (
    <div className="flex flex-col gap-6 w-full h-full border-l border-white/5 pl-8">
      <div className="flex flex-col gap-1">
        <h3 className="text-sm font-medium text-white tracking-tight">Workspace Summary</h3>
        <p className="text-xs text-white/50">Root node selected</p>
      </div>

      <div className="flex flex-col gap-5 mt-2">
        <div className="flex flex-col gap-1">
          <span className="text-[10px] text-white/40 uppercase tracking-wider">Total Datasets</span>
          <span className="text-lg text-white tabular-nums">126</span>
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-[10px] text-white/40 uppercase tracking-wider">Storage</span>
          <span className="text-lg text-white tabular-nums">4.2 PB</span>
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-[10px] text-white/40 uppercase tracking-wider">Health</span>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
            <span className="text-lg text-white tabular-nums">92%</span>
          </div>
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-[10px] text-white/40 uppercase tracking-wider">Owner</span>
          <span className="text-sm text-white">Platform Team</span>
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-[10px] text-white/40 uppercase tracking-wider">Last Updated</span>
          <span className="text-sm text-white">2 hours ago</span>
        </div>
      </div>
    </div>
  );
};

export const AtlasDatasetHierarchy = () => {
  const { insight, tree } = buildHierarchyPresentation();

  return (
    <AnimatedSection className="flex flex-col gap-6 mt-12">
      <div className="flex flex-col gap-4">
        <h2 className="text-2xl font-bold text-white tracking-tight">Dataset Hierarchy</h2>
        <p className="text-sm text-white/50 leading-relaxed max-w-3xl">
          Which assets belong to these growing storage clusters?
        </p>
      </div>
      
      <div className="grid grid-cols-1">
        <AtlasInsightCard 
          insight={insight}
          operationalImpactNode={<OperationalImpactNode affected="Synthetic Clusters" businessEffect="Becoming difficult to navigate without strict tagging." urgency="Low" />}
          recommendationNode={<RecommendationNode recommendations={insight.recommendations} />}
        >
          <div className="grid grid-cols-1 lg:grid-cols-10 gap-8 w-full">
            <div className="lg:col-span-7 flex justify-center items-center">
               <AtlasSunburstChart tree={tree} />
            </div>
            <div className="lg:col-span-3">
               <HierarchyInspector />
            </div>
          </div>
        </AtlasInsightCard>
      </div>

    </AnimatedSection>
  );
};
