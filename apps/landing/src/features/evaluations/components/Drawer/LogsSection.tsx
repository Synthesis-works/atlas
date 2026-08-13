import React, { useRef, useEffect } from 'react';
import type { EvaluationRun } from '@/domain/evaluations/types';

interface Props { evaluation: EvaluationRun; }

const LEVEL_COLORS: Record<string, string> = {
  '[System]': 'text-blue-400',
  '[Queue]': 'text-indigo-400',
  '[Dataset]': 'text-purple-400',
  '[Model]': 'text-cyan-400',
  '[Executor]': 'text-teal-400',
  '[Progress]': 'text-emerald-400',
  '[Scoring]': 'text-amber-400',
  '[Report]': 'text-violet-400',
  '[Error]': 'text-rose-400',
  '[Worker]': 'text-orange-400',
  '[Metrics]': 'text-yellow-400',
};

function colorize(line: string) {
  const match = Object.keys(LEVEL_COLORS).find(k => line.includes(k));
  return match ? LEVEL_COLORS[match] : 'text-white/50';
}

export const LogsSection: React.FC<Props> = ({ evaluation }) => {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [evaluation.logs]);

  if (evaluation.logs.length === 0) {
    return (
      <div className="p-8 text-center text-xs font-mono text-white/30">
        No logs available for this evaluation.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-semibold text-white">Execution Logs</h4>
        <span className="text-[10px] font-mono text-white/30">{evaluation.logs.length} lines</span>
      </div>
      <div className="bg-black/70 border border-white/5 rounded-xl overflow-hidden">
        <div className="flex items-center gap-2 px-4 py-2 bg-white/5 border-b border-white/5">
          <div className="w-3 h-3 rounded-full bg-rose-400/60" />
          <div className="w-3 h-3 rounded-full bg-amber-400/60" />
          <div className="w-3 h-3 rounded-full bg-emerald-400/60" />
          <span className="ml-2 text-[10px] font-mono text-white/20">atlas-eval-terminal</span>
        </div>
        <div className="p-4 overflow-auto max-h-72 space-y-0.5 font-mono text-[11px] leading-relaxed scrollbar-thin scrollbar-thumb-white/5">
          {evaluation.logs.map((line, i) => (
            <div key={i} className={colorize(line)}>
              <span className="text-white/20 mr-3 select-none">{String(i + 1).padStart(3, '0')}</span>
              {line}
            </div>
          ))}
          <div ref={endRef} />
        </div>
      </div>
    </div>
  );
};

export default LogsSection;
