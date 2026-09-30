import { useEffect, useState } from 'react';
import { WelcomeStrip } from './components/WelcomeStrip';
import { WorkspaceStatusBoard } from '@/components/workspace/WorkspaceStatusBoard';
import {
  getDashboardSummary,
  type DashboardSummaryData,
} from '@/features/dashboard/services/dashboardService';
import { WorkspacePage, WorkspaceHero } from '@/components/layout/WorkspacePage';

export default function Home() {
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
          </div>
        </WorkspaceHero>
      </WorkspacePage>
    </div>
  );
}
