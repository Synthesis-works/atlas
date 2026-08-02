import { Minus, X, Cpu } from 'lucide-react';

interface HeaderProps {
  collapsed: boolean;
  onToggleCollapse: () => void;
  onClose: () => void;
}

export function Header({ collapsed, onToggleCollapse, onClose }: HeaderProps) {
  return (
    <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.06] select-none">
      <div className="flex items-center gap-2">
        <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-indigo-500/10 border border-indigo-500/20">
          <Cpu className="h-3.5 w-3.5 text-indigo-400" />
        </div>
        <div>
          <h3 className="text-xs font-semibold text-white leading-none">Atlas AI Assistant</h3>
          <span className="text-[9px] text-white/35 leading-none">Active Model: GPT-5</span>
        </div>
      </div>

      <div className="flex items-center gap-1.5">
        <button
          onClick={(e) => {
            e.stopPropagation();
            onToggleCollapse();
          }}
          className="p-1 rounded-md text-white/40 hover:text-white/80 hover:bg-white/[0.04] transition-colors cursor-pointer"
          title={collapsed ? 'Expand' : 'Collapse'}
        >
          <Minus className="h-3.5 w-3.5" />
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onClose();
          }}
          className="p-1 rounded-md text-white/40 hover:text-red-400 hover:bg-red-500/10 transition-colors cursor-pointer"
          title="Close"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}
