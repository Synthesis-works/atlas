import React from 'react';

export const ChartSkeleton: React.FC = () => {
  return (
    <div className="p-5 rounded-2xl border border-white/5 bg-black/40 h-48 flex flex-col justify-between animate-pulse">
      <div className="w-28 h-4 rounded bg-white/10" />
      <div className="w-full h-24 rounded bg-white/5" />
      <div className="w-36 h-3 rounded bg-white/5" />
    </div>
  );
};

export default ChartSkeleton;
