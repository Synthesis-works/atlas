/**
 * ChartSkeleton — Shimmer loader preserving visual layout
 */

import React from 'react';

export const ChartSkeleton: React.FC<{ height?: number | string }> = ({ height = 200 }) => {
  return (
    <div
      className="w-full rounded-xl bg-white/[0.03] animate-pulse flex items-center justify-center p-6 border border-white/[0.05]"
      style={{ height }}
    >
      <div className="w-full space-y-4">
        <div className="h-4 w-1/3 bg-white/10 rounded" />
        <div className="h-32 w-full bg-white/5 rounded-lg" />
        <div className="flex gap-4 justify-between">
          <div className="h-3 w-16 bg-white/10 rounded" />
          <div className="h-3 w-16 bg-white/10 rounded" />
          <div className="h-3 w-16 bg-white/10 rounded" />
        </div>
      </div>
    </div>
  );
};
