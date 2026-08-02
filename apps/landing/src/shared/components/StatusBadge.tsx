import React from 'react';
import { cn } from '@/lib/utils';
import { BENCHMARK_STATUS_MAP } from '@/domain/benchmarks/constants';
import type { BenchmarkStatus } from '@/domain/benchmarks/types';

interface StatusBadgeProps {
  status: BenchmarkStatus | string;
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, className }) => {
  const meta = BENCHMARK_STATUS_MAP[status as BenchmarkStatus] || {
    label: status,
    badgeClass: 'bg-white/5 text-white/40 border-white/10',
    dotClass: 'bg-white/30',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-medium border select-none',
        meta.badgeClass,
        className
      )}
    >
      <span className={cn('w-1.5 h-1.5 rounded-full', meta.dotClass)} />
      {meta.label}
    </span>
  );
};

export default StatusBadge;
