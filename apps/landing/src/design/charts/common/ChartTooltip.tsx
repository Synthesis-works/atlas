/**
 * ChartTooltip & ChartLegend — Liquid Glass tooltips and legend controls.
 */

import React from 'react';
import { cn } from '@/lib/utils';
import type { LegendItem, TooltipData } from '../types';

export const ChartTooltip: React.FC<{
  data: TooltipData | null;
  className?: string;
}> = ({ data, className }) => {
  if (!data || !data.items || data.items.length === 0) return null;

  return (
    <div
      className={cn(
        'pointer-events-none absolute z-50 rounded-xl p-3 backdrop-blur-md bg-ink-3/90 border border-white/15 shadow-2xl space-y-1.5 min-w-[120px]',
        className,
      )}
      style={{
        left: data.x ?? 12,
        top: data.y ?? 12,
        transform: 'translate(-50%, -100%) translateY(-8px)',
      }}
    >
      {data.title && <p className="text-[10px] font-mono text-white/40 mb-1">{data.title}</p>}
      {data.items.map((item, idx) => (
        <div key={idx} className="flex items-center justify-between gap-3 text-xs font-mono">
          <div className="flex items-center gap-1.5">
            {item.color && (
              <span className="w-2 h-2 rounded-full" style={{ backgroundColor: item.color }} />
            )}
            <span className="text-white/70">{item.label}</span>
          </div>
          <span className="text-white font-medium">{item.value}</span>
        </div>
      ))}
    </div>
  );
};

export interface ChartLegendProps {
  items: LegendItem[];
  hoveredIndex?: number | null;
  onHoverChange?: (index: number | null) => void;
  align?: 'left' | 'center' | 'right';
  gap?: number;
  children?: React.ReactNode;
  className?: string;
}

export const ChartLegend: React.FC<ChartLegendProps> = ({
  items,
  hoveredIndex,
  onHoverChange,
  align = 'center',
  className,
}) => {
  const justifyClass =
    align === 'left' ? 'justify-start' : align === 'right' ? 'justify-end' : 'justify-center';

  return (
    <div className={cn('flex flex-wrap items-center gap-4 mt-4 font-mono text-xs', justifyClass, className)}>
      {items.map((item, i) => {
        const isHovered = hoveredIndex === i;
        return (
          <div
            key={item.label}
            onMouseEnter={() => onHoverChange?.(i)}
            onMouseLeave={() => onHoverChange?.(null)}
            className={cn(
              'flex items-center gap-2 cursor-pointer transition-opacity duration-200',
              hoveredIndex !== null && !isHovered ? 'opacity-40' : 'opacity-100',
            )}
          >
            <span className="w-2.5 h-2.5 rounded-sm shrink-0" style={{ backgroundColor: item.color }} />
            <span className="text-white/70">{item.label}</span>
            <span className="text-white font-medium">{item.value}</span>
          </div>
        );
      })}
    </div>
  );
};
