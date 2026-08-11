import React from 'react';
import { cn } from '@/lib/utils';

interface ChartCardProps {
  title: string;
  subtitle?: string;
  badge?: string;
  children: React.ReactNode;
  className?: string;
}

export const ChartCard: React.FC<ChartCardProps> = ({
  title,
  subtitle,
  badge,
  children,
  className,
}) => {
  return (
    <div className={cn('p-5 rounded-2xl border border-white/5 bg-black/40 backdrop-blur-md flex flex-col justify-between', className)}>
      <div className="flex items-start justify-between mb-4">
        <div>
          <h4 className="text-xs font-semibold text-white tracking-tight">{title}</h4>
          {subtitle && <p className="text-[11px] text-white/30 mt-0.5">{subtitle}</p>}
        </div>
        {badge && (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-white/5 text-white/40 border border-white/5">
            {badge}
          </span>
        )}
      </div>
      <div className="flex-1 w-full flex items-center justify-center">{children}</div>
    </div>
  );
};

export default ChartCard;
