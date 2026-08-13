import { AssistantWidget } from './Assistant/AssistantWidget';
import { NotesWidget } from './Notes/NotesWidget';
import { FloatingTerminalWidget } from './Terminal/FloatingTerminalWidget';
import { QueueMonitorWidget } from './Queue/QueueMonitorWidget';
import { LayoutPalette } from './Palette/LayoutPalette';
import { useWorkspaceStore } from '@/store/workspaceStore';
import { Sliders } from 'lucide-react';

export function WorkspaceWidgets() {
  const { widgetLayouts, updateWidgetLayout } = useWorkspaceStore();
  const palette = widgetLayouts.palette;

  return (
    <>
      <AssistantWidget />
      <NotesWidget />
      <FloatingTerminalWidget />
      <QueueMonitorWidget />
      <LayoutPalette />

      {/* Floating control toggle to open palette menu */}
      <div className="fixed bottom-24 right-6 z-[200] flex flex-col gap-2 pointer-events-auto">
        <div className="flex flex-col gap-1.5 p-1.5 bg-neutral-950/60 backdrop-blur-md border border-white/[0.08] rounded-xl shadow-lg">
          <button
            onClick={() => updateWidgetLayout('palette', { visible: !palette?.visible })}
            className={`p-2 rounded-lg transition-all cursor-pointer ${
              palette?.visible 
                ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30' 
                : 'text-white/40 hover:text-white/80 hover:bg-white/[0.04] border border-transparent'
            }`}
            title="Open Layout Palette"
          >
            <Sliders className="h-4 w-4" />
          </button>
        </div>
      </div>
    </>
  );
}
