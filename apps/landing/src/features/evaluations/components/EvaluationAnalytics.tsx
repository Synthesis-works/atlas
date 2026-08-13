import React from 'react';
import type { EvaluationRun } from '@/domain/evaluations/types';
import {
  HeatmapCard,
  createHeatmapData,
} from '@/design/charts';
import { AtlasPieChart } from '@/components/atlas/charts';

interface Props {
  evaluations: EvaluationRun[];
}

const failureData = createHeatmapData(
  ['GPT-5', 'Claude 3.5', 'Gemini 2.0', 'Llama 3.3'],
  ['Timeout', 'GPU', 'Dataset', 'Prompt', 'API', 'Memory'],
  (m, f) => (m.charCodeAt(0) * f.charCodeAt(0)) % 12,
);

const evalComposition = [
  { label: 'Models', value: 3 },
  { label: 'Benchmarks', value: 3 },
  { label: 'Metrics', value: 3 },
];

export const EvaluationAnalytics: React.FC<Props> = () => {
  return (
    <div className="space-y-6 mb-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <HeatmapCard
          title="Failure & Error Matrix"
          subtitle="Identifies which model fails most frequently and the root exception source"
          badge="Realtime Log Audit"
          data={failureData}
        />

        <AtlasPieChart
          title="Evaluation Composition Explorer"
          description="Interactive hierarchy connecting Models → Benchmarks → Datasets → Metrics"
          data={evalComposition}
          size={240}
          innerRadius={70}
          centerLabel="9 Attributes"
          showLegend={true}
          hoverEffect="grow"
          className="liquid-glass-card rounded-2xl p-5 border border-white/10 w-full"
        />
      </div>
    </div>
  );
};

export default EvaluationAnalytics;
