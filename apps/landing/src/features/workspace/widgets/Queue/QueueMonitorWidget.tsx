import { useWorkspaceStore } from '@/store/workspaceStore';
import { LiquidGlassCard } from '@/design/glass/LiquidGlassCard';
import { Minus, X, RefreshCw } from 'lucide-react';

export function QueueMonitorWidget() {
  const { widgetLayouts, updateWidgetLayout, queue } = useWorkspaceStore();
  const state = widgetLayouts.queue;

  if (!state || !state.visible) return null;

  // Filter running or queued jobs
  const runningJobs = queue.filter((job) => job.status === 'Running' || job.status === 'Queued');
  const activeJob = runningJobs[0];

  const handlePositionChange = (x: number, y: number) => {
    updateWidgetLayout('queue', { x, y });
  };

  const handleDragStateChange = (dragging: boolean) => {
    updateWidgetLayout('queue', { dragging });
  };

  const handleToggleCollapse = () => {
    updateWidgetLayout('queue', { collapsed: !state.collapsed });
  };

  const handleClose = () => {
    updateWidgetLayout('queue', { visible: false });
  };

  return (
    <LiquidGlassCard
      id="queue"
      initialX={state.x}
      initialY={state.y}
      onPositionChange={handlePositionChange}
      onDragStateChange={handleDragStateChange}
      className="w-[300px] flex flex-col z-[200] rounded-3xl"
      style={{
        height: state.collapsed ? 'auto' : '200px',
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.06] select-none">
        <div className="flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-emerald-500/10 border border-emerald-500/20">
            <RefreshCw className="h-3.5 w-3.5 text-emerald-400 animate-spin" style={{ animationDuration: '6s' }} />
          </div>
          <h3 className="text-xs font-semibold text-white">Queue Monitor</h3>
        </div>

        <div className="flex items-center gap-1.5">
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
        <div className="p-4 flex-1 flex flex-col justify-between">
          {activeJob ? (
            <div className="space-y-3">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-semibold text-white truncate max-w-[180px]">
                    {activeJob.model}
                  </p>
                  <p className="text-[10px] text-white/40 mt-0.5">
                    Benchmark: {activeJob.benchmarkName}
                  </p>
                </div>
                <span className="text-[9px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 uppercase tracking-wider font-semibold">
                  {activeJob.status}
                </span>
              </div>

              {activeJob.status === 'Running' && (
                <div className="space-y-1.5">
                  <div className="h-1 bg-white/[0.06] rounded-full overflow-hidden">
                    <div
                      className="h-full bg-emerald-400/80 rounded-full transition-all duration-500"
                      style={{ width: `${activeJob.progress}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-[9px] text-white/25">
                    <span>{activeJob.progress}% evaluated</span>
                    <span>Job ID: {activeJob.id}</span>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-4 text-center">
              <p className="text-xs text-white/40 font-medium">No active jobs in queue</p>
              <p className="text-[9px] text-white/20 mt-0.5">Trigger a benchmark from Registry.</p>
            </div>
          )}

          {runningJobs.length > 1 && (
            <div className="text-[9px] text-white/35 pt-2 border-t border-white/[0.04] mt-auto">
              {runningJobs.length - 1} more run{runningJobs.length > 2 ? 's' : ''} in queue.
            </div>
          )}
        </div>
      )}
    </LiquidGlassCard>
  );
}
