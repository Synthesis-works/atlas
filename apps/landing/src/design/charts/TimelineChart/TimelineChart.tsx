/**
 * TimelineChart — Lifecycle Event & Execution Timeline Visualization
 */

import React from 'react';
import { ChartContainer, ChartHeader } from '../common';
import { ChartPalette } from '../palette';

export interface TimelineStage {
  label: string;
  status: 'completed' | 'active' | 'queued' | 'error';
  timestamp?: string;
  duration?: string;
}

export interface TimelineChartProps {
  title?: string;
  stages: TimelineStage[];
}

export const TimelineChart: React.FC<TimelineChartProps> = ({
  title = 'Execution Lifecycle Timeline',
  stages,
}) => {
  return (
    <ChartContainer className="!rounded-lg !p-5">
      {title && <ChartHeader title={title} />}
      <div className="w-full pt-3 pb-1 font-mono text-xs overflow-x-auto">
        <div className="relative flex items-center justify-between min-w-[560px]">
          {/* Connecting Track Line */}
          <div className="absolute top-4 inset-x-4 h-0.5 bg-white/10 z-0" />

          {stages.map((stage) => {
            const isCompleted = stage.status === 'completed';
            const isActive = stage.status === 'active';
            const isError = stage.status === 'error';

            const dotColor = isError
              ? ChartPalette.danger
              : isCompleted
              ? ChartPalette.success
              : isActive
              ? ChartPalette.accent
              : 'rgba(255,255,255,0.2)';

            return (
              <div key={stage.label} className="relative z-10 flex flex-col items-center gap-1.5">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center border transition-all duration-300 ${
                    isActive ? 'ring-4 ring-accent/20 scale-110' : ''
                  }`}
                  style={{
                    backgroundColor: isActive ? 'rgba(99,102,241,0.2)' : '#111113',
                    borderColor: dotColor,
                  }}
                >
                  <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: dotColor }} />
                </div>
                <div className="text-center space-y-0.5">
                  <p className="text-[11px] font-semibold text-white">{stage.label}</p>
                  {stage.duration && (
                    <p className="text-[9px] text-white/40">{stage.duration}</p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </ChartContainer>
  );
};
