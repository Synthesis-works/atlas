import React, { useRef, useEffect } from 'react';
import { Terminal as TerminalIcon, Copy, Check } from 'lucide-react';
import { cn } from '@/lib/utils';

interface TerminalProps {
  title?: string;
  logs: string[];
  autoScroll?: boolean;
  className?: string;
}

export const Terminal: React.FC<TerminalProps> = ({
  title = 'Atlas Execution Console',
  logs,
  autoScroll = true,
  className,
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);
  const [copied, setCopied] = React.useState(false);

  useEffect(() => {
    if (autoScroll) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll]);

  const handleCopy = () => {
    navigator.clipboard.writeText(logs.join('\n'));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={cn('rounded-xl border border-white/10 bg-neutral-950 overflow-hidden font-mono text-xs shadow-2xl', className)}>
      {/* Console Header */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-white/[0.03] border-b border-white/5 select-none">
        <div className="flex items-center gap-2">
          <div className="flex gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500/80 inline-block" />
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500/80 inline-block" />
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/80 inline-block" />
          </div>
          <span className="text-[11px] text-white/50 font-medium flex items-center gap-1.5 ml-2">
            <TerminalIcon className="w-3.5 h-3.5 text-accent/70" />
            {title}
          </span>
        </div>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 text-[10px] text-white/30 hover:text-white transition-colors"
        >
          {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>

      {/* Console Output Body */}
      <div className="p-4 max-h-56 overflow-y-auto space-y-1.5 text-white/70">
        {logs.length === 0 ? (
          <div className="text-white/20 italic">No execution logs streaming.</div>
        ) : (
          logs.map((log, idx) => (
            <div key={idx} className="flex items-start gap-3 hover:bg-white/[0.02] py-0.5 px-1 rounded">
              <span className="text-white/20 select-none text-[10px] w-6 shrink-0 font-mono text-right">
                {idx + 1}
              </span>
              <span className="text-emerald-400/90 shrink-0">$</span>
              <span className="break-all">{log}</span>
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
};

export default Terminal;
