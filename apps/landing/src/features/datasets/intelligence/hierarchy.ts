import type { AtlasInsight } from '@/domain/intelligence/types';

export const computeHierarchyInsight = (): AtlasInsight => {
  return {
    id: 'hierarchy_overview',
    title: 'Dataset Relationships',
    description: 'Explore how datasets connect to models, benchmarks and evaluations.',
    priority: 'info',
    confidence: 100,
    source: 'computed',
    primaryKpi: {
      value: '12',
      label: 'Root Datasets'
    },
    secondaryKpi: {
      value: '84',
      label: 'Evaluations'
    },
    insight: 'COCO is linked to 12 active models.',
    recommendations: [
      { priority: 1, text: 'Open Dependency Graph' }
    ],
    metadata: [
      { label: 'Data Source', value: 'Atlas Graph API' },
      { label: 'Last Updated', value: 'Live' }
    ],
    legend: [
      { color: '#3B82F6', label: 'Datasets', value: '12', percentage: '20%' },
      { color: '#EAB308', label: 'Models', value: '34', percentage: '30%' },
      { color: '#EF4444', label: 'Benchmarks', value: '18', percentage: '15%' }
    ]
  };
};
