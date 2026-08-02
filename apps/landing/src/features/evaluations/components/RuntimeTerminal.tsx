import React, { useRef, useEffect, useState, useMemo } from 'react';

interface Props {
  logs: string[];
  paused: boolean;
  onPauseToggle: (p: boolean) => void;
}

const LEVEL_COLORS: Record<string, string> = {
  '[System]': 'text-blue-400 font-semibold',
  '[Queue]': 'text-indigo-400 font-semibold',
  '[Dataset]': 'text-purple-400 font-semibold',
  '[Model]': 'text-cyan-400 font-semibold',
  '[Executor]': 'text-teal-400 font-semibold',
  '[Progress]': 'text-emerald-400 font-semibold',
  '[Scoring]': 'text-amber-400 font-semibold',
  '[Report]': 'text-violet-400 font-semibold',
  '[Error]': 'text-rose-400 font-bold',
  '[Worker]': 'text-orange-400 font-semibold',
  '[Metrics]': 'text-yellow-400 font-semibold',
};

function getColor(line: string) {
  const key = Object.keys(LEVEL_COLORS).find(k => line.includes(k));
  return key ? LEVEL_COLORS[key] : 'text-neutral-200';
}

export const RuntimeTerminal: React.FC<Props> = ({ logs, paused, onPauseToggle }) => {
  const endRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearchOpen, setIsSearchOpen] = useState(false);

  const visibleLogs = useMemo(() => {
    const recent = logs.slice(-300); // show last 300 of 5000 for perf
    if (!searchQuery.trim()) return recent;
    const q = searchQuery.toLowerCase();
    return recent.filter(l => l.toLowerCase().includes(q));
  }, [logs, searchQuery]);

  const matchCount = useMemo(() => {
    if (!searchQuery.trim()) return 0;
    const q = searchQuery.toLowerCase();
    return logs.filter(l => l.toLowerCase().includes(q)).length;
  }, [logs, searchQuery]);

  useEffect(() => {
    if (!paused && !searchQuery) {
      endRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [visibleLogs, paused, searchQuery]);

  const handleDownload = () => {
    const blob = new Blob([logs.join('\n')], { type: 'text/plain' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `atlas-runtime-logs-${Date.now()}.txt`;
    a.click();
  };

  return (
    <div className="flex flex-col h-full bg-[#0a0a0e] border border-white/15 rounded-2xl overflow-hidden shadow-2xl">
      {/* Chrome bar */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-white/[0.04] border-b border-white/10 shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-rose-500" />
          <div className="w-2.5 h-2.5 rounded-full bg-amber-500" />
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
          <span className="ml-2 text-xs font-mono font-semibold text-neutral-300">atlas-runtime — worker-cluster</span>
          <div className="flex items-center gap-1.5 ml-3 px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-[10px] font-mono font-bold text-emerald-400">LIVE STREAM</span>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          {/* Search */}
          <button
            onClick={() => setIsSearchOpen(p => !p)}
            id="terminal-search-btn"
            className={`text-xs font-mono px-2.5 py-1 rounded border transition-colors cursor-pointer ${
              isSearchOpen ? 'border-white/30 text-white bg-white/15 font-semibold' : 'border-white/15 text-neutral-300 hover:text-white hover:bg-white/10'
            }`}
          >⌕ Search</button>
          {/* Pause */}
          <button
            onClick={() => onPauseToggle(!paused)}
            id="terminal-pause-btn"
            className={`text-xs font-mono px-2.5 py-1 rounded border transition-colors cursor-pointer ${
              paused ? 'border-amber-500/40 text-amber-300 bg-amber-500/15 font-semibold' : 'border-white/15 text-neutral-300 hover:text-white hover:bg-white/10'
            }`}
          >{paused ? '▶ Resume' : '⏸ Pause'}</button>
          {/* Download */}
          <button
            onClick={handleDownload}
            id="terminal-download-btn"
            className="text-xs font-mono px-2.5 py-1 rounded border border-white/15 text-neutral-300 hover:text-white hover:bg-white/10 transition-colors cursor-pointer"
          >⤓ Download</button>
        </div>
      </div>

      {/* Search bar */}
      {isSearchOpen && (
        <div className="flex items-center gap-2 px-4 py-2 bg-white/[0.03] border-b border-white/10">
          <input
            type="text"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder="Filter terminal output logs…"
            className="flex-1 bg-transparent text-xs font-mono text-white placeholder:text-neutral-400 focus:outline-none"
            autoFocus
          />
          {searchQuery && (
            <span className="text-xs font-mono text-neutral-300 font-semibold">{matchCount} matches</span>
          )}
          {searchQuery && (
            <button onClick={() => setSearchQuery('')} className="text-neutral-400 hover:text-white text-xs cursor-pointer">✕</button>
          )}
        </div>
      )}

      {/* Log lines */}
      <div
        ref={containerRef}
        className="flex-1 overflow-auto p-4 space-y-1 font-mono text-xs leading-relaxed scrollbar-thin scrollbar-thumb-white/10"
      >
        {visibleLogs.map((line, i) => (
          <div key={i} className={`flex items-start ${getColor(line)}`}>
            <span className="text-neutral-500 mr-3 select-none font-mono shrink-0 w-10 text-right">{String(i + 1).padStart(4, '0')}</span>
            <div className="flex-1 break-all">
              {searchQuery && line.toLowerCase().includes(searchQuery.toLowerCase()) ? (
                <>
                  {line.split(new RegExp(`(${searchQuery})`, 'gi')).map((part, pi) =>
                    part.toLowerCase() === searchQuery.toLowerCase()
                      ? <mark key={pi} className="bg-amber-400/40 text-amber-200 rounded px-1 font-bold">{part}</mark>
                      : <span key={pi}>{part}</span>
                  )}
                </>
              ) : line}
            </div>
          </div>
        ))}
        <div ref={endRef} />
      </div>

      {/* Footer */}
      <div className="shrink-0 flex items-center justify-between px-4 py-2 bg-white/[0.03] border-t border-white/10 text-xs font-mono text-neutral-300">
        <div className="flex items-center gap-3">
          <span className="font-semibold text-white">{logs.length.toLocaleString()} total lines</span>
          <span>·</span>
          <span>showing last 300</span>
          <span>·</span>
          <span>UTF-8</span>
        </div>
        <span className="font-semibold text-accent">Atlas Runtime Engine v2.4</span>
      </div>
    </div>
  );
};

export default RuntimeTerminal;
