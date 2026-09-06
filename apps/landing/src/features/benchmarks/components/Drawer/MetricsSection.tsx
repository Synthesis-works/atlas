import React from 'react';
import type { Benchmark } from '@/domain/benchmarks/types';

interface Props {
  benchmark: Benchmark;
}

export const MetricsSection: React.FC<Props> = ({ benchmark }) => {
  const realMetrics = [
    {
      id: 'avg_score',
      name: 'Average Score',
      value:
        benchmark.averageScore != null
          ? `${(benchmark.averageScore * 100).toFixed(1)}%`
          : '—',
      description: 'Historical average verification accuracy across all executions',
    },
    {
      id: 'latest_score',
      name: 'Latest Score',
      value:
        benchmark.latestScore != null
          ? `${(benchmark.latestScore * 100).toFixed(1)}%`
          : '—',
      description: 'Score from the most recent completed evaluation run',
    },
    {
      id: 'avg_latency',
      name: 'Average Latency',
      value:
        benchmark.averageLatencyMs != null
          ? `${Math.round(benchmark.averageLatencyMs)}ms`
          : '—',
      description: 'Mean model response duration per evaluation case',
    },
    {
      id: 'executions',
      name: 'Executions',
      value: `${benchmark.completedExecutionCount ?? 0} / ${benchmark.executionCount ?? 0}`,
      description: 'Completed vs total dispatched benchmark execution runs',
    },
    {
      id: 'eval_cases',
      name: 'Evaluation Cases',
      value:
        benchmark.evaluationCaseCount != null
          ? benchmark.evaluationCaseCount.toString()
          : '—',
      description: 'Number of active test cases in the primary dataset version',
    },
    {
      id: 'eval_results',
      name: 'Evaluations Passed',
      value: `${benchmark.passedEvaluationCount ?? 0} / ${benchmark.evaluationCount ?? 0}`,
      description: 'Passed evaluation case results over total evaluated cases',
    },
  ];

  return (
    <div className="space-y-3">
      <h4 className="text-xs font-semibold text-white">Evaluation Metrics Overview</h4>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
        {realMetrics.map((metric) => (
          <div
            key={metric.id}
            className="p-3 rounded-xl border border-white/5 bg-black/40 space-y-1 hover:border-white/10 transition-colors"
          >
            <div className="text-[10px] uppercase font-mono tracking-wider text-white/40 truncate">
              {metric.name}
            </div>
            <div className="text-base font-bold text-white font-mono flex items-baseline gap-1">
              {metric.value}
            </div>
            <div className="text-[10px] font-mono text-white/30 truncate" title={metric.description}>
              {metric.description}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default MetricsSection;
