import { useWorkspaceStore } from '@/store/workspaceStore';
import { LiquidGlassCard } from '@/design/glass/LiquidGlassCard';
import { Sliders, HelpCircle, FileText, Terminal, RefreshCw, Layers } from 'lucide-react';

export function LayoutPalette() {
  const { widgetLayouts, updateWidgetLayout, resetWidgetLayouts } = useWorkspaceStore();
  const state = widgetLayouts.palette;

  if (!state || !state.visible) return null;

  const handlePositionChange = (x: number, y: number) => {
    updateWidgetLayout('palette', { x, y });
  };

  const handleDragStateChange = (dragging: boolean) => {
    updateWidgetLayout('palette', { dragging });
  };

  const toggleWidget = (id: string) => {
    updateWidgetLayout(id, { visible: !widgetLayouts[id]?.visible });
  };

  return (
    <LiquidGlassCard
      id="palette"
      initialX={state.x}
      initialY={state.y}
      onPositionChange={handlePositionChange}
      onDragStateChange={handleDragStateChange}
      className="w-[240px] flex flex-col z-[200] rounded-3xl"
      style={{
        height: 'auto',
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-white/[0.06] select-none">
        <div className="flex items-center gap-1.5">
          <Sliders className="h-3.5 w-3.5 text-indigo-400" />
          <h3 className="text-xs font-semibold text-white">Widget Palette</h3>
        </div>
        <button
          onClick={() => updateWidgetLayout('palette', { visible: false })}
          className="p-1 rounded-md text-white/30 hover:text-white/70 hover:bg-white/[0.04] transition-colors cursor-pointer"
        >
          ✕
        </button>
      </div>

      {/* Grid switches */}
      <div className="p-3 space-y-2">
        <div className="grid grid-cols-2 gap-1.5">
          <button
            onClick={() => toggleWidget('assistant')}
            className={`flex items-center gap-2 p-2 rounded-xl text-[10px] font-medium border transition-all cursor-pointer ${
              widgetLayouts.assistant?.visible
                ? 'bg-indigo-500/10 border-indigo-500/30 text-indigo-300'
                : 'bg-white/[0.02] border-white/[0.04] text-white/40 hover:text-white/60 hover:bg-white/[0.05]'
            }`}
          >
            <HelpCircle className="h-3.5 w-3.5" />
            <span>Assistant</span>
          </button>

          <button
            onClick={() => toggleWidget('notes')}
            className={`flex items-center gap-2 p-2 rounded-xl text-[10px] font-medium border transition-all cursor-pointer ${
              widgetLayouts.notes?.visible
                ? 'bg-indigo-500/10 border-indigo-500/30 text-indigo-300'
                : 'bg-white/[0.02] border-white/[0.04] text-white/40 hover:text-white/60 hover:bg-white/[0.05]'
            }`}
          >
            <FileText className="h-3.5 w-3.5" />
            <span>Notepad</span>
          </button>

          <button
            onClick={() => toggleWidget('terminal')}
            className={`flex items-center gap-2 p-2 rounded-xl text-[10px] font-medium border transition-all cursor-pointer ${
              widgetLayouts.terminal?.visible
                ? 'bg-indigo-500/10 border-indigo-500/30 text-indigo-300'
                : 'bg-white/[0.02] border-white/[0.04] text-white/40 hover:text-white/60 hover:bg-white/[0.05]'
            }`}
          >
            <Terminal className="h-3.5 w-3.5" />
            <span>Terminal</span>
          </button>

          <button
            onClick={() => toggleWidget('queue')}
            className={`flex items-center gap-2 p-2 rounded-xl text-[10px] font-medium border transition-all cursor-pointer ${
              widgetLayouts.queue?.visible
                ? 'bg-indigo-500/10 border-indigo-500/30 text-indigo-300'
                : 'bg-white/[0.02] border-white/[0.04] text-white/40 hover:text-white/60 hover:bg-white/[0.05]'
            }`}
          >
            <Layers className="h-3.5 w-3.5" />
            <span>Queue</span>
          </button>
        </div>

        <button
          onClick={resetWidgetLayouts}
          className="w-full flex items-center justify-center gap-1.5 py-1.5 rounded-xl border border-dashed border-white/10 hover:border-white/20 text-[10px] font-semibold text-white/45 hover:text-white/80 transition-colors cursor-pointer"
        >
          <RefreshCw className="h-3 w-3" />
          <span>Reset Window Layouts</span>
        </button>
      </div>
    </LiquidGlassCard>
  );
}
