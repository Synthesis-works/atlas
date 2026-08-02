import React from 'react';
import type { Benchmark } from '@/domain/benchmarks/types';
import { Timeline, type TimelineItem } from '@/shared/components';

interface Props {
  benchmark: Benchmark;
}

export const HistorySection: React.FC<Props> = ({ benchmark }) => {
  const timelineItems: TimelineItem[] = benchmark.versionsHistory.map((ver, idx) => ({
    id: ver.version,
    title: `Version ${ver.version}`,
    subtitle: `Hash: ${ver.hash}`,
    timestamp: ver.date,
    description: `${ver.description} — Authored by ${ver.author}`,
    active: idx === 0,
  }));

  return (
    <div className="space-y-3">
      <h4 className="text-xs font-semibold text-white">Immutable Version History</h4>
      <Timeline items={timelineItems} />
    </div>
  );
};

export default HistorySection;
