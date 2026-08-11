import React from 'react';
import { cn } from '@/lib/utils';

export interface TimelineItem {
  id: string;
  title: string;
  subtitle?: string;
  timestamp?: string;
  description?: string;
  active?: boolean;
}

interface TimelineProps {
  items: TimelineItem[];
  className?: string;
}

export const Timeline: React.FC<TimelineProps> = ({ items, className }) => {
  return (
    <div className={cn('space-y-4 relative before:absolute before:inset-0 before:left-3 before:w-0.5 before:bg-white/10', className)}>
      {items.map((item) => (
        <div key={item.id} className="relative flex items-start gap-4 pl-8 group">
          {/* Node Dot */}
          <div
            className={cn(
              'absolute left-1.5 top-1 w-3 h-3 rounded-full border-2 border-neutral-950 transition-colors',
              item.active
                ? 'bg-accent border-accent ring-4 ring-accent/20'
                : 'bg-white/20 group-hover:bg-white/40'
            )}
          />

          <div className="flex-1 bg-white/[0.02] border border-white/5 rounded-xl p-3.5 hover:border-white/10 transition-colors">
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs font-semibold text-white">{item.title}</span>
              {item.timestamp && (
                <span className="text-[10px] font-mono text-white/30">{item.timestamp}</span>
              )}
            </div>
            {item.subtitle && <p className="text-xs text-accent/70 mt-0.5 font-mono">{item.subtitle}</p>}
            {item.description && (
              <p className="text-xs text-white/40 mt-1 leading-relaxed">{item.description}</p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
};

export default Timeline;
