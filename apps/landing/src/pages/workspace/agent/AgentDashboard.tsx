import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { submitAgentTask, fetchAgentProviders } from '@/features/agent/services/agentService';
import type { AgentProviderOption } from '@/features/agent/types';
import { Brain, Play, Settings2, AlertTriangle } from 'lucide-react';
import { useWorkspaceStore } from '@/store/workspaceStore';

export default function AgentDashboard() {
  const navigate = useNavigate();
  const { addNotification, setAgentTasks } = useWorkspaceStore();
  const [goal, setGoal] = useState('');
  const [providers, setProviders] = useState<AgentProviderOption[]>([]);
  const [provider, setProvider] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoadingProviders, setIsLoadingProviders] = useState(true);

  useEffect(() => {
    let cancelled = false;
    fetchAgentProviders().then(({ data }) => {
      if (cancelled) return;
      if (data) {
        const availableProviders = data.filter(p => !p.is_test_only);
        setProviders(availableProviders);
        if (availableProviders.length > 0) {
          setProvider(availableProviders[0].value);
        }
      }
      setIsLoadingProviders(false);
    });
    return () => { cancelled = true; };
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!goal.trim() || isSubmitting || !provider) return;

    setIsSubmitting(true);
    const selectedProvider = providers.find((p) => p.value === provider);
    const { data, error } = await submitAgentTask(goal, provider, selectedProvider?.model);
    setIsSubmitting(false);

    if (error || !data) {
      addNotification('Error', 'Failed to start agent task. Check the backend is running.', 'error');
      return;
    }

    // Backend returns task_id — add to store and navigate
    const taskId = data.task_id;
    setAgentTasks((prev) => {
      const existing = prev.find((t) => t.task_id === taskId);
      const taskEntry =
        existing && (existing.plan?.length ?? 0) >= (data.plan?.length ?? 0) ? existing : data;
      return [taskEntry, ...prev.filter((t) => t.task_id !== taskId)];
    });
    addNotification('Task Started', `Agent task #${taskId.substring(0, 8)} started`, 'success');
    navigate(`/dashboard/agent/run/${taskId}`);
  };

  const selectedProvider = providers.find((p) => p.value === provider);

  return (
    <div className="flex h-full w-full flex-col items-center justify-center p-8 overflow-y-auto">
      <div className="w-full max-w-2xl bg-ink-2/80 backdrop-blur-xl border border-white/10 rounded-2xl p-8 shadow-2xl">
        <div className="flex items-center gap-4 mb-8">
          <div className="w-12 h-12 rounded-xl bg-accent/20 flex items-center justify-center text-accent border border-accent/30">
            <Brain className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Atlas Agent</h1>
            <p className="text-white/50 text-sm mt-1">Autonomous evaluation &amp; benchmarking engine</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-6">
          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium text-white/80">Agent Goal</label>
            <textarea
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              placeholder="e.g., Create a benchmark to test math reasoning with 50 tasks..."
              className="w-full h-32 bg-black/40 border border-white/10 rounded-xl p-4 text-white focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/50 transition-all resize-none"
              required
            />
          </div>

          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium text-white/80 flex items-center gap-2">
              <Settings2 className="w-4 h-4" />
              Agent Reasoning Provider
            </label>
            
            {isLoadingProviders ? (
              <div className="w-full bg-black/40 border border-white/10 rounded-xl p-3 text-white/50 text-sm animate-pulse">
                Loading reasoning providers...
              </div>
            ) : providers.length === 0 ? (
              <div className="w-full bg-red-900/20 border border-red-500/20 rounded-xl p-3 text-red-400 text-sm flex items-center gap-2">
                <AlertTriangle className="w-4 h-4" />
                No reasoning providers available. Please configure the backend.
              </div>
            ) : (
              <>
                <select
                  value={provider}
                  onChange={(e) => setProvider(e.target.value)}
                  className="w-full bg-black/40 border border-white/10 rounded-xl p-3 text-white focus:outline-none focus:border-accent/50"
                >
                  {providers.map((p) => (
                    <option key={p.value} value={p.value}>
                      {p.label}
                    </option>
                  ))}
                </select>
                {selectedProvider && (
                  <p className="text-xs text-white/40">{selectedProvider.description}</p>
                )}
              </>
            )}
          </div>

          <button
            type="submit"
            disabled={isSubmitting || !goal.trim() || providers.length === 0}
            className="w-full h-[52px] flex items-center justify-center gap-2 bg-accent/20 hover:bg-accent/30 disabled:bg-white/5 disabled:text-white/30 text-accent font-medium rounded-xl border border-accent/40 disabled:border-white/10 transition-colors"
          >
            {isSubmitting ? (
              <div className="w-5 h-5 border-2 border-accent border-t-transparent rounded-full animate-spin" />
            ) : (
              <>
                <Play className="w-5 h-5" />
                Start Agent Run
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}


