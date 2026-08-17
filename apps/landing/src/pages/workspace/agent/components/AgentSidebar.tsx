import { useEffect, useState } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import { useWorkspaceStore } from '@/store/workspaceStore';
import { Plus } from 'lucide-react';
import type { AgentTask, AgentTaskStatus } from '@/features/agent/types';
import { taskStatusIcon, taskStatusLabel, taskTone, STATUS_TONES } from '@/features/agent/status';
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

type RunGroup = 'RUNNING' | 'NEEDS_INPUT' | 'COMPLETED' | 'FAILED';

const GROUP_ORDER: RunGroup[] = ['RUNNING', 'NEEDS_INPUT', 'COMPLETED', 'FAILED'];

const GROUP_LABEL: Record<RunGroup, string> = {
  RUNNING: 'Running',
  NEEDS_INPUT: 'Needs Input',
  COMPLETED: 'Completed',
  FAILED: 'Failed',
};

const GROUP_DOT: Record<RunGroup, string> = {
  RUNNING: 'bg-sky-400',
  NEEDS_INPUT: 'bg-amber-400',
  COMPLETED: 'bg-emerald-400',
  FAILED: 'bg-red-400',
};

function groupFor(status: AgentTaskStatus): RunGroup {
  switch (status) {
    case 'PENDING':
    case 'PLANNING':
    case 'EXECUTING':
    case 'REPAIRING':
      return 'RUNNING';
    case 'WAITING_FOR_CLARIFICATION':
    case 'WAITING_FOR_APPROVAL':
      return 'NEEDS_INPUT';
    case 'COMPLETED':
      return 'COMPLETED';
    case 'FAILED':
    case 'CANCELLED':
      return 'FAILED';
    default:
      return 'RUNNING';
  }
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
  // This re-initializes run history from the backend instead of showing stale "No runs yet".
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

  const getStatusIcon = (status: AgentTaskStatus) => {
    const tone = STATUS_TONES[taskTone(status)];
    const icon = taskStatusIcon(status, 'w-4 h-4');
    if (icon === null) return null;
    return (
      <span className={`relative inline-flex ${tone.text}`}>
        {icon}
        {status === 'PENDING' && (
          <span className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-sky-400 animate-pulse" />
        )}
      </span>
    );
  };

  const getStatusLabel = (status: AgentTaskStatus) => {
    const tone = STATUS_TONES[taskTone(status)];
    const isWorking =
      status === 'PLANNING' || status === 'EXECUTING' || status === 'REPAIRING';
    return (
      <span className={`text-[10px] uppercase tracking-wider ${tone.text} font-semibold flex items-center gap-1`}>
        {isWorking && <span className={`w-1.5 h-1.5 rounded-full ${tone.dot} animate-pulse`} />}
        {taskStatusLabel(status)}
      </span>
    );
  };

  const groups = GROUP_ORDER.map((group) => ({
    group,
    tasks: agentTasks.filter((t) => groupFor(t.status) === group).sort(sortByStart),
  })).filter((g) => g.tasks.length > 0);

  const totalRuns = agentTasks.length;

  return (
    <div className="w-64 shrink-0 h-full border-r border-white/10 bg-ink-2/50 backdrop-blur-md flex-col hidden lg:flex">
      <div className="p-4 border-b border-white/10">
        <button
          onClick={handleNewRun}
          className="w-full flex items-center justify-center gap-2 py-2 rounded-lg bg-accent/10 hover:bg-accent/20 border border-accent/20 text-accent transition-colors text-sm font-medium"
        >
          <Plus className="w-4 h-4" />
          <span>New Run</span>
        </button>
      </div>
      <div className="px-4 pt-3 pb-1 flex items-center justify-between">
        <span className="text-[10px] uppercase tracking-wider text-white/30 font-semibold">Run History</span>
        {totalRuns > 0 && (
          <span className="text-[10px] text-white/25 font-mono">{totalRuns}</span>
        )}
      </div>
      <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-3">
        {isLoading ? (
          <div className="text-center p-4 text-xs text-white/40 animate-pulse">Loading runs...</div>
        ) : (
          <>
            {groups.map(({ group, tasks }) => (
              <div key={group} className="flex flex-col gap-1">
                <div className="flex items-center gap-2 px-1 pb-1">
                  <span className={`w-1.5 h-1.5 rounded-full ${GROUP_DOT[group]}`} />
                  <span className="text-[10px] uppercase tracking-wider text-white/30 font-semibold">
                    {GROUP_LABEL[group]}
                  </span>
                  <span className="text-[10px] text-white/20 font-mono">{tasks.length}</span>
                </div>
                {tasks.map((task: AgentTask) => (
                  <NavLink
                    key={task.task_id}
                    to={`/dashboard/agent/run/${task.task_id}`}
                    className={({ isActive }) =>
                      `flex flex-col gap-1 p-3 rounded-lg transition-colors border ${
                        isActive
                          ? 'bg-white/5 border-white/10'
                          : 'bg-transparent border-transparent hover:bg-white/[0.02] hover:border-white/5'
                      }`
                    }
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-mono text-white/40">
                        #{task.task_id.slice(0, 6)}
                      </span>
                      <div className="flex items-center gap-1.5">
                        {formatTime(task.started_at ?? task.created_at) && (
                          <span className="text-[10px] text-white/25">{formatTime(task.started_at ?? task.created_at)}</span>
                        )}
                        {getStatusIcon(task.status)}
                      </div>
                    </div>
                    <div className="text-sm text-white/80 line-clamp-2 mt-1">{task.goal}</div>
                    <div className="flex items-center justify-between">
                      <div>{getStatusLabel(task.status)}</div>
                      {task.primary_provider && (
                        <span className="text-[10px] text-white/25 font-mono">{task.primary_provider}</span>
                      )}
                    </div>
                    {task.run_mode === 'RERUN' && task.source_task_id && (
                      <div className="text-[10px] text-accent/60 font-mono">
                        rerun of #{task.source_task_id.slice(0, 6)}
                      </div>
                    )}
                  </NavLink>
                ))}
              </div>
            ))}
            {groups.length === 0 && (
              <div className="text-center p-4 text-xs text-white/40">No runs yet</div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
