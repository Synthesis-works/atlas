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
    return (
    <div className="flex h-full w-full flex-col bg-ink-1">
      {/* Top Header */}
      <div className="flex-none px-6 py-4 border-b border-white/5 flex items-center bg-ink-2/80 backdrop-blur-md">
        <h1 className="text-sm font-semibold text-white/90 flex items-center gap-2">
          <Brain className="w-4 h-4 text-accent" />
          Atlas Agent
        </h1>
      </div>

      {/* Main empty area */}
      <div className="flex-1 overflow-y-auto flex flex-col items-center justify-center p-8">
         <div className="text-center max-w-lg">
            <div className="w-16 h-16 bg-accent/10 text-accent rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-[0_0_40px_-10px_rgba(99,102,241,0.3)] border border-accent/20">
               <Brain className="w-8 h-8" />
            </div>
            <h2 className="text-2xl font-semibold text-white mb-2">How can I help you benchmark today?</h2>
            <p className="text-white/40 text-sm">
              Describe your goal, and the autonomous agent will plan, execute, and generate a comprehensive evaluation report.
            </p>
         </div>
      </div>

      {/* Bottom Input Area mimicking Antigravity chat input */}
      <div className="flex-none p-6">
        <div className="max-w-4xl mx-auto">
          <form onSubmit={handleSubmit} className="flex flex-col gap-3">
            {/* The Chat-like Input Box */}
            <div className="relative flex items-end bg-black/40 border border-white/10 rounded-2xl p-2 focus-within:border-accent/50 focus-within:ring-1 focus-within:ring-accent/50 transition-all shadow-lg">
              <textarea
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSubmit(e);
                  }
                }}
                placeholder="Ask anything, e.g. Create a benchmark for math reasoning..."
                className="w-full bg-transparent border-none text-white text-sm p-3 focus:outline-none resize-none max-h-48 min-h-[52px]"
                rows={Math.min(5, Math.max(1, goal.split('\n').length))}
                required
              />
              <div className="shrink-0 flex items-center gap-2 px-2 pb-2">
                <button
                  type="submit"
                  disabled={isSubmitting || !goal.trim() || providers.length === 0}
                  className="w-8 h-8 flex items-center justify-center rounded-full bg-accent hover:bg-accent-hover disabled:bg-white/10 disabled:text-white/30 text-white transition-colors"
                >
                  {isSubmitting ? (
                    <div className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                  ) : (
                    <Play className="w-4 h-4 translate-x-[1px]" />
                  )}
                </button>
              </div>
            </div>

            {/* Bottom Controls */}
            <div className="flex items-center justify-between px-2">
              <div className="flex items-center gap-2">
                {isLoadingProviders ? (
                  <div className="text-[10px] text-white/30 animate-pulse">Loading providers...</div>
                ) : providers.length === 0 ? (
                  <div className="text-[10px] text-red-400 flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3" /> No providers configured
                  </div>
                ) : (
                  <div className="relative">
                    <div
                      onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/5 hover:bg-white/10 border border-white/5 cursor-pointer transition-colors text-[11px] text-white/60 hover:text-white/80"
                    >
                      <Settings2 className="w-3 h-3" />
                      {selectedProvider?.label || 'Select provider'}
                      <ChevronDown className="w-3 h-3 opacity-50" />
                    </div>
                    {isDropdownOpen && (
                      <>
                        <div className="fixed inset-0 z-10" onClick={() => setIsDropdownOpen(false)} />
                        <div className="absolute bottom-full left-0 mb-2 w-48 bg-ink-2 border border-white/10 rounded-xl overflow-hidden z-20 shadow-xl shadow-black/50">
                          {providers.map((p) => (
                            <div
                              key={p.value}
                              onClick={() => {
                                setProvider(p.value);
                                setIsDropdownOpen(false);
                              }}
                              className={`p-2.5 text-[11px] cursor-pointer transition-colors ${
                                provider === p.value ? 'bg-accent/20 text-accent' : 'text-white/80 hover:bg-white/5'
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
              <div className="text-[10px] text-white/30">
                Shift + Enter for new line
              </div>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
