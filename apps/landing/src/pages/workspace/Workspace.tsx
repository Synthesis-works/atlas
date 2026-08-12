import { useEffect, useState } from 'react';
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
import { WorkspaceStatusBoard } from '@/components/workspace/WorkspaceStatusBoard';
import {
  getDashboardSummary,
  type DashboardSummaryData,
} from '@/features/dashboard/services/dashboardService';

const healthData = createHeatmapData(
  ['Node 01', 'Node 02', 'Node 03', 'Node 04'],
  ['00', '04', '08', '12', '16', '20'],
  (r, c) => (r.charCodeAt(5) * c.charCodeAt(0) * 7) % 100,
);

const stagesData = createTimelineStages('Running');

export default function Workspace() {
  const [dashboard, setDashboard] = useState<DashboardSummaryData | null>(null);

  useEffect(() => {
    let isMounted = true;
    getDashboardSummary().then((res) => {
      if (isMounted && res) {
        setDashboard(res);
      }
    });
    return () => {
      isMounted = false;
    };
  }, []);

  const activeCount = dashboard?.summary.active_runs_count ?? 0;
  const modelsCount = dashboard?.hierarchy.models ?? 15;

  const hierarchyData = [
    { label: 'Models', value: dashboard?.hierarchy.models ?? 15 },
    { label: 'Benchmarks', value: dashboard?.hierarchy.benchmarks ?? 20 },
    { label: 'Datasets', value: dashboard?.hierarchy.datasets ?? 10 },
    { label: 'Evaluations', value: dashboard?.hierarchy.evaluations ?? 31 },
    { label: 'Reports', value: dashboard?.hierarchy.reports ?? 36 },
  ];


  const totalModules = hierarchyData.reduce((acc, curr) => acc + curr.value, 0);

  return (
    <div className="w-full text-white">
      <WorkspacePage>
        <WorkspaceHero>
          <div className="flex flex-col xl:flex-row gap-6 items-start w-full">
            <div className="flex-1 flex flex-col min-w-0 w-full gap-4">
              <WelcomeStrip activeCount={activeCount} />
              <WorkspaceStatusBoard 
                activeBenchmarkCount={activeCount} 
                modelsCount={modelsCount} 
                duration={1.2}
                className="my-0 w-full justify-start max-w-full"
              />
            </div>
            <div className="w-full xl:w-[400px] shrink-0">
              <RecentActivity events={dashboard?.activity} />
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
            <ActiveEvaluations items={dashboard?.active_executions} />
            <div className="flex flex-col gap-6 flex-1 min-h-0">
              <HeatmapCard
                title="System Health Matrix"
                subtitle="CPU and memory utilization across cluster worker nodes"
                badge="Live"
                data={healthData}
              />
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start w-full">
                <div className="min-w-0">
                  <AtlasRuntime
                    engineStatus={dashboard?.runtime.engine_status}
                    totalBenchmarks={dashboard?.runtime.total_benchmarks}
                    totalEvaluations={dashboard?.runtime.total_evaluations}
                    totalModels={dashboard?.runtime.total_models}
                    avgRuntimeSec={dashboard?.runtime.avg_runtime_sec}
                  />
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
              centerLabel={`${totalModules} Items`}
              showLegend={true}
              hoverEffect="grow"
              className="liquid-glass-card rounded-2xl p-5 border border-white/10 w-full"
            />
            <CapabilitySnapshot capability={dashboard?.capability} />
          </aside>
        </WorkspaceOperations>
      </WorkspacePage>
    </div>
  );
}
