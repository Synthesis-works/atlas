import { useEffect, useMemo, useState } from 'react';
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
  TimelineChart,
  createTimelineStages,
} from '@/design/charts';
import { AtlasPieChart } from '@/components/atlas/charts';
import { WorkspaceStatusBoard } from '@/components/workspace/WorkspaceStatusBoard';
import {
  getDashboardSummary,
  type DashboardSummaryData,
} from '@/features/dashboard/services/dashboardService';

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

  // Enrich timeline events with the provenance of their underlying execution (if any).
  // Events that cannot be linked to an execution keep their original content and stay
  // unlabeled (unknown provenance) rather than being guessed.
  const activityEvents = useMemo(() => {
    const byId = new Map((dashboard?.active_executions ?? []).map((ex) => [ex.id, ex]));
    return (dashboard?.activity ?? []).map((event) => {
      const match = /^ex(?:-completed)?-(.+)$/.exec(event.id);
      const run = match ? byId.get(match[1]) : undefined;
      if (!run) return event;
      return { ...event, source: run.source, is_verified: run.is_verified };
    });
  }, [dashboard]);

  // Real workspace hierarchy from the backend; no fabricated fallback counts.
  const hierarchyData = dashboard?.hierarchy
    ? [
        { label: 'Models', value: dashboard.hierarchy.models },
        { label: 'Benchmarks', value: dashboard.hierarchy.benchmarks },
        { label: 'Datasets', value: dashboard.hierarchy.datasets },
        { label: 'Evaluations', value: dashboard.hierarchy.evaluations },
        { label: 'Reports', value: dashboard.hierarchy.reports },
      ]
    : [];

  // Real run-state totals from the backend summary.
  const runStateTiles = dashboard?.summary
    ? [
        { label: 'Active', value: dashboard.summary.active_runs_count },
        { label: 'Queued', value: dashboard.summary.queued_runs_count },
        { label: 'Completed', value: dashboard.summary.completed_runs_count },
        { label: 'Failed', value: dashboard.summary.failed_runs_count },
      ]
    : null;

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
                modelsCount={dashboard?.hierarchy.models}
                duration={1.2}
                className="my-0 w-full justify-start max-w-full"
              />
            </div>
            <div className="w-full xl:w-[400px] shrink-0">
              <RecentActivity events={activityEvents} />
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
              <div className="rounded-2xl p-5 border border-white/10 liquid-glass-card space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-semibold text-white tracking-tight">Execution Health</h3>
                    <p className="text-xs text-white/50 mt-0.5">Real run-state totals reported by the backend</p>
                  </div>
                  <span className="text-[10px] font-mono text-white/30">/api/v1/dashboard</span>
                </div>
                {runStateTiles ? (
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                    {runStateTiles.map((tile) => (
                      <div key={tile.label} className="p-3 rounded-xl border border-white/5 bg-white/[0.02]">
                        <span className="text-lg font-semibold text-white tabular-nums">{tile.value}</span>
                        <span className="block text-[10px] text-white/25 mt-0.5 uppercase tracking-wider">{tile.label}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs font-mono text-white/40 py-4 text-center">
                    Execution telemetry not yet available.
                  </p>
                )}
              </div>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start w-full">
                <div className="min-w-0">
                  <AtlasRuntime
                    engineStatus={dashboard?.runtime.engine_status}
                    totalBenchmarks={dashboard?.runtime.total_benchmarks}
                    totalEvaluations={dashboard?.runtime.total_evaluations}
                    totalModels={dashboard?.runtime.total_models}
                    avgRuntimeSec={dashboard?.runtime.avg_runtime_sec}
                    engineVersion={dashboard?.version}
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
              centerLabel={totalModules > 0 ? `${totalModules} Items` : 'No Hierarchy'}
              emptyMessage="No workspace hierarchy yet"
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
