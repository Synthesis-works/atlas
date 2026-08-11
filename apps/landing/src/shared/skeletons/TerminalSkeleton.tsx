import React from 'react';

export const TerminalSkeleton: React.FC = () => {
  return (
    <div className="rounded-xl border border-white/10 bg-neutral-950 p-4 h-44 space-y-2 animate-pulse">
      <div className="w-32 h-3 rounded bg-white/10 mb-4" />
      <div className="w-3/4 h-3 rounded bg-white/5" />
      <div className="w-1/2 h-3 rounded bg-white/5" />
      <div className="w-5/6 h-3 rounded bg-white/5" />
    </div>
  );
};

export default TerminalSkeleton;
