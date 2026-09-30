import { useEffect, useState } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import { useWorkspaceStore } from '@/store/workspaceStore';
import { Plus } from 'lucide-react';
import type { AgentTask } from '@/features/agent/types';
import { fetchAgentTasks } from '@/features/agent/services/agentService';

/**
 * Merge backend list entries into the store without regressing richer, fresher state
 * already present (e.g. live polling snapshots that contain more plan/tool_call detail).
 */
function mergeAgentTasks(existing: AgentTask[], incoming: AgentTask[]): AgentTask[] {
  const map = new Map<string, AgentTask>(existing.map((t) => [t.task_id, t]));
  incoming.forEach((incomingTask) => {
    const current = map.get(incomingTask.task_id);
    if (!current) {
      map.set(incomingTask.task_id, incomingTask);
      return;
    }
    const currentScore = (current.plan?.length ?? 0) + (current.tool_calls?.length ?? 0);
    const incomingScore = (incomingTask.plan?.length ?? 0) + (incomingTask.tool_calls?.length ?? 0);
    const currentFresher =
      (current.step_count ?? 0) >= (incomingTask.step_count ?? 0) &&
      currentScore >= incomingScore;
    map.set(incomingTask.task_id, currentFresher ? current : incomingTask);
  });
  return Array.from(map.values());
}

function sortByStart(a: AgentTask, b: AgentTask): number {
  const ta = a.started_at ?? a.created_at ?? '';
  const tb = b.started_at ?? b.created_at ?? '';
  if (ta === tb) return 0;
  if (!ta) return 1;
  if (!tb) return -1;
  return ta < tb ? 1 : -1;
}

function formatTime(iso?: string | null): string {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export function AgentSidebar() {
  const { agentTasks, setAgentTasks } = useWorkspaceStore();
  const navigate = useNavigate();
  const location = useLocation();
  const [isLoading, setIsLoading] = useState(true);

  const isDashboard = location.pathname === '/dashboard/agent';

  // Hydrate sidebar from backend on mount and whenever returning to the dashboard index.
  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    fetchAgentTasks().then(({ data }) => {
      if (cancelled) return;
      if (data) {
        setAgentTasks((prev) => mergeAgentTasks(prev, data));
      }
      setIsLoading(false);
    });
    return () => { cancelled = true; };
  }, [isDashboard, setAgentTasks]);

  const handleNewRun = () => navigate('/dashboard/agent');

  // Only show completed (green) runs — transient states clutter history.
  const completedTasks = agentTasks.filter((t) => t.status === 'COMPLETED').sort(sortByStart);
  const totalRuns = completedTasks.length;

  return (
    <div className="w-64 shrink-0 min-h-0 border-r border-white/5 bg-ink-1 flex-col hidden lg:flex text-sm overflow-hidden">
      <div className="p-3">
        <button
          onClick={handleNewRun}
          className="w-full flex items-center gap-2 py-1.5 px-2 rounded hover:bg-white/5 text-white/80 transition-colors text-sm font-medium"
        >
          <Plus className="w-4 h-4 text-white/50" />
          <span>New Run</span>
        </button>
      </div>
      <div className="px-5 pt-4 pb-2 flex items-center justify-between">
        <span className="text-xs text-white/40 font-medium">Completed Runs</span>
        {totalRuns > 0 && (
          <span className="text-xs text-white/30">{totalRuns}</span>
        )}
      </div>
      <div className="flex-1 overflow-y-auto px-2 pb-3 flex flex-col gap-0.5">
        {isLoading ? (
          <div className="text-center p-4 text-xs text-white/40 animate-pulse">Loading runs...</div>
        ) : (
          <>
            {completedTasks.map((task: AgentTask) => (
              <NavLink
                key={task.task_id}
                to={`/dashboard/agent/run/${task.task_id}`}
                className={({ isActive }) =>
                  `flex flex-col gap-1 px-3 py-2 rounded transition-colors ${
                    isActive
                      ? 'bg-white/10 text-white'
                      : 'text-white/60 hover:bg-white/5 hover:text-white/80'
                  }`
                }
              >
                <div className="text-sm truncate pr-2">{task.goal}</div>
                <div className="flex items-center justify-between mt-0.5">
                  <div className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0" />
                    <span className="text-[10px] text-white/40 font-mono">#{task.task_id.slice(0, 4)}</span>
                  </div>
                  {formatTime(task.started_at ?? task.created_at) && (
                    <span className="text-[10px] text-white/30">{formatTime(task.started_at ?? task.created_at)}</span>
                  )}
                </div>
              </NavLink>
            ))}
            {completedTasks.length === 0 && (
              <div className="text-center p-4 text-xs text-white/40">No completed runs yet</div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
