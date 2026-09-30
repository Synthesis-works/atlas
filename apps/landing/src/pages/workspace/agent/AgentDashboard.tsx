import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { submitAgentTask, fetchAgentProviders } from '@/features/agent/services/agentService';
import type { AgentProviderOption } from '@/features/agent/types';
import { Brain, Play, Settings2, AlertTriangle, ChevronDown } from 'lucide-react';
import { useWorkspaceStore } from '@/store/workspaceStore';

export default function AgentDashboard() {
  const navigate = useNavigate();
  const { addNotification, setAgentTasks } = useWorkspaceStore();
  const [goal, setGoal] = useState('');
  const [providers, setProviders] = useState<AgentProviderOption[]>([]);
  const [provider, setProvider] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoadingProviders, setIsLoadingProviders] = useState(true);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);

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
    <div className="flex h-full w-full flex-col bg-[#0A0A0A] relative overflow-hidden">
      {/* Background decoration - massive centered glow */}
      <div className="absolute top-[-20%] left-1/2 -translate-x-1/2 w-[1000px] h-[800px] opacity-20 pointer-events-none">
        <div className="absolute inset-0 bg-accent rounded-full blur-[120px]" />
      </div>

      {/* Top Header */}
      <div className="flex-none px-6 py-4 border-b border-white/5 flex items-center bg-transparent relative z-10">
        <h1 className="text-sm font-semibold text-white/90 flex items-center gap-2">
          <Brain className="w-4 h-4 text-accent" />
          Atlas Agent
        </h1>
      </div>

      {/* Main content - Centered Prompt Interface */}
      <div className="flex-1 flex flex-col items-center justify-center p-8 relative z-10 pb-32">
         
         <div className="text-center w-full max-w-3xl mb-8">
            <div className="w-16 h-16 mx-auto mb-8 relative">
              <div className="absolute inset-0 bg-accent/30 rounded-2xl blur-xl animate-pulse" />
              <div className="relative w-full h-full bg-black/50 backdrop-blur text-accent rounded-2xl flex items-center justify-center border border-accent/20 shadow-2xl">
                 <Brain className="w-8 h-8" />
              </div>
            </div>
            <h2 className="text-4xl sm:text-5xl font-semibold mb-4 bg-gradient-to-br from-white via-white to-white/30 bg-clip-text text-transparent tracking-tight">
              What should we benchmark?
            </h2>
            <p className="text-white/40 text-base">
              Describe your goal. The autonomous agent will plan, execute, and generate a comprehensive evaluation report.
            </p>
         </div>

         {/* The Chat-like Input Box */}
         <div className="w-full max-w-3xl">
          <form onSubmit={handleSubmit} className="flex flex-col gap-3">
            <div className="relative flex flex-col bg-ink-2/60 backdrop-blur-xl border border-white/10 rounded-2xl p-2 focus-within:border-accent/50 focus-within:ring-2 focus-within:ring-accent/20 transition-all shadow-2xl">
              <textarea
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSubmit(e);
                  }
                }}
                placeholder="e.g. Create a benchmark for math reasoning with 5 questions..."
                className="w-full bg-transparent border-none text-white text-[15px] p-4 focus:outline-none resize-none max-h-64 min-h-[80px] placeholder:text-white/20"
                rows={Math.min(6, Math.max(2, goal.split('\n').length))}
                required
              />
              
              <div className="flex items-center justify-between px-3 pb-2 pt-1">
                {/* Left controls */}
                <div className="flex items-center gap-2">
                  {isLoadingProviders ? (
                    <div className="text-xs text-white/30 animate-pulse">Loading providers...</div>
                  ) : providers.length === 0 ? (
                    <div className="text-xs text-red-400 flex items-center gap-1">
                      <AlertTriangle className="w-3 h-3" /> No providers configured
                    </div>
                  ) : (
                    <div className="relative">
                      <div
                        onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-black/40 hover:bg-black/60 border border-white/5 cursor-pointer transition-colors text-xs text-white/60 hover:text-white/90"
                      >
                        <Settings2 className="w-3.5 h-3.5 text-accent/70" />
                        {selectedProvider?.label || 'Select provider'}
                        <ChevronDown className="w-3 h-3 opacity-50 ml-1" />
                      </div>
                      {isDropdownOpen && (
                        <>
                          <div className="fixed inset-0 z-10" onClick={() => setIsDropdownOpen(false)} />
                          <div className="absolute bottom-full left-0 mb-2 w-56 bg-ink-1 border border-white/10 rounded-xl overflow-hidden z-20 shadow-2xl">
                            {providers.map((p) => (
                              <div
                                key={p.value}
                                onClick={() => {
                                  setProvider(p.value);
                                  setIsDropdownOpen(false);
                                }}
                                className={`p-3 text-xs cursor-pointer transition-colors flex items-center justify-between ${
                                  provider === p.value ? 'bg-accent/10 text-accent font-medium' : 'text-white/70 hover:bg-white/5'
                                }`}
                              >
                                {p.label}
                              </div>
                            ))}
                          </div>
                        </>
                      )}
                    </div>
                  )}
                </div>

                {/* Right controls */}
                <div className="flex items-center gap-3">
                  <span className="text-[10px] text-white/20 font-medium tracking-wide hidden sm:block uppercase">
                    Shift + Return for new line
                  </span>
                  <button
                    type="submit"
                    disabled={isSubmitting || !goal.trim() || providers.length === 0}
                    className="w-10 h-10 flex items-center justify-center rounded-xl bg-accent hover:bg-accent-hover disabled:bg-white/5 disabled:text-white/20 text-white transition-all disabled:shadow-none shadow-[0_0_20px_rgba(99,102,241,0.4)]"
                  >
                    {isSubmitting ? (
                      <div className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                    ) : (
                      <Play className="w-4 h-4 translate-x-[1px]" fill="currentColor" />
                    )}
                  </button>
                </div>
              </div>
            </div>
          </form>
         </div>
      </div>
    </div>
  );
}
