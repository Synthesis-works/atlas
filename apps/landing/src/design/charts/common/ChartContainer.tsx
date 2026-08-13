/**
 * ChartContainer — Shared wrapper managing GlassSurface styling and chart states.
 * States: Loading | Empty | Ready | Error
 */

import React from 'react';
import { cn } from '@/lib/utils';
import { ChartSkeleton } from './ChartSkeleton';
import type { ChartState } from '../types';

interface ChartContainerProps {
  state?: ChartState;
  className?: string;
  children: React.ReactNode;
  height?: number | string;
}

export const ChartBody: React.FC<{ children: React.ReactNode; className?: string }> = ({
  children,
  className,
}) => (
  <div className={cn('flex-1 min-h-0 w-full relative flex flex-col justify-between', className)}>
    {children}
  </div>
);

export const ChartContainer: React.FC<ChartContainerProps> = ({
  state = 'ready',
  className,
  children,
  height,
}) => {
  const containerStyle = height ? { height } : undefined;

  if (state === 'loading') {
    return <ChartSkeleton height={height} />;
  }

  if (state === 'empty') {
    return (
      <div
        className={cn(
          'liquid-glass-card rounded-lg p-4 sm:p-5 flex flex-col items-center justify-center text-center border border-white/[0.08]',
          className,
        )}
        style={containerStyle}
      >
        <p className="text-xs font-mono text-white/30">No data points available</p>
      </div>
    );
  }

  if (state === 'error') {
    return (
      <div
        className={cn(
          'liquid-glass-card rounded-lg p-4 sm:p-5 flex flex-col items-center justify-center text-center border border-red-500/20 bg-red-500/5',
          className,
        )}
        style={containerStyle}
      >
        <p className="text-xs font-mono text-red-400">Failed to render visualization</p>
      </div>
    );
  }

  return (
    <div
      className={cn(
        'liquid-glass-card rounded-lg p-4 sm:p-5 flex flex-col border border-white/[0.08] relative overflow-hidden h-full w-full min-h-0',
        className,
      )}
      style={containerStyle}
    >
      {children}
    </div>
  );
};
