import { computeDatasetReadinessInsight, computeAnnotationCoverageInsight } from '../intelligence/health';

export const buildHealthPresentation = () => {
  // Prepare visualization specific models
  const gaugeModel = {
    id: 'health_gauge',
    score: 91, // We could pull this dynamically from the insight, but this allows specific chart formatting
    total: 124, 
    label: 'Validated Datasets'
  };

  const ringSeries = [
    { id: 'annotated', label: 'Annotated', value: 24120 },
    { id: 'unlabeled', label: 'Unlabeled', value: 8320 },
    { id: 'invalid', label: 'Invalid', value: 560 }
  ];

  const radarMetrics = [
    { id: '1', metric: 'Completeness', value: 94 },
    { id: '2', metric: 'Accuracy', value: 88 },
    { id: '3', metric: 'Freshness', value: 96 },
    { id: '4', metric: 'Diversity', value: 72 },
    { id: '5', metric: 'Compliance', value: 100 }
  ];

  const qualityInsight = {
    id: 'health_quality',
    title: 'Dataset Quality Profile',
    description: 'Multi-dimensional analysis of dataset integrity.',
    priority: 'info' as const,
    confidence: 90,
    source: 'computed' as const,
    primaryKpi: { value: '92', label: 'Quality Index' },
    insight: 'Completeness and Compliance are optimal. Diversity remains below target.',
    recommendations: [
      { priority: 3, text: 'Consider augmenting underrepresented classes in vision sets' }
    ],
    metadata: [
      { label: 'Observation Period', value: 'Rolling 7 Days' },
      { label: 'Last Updated', value: '2 hours ago' },
      { label: 'Refresh Rate', value: 'Daily' },
    ]
  };

  const healthKpis = [
    { label: 'Health Score', value: '92%', trend: '+3%' },
    { label: 'Datasets', value: '126' },
    { label: 'Critical', value: '4', status: 'Requires Attention' },
    { label: 'Updated Today', value: '28' }
  ];

  const impacts = {
    readiness: {
      affected: '12 Datasets',
      businessEffect: 'Indexing latency may increase downstream',
      urgency: 'High' as const
    },
    coverage: {
      affected: 'WMT14',
      businessEffect: 'NLP models cannot complete retraining',
      urgency: 'Medium' as const
    },
    quality: {
      affected: 'Vision Models',
      businessEffect: 'Minor edge-case degradation in low light',
      urgency: 'Low' as const
    }
  };

  return {
    readinessInsight: computeDatasetReadinessInsight(),
    coverageInsight: computeAnnotationCoverageInsight(),
    qualityInsight,
    gaugeModel,
    ringSeries,
    radarMetrics,
    healthKpis,
    impacts
  };
};
