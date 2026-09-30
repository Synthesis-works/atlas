import { useEffect, useState } from 'react';
import { WorkspaceStatusBoard } from '@/components/workspace/WorkspaceStatusBoard';
import {
  getDashboardSummary,
  type DashboardSummaryData,
} from '@/features/dashboard/services/dashboardService';

export default function Home() {
  const [dashboard, setDashboard] = useState<DashboardSummaryData | null>(null);
  const [username, setUsername] = useState('User');

  useEffect(() => {
    const storedUser = localStorage.getItem('atlas_username');
    if (storedUser) {
      setUsername(storedUser);
    }
  }, []);

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
    <div className="w-full min-h-[calc(100vh-4rem)] flex flex-col pt-12 items-center text-white gap-12">
      <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight text-center">
        Welcome <span className="text-accent">{username}</span> to Atlas
      </h1>
      
      <div className="w-full flex justify-center items-center flex-1 pb-16">
        <WorkspaceStatusBoard 
          activeBenchmarkCount={activeCount} 
          modelsCount={dashboard?.hierarchy.models}
          duration={1.2}
          className="my-0 scale-110 md:scale-125 lg:scale-150 origin-center max-w-5xl"
        />
      </div>
    </div>
  );
}
