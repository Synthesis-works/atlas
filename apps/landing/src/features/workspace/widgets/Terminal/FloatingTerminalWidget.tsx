import { useRef, useEffect, useState } from 'react';
import { useWorkspaceStore } from '@/store/workspaceStore';
import { LiquidGlassCard } from '@/design/glass/LiquidGlassCard';
import { Terminal, Minus, X, Download, Play, Pause } from 'lucide-react';

export function FloatingTerminalWidget() {
  const { widgetLayouts, updateWidgetLayout, terminalLogs } = useWorkspaceStore();
  const state = widgetLayouts.terminal;
  
  const [paused, setPaused] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!paused && state?.visible && !state?.collapsed) {
      endRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [terminalLogs, paused, state]);

  if (!state || !state.visible) return null;

  const handlePositionChange = (x: number, y: number) => {
    updateWidgetLayout('terminal', { x, y });
  };

  const handleDragStateChange = (dragging: boolean) => {
    updateWidgetLayout('terminal', { dragging });
  };

  const handleToggleCollapse = () => {
    updateWidgetLayout('terminal', { collapsed: !state.collapsed });
  };

  const handleClose = () => {
    updateWidgetLayout('terminal', { visible: false });
  };

  const handleDownload = () => {
    const blob = new Blob([terminalLogs.join('\n')], { type: 'text/plain' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `atlas-terminal-logs-${Date.now()}.txt`;
    a.click();
  };

  return (
    <LiquidGlassCard
      id="terminal"
      initialX={state.x}
      initialY={state.y}
      onPositionChange={handlePositionChange}
      onDragStateChange={handleDragStateChange}
      className="w-[460px] flex flex-col z-[200] rounded-3xl"
      style={{
        height: state.collapsed ? 'auto' : '320px',
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.06] select-none">
        <div className="flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-indigo-500/10 border border-indigo-500/20">
            <Terminal className="h-3.5 w-3.5 text-indigo-400" />
          </div>
          <div>
            <h3 className="text-xs font-semibold text-white">Live Execution Terminal</h3>
            <span className="text-[9px] text-white/35">atlas-runtime — cluster-node-1</span>
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setPaused(!paused)}
            className="p-1 rounded-md text-white/40 hover:text-white/80 hover:bg-white/[0.04] transition-colors cursor-pointer"
            title={paused ? 'Resume logs' : 'Pause logs'}
          >
            {paused ? <Play className="h-3.5 w-3.5 text-emerald-400" /> : <Pause className="h-3.5 w-3.5" />}
          </button>
          <button
            onClick={handleDownload}
            className="p-1 rounded-md text-white/40 hover:text-white/80 hover:bg-white/[0.04] transition-colors cursor-pointer"
            title="Download Logs"
          >
            <Download className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={handleToggleCollapse}
            className="p-1 rounded-md text-white/40 hover:text-white/80 hover:bg-white/[0.04] transition-colors cursor-pointer"
            title="Collapse"
          >
            <Minus className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={handleClose}
            className="p-1 rounded-md text-white/40 hover:text-red-400 hover:bg-red-500/10 transition-colors cursor-pointer"
            title="Close"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {!state.collapsed && (
        <div className="flex-1 min-h-0 flex flex-col bg-black/40">
          <div className="flex-1 overflow-y-auto p-4 space-y-1 font-mono text-[10px] text-white/70 select-text leading-relaxed">
            {terminalLogs.map((log, index) => {
              const isError = log.includes('[Error]');
              const isSystem = log.includes('[System]');
              const colorClass = isError ? 'text-red-400' : isSystem ? 'text-blue-400' : 'text-white/50';
              return (
                <div key={index} className="flex gap-2">
                  <span className="text-white/10 select-none">{String(index + 1).padStart(3, '0')}</span>
                  <span className={colorClass}>{log}</span>
                </div>
              );
            })}
            <div ref={endRef} />
          </div>
          <div className="px-4 py-1 bg-white/[0.02] border-t border-white/[0.04] text-[9px] font-mono text-white/20 select-none">
            {terminalLogs.length} lines · active run
          </div>
        </div>
      )}
    </LiquidGlassCard>
  );
}
