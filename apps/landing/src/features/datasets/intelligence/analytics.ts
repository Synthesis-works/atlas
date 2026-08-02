import type { AtlasInsight } from '@/domain/intelligence/types';
import { selectDatasetTypes } from '../selectors/analytics';

export const computeTypeDistributionInsight = (): AtlasInsight => {
  const types = selectDatasetTypes();
  const total = types.reduce((sum, t) => sum + t.value, 0);
  
  return {
    id: 'analytics_distribution',
    title: 'Modality Distribution',
    description: 'Breakdown of datasets by primary modality.',
    priority: 'info',
    confidence: 100,
    source: 'rule',
    primaryKpi: {
      value: total.toString(),
      label: 'Total Datasets'
    },
    secondaryKpi: {
      value: types.find(t => t.id === 'image')?.value.toString() || '0',
      label: 'Image Datasets',
      trend: 'Dominant'
    },
    insight: 'Provider adoption increasing for vision models. Text datasets are limited.',
    recommendations: [
      { priority: 2, text: 'Review Kaggle synchronization for NLP' }
    ],
    metadata: [
      { label: 'Data Source', value: 'Registry' },
      { label: 'Last Updated', value: 'Live' }
    ],
    legend: types.map(t => ({
      color: t.id === 'image' ? '#3B82F6' : t.id === 'video' ? '#8B5CF6' : '#10B981',
      label: t.label,
      value: t.value.toString(),
      percentage: `${((t.value / total) * 100).toFixed(0)}%`
    }))
  };
};
