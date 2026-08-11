import { Cpu } from 'lucide-react';

export const AtlasRuntimeWidget: React.FC = () => {
  return (
    <div className="fixed bottom-6 right-6 z-40 p-3.5 rounded-2xl border border-white/10 bg-neutral-950/90 backdrop-blur-xl shadow-2xl space-y-2 text-xs font-mono select-none">
      <div className="flex items-center justify-between gap-4 border-b border-white/5 pb-2">
        <div className="flex items-center gap-2">
          <Cpu className="w-4 h-4 text-accent animate-pulse" />
          <span className="font-bold text-white tracking-wider">Atlas Runtime</span>
        </div>
        <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          Connected
        </span>
      </div>

      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[11px] text-white/50">
        <div className="flex items-center justify-between gap-2">
          <span>API:</span>
          <span className="text-emerald-400 font-medium">Connected</span>
        </div>
        <div className="flex items-center justify-between gap-2">
          <span>Engine:</span>
          <span className="text-emerald-400 font-medium">Ready</span>
        </div>
        <div className="flex items-center justify-between gap-2">
          <span>ML Server:</span>
          <span className="text-emerald-400 font-medium">Connected</span>
        </div>
        <div className="flex items-center justify-between gap-2">
          <span>Queue:</span>
          <span className="text-emerald-400 font-medium">Healthy</span>
        </div>
      </div>
    </div>
  );
};

export default AtlasRuntimeWidget;
