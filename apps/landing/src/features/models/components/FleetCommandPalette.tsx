import React, { useEffect, useState } from 'react';
import { Search, Terminal, RotateCcw, Cpu, Play, Download, Sliders, ShieldAlert, Sparkles, Activity } from 'lucide-react';
import { useModelsStore } from '../store/modelsStore';

const COMMANDS = [
  { id: 'deploy-claude', label: 'Deploy Claude 3.5 Sonnet to us-east-1', category: 'Deployment', icon: Play, shortcut: '⌘D' },
  { id: 'restart-llama', label: 'Restart Llama 3.3 70B Endpoint (vLLM Node 02)', category: 'Operation', icon: RotateCcw, shortcut: '⌘R' },
  { id: 'compare-models', label: 'Compare GPT-5 vs Claude 3.5 vs Gemini 2.0', category: 'Intelligence', icon: Sparkles, shortcut: '⌘C' },
  { id: 'open-logs', label: 'Open Live Stream Logs for Active Deployments', category: 'Telemetry', icon: Terminal, shortcut: '⌘L' },
  { id: 'scale-qwen', label: 'Autoscale Qwen 2.5 Replicas (Current: 2 → Target: 4)', category: 'Scaling', icon: Sliders, shortcut: '⌘S' },
  { id: 'rollback-version', label: 'Rollback Gemini 2.0 Flash to v2.3.1 (Stable)', category: 'Safety', icon: ShieldAlert, shortcut: '⌘B' },
  { id: 'export-config', label: 'Export Fleet Helm & Kubernetes Manifests', category: 'Export', icon: Download, shortcut: '⌘E' },
  { id: 'open-telemetry', label: 'Open GPU VRAM Saturation & Latency Dashboard', category: 'Telemetry', icon: Activity, shortcut: '⌘T' },
];

export const FleetCommandPalette: React.FC = () => {
  const { commandPaletteOpen, setCommandPaletteOpen, triggerAction } = useModelsStore();
  const [query, setQuery] = useState('');

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && commandPaletteOpen) {
        setCommandPaletteOpen(false);
      }
    };
    const handleOpen = () => setCommandPaletteOpen(true);
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('open-fleet-commands', handleOpen);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('open-fleet-commands', handleOpen);
    };
  }, [commandPaletteOpen, setCommandPaletteOpen]);

  if (!commandPaletteOpen) return null;

  const filteredCommands = COMMANDS.filter(c =>
    c.label.toLowerCase().includes(query.toLowerCase()) ||
    c.category.toLowerCase().includes(query.toLowerCase())
  );

  const handleSelect = (cmdId: string) => {
    if (cmdId.includes('logs')) triggerAction('logs');
    else if (cmdId.includes('telemetry')) triggerAction('telemetry');
    else triggerAction('inspect');
    setCommandPaletteOpen(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4 bg-black/70 backdrop-blur-md animate-in fade-in duration-200">
      <div className="w-full max-w-xl liquid-glass-card rounded-2xl border border-accent/40 shadow-[0_0_50px_rgba(99,102,241,0.2)] overflow-hidden flex flex-col">
        {/* Search Header */}
        <div className="flex items-center gap-3 px-4 py-3.5 border-b border-white/10 bg-white/[0.02]">
          <Search className="w-4 h-4 text-accent shrink-0" />
          <input
            type="text"
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type a command or search fleet actions… (e.g., 'Deploy', 'Logs', 'Scale')"
            className="w-full bg-transparent text-sm text-white placeholder:text-white/30 outline-none font-mono"
          />
          <kbd className="px-2 py-0.5 rounded text-[10px] font-mono text-white/40 bg-white/5 border border-white/10">ESC</kbd>
        </div>

        {/* Command List */}
        <div className="max-h-[360px] overflow-y-auto p-2 space-y-1 scrollbar-thin scrollbar-thumb-white/10">
          <div className="px-2 py-1 text-[10px] font-mono uppercase tracking-wider text-white/30 font-semibold">
            Fleet Control Commands ({filteredCommands.length})
          </div>
          {filteredCommands.map((cmd) => {
            const Icon = cmd.icon;
            return (
              <button
                key={cmd.id}
                onClick={() => handleSelect(cmd.id)}
                className="w-full flex items-center justify-between px-3 py-2.5 rounded-xl hover:bg-white/10 text-left transition-colors group cursor-pointer"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-7 h-7 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center shrink-0 group-hover:border-accent/40 group-hover:bg-accent/10">
                    <Icon className="w-3.5 h-3.5 text-white/70 group-hover:text-accent" />
                  </div>
                  <div className="min-w-0">
                    <div className="text-xs font-mono text-white/90 group-hover:text-white font-medium truncate">
                      {cmd.label}
                    </div>
                    <div className="text-[10px] font-mono text-white/30">{cmd.category}</div>
                  </div>
                </div>
                <kbd className="px-2 py-0.5 rounded text-[10px] font-mono text-white/40 bg-white/5 border border-white/10 shrink-0">
                  {cmd.shortcut}
                </kbd>
              </button>
            );
          })}
        </div>

        {/* Footer */}
        <div className="px-4 py-2 border-t border-white/5 bg-white/[0.01] flex items-center justify-between text-[10px] font-mono text-white/30">
          <span className="flex items-center gap-1.5">
            <Cpu className="w-3 h-3 text-accent" /> Atlas Fleet Command Palette v2.4
          </span>
          <span>Use ↑ ↓ to navigate · ↵ to select</span>
        </div>
      </div>
    </div>
  );
};
