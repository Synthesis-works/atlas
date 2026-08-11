import type { AtlasInsight } from '@/domain/intelligence/types';
import { selectStorageMetrics } from '../selectors/storage';

export const computeStorageCapacityInsight = (): AtlasInsight => {
  const metrics = selectStorageMetrics();
  
  return {
    id: 'storage_capacity',
    title: 'Storage Consumption',
    description: 'Current dataset volume footprint across standard and archive tiers.',
    priority: 'warning',
    confidence: 99,
    source: 'computed',
    primaryKpi: {
      value: `${metrics.totalTb.toFixed(1)} TB`,
      label: 'Total Storage'
    },
    secondaryKpi: {
      value: '68%',
      label: 'Capacity Used',
      trend: '↑ 2.1 TB/mo'
    },
    insight: 'ImageNet-1K is consuming 68% of the total storage capacity.',
    recommendations: [
      { priority: 1, text: 'Archive Legacy NLP v1 to Cold Storage' }
    ],
    metadata: [
      { label: 'Observation Period', value: 'Current Month' },
      { label: 'Data Source', value: 'Blob Storage Metrics' }
    ]
  };
};
