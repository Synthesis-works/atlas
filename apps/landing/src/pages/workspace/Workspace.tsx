import { motion } from 'framer-motion';
import { pageCrossfade } from '@/lib/motion';
import { WelcomeStrip } from './components/WelcomeStrip';
import { ActiveEvaluations } from './components/ActiveEvaluations';
import { RecentActivity } from './components/RecentActivity';
import { CapabilitySnapshot } from './components/CapabilitySnapshot';
import { AtlasRuntime } from './components/AtlasRuntime';
import { QuickActions } from './components/QuickActions';
import {
  WorkspacePage,
  WorkspaceHero,
  WorkspaceAnalytics,
  WorkspaceOperations,
} from '@/components/layout/WorkspacePage';
import { LayoutTokens } from '@/design/layout';
import { cn } from '@/lib/utils';
import {
  HeatmapCard,
  TimelineChart,
  createHeatmapData,
  createTimelineStages,
} from '@/design/charts';
import { AtlasPieChart } from '@/components/atlas/charts';

const healthData = createHeatmapData(
  ['Node 01', 'Node 02', 'Node 03', 'Node 04'],
  ['00', '04', '08', '12', '16', '20'],
  (r, c) => (r.charCodeAt(5) * c.charCodeAt(0) * 7) % 100,
);

const hierarchyData = [
  { label: 'Models', value: 3 },
  { label: 'Benchmarks', value: 3 },
  { label: 'Datasets', value: 4 },
  { label: 'Evaluations', value: 3 },
  { label: 'Reports', value: 2 },
];

const stagesData = createTimelineStages('Running');

import { WorkspaceStatusBoard } from '@/components/workspace/WorkspaceStatusBoard';
import { useEvaluations } from '@/features/evaluations/hooks/useEvaluations';
import { AI_MODELS } from '@/domain/models/types';

export default function Workspace() {
  const { activeEvaluations } = useEvaluations();
  const activeCount = activeEvaluations.filter(
    (e) => e.status === 'Running' || e.status === 'Scoring' || e.status === 'Loading' || e.status === 'Preparing',
  ).length;

  return (
    <motion.div
      variants={pageCrossfade}
      initial="initial"
      animate="animate"
      exit="exit"
    >
      <WorkspacePage>
        <WorkspaceHero>
          <div className="flex flex-col xl:flex-row gap-6 items-start w-full">
            <div className="flex-1 flex flex-col min-w-0 w-full gap-4">
              <WelcomeStrip />
              <WorkspaceStatusBoard 
                activeBenchmarkCount={activeCount} 
                modelsCount={AI_MODELS.length} 
                duration={1.2}
                className="my-0 w-full justify-start max-w-full"
              />
            </div>
            <div className="w-full xl:w-[400px] shrink-0">
              <RecentActivity />
            </div>
          </div>
        </WorkspaceHero>

        {/* Lifecycle Timeline */}
        <WorkspaceAnalytics>
          <TimelineChart title="Active Execution Lifecycle" stages={stagesData} />
        </WorkspaceAnalytics>

        <WorkspaceOperations className={cn(LayoutTokens.grid, LayoutTokens.gridGap, "items-stretch")}>
          {/* Main column */}
          <div className="col-span-4 md:col-span-8 xl:col-span-8 flex flex-col gap-6 min-w-0 h-full justify-between">
            <ActiveEvaluations />
            <div className="flex flex-col gap-6 flex-1 min-h-0">
              <HeatmapCard
                title="System Health Matrix"
                subtitle="CPU and memory utilization across cluster worker nodes"
                badge="Live"
                data={healthData}
              />
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start w-full">
                <div className="min-w-0">
                  <AtlasRuntime />
                </div>
                <div className="min-w-0">
                  <QuickActions />
                </div>
              </div>
            </div>
          </div>

          {/* Sidebar column */}
          <aside className="col-span-4 md:col-span-8 xl:col-span-4 flex flex-col gap-6 min-w-0 h-full">
            <AtlasPieChart
              title="Workspace Hierarchy"
              description="Drillable module navigation tree"
              data={hierarchyData}
              size={240}
              innerRadius={70}
              centerLabel="11 Modules"
              showLegend={true}
              hoverEffect="grow"
              className="liquid-glass-card rounded-2xl p-5 border border-white/10 w-full"
            />
            <CapabilitySnapshot />
          </aside>
        </WorkspaceOperations>
      </WorkspacePage>
    </motion.div>
  );
}
