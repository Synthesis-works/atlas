import { useWorkspaceStore } from '@/store/workspaceStore';
import { LiquidGlassCard } from '@/design/glass/LiquidGlassCard';
import { Editor } from './Editor';
import { FileText, Minus, X } from 'lucide-react';

export function NotesWidget() {
  const { widgetLayouts, updateWidgetLayout } = useWorkspaceStore();
  const state = widgetLayouts.notes;

  if (!state || !state.visible) return null;

  const handlePositionChange = (x: number, y: number) => {
    updateWidgetLayout('notes', { x, y });
  };

  const handleDragStateChange = (dragging: boolean) => {
    updateWidgetLayout('notes', { dragging });
  };

  const handleToggleCollapse = () => {
    updateWidgetLayout('notes', { collapsed: !state.collapsed });
  };

  const handleClose = () => {
    updateWidgetLayout('notes', { visible: false });
  };

  return (
    <LiquidGlassCard
      id="notes"
      initialX={state.x}
      initialY={state.y}
      onPositionChange={handlePositionChange}
      onDragStateChange={handleDragStateChange}
      className="w-[300px] flex flex-col z-[200] rounded-3xl"
      style={{
        height: state.collapsed ? 'auto' : '240px',
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.06] select-none">
        <div className="flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-indigo-500/10 border border-indigo-500/20">
            <FileText className="h-3.5 w-3.5 text-indigo-400" />
          </div>
          <h3 className="text-xs font-semibold text-white">Evaluation Notes</h3>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            onClick={handleToggleCollapse}
            className="p-1 rounded-md text-white/40 hover:text-white/80 hover:bg-white/[0.04] transition-colors cursor-pointer"
          >
            <Minus className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={handleClose}
            className="p-1 rounded-md text-white/40 hover:text-red-400 hover:bg-red-500/10 transition-colors cursor-pointer"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {!state.collapsed && <Editor />}
    </LiquidGlassCard>
  );
}
